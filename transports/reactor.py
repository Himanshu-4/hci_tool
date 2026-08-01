"""
Event-driven I/O engine for the transport layer.

Design goal: **interrupt-style I/O with no polling**. The I/O thread must sit
parked in a kernel wait until the device actually has something to say, and cost
zero CPU while it waits. No `while True: if in_waiting: ... time.sleep(0.01)`.

Two backends, one interface:

`SelectorReactor` (POSIX -- macOS/Linux, the default)
    Parks in ``selectors.select()`` with **no timeout**, i.e. kqueue on macOS and
    epoll on Linux. The thread is descheduled entirely until the kernel marks the
    serial fd readable. This is as close to "interrupt driven" as userspace gets:
    the UART driver's receive interrupt is what ultimately makes the fd ready and
    wakes this thread.

`BlockingReactor` (Windows, or any fd that cannot be selected on)
    `selectors` on Windows only accepts sockets, so a serial handle cannot be
    registered. Instead a reader thread blocks in ``read(1)`` with no timeout.
    pyserial's Windows backend implements that with overlapped I/O plus
    ``WaitForSingleObject``, so the thread is likewise blocked in the kernel at
    zero CPU. A second small thread drains the TX queue.

Both wake on a **self-pipe** (POSIX) or an ``Event`` (Windows) so that
``submit()`` and ``stop()`` take effect immediately instead of at the end of some
timeout. Nothing in here spins, and nothing sleeps on a timer.

Write readiness is registered *only while there is data queued*. Registering
EVENT_WRITE permanently against a level-triggered selector would busy-spin at
100% CPU, since a serial fd is almost always writable -- that is the classic
mistake this class exists to avoid.
"""

from __future__ import annotations

import errno
import os
import threading
from abc import ABC, abstractmethod
from collections import deque
from typing import Callable, Deque, Optional

try:
    import selectors

    _HAVE_SELECTORS = True
except ImportError:  # pragma: no cover - stdlib, always present
    _HAVE_SELECTORS = False


OnData = Callable[[bytes], None]
OnError = Callable[[BaseException], None]
OnClosed = Callable[[], None]


class ReactorError(Exception):
    """Raised for reactor lifecycle misuse (start twice, submit when stopped)."""


class IoReactor(ABC):
    """
    Common surface for the I/O engines.

    Callbacks fire on the reactor's own thread. Keep them short, and marshal to
    the UI thread yourself (see `transports.qt_bridge`).
    """

    #: Refuse to queue more than this many bytes of unwritten TX data.
    DEFAULT_MAX_TX_QUEUE = 1 << 20  # 1 MiB

    def __init__(
        self,
        name: str,
        on_data: OnData,
        on_error: Optional[OnError] = None,
        on_closed: Optional[OnClosed] = None,
        max_tx_queue: int = DEFAULT_MAX_TX_QUEUE,
    ):
        self.name = name
        self._on_data = on_data
        self._on_error = on_error
        self._on_closed = on_closed
        self._max_tx_queue = max_tx_queue

        self._thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()
        self._running = threading.Event()

        self._tx_lock = threading.Lock()
        self._tx_queue: Deque[bytes] = deque()
        self._tx_bytes = 0
        self._tx_partial = b""

        # Counters. Read without a lock -- they are advisory.
        self._bytes_rx = 0
        self._bytes_tx = 0
        self._wakeups = 0

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise ReactorError(f"reactor '{self.name}' already running")

        self._stopping.clear()
        self._open()
        self._thread = threading.Thread(
            target=self._thread_main, name=f"io-{self.name}", daemon=True
        )
        self._thread.start()
        # Don't return until the loop is actually armed, so a submit() that
        # immediately follows start() cannot be lost.
        self._running.wait(timeout=2.0)

    def stop(self, timeout: float = 2.0) -> None:
        if self._thread is None:
            return
        self._stopping.set()
        self._wake()
        self._thread.join(timeout=timeout)
        self._thread = None
        self._running.clear()
        self._close()
        with self._tx_lock:
            self._tx_queue.clear()
            self._tx_bytes = 0
            self._tx_partial = b""

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------ TX

    def submit(self, data: bytes) -> int:
        """
        Queue bytes for transmission. Thread-safe, never blocks on the device.

        Returns the number of bytes accepted. Raises ReactorError if the queue is
        full -- silently dropping a command would be far worse than a loud error.
        """
        if not data:
            return 0
        if not self.is_running:
            raise ReactorError(f"reactor '{self.name}' is not running")

        with self._tx_lock:
            if self._tx_bytes + len(data) > self._max_tx_queue:
                raise ReactorError(
                    f"TX queue full for '{self.name}': "
                    f"{self._tx_bytes} queued, refusing {len(data)} more"
                )
            self._tx_queue.append(bytes(data))
            self._tx_bytes += len(data)

        self._wake()
        return len(data)

    @property
    def tx_pending(self) -> int:
        with self._tx_lock:
            return self._tx_bytes + len(self._tx_partial)

    def _next_tx_chunk(self) -> Optional[bytes]:
        """Take the next pending chunk, or None if the queue is empty."""
        with self._tx_lock:
            if self._tx_partial:
                chunk, self._tx_partial = self._tx_partial, b""
                return chunk
            if self._tx_queue:
                chunk = self._tx_queue.popleft()
                self._tx_bytes -= len(chunk)
                return chunk
        return None

    def _return_tx_remainder(self, remainder: bytes) -> None:
        """Push back the tail of a short write."""
        if remainder:
            with self._tx_lock:
                self._tx_partial = remainder + self._tx_partial

    def _has_tx_work(self) -> bool:
        with self._tx_lock:
            return bool(self._tx_partial or self._tx_queue)

    # ------------------------------------------------------------ reporting

    def stats(self) -> dict:
        return {
            "name": self.name,
            "backend": type(self).__name__,
            "running": self.is_running,
            "bytes_rx": self._bytes_rx,
            "bytes_tx": self._bytes_tx,
            "tx_pending": self.tx_pending,
            "wakeups": self._wakeups,
        }

    # ------------------------------------------------------------- internals

    def _emit_data(self, data: bytes) -> None:
        self._bytes_rx += len(data)
        try:
            self._on_data(data)
        except Exception as exc:  # a bad consumer must not kill the link
            self._report(exc)

    def _report(self, exc: BaseException) -> None:
        if self._on_error is not None:
            try:
                self._on_error(exc)
            except Exception:
                pass

    def _thread_main(self) -> None:
        try:
            self._running.set()
            self._loop()
        except Exception as exc:
            self._report(exc)
        finally:
            self._running.clear()
            if self._on_closed is not None:
                try:
                    self._on_closed()
                except Exception:
                    pass

    # Backend hooks.
    def _open(self) -> None:  # pragma: no cover - trivial default
        pass

    def _close(self) -> None:  # pragma: no cover - trivial default
        pass

    @abstractmethod
    def _loop(self) -> None:
        """Run until `self._stopping` is set."""

    @abstractmethod
    def _wake(self) -> None:
        """Nudge the loop out of its kernel wait. Must be thread-safe."""


