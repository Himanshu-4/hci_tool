"""
High-level procedures -- the four POC flows.

Each is a short, explicit sequence built on `HciSession`. They are what turns
the tool from "a thing that sends bytes" into "a thing that connects".

All of them are written in the blocking style (`send_and_wait`) because that is
what makes a flow readable and what a CLI wants. Call them from a worker thread,
never from the thread delivering packets -- `run_in_thread()` is provided for
exactly that.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import hci.cmd.controller_baseband as cb_cmds
import hci.cmd.le_cmds as le_cmds
import hci.cmd.link_controller as lc_cmds
from hci.cmd.information.information_cmds import (
    ReadBdAddr,
    ReadLocalVersionInformation,
)
from hci.evt.le.adv_data import AdvertisingDataBuilder, parse_adv_data

from .connection import ConnectionInfo, LinkType
from .session import (
    EVT_ADV_REPORT,
    EVT_CONNECTION_DOWN,
    EVT_CONNECTION_UP,
    EVT_ERROR,
    EVT_INQUIRY_COMPLETE,
    EVT_INQUIRY_RESULT,
    CommandError,
    HciSession,
)

Reporter = Optional[Callable[[str], None]]


def _report(reporter: Reporter, message: str) -> None:
    if reporter is not None:
        try:
            reporter(message)
            return
        except Exception:
            pass
    print(f"[procedure] {message}")


def run_in_thread(fn: Callable, *args, **kwargs) -> threading.Thread:
    """Run a procedure off the caller's thread (e.g. off the Qt main thread)."""
    thread = threading.Thread(target=fn, args=args, kwargs=kwargs,
                              name=f"proc-{fn.__name__}", daemon=True)
    thread.start()
    return thread


# ============================================================ discovered device

@dataclass
class DiscoveredDevice:
    """One device seen during a scan or an inquiry."""

    address: str
    link_type: LinkType
    address_type: int = 0x00
    name: Optional[str] = None
    rssi: Optional[int] = None
    class_of_device: Optional[int] = None
    connectable: bool = True
    services: List[str] = field(default_factory=list)
    manufacturer_id: Optional[int] = None
    times_seen: int = 1
    last_seen: float = field(default_factory=time.monotonic)

    def __str__(self) -> str:
        parts = [self.address]
        if self.name:
            parts.append(f"'{self.name}'")
        if self.rssi is not None:
            parts.append(f"{self.rssi}dBm")
        if self.class_of_device is not None:
            parts.append(f"CoD=0x{self.class_of_device:06X}")
        if self.services:
            parts.append(f"services={','.join(self.services[:3])}")
        parts.append(f"x{self.times_seen}")
        return " ".join(parts)


class DeviceRegistry:
    """Deduplicating store of discovered devices, keyed by address."""

    def __init__(self):
        self._lock = threading.RLock()
        self._devices: Dict[str, DiscoveredDevice] = {}

    def upsert(self, device: DiscoveredDevice) -> DiscoveredDevice:
        with self._lock:
            existing = self._devices.get(device.address)
            if existing is None:
                self._devices[device.address] = device
                return device
            existing.times_seen += 1
            existing.last_seen = time.monotonic()
            if device.rssi is not None:
                existing.rssi = device.rssi
            if device.name and not existing.name:
                existing.name = device.name
            if device.services and not existing.services:
                existing.services = device.services
            if device.manufacturer_id is not None:
                existing.manufacturer_id = device.manufacturer_id
            if device.class_of_device is not None:
                existing.class_of_device = device.class_of_device
            return existing

    def all(self) -> List[DiscoveredDevice]:
        with self._lock:
            return sorted(self._devices.values(),
                          key=lambda d: (d.rssi is None, -(d.rssi or 0)))

    def get(self, address: str) -> Optional[DiscoveredDevice]:
        with self._lock:
            return self._devices.get(address.upper())

    def clear(self) -> None:
        with self._lock:
            self._devices.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._devices)


# ==================================================================== init

