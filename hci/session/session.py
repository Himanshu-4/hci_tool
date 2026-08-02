"""
HciSession -- the host layer.

Sits between the transport (bytes) and the UI/procedures (intent). It is the
piece the tool never had, and without it multi-step flows like "connect to this
address" cannot be expressed at all.

Responsibilities, in order of how much trouble they save:

1. **Command flow control.** The controller tells you how many command packets
   it can accept via `Num_HCI_Command_Packets` in every Command Complete and
   Command Status. Exceeding it is the single most common way to wedge a
   controller -- it silently drops commands and the host waits forever. The
   session starts with one credit and never has more outstanding than allowed.

2. **Correlation.** Match each completion back to the command that caused it,
   by opcode, and fire that command's callback. Time out with a clear error
   rather than hanging.

3. **State.** Connection table, plus adv/scan/inquiry flags so callers can be
   stopped from issuing commands the controller would reject (LE_Create_Connection
   while scanning, for one).

4. **Fan-out.** Typed observer callbacks so nothing above this layer parses bytes.

Threading: `feed_packet` may be called from the transport's I/O thread. All
mutable state is guarded, and observer callbacks run on whichever thread
delivered the packet. The Qt adapter (`hci.session.qt_session`) marshals to the
main thread for widgets.
"""

from __future__ import annotations

import heapq
import itertools
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import hci.evt as hci_evt
from hci.cmd.cmd_base_packet import HciCmdBasePacket
from hci.cmd.cmd_opcodes import OPCODE_TO_NAME
from hci.evt.error_codes import get_status_description
from hci.evt.evt_codes import HciEventCode, LeMetaEventSubCode

from .connection import (
    ConnectionInfo,
    ConnectionTable,
    LinkType,
    Role,
    addr_to_str,
)

#: Observer channels. Subscribe with `session.on(<name>, callback)`.
EVT_PACKET = "packet"                 # (raw_bytes, parsed_event)
EVT_EVENT = "event"                   # (parsed_event)
EVT_COMMAND_SENT = "command_sent"     # (command, raw_bytes)
EVT_ADV_REPORT = "adv_report"         # (report_dict)
EVT_INQUIRY_RESULT = "inquiry_result"  # (result_dict)
EVT_INQUIRY_COMPLETE = "inquiry_complete"   # (status)
EVT_CONNECTION_UP = "connection_up"   # (ConnectionInfo)
EVT_CONNECTION_DOWN = "connection_down"     # (ConnectionInfo|None, handle, reason)
EVT_STATE = "state"                   # (name, value)
EVT_ERROR = "error"                   # (message)

_ALL_CHANNELS = (
    EVT_PACKET, EVT_EVENT, EVT_COMMAND_SENT, EVT_ADV_REPORT, EVT_INQUIRY_RESULT,
    EVT_INQUIRY_COMPLETE, EVT_CONNECTION_UP, EVT_CONNECTION_DOWN, EVT_STATE, EVT_ERROR,
)


class CommandError(Exception):
    """A command failed, timed out, or was rejected by the controller."""

    def __init__(self, message: str, opcode: Optional[int] = None,
                 status: Optional[int] = None):
        super().__init__(message)
        self.opcode = opcode
        self.status = status


class CmdToken:
    """
    Handle for one in-flight command.

    Deliberately not a `concurrent.futures.Future`: the same object has to work
    for the callback style (UI) and the blocking style (scripts/CLI), without
    dragging an executor in.
    """

    __slots__ = ("opcode", "command", "on_complete", "timeout", "deadline",
                 "_event", "response", "error", "sent_at", "completed")

    def __init__(self, command: HciCmdBasePacket, opcode: int,
                 on_complete: Optional[Callable] = None, timeout: float = 2.0):
        self.command = command
        self.opcode = opcode
        self.on_complete = on_complete
        self.timeout = timeout
        self.deadline = 0.0
        self.sent_at = 0.0
        self._event = threading.Event()
        self.response: Any = None
        self.error: Optional[Exception] = None
        self.completed = False

    @property
    def name(self) -> str:
        return OPCODE_TO_NAME.get(self.opcode, f"Opcode_0x{self.opcode:04X}")

    def wait(self, timeout: Optional[float] = None):
        """Block until the controller answers. Raises CommandError on failure."""
        if not self._event.wait(timeout if timeout is not None else self.timeout + 1.0):
            raise CommandError(f"{self.name}: wait() timed out", self.opcode)
        if self.error is not None:
            raise self.error
        return self.response

    def _resolve(self, response: Any = None, error: Optional[Exception] = None) -> None:
        if self.completed:
            return
        self.completed = True
        self.response = response
        self.error = error
        self._event.set()
        if self.on_complete is not None:
            try:
                self.on_complete(response, error)
            except Exception as exc:
                print(f"[hci.session] on_complete for {self.name} raised: {exc!r}")

    def __repr__(self) -> str:
        return f"<CmdToken {self.name} 0x{self.opcode:04X} completed={self.completed}>"


