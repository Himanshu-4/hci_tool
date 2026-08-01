"""
UART (H4) sub-transport.

A complete implementation of the HCI UART transport on top of pyserial:

  * **Interrupt-style receive.** The RX engine is `transports.reactor`, which
    parks in a kernel wait (kqueue/epoll on POSIX, overlapped I/O on Windows)
    and is woken by the driver when bytes actually arrive. There is no polling
    loop and no `sleep()` anywhere in the data path -- an idle link costs zero
    CPU.
  * **Proper H4 framing.** Received bytes go through `transports.h4.H4Framer`, so
    subscribers get whole packets of every type (event, ACL, SCO, ISO), not just
    events, and partial/coalesced reads are handled.
  * **Non-blocking transmit.** `write()` queues into the reactor and returns; the
    I/O thread drains it when the port reports writable.
  * **Hardware flow control** (RTS/CTS) is supported and recommended -- most
    controllers need it above 115200 baud.

Callbacks fire on the I/O thread; see `transports.base_lib` for the contract.
"""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import serial
import serial.tools.list_ports

from ..base_lib import (
    ConfigurationError,
    ConnectionError,
    TransportError,
    TransportEvent,
    TransportInterface,
    TransportState,
)
from ..h4 import H4Framer, H4Packet
from ..reactor import (
    BlockingReactor,
    IoReactor,
    ReactorError,
    SelectorReactor,
    supports_selector_io,
)

#: Baud rates worth offering in the UI. Non-standard values are still accepted --
#: plenty of controllers run at 3000000 or 921600 after a vendor baud change.
COMMON_BAUDRATES: Tuple[int, ...] = (
    9600, 19200, 38400, 57600, 115200, 230400, 460800,
    921600, 1000000, 1500000, 2000000, 3000000, 4000000,
)

_BYTESIZES = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
_PARITIES = {
    "N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD,
    "M": serial.PARITY_MARK, "S": serial.PARITY_SPACE,
}
_STOPBITS = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}


@dataclass
class UARTConfig:
    """Validated UART settings. Unknown keys are rejected at construction."""

    port: Optional[str] = None
    baudrate: int = 115200
    bytesize: int = serial.EIGHTBITS
    parity: str = serial.PARITY_NONE
    stopbits: float = serial.STOPBITS_ONE

    # Flow control. rtscts is the one that matters for HCI.
    rtscts: bool = False
    xonxoff: bool = False
    dsrdtr: bool = False

    # Modem lines asserted on open; some modules hold reset via DTR.
    rts: bool = True
    dtr: bool = True

    #: Cap on unwritten TX bytes before write() refuses (backpressure).
    max_tx_queue: int = 1 << 20
    #: Bytes requested per readable event.
    read_chunk: int = 4096

    _extras: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "UARTConfig":
        known = {f for f in cls.__dataclass_fields__ if not f.startswith("_")}
        kwargs = {k: v for k, v in config.items() if k in known}
        extras = {k: v for k, v in config.items() if k not in known}

        # Accept friendly forms: bytesize=8, parity="N"/"none", stopbits=1.
        if "bytesize" in kwargs:
            kwargs["bytesize"] = _BYTESIZES.get(kwargs["bytesize"], kwargs["bytesize"])
        if "parity" in kwargs and isinstance(kwargs["parity"], str):
            p = kwargs["parity"].upper()
            kwargs["parity"] = _PARITIES.get(p[:1], serial.PARITY_NONE)
        if "stopbits" in kwargs:
            kwargs["stopbits"] = _STOPBITS.get(kwargs["stopbits"], kwargs["stopbits"])

        cfg = cls(**kwargs)
        cfg._extras = extras
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not self.port:
            raise ConfigurationError("UART 'port' is required")
        if not isinstance(self.baudrate, int) or self.baudrate <= 0:
            raise ConfigurationError(f"Invalid baudrate: {self.baudrate!r}")
        if self.bytesize not in _BYTESIZES.values():
            raise ConfigurationError(f"Invalid bytesize: {self.bytesize!r}")
        if self.parity not in _PARITIES.values():
            raise ConfigurationError(f"Invalid parity: {self.parity!r}")
        if self.stopbits not in _STOPBITS.values():
            raise ConfigurationError(f"Invalid stopbits: {self.stopbits!r}")
        if self.xonxoff:
            # Software flow control mangles binary HCI: 0x11/0x13 appear inside
            # payloads constantly. Refusing here saves hours of debugging.
            raise ConfigurationError(
                "xonxoff (software flow control) cannot be used with HCI H4; "
                "use rtscts instead"
            )

    def to_dict(self) -> Dict[str, Any]:
        d = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        d.update(self._extras)
        return d