def initialize_controller(session: HciSession, reporter: Reporter = None,
                          reset_settle: float = 0.15) -> Dict[str, object]:
    """
    Bring the controller into a known state.

    Every other flow depends on this having run. `LE_Set_Event_Mask` matters in
    particular: several controllers mask off advertising reports by default, so
    without it a scan produces nothing and looks like a hardware fault.
    """
    _report(reporter, "initialising controller...")

    session.send_and_wait(cb_cmds.Reset(), timeout=5.0)
    # Some parts need a moment after reset before they accept commands.
    time.sleep(reset_settle)
    _report(reporter, "  reset OK")

    try:
        session.send_and_wait(ReadLocalVersionInformation())
        _report(reporter, f"  HCI version {session.hci_version}, "
                          f"manufacturer 0x{(session.manufacturer or 0):04X}")
    except CommandError as exc:
        _report(reporter, f"  read local version failed: {exc}")

    try:
        session.send_and_wait(ReadBdAddr())
        _report(reporter, f"  local BD_ADDR {session.local_bd_addr}")
    except CommandError as exc:
        _report(reporter, f"  read BD_ADDR failed: {exc}")

    # Unmask classic events (incl. Disconnection Complete, Inquiry Result w/ RSSI).
    for command, label in (
        (cb_cmds.SetEventMask(event_mask=0x3FFFFFFFFFFFFFFF), "event mask"),
        (le_cmds.LeSetEventMask(le_cmds.LeSetEventMask.ALL_EVENTS), "LE event mask"),
        (le_cmds.LeReadBufferSize(), "LE buffer size"),
        (cb_cmds.ReadBufferSize(), "ACL buffer size"),
    ):
        try:
            session.send_and_wait(command)
        except CommandError as exc:
            # Not fatal: a controller lacking one of these is still usable.
            _report(reporter, f"  {label} not accepted ({exc})")

    _report(reporter, "controller ready")
    return session.status_summary()


# =============================================================== LE advertise

def start_advertising(session: HciSession,
                      local_name: str = "HCI Tool",
                      adv_interval_min: int = 0x00A0,   # 100 ms
                      adv_interval_max: int = 0x00F0,   # 150 ms
                      adv_type: int = 0x00,             # ADV_IND, connectable
                      own_addr_type: int = 0x00,
                      random_address: Optional[str] = None,
                      service_uuids: Optional[List[int]] = None,
                      reporter: Reporter = None) -> bool:
    """
    Configure and enable legacy LE advertising.

    With `adv_type=0x00` (ADV_IND) the device is connectable: a central that
    connects produces an LE Connection Complete, which the session turns into
    `connection_up`.
    """
    _report(reporter, f"starting LE advertising as '{local_name}'...")

    if random_address is not None:
        session.send_and_wait(le_cmds.LeSetRandomAddress(random_address))
        own_addr_type = 0x01
        _report(reporter, f"  random address {random_address}")

    session.send_and_wait(le_cmds.LeSetAdvParams(
        adv_interval_min=adv_interval_min,
        adv_interval_max=adv_interval_max,
        adv_type=adv_type,
        own_addr_type=own_addr_type,
    ))
    _report(reporter, f"  params: interval "
                      f"{adv_interval_min * 0.625:.1f}-{adv_interval_max * 0.625:.1f}ms")

    builder = AdvertisingDataBuilder().add_flags()
    if service_uuids:
        builder.add_service_uuids16(service_uuids)
    try:
        builder.add_name(local_name)
    except ValueError:
        # Name does not fit alongside the other structures: shorten rather than
        # fail the whole flow.
        room = AdvertisingDataBuilder.MAX_PAYLOAD - len(builder) - 2
        builder.add_name(local_name[:max(room, 0)], complete=False)
        _report(reporter, "  name truncated to fit the 31-byte payload")

    payload = builder.build()
    session.send_and_wait(le_cmds.LeSetAdvData(data=payload))
    _report(reporter, f"  adv data: {len(payload)} bytes")

    scan_rsp = AdvertisingDataBuilder().add_name(local_name).build()
    try:
        session.send_and_wait(le_cmds.LeSetScanResponseData(scan_rsp))
    except CommandError as exc:
        _report(reporter, f"  scan response rejected ({exc})")

    session.send_and_wait(le_cmds.LeSetAdvertiseEnable(True))
    _report(reporter, "advertising ENABLED")
    return True


def stop_advertising(session: HciSession, reporter: Reporter = None) -> bool:
    session.send_and_wait(le_cmds.LeSetAdvertiseEnable(False))
    _report(reporter, "advertising disabled")
    return True


# ==================================================================== LE scan