class SelectorReactor(IoReactor):
    """
    Readiness-based reactor for POSIX file descriptors (the normal path).

    Blocks in ``selectors.select()`` with no timeout. Woken by the device fd
    becoming ready, or by a byte on the internal self-pipe.
    """

    #: Bytes to pull per readable event.
    READ_CHUNK = 4096

    def __init__(
        self,
        name: str,
        fd: int,
        on_data: OnData,
        on_error: Optional[OnError] = None,
        on_closed: Optional[OnClosed] = None,
        max_tx_queue: int = IoReactor.DEFAULT_MAX_TX_QUEUE,
    ):
        super().__init__(name, on_data, on_error, on_closed, max_tx_queue)
        if not _HAVE_SELECTORS:  # pragma: no cover
            raise ReactorError("selectors module unavailable")
        self._fd = fd
        self._sel: Optional[selectors.BaseSelector] = None
        self._wake_r = -1
        self._wake_w = -1
        self._wake_pending = False
        self._wake_lock = threading.Lock()
        self._interest = 0

    def _open(self) -> None:
        self._wake_r, self._wake_w = os.pipe()
        os.set_blocking(self._wake_r, False)
        os.set_blocking(self._wake_w, False)

        self._sel = selectors.DefaultSelector()
        self._sel.register(self._wake_r, selectors.EVENT_READ, "wake")
        self._interest = selectors.EVENT_READ
        self._sel.register(self._fd, self._interest, "dev")

    def _close(self) -> None:
        if self._sel is not None:
            try:
                self._sel.unregister(self._fd)
            except (KeyError, ValueError, OSError):
                pass
            try:
                self._sel.unregister(self._wake_r)
            except (KeyError, ValueError, OSError):
                pass
            self._sel.close()
            self._sel = None

        for fd_attr in ("_wake_r", "_wake_w"):
            fd = getattr(self, fd_attr)
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_attr, -1)

    def _wake(self) -> None:
        # Coalesce: one pending byte is enough to guarantee a wakeup, and it
        # keeps a burst of submit() calls from ever filling the pipe.
        with self._wake_lock:
            if self._wake_pending or self._wake_w < 0:
                return
            self._wake_pending = True
        try:
            os.write(self._wake_w, b"\x01")
        except (BlockingIOError, OSError):
            with self._wake_lock:
                self._wake_pending = False

    def _drain_wake(self) -> None:
        try:
            while True:
                if not os.read(self._wake_r, 4096):
                    break
        except (BlockingIOError, OSError):
            pass
        finally:
            with self._wake_lock:
                self._wake_pending = False
        self._wakeups += 1

    def _sync_interest(self) -> None:
        """
        Register for write readiness only while TX data is queued.

        Leaving EVENT_WRITE armed against a level-triggered selector spins the
        CPU, because the fd is writable virtually always.
        """
        wanted = selectors.EVENT_READ
        if self._has_tx_work():
            wanted |= selectors.EVENT_WRITE
        if wanted != self._interest and self._sel is not None:
            self._sel.modify(self._fd, wanted, "dev")
            self._interest = wanted

    def _loop(self) -> None:
        assert self._sel is not None
        while not self._stopping.is_set():
            self._sync_interest()

            events = self._sel.select()  # no timeout: parks until something happens

            for key, mask in events:
                if key.data == "wake":
                    self._drain_wake()
                    continue

                if mask & selectors.EVENT_READ:
                    if not self._do_read():
                        return  # device closed / fatal
                if mask & selectors.EVENT_WRITE:
                    self._do_write()

        # Best-effort flush of anything still queued at shutdown.
        deadline_writes = 64
        while self._has_tx_work() and deadline_writes > 0:
            if not self._do_write():
                break
            deadline_writes -= 1

    def _do_read(self) -> bool:
        """Returns False if the device is gone."""
        try:
            data = os.read(self._fd, self.READ_CHUNK)
        except BlockingIOError:
            return True
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                return True
            self._report(exc)
            return False

        if not data:
            # EOF: the USB serial adapter was unplugged, or the peer closed.
            self._report(ConnectionResetError(f"'{self.name}': device closed the link"))
            return False

        self._emit_data(data)
        return True

    def _do_write(self) -> bool:
        chunk = self._next_tx_chunk()
        if chunk is None:
            return True
        try:
            written = os.write(self._fd, chunk)
        except BlockingIOError:
            self._return_tx_remainder(chunk)
            return True
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                self._return_tx_remainder(chunk)
                return True
            self._return_tx_remainder(chunk)
            self._report(exc)
            return False

        self._bytes_tx += written
        if written < len(chunk):
            self._return_tx_remainder(chunk[written:])
        return True