class UARTTransport(TransportInterface):
    """HCI-over-UART transport."""

    def __init__(self):
        super().__init__()
        self.config: Optional[UARTConfig] = None
        self._serial: Optional[serial.Serial] = None
        self._reactor: Optional[IoReactor] = None
        self._framer = H4Framer(on_error=self._on_framer_error)
        self._lock = threading.RLock()

    # ------------------------------------------------------------ discovery

    @staticmethod
    def list_ports() -> List[Tuple[str, str]]:
        """(device, description) for every serial port present."""
        return [(p.device, p.description or p.device)
                for p in serial.tools.list_ports.comports()]

    def get_available_ports(self) -> List[Tuple[str, str]]:
        return self.list_ports()

    # -------------------------------------------------------------- config

    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Validate and store settings.

        Deliberately does *not* check the port against the enumerated list: USB
        adapters come and go, and a stale enumeration should not stop a connect
        attempt. An unavailable port fails loudly at `connect()` instead.
        """
        try:
            self.config = UARTConfig.from_dict(config)
            return True
        except ConfigurationError:
            raise
        except Exception as exc:
            raise ConfigurationError(f"UART configuration error: {exc}") from exc

    # ----------------------------------------------------------- lifecycle

    def connect(self) -> bool:
        with self._lock:
            if self.is_connected():
                return True
            if self.config is None:
                raise ConnectionError("configure() must be called before connect()")

            self._set_status(TransportState.CONNECTING)
            try:
                self._serial = serial.Serial(
                    port=self.config.port,
                    baudrate=self.config.baudrate,
                    bytesize=self.config.bytesize,
                    parity=self.config.parity,
                    stopbits=self.config.stopbits,
                    rtscts=self.config.rtscts,
                    xonxoff=self.config.xonxoff,
                    dsrdtr=self.config.dsrdtr,
                    timeout=None,        # blocking reads; the reactor drives readiness
                    write_timeout=None,
                )
                if not self._serial.is_open:
                    self._serial.open()

                # Assert modem lines only when not delegated to the driver.
                # Not every device has them: PTYs and some USB-serial bridges
                # reject TIOCMBIS with EINVAL/ENOTTY. That is not a reason to
                # refuse the connection -- the data path works regardless.
                self._try_set_line("rts", self.config.rts, self.config.rtscts)
                self._try_set_line("dtr", self.config.dtr, self.config.dsrdtr)

                # Discard anything the controller emitted before we attached
                # (boot banners, a partial packet from a previous session).
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
                self._framer.reset()

                self._reactor = self._build_reactor()
                self._reactor.start()

            except (serial.SerialException, OSError, ReactorError) as exc:
                self._teardown()
                self._set_status(TransportState.ERROR)
                raise ConnectionError(f"UART connect failed: {exc}") from exc

            self._set_status(TransportState.CONNECTED)
            self._trigger_callbacks(TransportEvent.CONNECT, self)
            return True

    def disconnect(self) -> bool:
        with self._lock:
            if self._serial is None and self._reactor is None:
                self._set_status(TransportState.DISCONNECTED)
                return True

            self._set_status(TransportState.DISCONNECTING)
            self._teardown()
            self._set_status(TransportState.DISCONNECTED)
            self._trigger_callbacks(TransportEvent.DISCONNECT, self)
            return True

    def _teardown(self) -> None:
        if self._reactor is not None:
            try:
                self._reactor.stop()
            except Exception:
                pass
            self._reactor = None

        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except Exception:
                pass
            self._serial = None

        self._framer.reset()

    def _try_set_line(self, line: str, value: bool, delegated_to_driver: bool) -> None:
        """Best-effort modem-line assertion; a device without them is fine."""
        if delegated_to_driver or self._serial is None:
            return
        try:
            setattr(self._serial, line, value)
        except (OSError, serial.SerialException) as exc:
            print(f"[uart] {line.upper()} not settable on {self.config.port}: {exc}")

    def _build_reactor(self) -> IoReactor:
        """Pick the readiness backend the platform can actually support."""
        assert self._serial is not None and self.config is not None

        if supports_selector_io(self._serial):
            reactor = SelectorReactor(
                name=f"uart:{self.config.port}",
                fd=self._serial.fileno(),
                on_data=self._on_bytes,
                on_error=self._on_io_error,
                on_closed=self._on_io_closed,
                max_tx_queue=self.config.max_tx_queue,
            )
            reactor.READ_CHUNK = self.config.read_chunk
            return reactor

        return BlockingReactor(
            name=f"uart:{self.config.port}",
            read_fn=self._blocking_read,
            write_fn=self._blocking_write,
            on_data=self._on_bytes,
            on_error=self._on_io_error,
            on_closed=self._on_io_closed,
            cancel_fn=self._cancel_read,
            max_tx_queue=self.config.max_tx_queue,
        )

    # ------------------------------------------- blocking backend (Windows)

    def _blocking_read(self) -> bytes:
        """Block until at least one byte arrives, then drain what's buffered."""
        ser = self._serial
        if ser is None or not ser.is_open:
            return b""
        first = ser.read(1)          # blocks in the OS; timeout=None
        if not first:
            return b""
        extra = ser.in_waiting
        if extra:
            first += ser.read(extra)
        return first

    def _blocking_write(self, data: bytes) -> int:
        ser = self._serial
        if ser is None or not ser.is_open:
            raise ConnectionError("UART is not open")
        return ser.write(data) or 0

    def _cancel_read(self) -> None:
        ser = self._serial
        if ser is not None and ser.is_open:
            try:
                ser.cancel_read()
            except (AttributeError, OSError):
                pass

    # ------------------------------------------------------------- RX path

    def _on_bytes(self, chunk: bytes) -> None:
        """Reactor gave us raw bytes. Frame them and publish whole packets."""
        self._stats["bytes_rx"] += len(chunk)
        if self.callbacks[TransportEvent.RAW_RX]:
            self._trigger_callbacks(TransportEvent.RAW_RX, chunk)

        for packet in self._framer.feed(chunk):
            self._stats["packets_rx"] += 1
            self._trigger_callbacks(TransportEvent.READ, packet.raw)

    def _on_framer_error(self, message: str) -> None:
        self._stats["errors"] += 1
        print(f"[uart] {message}")

    def _on_io_error(self, exc: BaseException) -> None:
        self._stats["errors"] += 1
        self._trigger_callbacks(TransportEvent.ERROR, exc)

    def _on_io_closed(self) -> None:
        """
        The I/O thread exited. If that wasn't a requested disconnect, the cable
        was pulled -- surface it so the UI can drop back to a sane state.
        """
        if self._status in (TransportState.DISCONNECTING, TransportState.DISCONNECTED):
            return
        self._set_status(TransportState.ERROR)
        self._trigger_callbacks(TransportEvent.DISCONNECT, self)

    # ------------------------------------------------------------- TX path

    def write(self, data: bytes) -> bool:
        """Queue one complete HCI packet. Returns False if it could not be queued."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise ValueError("data must be bytes-like")
        data = bytes(data)
        if not data:
            return True

        reactor = self._reactor
        if reactor is None or not self.is_connected():
            raise TransportError("UART is not connected")

        try:
            reactor.submit(data)
        except ReactorError as exc:
            self._stats["errors"] += 1
            self._trigger_callbacks(TransportEvent.ERROR, exc)
            return False

        self._stats["packets_tx"] += 1
        self._stats["bytes_tx"] += len(data)
        if self.callbacks[TransportEvent.RAW_TX]:
            self._trigger_callbacks(TransportEvent.RAW_TX, data)
        self._trigger_callbacks(TransportEvent.WRITE, data)
        return True

    def read(self, size: int = -1) -> Optional[bytes]:
        """
        Not supported: this transport is push-based.

        Subscribe to `TransportEvent.READ` to receive framed packets.
        """
        raise TransportError(
            "UARTTransport is push-based; subscribe to TransportEvent.READ "
            "instead of calling read()"
        )

    # ------------------------------------------------------------ utilities

    def flush_input(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.reset_input_buffer()
        self._framer.reset()

    def flush_output(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.reset_output_buffer()

    def set_baudrate(self, baudrate: int) -> None:
        """Change baud on a live port (after a vendor baud-change command)."""
        if self._serial is None or not self._serial.is_open:
            raise TransportError("UART is not open")
        self._serial.baudrate = baudrate
        if self.config is not None:
            self.config.baudrate = baudrate

    def get_config(self) -> Dict[str, Any]:
        return self.config.to_dict() if self.config else {}

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        stats["framer"] = self._framer.stats.as_dict()
        if self._reactor is not None:
            stats["reactor"] = self._reactor.stats()
        return stats


__all__ = ["UARTTransport", "UARTConfig", "COMMON_BAUDRATES"]