class HciSession:
    """Host-side HCI state machine over a transport."""

    #: Commands that answer with Command Status instead of Command Complete.
    #: Their real result arrives later as a dedicated event.
    STATUS_ONLY_OPCODES = frozenset({
        0x0401,  # Inquiry
        0x0405,  # Create_Connection
        0x0406,  # Disconnect
        0x0419,  # Remote_Name_Request
        0x041B,  # Setup_Synchronous_Connection
        0x200D,  # LE_Create_Connection
        0x2013,  # LE_Connection_Update
        0x2016,  # LE_Read_Remote_Features
        0x2019,  # LE_Start_Encryption
    })

    DEFAULT_TIMEOUT = 5.0

    def __init__(self, transport, name: str = "hci", auto_open: bool = True):
        self.transport = transport
        self.name = name

        self._lock = threading.RLock()
        self._observers: Dict[str, List[Callable]] = defaultdict(list)

        # Command flow control
        self._credits = 1
        self._queue: Deque[CmdToken] = deque()
        self._outstanding: Deque[CmdToken] = deque()

        # Controller / link state
        self.connections = ConnectionTable()
        self.local_bd_addr: Optional[str] = None
        self.local_name: Optional[str] = None
        self.hci_version: Optional[int] = None
        self.manufacturer: Optional[int] = None
        self.le_buffer_size: Optional[Tuple[int, int]] = None
        self.acl_buffer_size: Optional[Tuple[int, int]] = None

        self._scanning = False
        self._advertising = False
        self._inquiring = False

        # Timeout watchdog
        self._watch_heap: List[Tuple[float, int, CmdToken]] = []
        self._watch_seq = itertools.count()
        self._watch_cv = threading.Condition()
        self._watch_thread: Optional[threading.Thread] = None
        self._closing = False

        self._opened = False
        if auto_open:
            self.open()

    # ------------------------------------------------------------- lifecycle

    def open(self) -> None:
        """Subscribe to the transport and start the timeout watchdog."""
        if self._opened:
            return
        from transports.base_lib import TransportEvent

        self.transport.add_callback(TransportEvent.READ, self.feed_packet)
        self._closing = False
        self._watch_thread = threading.Thread(
            target=self._watchdog_main, name=f"hci-watchdog-{self.name}", daemon=True
        )
        self._watch_thread.start()
        self._opened = True

    def close(self) -> None:
        if not self._opened:
            return
        from transports.base_lib import TransportEvent

        try:
            self.transport.remove_callback(TransportEvent.READ, self.feed_packet)
        except Exception:
            pass

        with self._watch_cv:
            self._closing = True
            self._watch_cv.notify_all()
        if self._watch_thread is not None:
            self._watch_thread.join(timeout=1.0)
            self._watch_thread = None

        self._fail_all(CommandError("session closed"))
        self.connections.clear()
        self._opened = False

    def __enter__(self) -> "HciSession":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------- observers

    def on(self, channel: str, callback: Callable) -> Callable:
        if channel not in _ALL_CHANNELS:
            raise ValueError(f"unknown channel {channel!r}; expected one of {_ALL_CHANNELS}")
        with self._lock:
            if callback not in self._observers[channel]:
                self._observers[channel].append(callback)
        return callback

    def off(self, channel: str, callback: Callable) -> None:
        with self._lock:
            if callback in self._observers.get(channel, ()):
                self._observers[channel].remove(callback)

    def _emit(self, channel: str, *args) -> None:
        with self._lock:
            handlers = list(self._observers.get(channel, ()))
        for handler in handlers:
            try:
                handler(*args)
            except Exception as exc:
                print(f"[hci.session] observer on '{channel}' raised: {exc!r}")

    # ---------------------------------------------------------- send / queue

    def send(self, command: HciCmdBasePacket,
             on_complete: Optional[Callable] = None,
             timeout: Optional[float] = None) -> CmdToken:
        """
        Queue a command. Returns immediately with a token.

        The command goes out as soon as the controller has a credit free.
        """
        opcode = getattr(command, "OPCODE", None)
        if opcode is None:
            raise ValueError(f"{type(command).__name__} has no OPCODE")

        token = CmdToken(command, int(opcode), on_complete,
                         self.DEFAULT_TIMEOUT if timeout is None else timeout)
        with self._lock:
            self._queue.append(token)
        self._pump()
        return token

    def send_and_wait(self, command: HciCmdBasePacket,
                      timeout: Optional[float] = None):
        """
        Send and block until the controller answers.

        For scripts and the CLI. Never call this from the thread that delivers
        packets -- it would deadlock waiting for itself.
        """
        token = self.send(command, timeout=timeout)
        return token.wait()

    def _pump(self) -> None:
        """Send as many queued commands as the controller has credits for."""
        while True:
            with self._lock:
                if self._credits <= 0 or not self._queue:
                    return
                token = self._queue.popleft()
                self._credits -= 1
                self._outstanding.append(token)
                token.sent_at = time.monotonic()
                token.deadline = token.sent_at + token.timeout

            try:
                raw = token.command.to_bytes()
                self.transport.write(raw)
            except Exception as exc:
                with self._lock:
                    if token in self._outstanding:
                        self._outstanding.remove(token)
                    self._credits += 1
                token._resolve(error=CommandError(
                    f"{token.name}: transport write failed: {exc}", token.opcode))
                continue

            self._schedule_timeout(token)
            self._emit(EVT_COMMAND_SENT, token.command, raw)

    def _schedule_timeout(self, token: CmdToken) -> None:
        with self._watch_cv:
            heapq.heappush(self._watch_heap,
                           (token.deadline, next(self._watch_seq), token))
            self._watch_cv.notify_all()

    def _watchdog_main(self) -> None:
        """Fail commands the controller never answered."""
        while True:
            with self._watch_cv:
                if self._closing:
                    return
                if not self._watch_heap:
                    self._watch_cv.wait()
                    continue
                deadline, _, token = self._watch_heap[0]
                now = time.monotonic()
                if deadline > now:
                    self._watch_cv.wait(timeout=deadline - now)
                    continue
                heapq.heappop(self._watch_heap)

            if token.completed:
                continue

            with self._lock:
                if token in self._outstanding:
                    self._outstanding.remove(token)
                    # Assume the credit is gone with it; the next completion
                    # will restore the controller's real figure anyway.
                    self._credits = max(self._credits, 1)
            token._resolve(error=CommandError(
                f"{token.name}: no response within {token.timeout:.1f}s",
                token.opcode))
            self._emit(EVT_ERROR, f"{token.name} timed out")
            self._pump()

    def _fail_all(self, error: Exception) -> None:
        with self._lock:
            pending = list(self._outstanding) + list(self._queue)
            self._outstanding.clear()
            self._queue.clear()
        for token in pending:
            token._resolve(error=error)

    def _complete_token(self, opcode: int, response: Any,
                        error: Optional[Exception] = None) -> None:
        """Resolve the oldest outstanding command matching `opcode`."""
        with self._lock:
            match = next((t for t in self._outstanding if t.opcode == opcode), None)
            if match is not None:
                self._outstanding.remove(match)
        if match is not None:
            match._resolve(response, error)

    # ------------------------------------------------------------- RX path

    def feed_packet(self, raw: bytes) -> None:
        """
        Consume one complete H4 packet. Called from the transport I/O thread.

        Never raises: the receive path has to survive whatever the controller
        sends.
        """
        try:
            self._handle_packet(bytes(raw))
        except Exception as exc:
            print(f"[hci.session] error handling packet {bytes(raw).hex()}: {exc!r}")
            self._emit(EVT_ERROR, f"packet handling failed: {exc}")

    def _handle_packet(self, raw: bytes) -> None:
        if not raw:
            return
        if raw[0] != 0x04:
            self._emit(EVT_PACKET, raw, None)   # ACL/SCO/ISO: pass through
            return

        event = hci_evt.hci_evt_parse_from_bytes(raw)
        self._emit(EVT_PACKET, raw, event)
        if event is None:
            return
        self._emit(EVT_EVENT, event)

        code = getattr(event, "EVENT_CODE", None)
        if code == HciEventCode.COMMAND_COMPLETE:
            self._on_command_complete(event)
        elif code == HciEventCode.COMMAND_STATUS:
            self._on_command_status(event)
        elif code == HciEventCode.LE_META_EVENT:
            self._on_le_meta(event)
        elif code == HciEventCode.CONNECTION_COMPLETE:
            self._on_connection_complete(event)
        elif code == HciEventCode.DISCONNECTION_COMPLETE:
            self._on_disconnection_complete(event)
        elif code == HciEventCode.INQUIRY_RESULT:
            self._on_inquiry_result(event)
        elif code in (HciEventCode.INQUIRY_RESULT_WITH_RSSI,
                      HciEventCode.EXTENDED_INQUIRY_RESULT):
            self._on_inquiry_result(event)
        elif code == HciEventCode.INQUIRY_COMPLETE:
            self._set_state("inquiring", False)
            self._emit(EVT_INQUIRY_COMPLETE, event.params.get("status", 0))
        elif code == HciEventCode.ENCRYPTION_CHANGE:
            self._on_encryption_change(event)

    # ------------------------------------------------------ event handlers

    def _restore_credits(self, event) -> None:
        credits_ = event.params.get("num_hci_command_packets")
        if isinstance(credits_, int) and credits_ >= 0:
            with self._lock:
                self._credits = credits_
        else:
            with self._lock:
                self._credits = max(self._credits, 1)

    def _on_command_complete(self, event) -> None:
        self._restore_credits(event)
        opcode = event.params.get("opcode")

        # opcode 0x0000 is the controller volunteering a credit refill, not a
        # completion for anything we sent.
        if opcode:
            self._absorb_command_result(opcode, event)
            status = event.params.get("status")
            error = None
            if isinstance(status, int) and status != 0x00:
                error = CommandError(
                    f"{OPCODE_TO_NAME.get(opcode, hex(opcode))} failed: "
                    f"{get_status_description(status)} (0x{status:02X})",
                    opcode, status)
            self._complete_token(opcode, event, error)

        self._pump()

    def _on_command_status(self, event) -> None:
        self._restore_credits(event)
        opcode = event.params.get("opcode")
        status = event.params.get("status", 0)

        if opcode:
            error = None
            if status != 0x00:
                error = CommandError(
                    f"{OPCODE_TO_NAME.get(opcode, hex(opcode))} rejected: "
                    f"{get_status_description(status)} (0x{status:02X})",
                    opcode, status)
            self._complete_token(opcode, event, error)

            if status == 0x00 and opcode == 0x0401:
                self._set_state("inquiring", True)

        self._pump()

    def _absorb_command_result(self, opcode: int, event) -> None:
        """Pick up controller facts that arrive in Command Complete payloads."""
        extra = event.params.get("return_params") or b""

        if opcode == 0x1009 and len(extra) >= 6:            # Read_BD_ADDR
            self.local_bd_addr = addr_to_str(extra[:6], wire_order=True)
            self._emit(EVT_STATE, "local_bd_addr", self.local_bd_addr)

        elif opcode == 0x1001 and len(extra) >= 8:          # Read_Local_Version
            # hci_ver(1) hci_rev(2) lmp_ver(1) manufacturer(2) lmp_subver(2)
            self.hci_version = extra[0]
            self.manufacturer = int.from_bytes(extra[4:6], "little")
            self._emit(EVT_STATE, "hci_version", self.hci_version)

        elif opcode == 0x2002 and len(extra) >= 3:          # LE_Read_Buffer_Size
            self.le_buffer_size = (int.from_bytes(extra[:2], "little"), extra[2])
            self._emit(EVT_STATE, "le_buffer_size", self.le_buffer_size)

        elif opcode == 0x1005 and len(extra) >= 7:          # Read_Buffer_Size
            self.acl_buffer_size = (int.from_bytes(extra[:2], "little"),
                                    int.from_bytes(extra[3:5], "little"))
            self._emit(EVT_STATE, "acl_buffer_size", self.acl_buffer_size)

        elif opcode == 0x0C14 and extra:                    # Read_Local_Name
            self.local_name = extra.split(b"\x00", 1)[0].decode("utf-8", "replace")
            self._emit(EVT_STATE, "local_name", self.local_name)

        elif opcode in (0x200A, 0x2039):    # LE_Set_(Extended_)Advertise_Enable
            if event.params.get("status") in (0x00, None):
                self._set_state("advertising", self._pending_flag("advertising"))

        elif opcode in (0x200C, 0x2042):    # LE_Set_(Extended_)Scan_Enable
            if event.params.get("status") in (0x00, None):
                self._set_state("scanning", self._pending_flag("scanning"))

    #: Opcodes that turn advertising/scanning on or off, and the params key
    #: holding the intent, legacy first then extended.
    _ENABLE_OPCODES = {
        "advertising": ((0x200A, "enable"), (0x2039, "enable")),
        "scanning": ((0x200C, "scan_enable"), (0x2042, "enable")),
    }

    def _pending_flag(self, which: str) -> bool:
        """
        Resolve what an enable/disable command was actually asking for.

        The Command Complete carries only a status, so the intent has to come
        from the command we sent.
        """
        with self._lock:
            for token in self._outstanding:
                for opcode, key in self._ENABLE_OPCODES[which]:
                    if token.opcode == opcode:
                        return bool(token.command.params.get(key, 0))
        return not getattr(self, f"_{which}")

    def _on_le_meta(self, event) -> None:
        sub = getattr(event, "SUB_EVENT_CODE", None)

        if sub in (LeMetaEventSubCode.ADVERTISING_REPORT,
                   LeMetaEventSubCode.EXTENDED_ADVERTISING_REPORT):
            # Extended reports carry the same 'address'/'rssi'/'adv_data' keys,
            # so scan consumers do not care which flavour arrived.
            for report in getattr(event, "reports", []):
                self._emit(EVT_ADV_REPORT, report)

        elif sub == LeMetaEventSubCode.SCAN_TIMEOUT:
            # An extended scan with a duration ends itself; nothing else tells
            # the host that scanning stopped.
            self._set_state("scanning", False)

        elif sub == LeMetaEventSubCode.ADVERTISING_SET_TERMINATED:
            # The set stopped -- either it hit its limit or it was consumed by
            # an incoming connection (which arrives as its own event).
            self._set_state("advertising", False)

        elif sub in (LeMetaEventSubCode.CONNECTION_COMPLETE,
                     LeMetaEventSubCode.ENHANCED_CONNECTION_COMPLETE):
            self._on_le_connection_complete(event)

        elif sub == LeMetaEventSubCode.CONNECTION_UPDATE_COMPLETE:
            handle = event.params.get("connection_handle")
            info = self.connections.get(handle) if handle is not None else None
            if info is not None:
                info.conn_interval = event.params.get("conn_interval")
                info.conn_latency = event.params.get("conn_latency")
                info.supervision_timeout = event.params.get("supervision_timeout")

    def _on_le_connection_complete(self, event) -> None:
        status = event.params.get("status", 0xFF)
        if status != 0x00:
            self._emit(EVT_ERROR,
                       f"LE connection failed: {get_status_description(status)} "
                       f"(0x{status:02X})")
            return

        peer = event.params.get("peer_address") or b"\x00" * 6
        info = ConnectionInfo(
            handle=event.params.get("connection_handle", 0),
            bd_addr=addr_to_str(peer),
            link_type=LinkType.LE,
            role=Role.from_hci(event.params.get("role", 0)),
            address_type=event.params.get("peer_address_type", 0),
            conn_interval=event.params.get("conn_interval"),
            conn_latency=event.params.get("conn_latency"),
            supervision_timeout=event.params.get("supervision_timeout"),
        )
        self.connections.add(info)
        # A connectable advertiser stops advertising the moment it connects.
        if info.role is Role.PERIPHERAL:
            self._set_state("advertising", False)
        self._emit(EVT_CONNECTION_UP, info)

    def _on_connection_complete(self, event) -> None:
        status = event.params.get("status", 0xFF)
        if status != 0x00:
            self._emit(EVT_ERROR,
                       f"BR/EDR connection failed: {get_status_description(status)} "
                       f"(0x{status:02X})")
            return

        # ConnectionCompleteEvent.from_bytes already reverses the address, so it
        # arrives in display order.
        addr = event.params.get("bd_addr") or b"\x00" * 6
        info = ConnectionInfo(
            handle=event.params.get("connection_handle", 0),
            bd_addr=addr_to_str(addr),
            link_type=LinkType.BR_EDR,
            role=Role.CENTRAL,
        )
        self.connections.add(info)
        self._emit(EVT_CONNECTION_UP, info)

    def _on_disconnection_complete(self, event) -> None:
        handle = event.params.get("connection_handle")
        reason = event.params.get("reason", 0)
        info = self.connections.remove(handle) if handle is not None else None
        self._emit(EVT_CONNECTION_DOWN, info, handle, reason)

    def _on_encryption_change(self, event) -> None:
        info = self.connections.get(event.params.get("connection_handle"))
        if info is not None:
            info.encrypted = bool(event.params.get("encryption_enabled"))

    def _on_inquiry_result(self, event) -> None:
        responses = event.params.get("responses")
        if responses:
            for entry in responses:
                self._emit(EVT_INQUIRY_RESULT, entry)
            return

        # Single-response flavours (Extended Inquiry Result) and the legacy
        # class's list-of-parallel-arrays shape.
        addrs = event.params.get("bd_addrs")
        if addrs:
            for i, addr in enumerate(addrs):
                self._emit(EVT_INQUIRY_RESULT, {
                    "bd_addr": addr,
                    "bd_addr_str": addr_to_str(addr),
                    "class_of_device": _as_cod(
                        _nth(event.params.get("class_of_devices"), i)),
                    "clock_offset": _nth(event.params.get("clock_offsets"), i),
                    "rssi": _nth(event.params.get("rssis"), i),
                })
        elif event.params.get("bd_addr"):
            self._emit(EVT_INQUIRY_RESULT, {
                "bd_addr": event.params["bd_addr"],
                "bd_addr_str": event.params.get(
                    "bd_addr_str", addr_to_str(event.params["bd_addr"], wire_order=True)
                ),
                "class_of_device": _as_cod(event.params.get("class_of_device")),
                "clock_offset": event.params.get("clock_offset"),
                "rssi": event.params.get("rssi"),
            })

    # ---------------------------------------------------------------- state

    def _set_state(self, name: str, value: bool) -> None:
        attr = f"_{name}"
        if getattr(self, attr, None) == value:
            return
        setattr(self, attr, value)
        self._emit(EVT_STATE, name, value)

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    @property
    def is_advertising(self) -> bool:
        return self._advertising

    @property
    def is_inquiring(self) -> bool:
        return self._inquiring

    @property
    def credits(self) -> int:
        """Command packets the controller will currently accept."""
        with self._lock:
            return self._credits

    @property
    def pending_commands(self) -> int:
        with self._lock:
            return len(self._outstanding) + len(self._queue)

    def status_summary(self) -> Dict[str, Any]:
        return {
            "local_bd_addr": self.local_bd_addr,
            "local_name": self.local_name,
            "hci_version": self.hci_version,
            "scanning": self._scanning,
            "advertising": self._advertising,
            "inquiring": self._inquiring,
            "connections": len(self.connections),
            "credits": self.credits,
            "pending_commands": self.pending_commands,
        }


def _as_cod(value):
    """
    Normalise Class of Device to an int.

    The legacy InquiryResultEvent leaves it as 3 raw bytes while the newer
    events decode it, so consumers would otherwise have to handle both.
    """
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(value, "little")
    return value


def _nth(seq, index):
    try:
        return seq[index]
    except (TypeError, IndexError):
        return None


__all__ = [
    "HciSession",
    "CmdToken",
    "CommandError",
    "EVT_PACKET",
    "EVT_EVENT",
    "EVT_COMMAND_SENT",
    "EVT_ADV_REPORT",
    "EVT_INQUIRY_RESULT",
    "EVT_INQUIRY_COMPLETE",
    "EVT_CONNECTION_UP",
    "EVT_CONNECTION_DOWN",
    "EVT_STATE",
    "EVT_ERROR",
]
