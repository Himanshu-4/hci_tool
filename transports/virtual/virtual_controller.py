"""
Virtual Bluetooth controller.

A `TransportInterface` that answers HCI commands with believable events, so the
whole stack -- framing, event parsing, session bookkeeping, procedures, UI -- can
be exercised without a dongle attached. It is the reference peer for the test
suite and the fastest way to develop UI against.

It is intentionally *not* a spec-complete controller. It implements exactly the
commands the four POC flows use, plus a catch-all that returns
"Unknown HCI Command" (0x01) for anything else -- the same thing real silicon
does, which makes it useful for exercising error paths too.

Scheduling note: deferred events go on a heap and the emulator thread waits on a
`Condition` until the next one is actually due. No polling loop, consistent with
the rest of the transport layer.
"""

from __future__ import annotations

import heapq
import itertools
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..base_lib import (
    ConfigurationError,
    TransportError,
    TransportEvent,
    TransportInterface,
    TransportState,
)

# --- Opcodes / codes used here -------------------------------------------
# Spelled out locally so the transport layer keeps no dependency on `hci`.

OP_INQUIRY = 0x0401
OP_INQUIRY_CANCEL = 0x0402
OP_CREATE_CONNECTION = 0x0405
OP_DISCONNECT = 0x0406
OP_ACCEPT_CONN_REQ = 0x0409
OP_REMOTE_NAME_REQUEST = 0x0419

OP_SET_EVENT_MASK = 0x0C01
OP_RESET = 0x0C03
OP_WRITE_LOCAL_NAME = 0x0C13
OP_READ_LOCAL_NAME = 0x0C14
OP_WRITE_SCAN_ENABLE = 0x0C1A
OP_READ_BUFFER_SIZE = 0x1005

OP_READ_LOCAL_VERSION = 0x1001
OP_READ_LOCAL_COMMANDS = 0x1002
OP_READ_BD_ADDR = 0x1009

OP_LE_SET_EVENT_MASK = 0x2001
OP_LE_READ_BUFFER_SIZE = 0x2002
OP_LE_READ_LOCAL_FEATURES = 0x2003
OP_LE_SET_RANDOM_ADDRESS = 0x2005
OP_LE_SET_ADV_PARAMS = 0x2006
OP_LE_READ_ADV_TX_POWER = 0x2007
OP_LE_SET_ADV_DATA = 0x2008
OP_LE_SET_SCAN_RSP_DATA = 0x2009
OP_LE_SET_ADV_ENABLE = 0x200A
OP_LE_SET_SCAN_PARAMS = 0x200B
OP_LE_SET_SCAN_ENABLE = 0x200C
OP_LE_CREATE_CONNECTION = 0x200D
OP_LE_CREATE_CONNECTION_CANCEL = 0x200E
OP_LE_READ_SUPPORTED_STATES = 0x201C

EVT_INQUIRY_COMPLETE = 0x01
EVT_INQUIRY_RESULT = 0x02
EVT_CONNECTION_COMPLETE = 0x03
EVT_DISCONNECTION_COMPLETE = 0x05
EVT_REMOTE_NAME_COMPLETE = 0x07
EVT_COMMAND_COMPLETE = 0x0E
EVT_COMMAND_STATUS = 0x0F
EVT_LE_META = 0x3E

LE_SUB_CONNECTION_COMPLETE = 0x01
LE_SUB_ADVERTISING_REPORT = 0x02

STATUS_SUCCESS = 0x00
STATUS_UNKNOWN_COMMAND = 0x01
STATUS_UNKNOWN_CONN_ID = 0x02
STATUS_PAGE_TIMEOUT = 0x04
STATUS_CONN_TERMINATED_LOCAL = 0x16

HCI_PKT_COMMAND = 0x01
HCI_PKT_EVENT = 0x04