class BlockingReactor(IoReactor):
    """
    Fallback reactor for platforms where the device fd cannot be selected on
    (Windows serial handles, most notably).

    The reader thread blocks inside ``read_fn`` with no timeout, so it consumes
    no CPU while idle -- pyserial's Windows backend waits on an OS event object
    there. A second thread drains the TX queue, waking on an ``Event`` rather
    than a timer.

    ``read_fn`` must block until at least one byte is available and return b""
    only on close.
    """

    def __init__(
        self,
        name: str,
        read_fn: Callable[[], bytes],
        write_fn: Callable[[bytes], int],
        on_data: OnData,
        on_error: Optional[OnError] = None,
        on_closed: Optional[OnClosed] = None,
        cancel_fn: Optional[Callable[[], None]] = None,
        max_tx_queue: int = IoReactor.DEFAULT_MAX_TX_QUEUE,
    ):
        super().__init__(name, on_data, on_error, on_closed, max_tx_queue)
        self._read_fn = read_fn
        self._write_fn = write_fn
        self._cancel_fn = cancel_fn
        self._tx_event = threading.Event()
        self._tx_thread: Optional[threading.Thread] = None

    def _open(self) -> None:
        self._tx_event.clear()
        self._tx_thread = threading.Thread(
            target=self._tx_main, name=f"io-{self.name}-tx", daemon=True
        )

    def _close(self) -> None:
        tx = self._tx_thread
        if tx is not None and tx.is_alive():
            self._tx_event.set()
            tx.join(timeout=1.0)
        self._tx_thread = None

    def _wake(self) -> None:
        self._tx_event.set()
        if self._stopping.is_set() and self._cancel_fn is not None:
            # Break the reader out of its blocking read so stop() is prompt.
            try:
                self._cancel_fn()
            except Exception:
                pass

    def _loop(self) -> None:
        if self._tx_thread is not None:
            self._tx_thread.start()

        while not self._stopping.is_set():
            try:
                data = self._read_fn()
            except OSError as exc:
                if not self._stopping.is_set():
                    self._report(exc)
                return
            except Exception as exc:
                if not self._stopping.is_set():
                    self._report(exc)
                return

            if data:
                self._emit_data(data)
            elif self._stopping.is_set():
                return

    def _tx_main(self) -> None:
        while not self._stopping.is_set():
            self._tx_event.wait()
            self._tx_event.clear()
            while True:
                chunk = self._next_tx_chunk()
                if chunk is None:
                    break
                try:
                    written = self._write_fn(chunk)
                except Exception as exc:
                    self._return_tx_remainder(chunk)
                    if not self._stopping.is_set():
                        self._report(exc)
                    return
                self._bytes_tx += written or 0
                if written is not None and written < len(chunk):
                    self._return_tx_remainder(chunk[written:])


def supports_selector_io(fileobj) -> bool:
    """
    True when `fileobj` exposes a descriptor this platform can select on.

    On Windows `selectors` handles sockets only, so serial ports fall back to
    the blocking reactor.
    """
    if not _HAVE_SELECTORS or os.name != "posix":
        return False
    try:
        fd = fileobj.fileno()
    except (AttributeError, OSError, ValueError):
        return False
    return isinstance(fd, int) and fd >= 0


__all__ = [
    "IoReactor",
    "SelectorReactor",
    "BlockingReactor",
    "ReactorError",
    "supports_selector_io",
]
