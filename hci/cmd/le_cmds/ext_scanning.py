"""
LE extended scanning and periodic-advertising synchronisation commands.

    0x2041  LE_Set_Extended_Scan_Parameters
    0x2042  LE_Set_Extended_Scan_Enable
    0x2044  LE_Periodic_Advertising_Create_Sync
    0x2045  LE_Periodic_Advertising_Create_Sync_Cancel
    0x2046  LE_Periodic_Advertising_Terminate_Sync
    0x2059  LE_Set_Periodic_Advertising_Receive_Enable

Extended scanning takes *per-PHY* parameters: the scanning PHYs bitmap says
which PHYs are used, and one (type, interval, window) triple follows for each
bit set, in ascending bit order. Getting the count wrong is the usual reason a
controller rejects 0x2041, so `scan_phys` here is a dict keyed by PHY and the
wire order is derived rather than trusted.
"""

from __future__ import annotations

import struct
from enum import IntEnum, IntFlag, unique
from typing import Dict, Mapping, Tuple, Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode
from .advertisement import _coerce_addr


class ScanPhy(IntFlag):
    """Bits in the `Scanning_PHYs` / `Initiating_PHYs` fields."""

    LE_1M = 0x01
    LE_2M = 0x02       # not valid for scanning; connections only
    LE_CODED = 0x04


#: Ascending bit order, which is the order the per-PHY blocks appear on the wire.
_PHY_ORDER = (ScanPhy.LE_1M, ScanPhy.LE_2M, ScanPhy.LE_CODED)


@unique
class PeriodicSyncFilterPolicy(IntEnum):
    """How `LE_Periodic_Advertising_Create_Sync` picks the advertiser."""

    USE_PARAMS = 0x00          # match SID + address given here
    USE_PERIODIC_ADV_LIST = 0x01


class PeriodicSyncOptions(IntFlag):
    USE_PERIODIC_ADV_LIST = 0x01
    REPORTS_INITIALLY_DISABLED = 0x02
    DUPLICATE_FILTERING_ENABLED = 0x04


def _phy_blocks(scan_phys: Mapping[int, Tuple[int, int, int]]
                ) -> Tuple[int, list]:
    """Turn {phy: (type, interval, window)} into (bitmap, ordered blocks)."""
    bitmap = 0
    blocks = []
    for phy in _PHY_ORDER:
        entry = scan_phys.get(int(phy)) or scan_phys.get(phy)
        if entry is None:
            continue
        bitmap |= int(phy)
        blocks.append(tuple(entry))
    return bitmap, blocks