@dataclass
class VirtualDevice:
    """A fake peer the virtual controller will report during scan / inquiry."""

    bd_addr: bytes                      # 6 bytes, little-endian wire order
    name: str = "VirtualDev"
    le: bool = True
    addr_type: int = 0x00               # 0 = public, 1 = random
    rssi: int = -55
    class_of_device: int = 0x240404     # rendering / audio
    connectable: bool = True

    @staticmethod
    def addr_from_str(text: str) -> bytes:
        """'AA:BB:CC:DD:EE:FF' -> wire-order bytes."""
        parts = text.replace("-", ":").split(":")
        if len(parts) != 6:
            raise ValueError(f"bad BD_ADDR: {text}")
        return bytes(int(p, 16) for p in reversed(parts))

    def addr_str(self) -> str:
        return ":".join(f"{b:02X}" for b in reversed(self.bd_addr))

    def adv_payload(self) -> bytes:
        """A small but valid AD payload: Flags + Complete Local Name."""
        name = self.name.encode("utf-8")[:20]
        flags = bytes([0x02, 0x01, 0x06])
        name_ad = bytes([len(name) + 1, 0x09]) + name
        return flags + name_ad


DEFAULT_DEVICES: Tuple[VirtualDevice, ...] = (
    VirtualDevice(VirtualDevice.addr_from_str("AA:BB:CC:11:22:33"), "Virtual LE Sensor", le=True, rssi=-48),
    VirtualDevice(VirtualDevice.addr_from_str("AA:BB:CC:44:55:66"), "Virtual LE Tag", le=True, addr_type=0x01, rssi=-72),
    VirtualDevice(VirtualDevice.addr_from_str("11:22:33:44:55:66"), "Virtual Headset", le=False, rssi=-60),
    VirtualDevice(VirtualDevice.addr_from_str("77:88:99:AA:BB:CC"), "Virtual Speaker", le=False, rssi=-77),
)


@dataclass
class _Scheduled:
    due: float
    seq: int
    packet: bytes = field(compare=False)

    def __lt__(self, other: "_Scheduled") -> bool:
        return (self.due, self.seq) < (other.due, other.seq)