def scan_le(session: HciSession,
            duration: float = 5.0,
            active: bool = True,
            filter_duplicates: bool = False,
            scan_interval: int = 0x0060,
            scan_window: int = 0x0030,
            on_device: Optional[Callable[[DiscoveredDevice], None]] = None,
            reporter: Reporter = None) -> List[DiscoveredDevice]:
    """
    Scan for LE advertisers for `duration` seconds.

    `filter_duplicates=False` by default so repeat sightings still arrive and
    RSSI stays live; the registry deduplicates for display anyway.
    """
    registry = DeviceRegistry()

    def _on_report(report: dict) -> None:
        ad = report.get("adv_data") or parse_adv_data(report.get("data", b""))
        device = DiscoveredDevice(
            address=report["address_str"],
            link_type=LinkType.LE,
            address_type=report.get("address_type", 0),
            name=ad.local_name,
            rssi=report.get("rssi"),
            connectable=report.get("event_type") in (0x00, 0x01),
            services=list(ad.service_uuids),
            manufacturer_id=ad.manufacturer_id,
        )
        stored = registry.upsert(device)
        if on_device is not None and stored.times_seen == 1:
            on_device(stored)

    _report(reporter, f"scanning for {duration:.1f}s "
                      f"({'active' if active else 'passive'})...")
    session.on(EVT_ADV_REPORT, _on_report)
    try:
        session.send_and_wait(le_cmds.le_set_scan_parameters(
            scan_type=0x01 if active else 0x00,
            scan_interval=scan_interval,
            scan_window=scan_window,
        ))
        session.send_and_wait(le_cmds.le_set_scan_enable(True, filter_duplicates))
        time.sleep(duration)
    finally:
        try:
            session.send_and_wait(le_cmds.le_set_scan_enable(False, False))
        except CommandError as exc:
            _report(reporter, f"  failed to stop scan: {exc}")
        session.off(EVT_ADV_REPORT, _on_report)

    devices = registry.all()
    _report(reporter, f"scan complete: {len(devices)} device(s)")
    for device in devices:
        _report(reporter, f"  {device}")
    return devices


# ================================================================= LE connect

def connect_le(session: HciSession,
               peer_address: str,
               peer_address_type: int = 0x00,
               timeout: float = 10.0,
               reporter: Reporter = None) -> ConnectionInfo:
    """
    Open an LE connection and wait for it to come up.

    Scanning is stopped first: the controller answers LE_Create_Connection with
    "Command Disallowed" (0x0C) while a scan is running, which is one of the
    most confusing errors to hit blind.
    """
    if session.is_scanning:
        _report(reporter, "stopping scan before connecting...")
        session.send_and_wait(le_cmds.le_set_scan_enable(False, False))

    settled = threading.Event()
    result: Dict[str, ConnectionInfo] = {}
    failure: Dict[str, str] = {}

    def _on_up(info: ConnectionInfo) -> None:
        if info.bd_addr.upper() == peer_address.upper():
            result["info"] = info
            settled.set()

    def _on_error(message: str) -> None:
        # A failed LE Connection Complete arrives here. Without it the caller
        # would sit out the full timeout even though the controller already
        # said no.
        if "LE connection failed" in message:
            failure["message"] = message
            settled.set()

    _report(reporter, f"connecting to {peer_address} (LE)...")
    session.on(EVT_CONNECTION_UP, _on_up)
    session.on(EVT_ERROR, _on_error)
    try:
        session.send_and_wait(le_cmds.LeCreateConnection(
            peer_address=peer_address,
            peer_address_type=peer_address_type,
        ), timeout=min(timeout, 5.0))

        if not settled.wait(timeout):
            _report(reporter, "  no LE Connection Complete; cancelling")
            try:
                session.send_and_wait(le_cmds.LeCreateConnectionCancel())
            except CommandError as exc:
                _report(reporter, f"  cancel failed: {exc}")
            raise CommandError(f"LE connection to {peer_address} timed out "
                               f"after {timeout:.1f}s")
        if failure:
            raise CommandError(failure["message"])
    finally:
        session.off(EVT_CONNECTION_UP, _on_up)
        session.off(EVT_ERROR, _on_error)

    info = result["info"]
    _report(reporter, f"CONNECTED: {info}")
    return info


# ==================================================== BR/EDR inquiry + connect