class LeSetExtendedScanParameters(HciCmdBasePacket):
    """
    LE Set Extended Scan Parameters Command (0x2041).

    `scan_phys` maps a `ScanPhy` to `(scan_type, scan_interval, scan_window)`,
    with the interval/window in 0.625 ms units. Must be sent while scanning is
    disabled.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_SCAN_PARAMETERS)
    NAME = "LE_Set_Extended_Scan_Parameters"

    def __init__(self, own_address_type: int = 0x00,
                 scanning_filter_policy: int = 0x00,
                 scan_phys: Mapping[int, Tuple[int, int, int]] = None):
        if scan_phys is None:
            scan_phys = {int(ScanPhy.LE_1M): (0x01, 0x0060, 0x0030)}
        super().__init__(own_address_type=own_address_type,
                         scanning_filter_policy=scanning_filter_policy,
                         scan_phys={int(k): tuple(v) for k, v in scan_phys.items()})

    def _validate_params(self) -> None:
        p = self.params
        if not p['scan_phys']:
            raise ValueError("at least one scanning PHY is required")
        if int(ScanPhy.LE_2M) in p['scan_phys']:
            raise ValueError("LE 2M cannot be used for scanning; it carries no "
                             "primary advertising channel")
        for phy, (scan_type, interval, window) in p['scan_phys'].items():
            if phy not in (int(ScanPhy.LE_1M), int(ScanPhy.LE_CODED)):
                raise ValueError(f"Invalid scanning PHY: 0x{phy:02X}")
            if scan_type not in (0x00, 0x01):
                raise ValueError(f"Invalid scan_type {scan_type} for PHY 0x{phy:02X}")
            if not (0x0004 <= interval <= 0xFFFF):
                raise ValueError(f"scan_interval 0x{interval:04X} out of range "
                                 "(0x0004..0xFFFF)")
            if not (0x0004 <= window <= 0xFFFF):
                raise ValueError(f"scan_window 0x{window:04X} out of range "
                                 "(0x0004..0xFFFF)")
            if window > interval:
                raise ValueError("scan_window must be <= scan_interval")

    def _serialize_params(self) -> bytes:
        p = self.params
        bitmap, blocks = _phy_blocks(p['scan_phys'])
        out = bytearray([p['own_address_type'], p['scanning_filter_policy'], bitmap])
        # One {type, interval, window} block per PHY, in ascending bit order --
        # the fields are interleaved per PHY, not three parallel arrays.
        for scan_type, interval, window in blocks:
            out += struct.pack("<BHH", scan_type, interval, window)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetExtendedScanParameters":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 3")
        own_type, policy, bitmap = data[0], data[1], data[2]
        phys = [phy for phy in _PHY_ORDER if bitmap & int(phy)]
        count = len(phys)
        needed = 3 + count * 5
        if len(data) < needed:
            raise ValueError(f"Invalid data length: {len(data)}, expected {needed}")

        scan_phys = {
            int(phy): struct.unpack_from("<BHH", data, 3 + i * 5)
            for i, phy in enumerate(phys)
        }
        return cls(own_type, policy, scan_phys)


class LeSetExtendedScanEnable(HciCmdBasePacket):
    """
    LE Set Extended Scan Enable Command (0x2042).

    `duration` is in 10 ms units (0 = until disabled) and `period` in 1.28 s
    units (0 = scan continuously rather than in bursts). A non-zero duration
    ends with an LE Scan Timeout event.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_SCAN_ENABLE)
    NAME = "LE_Set_Extended_Scan_Enable"

    def __init__(self, enable: bool = True, filter_duplicates: int = 0x01,
                 duration: int = 0x0000, period: int = 0x0000):
        super().__init__(enable=bool(enable),
                         filter_duplicates=int(filter_duplicates),
                         duration=duration, period=period)

    def _validate_params(self) -> None:
        p = self.params
        if p['filter_duplicates'] not in (0x00, 0x01, 0x02):
            raise ValueError(f"Invalid filter_duplicates: {p['filter_duplicates']}")
        if not (0x0000 <= p['duration'] <= 0xFFFF):
            raise ValueError(f"duration {p['duration']} out of range")
        if not (0x0000 <= p['period'] <= 0xFFFF):
            raise ValueError(f"period {p['period']} out of range")
        if p['period'] and p['duration'] and p['duration'] * 10 >= p['period'] * 1280:
            raise ValueError("duration must be shorter than period")

    def _serialize_params(self) -> bytes:
        p = self.params
        return struct.pack("<BBHH", 0x01 if p['enable'] else 0x00,
                           p['filter_duplicates'], p['duration'], p['period'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetExtendedScanEnable":
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected 6")
        enable, filter_dup, duration, period = struct.unpack_from("<BBHH", data, 0)
        return cls(bool(enable), filter_dup, duration, period)


class LePeriodicAdvertisingCreateSync(HciCmdBasePacket):
    """
    LE Periodic Advertising Create Sync Command (0x2044).

    Scanning must be running (0x2042) for the controller to find the train;
    otherwise this sits pending until it is cancelled or times out.

    `skip` is how many periodic events may be ignored, `sync_timeout` is in
    10 ms units.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.PERIODIC_ADV_CREATE_SYNC)
    NAME = "LE_Periodic_Advertising_Create_Sync"

    def __init__(self, adv_sid: int = 0x00,
                 advertiser_address: Union[bytes, str] = b"\x00" * 6,
                 advertiser_address_type: int = 0x00,
                 options: int = 0x00,
                 skip: int = 0x0000,
                 sync_timeout: int = 0x03E8,       # 10 s
                 sync_cte_type: int = 0x00):
        super().__init__(options=int(options), adv_sid=adv_sid,
                         advertiser_address_type=advertiser_address_type,
                         advertiser_address=_coerce_addr(advertiser_address),
                         skip=skip, sync_timeout=sync_timeout,
                         sync_cte_type=sync_cte_type)

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['adv_sid'] <= 0x0F):
            raise ValueError(f"adv_sid {p['adv_sid']} out of range (0x00..0x0F)")
        if p['advertiser_address_type'] not in (0x00, 0x01):
            raise ValueError(f"Invalid advertiser_address_type: "
                             f"{p['advertiser_address_type']}")
        if not (0x0000 <= p['skip'] <= 0x01F3):
            raise ValueError(f"skip {p['skip']} out of range (0..499)")
        if not (0x000A <= p['sync_timeout'] <= 0x4000):
            raise ValueError(f"sync_timeout 0x{p['sync_timeout']:04X} out of range "
                             "(0x000A..0x4000)")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([p['options'], p['adv_sid'], p['advertiser_address_type']])
                + bytes(reversed(p['advertiser_address']))
                + struct.pack("<HHB", p['skip'], p['sync_timeout'],
                              p['sync_cte_type']))

    @classmethod
    def from_bytes(cls, data: bytes) -> "LePeriodicAdvertisingCreateSync":
        if len(data) < 14:
            raise ValueError(f"Invalid data length: {len(data)}, expected 14")
        options, sid, addr_type = data[0], data[1], data[2]
        address = bytes(reversed(data[3:9]))
        skip, timeout, cte = struct.unpack_from("<HHB", data, 9)
        return cls(sid, address, addr_type, options, skip, timeout, cte)


class LePeriodicAdvertisingCreateSyncCancel(HciCmdBasePacket):
    """LE Periodic Advertising Create Sync Cancel Command (0x2045)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.PERIODIC_ADV_CREATE_SYNC_CANCEL)
    NAME = "LE_Periodic_Advertising_Create_Sync_Cancel"

    def __init__(self):
        super().__init__()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LePeriodicAdvertisingCreateSyncCancel":
        return cls()


class LePeriodicAdvertisingTerminateSync(HciCmdBasePacket):
    """LE Periodic Advertising Terminate Sync Command (0x2046)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.PERIODIC_ADV_TERMINATE_SYNC)
    NAME = "LE_Periodic_Advertising_Terminate_Sync"

    def __init__(self, sync_handle: int = 0x0000):
        super().__init__(sync_handle=sync_handle)

    def _validate_params(self) -> None:
        if not (0x0000 <= self.params['sync_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid sync_handle: 0x{self.params['sync_handle']:04X}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['sync_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LePeriodicAdvertisingTerminateSync":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


class LeSetPeriodicAdvertisingReceiveEnable(HciCmdBasePacket):
    """
    LE Set Periodic Advertising Receive Enable Command (0x2059).

    Pauses or resumes reports for a sync without losing it -- cheaper than
    terminating and re-establishing when you only want to stop the flood.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADV_RECEIVE_ENABLE)
    NAME = "LE_Set_Periodic_Advertising_Receive_Enable"

    #: Enable bit 1: also generate Duplicate-filtered reports.
    DUPLICATE_FILTERING = 0x02

    def __init__(self, sync_handle: int = 0x0000, enable: Union[bool, int] = True):
        super().__init__(sync_handle=sync_handle, enable=int(enable))

    def _validate_params(self) -> None:
        if not (0x0000 <= self.params['sync_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid sync_handle: 0x{self.params['sync_handle']:04X}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['sync_handle'],
                           self.params['enable'] & 0xFF)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetPeriodicAdvertisingReceiveEnable":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, enable = struct.unpack_from("<HB", data, 0)
        return cls(handle, enable)


# ------------------------------------------------------------ helper builders

def le_set_extended_scan_parameters(scan_type: int = 0x01,
                                    scan_interval: int = 0x0060,
                                    scan_window: int = 0x0030,
                                    own_address_type: int = 0x00,
                                    filter_policy: int = 0x00,
                                    coded: bool = False
                                    ) -> LeSetExtendedScanParameters:
    """Single-PHY scan parameters -- 1M, plus Coded when `coded` is set."""
    phys: Dict[int, Tuple[int, int, int]] = {
        int(ScanPhy.LE_1M): (scan_type, scan_interval, scan_window)
    }
    if coded:
        phys[int(ScanPhy.LE_CODED)] = (scan_type, scan_interval, scan_window)
    return LeSetExtendedScanParameters(own_address_type, filter_policy, phys)


def le_set_extended_scan_enable(enable: bool = True, filter_duplicates: int = 0x01,
                                duration: int = 0x0000, period: int = 0x0000):
    return LeSetExtendedScanEnable(enable, filter_duplicates, duration, period)


def le_periodic_advertising_create_sync(adv_sid, advertiser_address, **kwargs):
    return LePeriodicAdvertisingCreateSync(adv_sid, advertiser_address, **kwargs)


def le_periodic_advertising_create_sync_cancel():
    return LePeriodicAdvertisingCreateSyncCancel()


def le_periodic_advertising_terminate_sync(sync_handle):
    return LePeriodicAdvertisingTerminateSync(sync_handle)


def le_set_periodic_advertising_receive_enable(sync_handle, enable=True):
    return LeSetPeriodicAdvertisingReceiveEnable(sync_handle, enable)


for _cls in (LeSetExtendedScanParameters, LeSetExtendedScanEnable,
             LePeriodicAdvertisingCreateSync, LePeriodicAdvertisingCreateSyncCancel,
             LePeriodicAdvertisingTerminateSync,
             LeSetPeriodicAdvertisingReceiveEnable):
    register_command(_cls)
del _cls


__all__ = [
    'ScanPhy',
    'PeriodicSyncFilterPolicy',
    'PeriodicSyncOptions',
    'LeSetExtendedScanParameters',
    'LeSetExtendedScanEnable',
    'LePeriodicAdvertisingCreateSync',
    'LePeriodicAdvertisingCreateSyncCancel',
    'LePeriodicAdvertisingTerminateSync',
    'LeSetPeriodicAdvertisingReceiveEnable',
    'le_set_extended_scan_parameters',
    'le_set_extended_scan_enable',
    'le_periodic_advertising_create_sync',
    'le_periodic_advertising_create_sync_cancel',
    'le_periodic_advertising_terminate_sync',
    'le_set_periodic_advertising_receive_enable',
]