class VirtualControllerTransport(TransportInterface):
    """An emulated controller speaking H4 over an in-process channel."""

    LOCAL_BD_ADDR = VirtualDevice.addr_from_str("00:1A:7D:DA:71:13")
    LOCAL_NAME = "Virtual HCI Controller"

    def __init__(self):
        super().__init__()
        self.config: Dict[str, Any] = {}
        self.devices: List[VirtualDevice] = list(DEFAULT_DEVICES)

        #: Simulated controller-response latency, seconds.
        self.latency = 0.002
        #: Interval between synthetic advertising reports while scanning.
        self.adv_interval = 0.15

        self._heap: List[_Scheduled] = []
        self._seq = itertools.count()
        self._cv = threading.Condition()
        self._thread: Optional[threading.Thread] = None
        self._stopping = False

        # Emulated controller state
        self._scanning = False
        self._advertising = False
        self._inquiring = False
        self._next_handle = 0x0001
        self._connections: Dict[int, VirtualDevice] = {}
        self._local_name = self.LOCAL_NAME

    # ------------------------------------------------------------- config

    def configure(self, config: Dict[str, Any]) -> bool:
        try:
            self.config = dict(config or {})
            self.latency = float(self.config.get("latency", self.latency))
            self.adv_interval = float(self.config.get("adv_interval", self.adv_interval))
            devices = self.config.get("devices")
            if devices:
                self.devices = list(devices)
            return True
        except Exception as exc:
            raise ConfigurationError(f"virtual controller config error: {exc}") from exc

    # ---------------------------------------------------------- lifecycle

    def connect(self) -> bool:
        if self.is_connected():
            return True
        self._set_status(TransportState.CONNECTING)
        self._stopping = False
        self._thread = threading.Thread(
            target=self._emulator_main, name="virtual-ctrl", daemon=True
        )
        self._thread.start()
        self._set_status(TransportState.CONNECTED)
        self._trigger_callbacks(TransportEvent.CONNECT, self)
        return True

    def disconnect(self) -> bool:
        if self._thread is None:
            self._set_status(TransportState.DISCONNECTED)
            return True
        self._set_status(TransportState.DISCONNECTING)
        with self._cv:
            self._stopping = True
            self._heap.clear()
            self._cv.notify_all()
        self._thread.join(timeout=2.0)
        self._thread = None
        self._scanning = self._advertising = self._inquiring = False
        self._connections.clear()
        self._set_status(TransportState.DISCONNECTED)
        self._trigger_callbacks(TransportEvent.DISCONNECT, self)
        return True

    def read(self, size: int = -1) -> Optional[bytes]:
        raise TransportError("virtual controller is push-based; subscribe to READ")

    # ---------------------------------------------------------------- TX

    def write(self, data: bytes) -> bool:
        if not self.is_connected():
            raise TransportError("virtual controller is not connected")
        data = bytes(data)
        self._stats["packets_tx"] += 1
        self._stats["bytes_tx"] += len(data)
        self._trigger_callbacks(TransportEvent.WRITE, data)

        if not data or data[0] != HCI_PKT_COMMAND or len(data) < 4:
            return True  # ACL/SCO/ISO: accepted and dropped

        opcode, plen = struct.unpack_from("<HB", data, 1)
        params = data[4:4 + plen]
        try:
            self._handle_command(opcode, params)
        except Exception as exc:  # a broken emulator must not look like a hang
            self._trigger_callbacks(TransportEvent.ERROR, exc)
        return True

    # ------------------------------------------------------- event engine

    def _emulator_main(self) -> None:
        while True:
            with self._cv:
                if self._stopping:
                    return
                if not self._heap:
                    self._cv.wait()          # sleeps until something is scheduled
                    continue
                now = time.monotonic()
                if self._heap[0].due > now:
                    self._cv.wait(timeout=self._heap[0].due - now)
                    continue
                item = heapq.heappop(self._heap)
            self._deliver(item.packet)

    def _schedule(self, packet: bytes, delay: Optional[float] = None) -> None:
        delay = self.latency if delay is None else delay
        with self._cv:
            if self._stopping:
                return
            heapq.heappush(
                self._heap,
                _Scheduled(time.monotonic() + delay, next(self._seq), packet),
            )
            self._cv.notify_all()

    def _deliver(self, packet: bytes) -> None:
        self._stats["packets_rx"] += 1
        self._stats["bytes_rx"] += len(packet)
        self._trigger_callbacks(TransportEvent.RAW_RX, packet)
        self._trigger_callbacks(TransportEvent.READ, packet)

    # ------------------------------------------------------ packet builders

    @staticmethod
    def _event(code: int, params: bytes) -> bytes:
        return bytes([HCI_PKT_EVENT, code, len(params)]) + params

    def _cmd_complete(self, opcode: int, return_params: bytes = b"\x00") -> bytes:
        return self._event(
            EVT_COMMAND_COMPLETE, struct.pack("<BH", 1, opcode) + return_params
        )

    def _cmd_status(self, opcode: int, status: int = STATUS_SUCCESS) -> bytes:
        return self._event(EVT_COMMAND_STATUS, struct.pack("<BBH", status, 1, opcode))

    def _le_meta(self, subcode: int, params: bytes) -> bytes:
        return self._event(EVT_LE_META, bytes([subcode]) + params)

    # --------------------------------------------------------- command map

    def _handle_command(self, opcode: int, params: bytes) -> None:
        simple_ok = {
            OP_RESET, OP_SET_EVENT_MASK, OP_LE_SET_EVENT_MASK,
            OP_LE_SET_RANDOM_ADDRESS, OP_LE_SET_ADV_PARAMS, OP_LE_SET_ADV_DATA,
            OP_LE_SET_SCAN_RSP_DATA, OP_LE_SET_SCAN_PARAMS, OP_WRITE_SCAN_ENABLE,
            OP_ACCEPT_CONN_REQ,
        }

        if opcode == OP_RESET:
            self._scanning = self._advertising = self._inquiring = False
            self._connections.clear()
            self._schedule(self._cmd_complete(opcode))

        elif opcode in simple_ok:
            self._schedule(self._cmd_complete(opcode))

        elif opcode == OP_READ_BD_ADDR:
            self._schedule(self._cmd_complete(opcode, b"\x00" + self.LOCAL_BD_ADDR))

        elif opcode == OP_READ_LOCAL_VERSION:
            # status, hci_ver 5.3(0x0C), hci_rev, lmp_ver, manufacturer, lmp_subver
            self._schedule(self._cmd_complete(
                opcode, struct.pack("<BBHBHH", 0, 0x0C, 0x0001, 0x0C, 0xFFFF, 0x0001)))

        elif opcode == OP_READ_LOCAL_COMMANDS:
            self._schedule(self._cmd_complete(opcode, b"\x00" + b"\xFF" * 64))

        elif opcode == OP_LE_READ_LOCAL_FEATURES:
            self._schedule(self._cmd_complete(opcode, b"\x00" + b"\x21" + b"\x00" * 7))

        elif opcode == OP_LE_READ_SUPPORTED_STATES:
            self._schedule(self._cmd_complete(opcode, b"\x00" + b"\xFF" * 8))

        elif opcode == OP_LE_READ_ADV_TX_POWER:
            self._schedule(self._cmd_complete(opcode, struct.pack("<Bb", 0, 7)))

        elif opcode == OP_READ_BUFFER_SIZE:
            # status, acl_len, sco_len, acl_pkts, sco_pkts
            self._schedule(self._cmd_complete(
                opcode, struct.pack("<BHBHH", 0, 1021, 255, 8, 8)))

        elif opcode == OP_LE_READ_BUFFER_SIZE:
            self._schedule(self._cmd_complete(opcode, struct.pack("<BHB", 0, 251, 8)))

        elif opcode == OP_READ_LOCAL_NAME:
            padded = self._local_name.encode()[:248].ljust(248, b"\x00")
            self._schedule(self._cmd_complete(opcode, b"\x00" + padded))

        elif opcode == OP_WRITE_LOCAL_NAME:
            self._local_name = params.rstrip(b"\x00").decode("utf-8", "replace")
            self._schedule(self._cmd_complete(opcode))

        elif opcode == OP_LE_SET_ADV_ENABLE:
            self._advertising = bool(params and params[0])
            self._schedule(self._cmd_complete(opcode))

        elif opcode == OP_LE_SET_SCAN_ENABLE:
            self._handle_scan_enable(opcode, params)

        elif opcode == OP_LE_CREATE_CONNECTION:
            self._handle_le_create_connection(opcode, params)

        elif opcode == OP_LE_CREATE_CONNECTION_CANCEL:
            self._schedule(self._cmd_complete(opcode))
            self._schedule(self._le_meta(
                LE_SUB_CONNECTION_COMPLETE,
                struct.pack("<BHBB", STATUS_UNKNOWN_CONN_ID, 0, 0, 0) + b"\x00" * 6
                + struct.pack("<HHHB", 0, 0, 0, 0)), 0.01)

        elif opcode == OP_INQUIRY:
            self._handle_inquiry(opcode, params)

        elif opcode == OP_INQUIRY_CANCEL:
            self._inquiring = False
            self._schedule(self._cmd_complete(opcode))

        elif opcode == OP_CREATE_CONNECTION:
            self._handle_bredr_create_connection(opcode, params)

        elif opcode == OP_REMOTE_NAME_REQUEST:
            self._handle_remote_name(opcode, params)

        elif opcode == OP_DISCONNECT:
            self._handle_disconnect(opcode, params)

        else:
            self._schedule(self._cmd_complete(opcode, bytes([STATUS_UNKNOWN_COMMAND])))

    # ----------------------------------------------------- command handlers

    def _handle_scan_enable(self, opcode: int, params: bytes) -> None:
        enable = bool(params and params[0])
        self._schedule(self._cmd_complete(opcode))
        self._scanning = enable
        if enable:
            self._queue_adv_reports()

    def _queue_adv_reports(self) -> None:
        """Emit one advertising report per LE device, then repeat."""
        if not self._scanning:
            return
        delay = self.latency
        for dev in (d for d in self.devices if d.le):
            payload = dev.adv_payload()
            body = (
                struct.pack("<BBB", 1, 0x00 if dev.connectable else 0x03, dev.addr_type)
                + dev.bd_addr
                + bytes([len(payload)])
                + payload
                + struct.pack("<b", dev.rssi)
            )
            self._schedule(self._le_meta(LE_SUB_ADVERTISING_REPORT, body), delay)
            delay += 0.01

        # Re-arm. `_scanning` is re-checked on entry, so disabling scan stops it.
        self._schedule_repeat_scan(delay)

    def _schedule_repeat_scan(self, after: float) -> None:
        timer = threading.Timer(
            max(self.adv_interval, after), self._queue_adv_reports
        )
        timer.daemon = True
        timer.start()

    def _handle_le_create_connection(self, opcode: int, params: bytes) -> None:
        self._schedule(self._cmd_status(opcode))
        # LE_Create_Connection layout: scan_interval(2) scan_window(2)
        # filter_policy(1) peer_addr_type(1) peer_addr(6) own_addr_type(1) ...
        if len(params) < 12:
            return
        peer_addr_type = params[5]
        peer_addr = params[6:12]

        known = next((d for d in self.devices if d.bd_addr == peer_addr and d.le), None)
        handle = self._alloc_handle()
        if known is None:
            body = struct.pack("<BHBB", STATUS_PAGE_TIMEOUT, 0, 0, peer_addr_type) \
                + peer_addr + struct.pack("<HHHB", 0, 0, 0, 0)
        else:
            self._connections[handle] = known
            body = struct.pack("<BHBB", STATUS_SUCCESS, handle, 0x00, peer_addr_type) \
                + peer_addr + struct.pack("<HHHB", 0x0028, 0x0000, 0x01F4, 0x00)
        self._schedule(self._le_meta(LE_SUB_CONNECTION_COMPLETE, body), 0.05)

    def _handle_inquiry(self, opcode: int, params: bytes) -> None:
        self._schedule(self._cmd_status(opcode))
        self._inquiring = True
        delay = 0.05
        for dev in (d for d in self.devices if not d.le):
            body = (
                bytes([1]) + dev.bd_addr
                + bytes([0x01])                             # page scan repetition mode
                + bytes([0x00, 0x00])                       # reserved (2 bytes)
                + struct.pack("<BBB", *self._cod_bytes(dev))
                + struct.pack("<H", 0x0000)                 # clock offset
            )
            self._schedule(self._event(EVT_INQUIRY_RESULT, body), delay)
            delay += 0.03
        self._schedule(self._event(EVT_INQUIRY_COMPLETE, bytes([STATUS_SUCCESS])),
                       delay + 0.05)
        self._inquiring = False

    @staticmethod
    def _cod_bytes(dev: VirtualDevice) -> Tuple[int, int, int]:
        cod = dev.class_of_device
        return cod & 0xFF, (cod >> 8) & 0xFF, (cod >> 16) & 0xFF

    def _handle_bredr_create_connection(self, opcode: int, params: bytes) -> None:
        self._schedule(self._cmd_status(opcode))
        if len(params) < 6:
            return
        peer = params[0:6]
        known = next((d for d in self.devices if d.bd_addr == peer and not d.le), None)
        if known is None:
            body = struct.pack("<BH", STATUS_PAGE_TIMEOUT, 0) + peer + bytes([0x01, 0x00])
        else:
            handle = self._alloc_handle()
            self._connections[handle] = known
            body = struct.pack("<BH", STATUS_SUCCESS, handle) + peer + bytes([0x01, 0x00])
        self._schedule(self._event(EVT_CONNECTION_COMPLETE, body), 0.08)

    def _handle_remote_name(self, opcode: int, params: bytes) -> None:
        self._schedule(self._cmd_status(opcode))
        if len(params) < 6:
            return
        peer = params[0:6]
        known = next((d for d in self.devices if d.bd_addr == peer), None)
        name = (known.name if known else "Unknown").encode()[:248].ljust(248, b"\x00")
        self._schedule(
            self._event(EVT_REMOTE_NAME_COMPLETE, bytes([STATUS_SUCCESS]) + peer + name),
            0.05,
        )

    def _handle_disconnect(self, opcode: int, params: bytes) -> None:
        self._schedule(self._cmd_status(opcode))
        if len(params) < 3:
            return
        handle, reason = struct.unpack("<HB", params[:3])
        if handle in self._connections:
            del self._connections[handle]
            body = struct.pack("<BHB", STATUS_SUCCESS, handle, reason)
        else:
            body = struct.pack("<BHB", STATUS_UNKNOWN_CONN_ID, handle, 0)
        self._schedule(self._event(EVT_DISCONNECTION_COMPLETE, body), 0.03)

    def _alloc_handle(self) -> int:
        handle = self._next_handle
        self._next_handle = (self._next_handle + 1) & 0x0EFF or 1
        return handle

    # ------------------------------------------------------------- helpers

    def inject_event(self, packet: bytes, delay: float = 0.0) -> None:
        """Push an arbitrary event up the stack -- for negative tests."""
        self._schedule(bytes(packet), delay)

    def get_config(self) -> Dict[str, Any]:
        return dict(self.config)

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        stats.update(
            scanning=self._scanning,
            advertising=self._advertising,
            connections=len(self._connections),
        )
        return stats


__all__ = ["VirtualControllerTransport", "VirtualDevice", "DEFAULT_DEVICES"]