def inquiry(session: HciSession,
            duration_units: int = 8,        # 8 * 1.28s ~= 10s
            max_responses: int = 0,         # 0 = unlimited
            lap: int = 0x9E8B33,            # General Inquiry Access Code
            discoverable: bool = True,
            on_device: Optional[Callable[[DiscoveredDevice], None]] = None,
            reporter: Reporter = None) -> List[DiscoveredDevice]:
    """Run a BR/EDR inquiry and collect the responses."""
    registry = DeviceRegistry()
    finished = threading.Event()

    def _on_result(entry: dict) -> None:
        device = DiscoveredDevice(
            address=entry["bd_addr_str"],
            link_type=LinkType.BR_EDR,
            rssi=entry.get("rssi"),
            class_of_device=entry.get("class_of_device"),
        )
        stored = registry.upsert(device)
        if on_device is not None and stored.times_seen == 1:
            on_device(stored)

    def _on_complete(_status: int) -> None:
        finished.set()

    if discoverable:
        try:
            session.send_and_wait(cb_cmds.WriteScanEnable(cb_cmds.ScanEnable.BOTH))
            _report(reporter, "  discoverable + connectable")
        except CommandError as exc:
            _report(reporter, f"  write scan enable failed: {exc}")

    timeout = duration_units * 1.28 + 3.0
    _report(reporter, f"inquiry for ~{duration_units * 1.28:.1f}s...")

    session.on(EVT_INQUIRY_RESULT, _on_result)
    session.on(EVT_INQUIRY_COMPLETE, _on_complete)
    try:
        session.send_and_wait(lc_cmds.Inquiry(
            lap=lap, inquiry_length=duration_units, num_responses=max_responses))
        if not finished.wait(timeout):
            _report(reporter, "  no Inquiry Complete; cancelling")
            try:
                session.send_and_wait(lc_cmds.InquiryCancel())
            except CommandError as exc:
                _report(reporter, f"  inquiry cancel failed: {exc}")
    finally:
        session.off(EVT_INQUIRY_RESULT, _on_result)
        session.off(EVT_INQUIRY_COMPLETE, _on_complete)

    devices = registry.all()
    _report(reporter, f"inquiry complete: {len(devices)} device(s)")
    for device in devices:
        _report(reporter, f"  {device}")
    return devices


def connect_bredr(session: HciSession,
                  peer_address: str,
                  packet_type: int = 0xCC18,       # DM1/DH1/DM3/DH3/DM5/DH5
                  allow_role_switch: bool = True,
                  timeout: float = 15.0,
                  reporter: Reporter = None) -> ConnectionInfo:
    """Open a BR/EDR ACL connection and wait for Connection Complete."""
    established = threading.Event()
    result: Dict[str, ConnectionInfo] = {}

    def _on_up(info: ConnectionInfo) -> None:
        if info.bd_addr.upper() == peer_address.upper():
            result["info"] = info
            established.set()

    _report(reporter, f"connecting to {peer_address} (BR/EDR)...")
    session.on(EVT_CONNECTION_UP, _on_up)
    try:
        session.send_and_wait(lc_cmds.CreateConnection(
            bd_addr=peer_address,
            packet_type=packet_type,
            allow_role_switch=0x01 if allow_role_switch else 0x00,
        ), timeout=min(timeout, 5.0))

        if not established.wait(timeout):
            raise CommandError(f"BR/EDR connection to {peer_address} timed out "
                               f"after {timeout:.1f}s (page timeout?)")
    finally:
        session.off(EVT_CONNECTION_UP, _on_up)

    info = result["info"]
    _report(reporter, f"CONNECTED: {info}")
    return info


# =================================================================== disconnect

def disconnect(session: HciSession,
               handle: int,
               reason: int = 0x13,             # Remote User Terminated Connection
               timeout: float = 10.0,
               reporter: Reporter = None) -> bool:
    """Tear down a connection and wait for Disconnection Complete."""
    done = threading.Event()

    def _on_down(_info, closed_handle: int, _reason: int) -> None:
        if closed_handle == handle:
            done.set()

    _report(reporter, f"disconnecting handle 0x{handle:04X}...")
    session.on(EVT_CONNECTION_DOWN, _on_down)
    try:
        session.send_and_wait(
            lc_cmds.Disconnect(connection_handle=handle, reason=reason),
            timeout=min(timeout, 5.0))
        if not done.wait(timeout):
            _report(reporter, "  no Disconnection Complete received")
            return False
    finally:
        session.off(EVT_CONNECTION_DOWN, _on_down)

    _report(reporter, "disconnected")
    return True


def disconnect_all(session: HciSession, reporter: Reporter = None) -> int:
    closed = 0
    for info in session.connections.all():
        try:
            if disconnect(session, info.handle, reporter=reporter):
                closed += 1
        except CommandError as exc:
            _report(reporter, f"  failed to close 0x{info.handle:04X}: {exc}")
    return closed


__all__ = [
    "DiscoveredDevice",
    "DeviceRegistry",
    "initialize_controller",
    "start_advertising",
    "stop_advertising",
    "scan_le",
    "connect_le",
    "inquiry",
    "connect_bredr",
    "disconnect",
    "disconnect_all",
    "run_in_thread",
]
