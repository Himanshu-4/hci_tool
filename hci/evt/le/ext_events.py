"""
LE extended advertising, periodic advertising and scanning events.

    0x3E/0x0D  LE_Extended_Advertising_Report
    0x3E/0x0E  LE_Periodic_Advertising_Sync_Established
    0x3E/0x0F  LE_Periodic_Advertising_Report
    0x3E/0x10  LE_Periodic_Advertising_Sync_Lost
    0x3E/0x11  LE_Scan_Timeout
    0x3E/0x12  LE_Advertising_Set_Terminated
    0x3E/0x13  LE_Scan_Request_Received
    0x3E/0x14  LE_Channel_Selection_Algorithm

The extended advertising report is the one that matters for scanning: unlike the
legacy 0x02 report it carries the PHYs, the advertising SID and a *data status*
that says whether the payload is complete, still arriving in fragments, or was
truncated. A scanner that ignores `data_status` will show half a name and call
it a device.
"""

from __future__ import annotations

import struct
from typing import Optional

from .. import register_event
from ..error_codes import get_status_description
from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode, LeMetaEventSubCode
from .adv_data import parse_adv_data


def _addr_str(addr: bytes) -> str:
    return ":".join(f"{b:02X}" for b in addr)


#: `Event_Type` bits in the extended advertising report.
EXT_ADV_CONNECTABLE = 0x0001
EXT_ADV_SCANNABLE = 0x0002
EXT_ADV_DIRECTED = 0x0004
EXT_ADV_SCAN_RESPONSE = 0x0008
EXT_ADV_LEGACY = 0x0010

#: Bits 5-6 of `Event_Type`.
DATA_STATUS_COMPLETE = 0x00
DATA_STATUS_MORE_TO_COME = 0x01
DATA_STATUS_TRUNCATED = 0x02

_DATA_STATUS_NAMES = {
    DATA_STATUS_COMPLETE: "complete",
    DATA_STATUS_MORE_TO_COME: "more data",
    DATA_STATUS_TRUNCATED: "truncated",
    0x03: "reserved",
}

_PHY_NAMES = {0x00: "-", 0x01: "1M", 0x02: "2M", 0x03: "Coded"}


def phy_name(value: Optional[int]) -> str:
    """PHY code to a short label, for display."""
    if value is None:
        return "-"
    return _PHY_NAMES.get(value, f"0x{value:02X}")


def ext_event_type_str(event_type: int) -> str:
    """Decode the extended report's `Event_Type` bitfield into words."""
    bits = []
    if event_type & EXT_ADV_LEGACY:
        bits.append("legacy")
    if event_type & EXT_ADV_CONNECTABLE:
        bits.append("conn")
    if event_type & EXT_ADV_SCANNABLE:
        bits.append("scan")
    if event_type & EXT_ADV_DIRECTED:
        bits.append("directed")
    if event_type & EXT_ADV_SCAN_RESPONSE:
        bits.append("scan-rsp")
    if not bits:
        bits.append("ext")
    status = (event_type >> 5) & 0x03
    if status != DATA_STATUS_COMPLETE:
        bits.append(_DATA_STATUS_NAMES[status])
    return "+".join(bits)


class LeExtendedAdvertisingReportEvent(HciEvtBasePacket):
    """LE Extended Advertising Report Event (0x3E / 0x0D)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.EXTENDED_ADVERTISING_REPORT
    NAME = "LE_Extended_Advertising_Report"

    #: Fixed part of one report, before the variable-length data.
    _REPORT_HEADER = 24

    def __init__(self, reports: list):
        super().__init__(num_reports=len(reports), reports=reports)

    def _validate_params(self) -> None:
        if not self.params['reports']:
            raise ValueError("LE_Extended_Advertising_Report carries no reports")

    def _serialize_params(self) -> bytes:
        out = bytearray([int(self.SUB_EVENT_CODE), len(self.params['reports'])])
        for r in self.params['reports']:
            out += struct.pack("<HB", r['event_type'], r['address_type'])
            out += bytes(reversed(r['address']))
            out += bytes([r['primary_phy'], r['secondary_phy'], r['adv_sid']])
            # None means "not available", which is 0x7F on the wire.
            out += struct.pack("<bbH",
                               0x7F if r['tx_power'] is None else r['tx_power'],
                               0x7F if r['rssi'] is None else r['rssi'],
                               r['periodic_adv_interval'])
            out += bytes([r['direct_address_type']])
            out += bytes(reversed(r['direct_address']))
            out += bytes([len(r['data'])]) + r['data']
        return bytes(out)

    @classmethod
    def from_bytes_sub_event(cls, data: bytes,
                             sub_event_code: int) -> "LeExtendedAdvertisingReportEvent":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 2")

        num_reports = data[1]
        reports = []
        off = 2

        for _ in range(num_reports):
            # A truncated tail is normal when a controller batches reports and
            # the transport delivers a short packet; keep what parsed.
            if off + cls._REPORT_HEADER > len(data):
                break
            event_type = struct.unpack_from("<H", data, off)[0]
            address_type = data[off + 2]
            address = bytes(reversed(data[off + 3:off + 9]))
            primary_phy, secondary_phy, adv_sid = data[off + 9:off + 12]
            tx_power, rssi = struct.unpack_from("<bb", data, off + 12)
            periodic_interval = struct.unpack_from("<H", data, off + 14)[0]
            direct_address_type = data[off + 16]
            direct_address = bytes(reversed(data[off + 17:off + 23]))
            data_length = data[off + 23]
            if off + cls._REPORT_HEADER + data_length > len(data):
                break
            payload = bytes(data[off + 24:off + 24 + data_length])
            off += cls._REPORT_HEADER + data_length

            reports.append({
                'event_type': event_type,
                'event_type_str': ext_event_type_str(event_type),
                'data_status': (event_type >> 5) & 0x03,
                'legacy': bool(event_type & EXT_ADV_LEGACY),
                'address_type': address_type,
                'address': address,
                'address_str': _addr_str(address),
                'primary_phy': primary_phy,
                'secondary_phy': secondary_phy,
                'adv_sid': adv_sid,
                # 0x7F means the controller has no TX power to report.
                'tx_power': None if tx_power == 0x7F else tx_power,
                'rssi': None if rssi == 0x7F else rssi,
                'periodic_adv_interval': periodic_interval,
                'direct_address_type': direct_address_type,
                'direct_address': direct_address,
                'direct_address_str': _addr_str(direct_address),
                'data_length': data_length,
                'data': payload,
                'adv_data': parse_adv_data(payload),
            })

        if not reports:
            raise ValueError(
                f"LE_Extended_Advertising_Report: no complete report in {len(data)} bytes")
        return cls(reports)

    @property
    def reports(self) -> list:
        """Every report carried by this event."""
        return self.params.get('reports', [])

    def __str__(self) -> str:
        lines = []
        for r in self.reports:
            addr_kind = "random" if r['address_type'] in (0x01, 0x03) else "public"
            rssi = "-" if r['rssi'] is None else f"{r['rssi']}dBm"
            lines.append(
                f"{r['address_str']} ({addr_kind}) {r['event_type_str']} "
                f"SID={r['adv_sid']} PHY={phy_name(r['primary_phy'])}/"
                f"{phy_name(r['secondary_phy'])} RSSI={rssi} "
                f"{r['adv_data'].summary()}"
            )
        head = f"LE_Extended_Advertising_Report [{len(self.reports)}]"
        return f"{head}: " + " | ".join(lines) if lines else head


class LePeriodicAdvertisingSyncEstablishedEvent(HciEvtBasePacket):
    """LE Periodic Advertising Sync Established Event (0x3E / 0x0E)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_ESTABLISHED
    NAME = "LE_Periodic_Advertising_Sync_Established"

    def __init__(self, status: int, sync_handle: int, adv_sid: int,
                 advertiser_address_type: int, advertiser_address: bytes,
                 advertiser_phy: int, periodic_adv_interval: int,
                 advertiser_clock_accuracy: int):
        super().__init__(
            status=status,
            sync_handle=sync_handle,
            adv_sid=adv_sid,
            advertiser_address_type=advertiser_address_type,
            advertiser_address=advertiser_address,
            advertiser_address_str=_addr_str(advertiser_address),
            advertiser_phy=advertiser_phy,
            periodic_adv_interval=periodic_adv_interval,
            advertiser_clock_accuracy=advertiser_clock_accuracy,
        )

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([int(self.SUB_EVENT_CODE), p['status']])
                + struct.pack("<HBB", p['sync_handle'], p['adv_sid'],
                              p['advertiser_address_type'])
                + bytes(reversed(p['advertiser_address']))
                + struct.pack("<BHB", p['advertiser_phy'],
                              p['periodic_adv_interval'],
                              p['advertiser_clock_accuracy']))

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 16:
            raise ValueError(f"Invalid data length: {len(data)}, expected 16")
        status = data[1]
        sync_handle, adv_sid, addr_type = struct.unpack_from("<HBB", data, 2)
        address = bytes(reversed(data[6:12]))
        phy, interval, accuracy = struct.unpack_from("<BHB", data, 12)
        return cls(status, sync_handle, adv_sid, addr_type, address, phy,
                   interval, accuracy)

    def __str__(self) -> str:
        p = self.params
        if p['status'] != 0x00:
            return (f"LE_Periodic_Advertising_Sync_Established: FAILED "
                    f"{get_status_description(p['status'])} (0x{p['status']:02X})")
        return (f"LE_Periodic_Advertising_Sync_Established: "
                f"Sync=0x{p['sync_handle']:04X}, "
                f"Advertiser={p['advertiser_address_str']}, SID={p['adv_sid']}, "
                f"PHY={phy_name(p['advertiser_phy'])}, "
                f"Interval={p['periodic_adv_interval'] * 1.25:.2f}ms")


class LePeriodicAdvertisingReportEvent(HciEvtBasePacket):
    """LE Periodic Advertising Report Event (0x3E / 0x0F)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.PERIODIC_ADVERTISING_REPORT
    NAME = "LE_Periodic_Advertising_Report"

    def __init__(self, sync_handle: int, tx_power: Optional[int],
                 rssi: Optional[int], cte_type: int, data_status: int,
                 data: bytes):
        super().__init__(
            sync_handle=sync_handle,
            tx_power=tx_power,
            rssi=rssi,
            cte_type=cte_type,
            data_status=data_status,
            data_length=len(data),
            data=bytes(data),
            adv_data=parse_adv_data(bytes(data)),
        )

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([int(self.SUB_EVENT_CODE)])
                + struct.pack("<HbbBBB", p['sync_handle'],
                              0x7F if p['tx_power'] is None else p['tx_power'],
                              0x7F if p['rssi'] is None else p['rssi'],
                              p['cte_type'], p['data_status'], p['data_length'])
                + p['data'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 8:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 8")
        sync_handle, tx_power, rssi, cte_type, data_status, length = \
            struct.unpack_from("<HbbBBB", data, 1)
        payload = bytes(data[8:8 + length])
        return cls(sync_handle,
                   None if tx_power == 0x7F else tx_power,
                   None if rssi == 0x7F else rssi,
                   cte_type, data_status, payload)

    def __str__(self) -> str:
        p = self.params
        rssi = "-" if p['rssi'] is None else f"{p['rssi']}dBm"
        return (f"LE_Periodic_Advertising_Report: Sync=0x{p['sync_handle']:04X}, "
                f"RSSI={rssi}, {_DATA_STATUS_NAMES.get(p['data_status'], '?')}, "
                f"{p['adv_data'].summary()}")


class LePeriodicAdvertisingSyncLostEvent(HciEvtBasePacket):
    """LE Periodic Advertising Sync Lost Event (0x3E / 0x10)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_LOST
    NAME = "LE_Periodic_Advertising_Sync_Lost"

    def __init__(self, sync_handle: int):
        super().__init__(sync_handle=sync_handle)

    def _serialize_params(self) -> bytes:
        return bytes([int(self.SUB_EVENT_CODE)]) + struct.pack(
            "<H", self.params['sync_handle'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        return cls(struct.unpack_from("<H", data, 1)[0])

    def __str__(self) -> str:
        return (f"LE_Periodic_Advertising_Sync_Lost: "
                f"Sync=0x{self.params['sync_handle']:04X}")


class LeScanTimeoutEvent(HciEvtBasePacket):
    """
    LE Scan Timeout Event (0x3E / 0x11).

    Sent when an extended scan started with a non-zero duration finishes on its
    own. Scanning is off afterwards -- the host must re-enable it.
    """

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.SCAN_TIMEOUT
    NAME = "LE_Scan_Timeout"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return bytes([int(self.SUB_EVENT_CODE)])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        return cls()

    def __str__(self) -> str:
        return "LE_Scan_Timeout: extended scan duration elapsed, scanning stopped"


class LeAdvertisingSetTerminatedEvent(HciEvtBasePacket):
    """
    LE Advertising Set Terminated Event (0x3E / 0x12).

    A set stopped: either its duration/event limit ran out (status != 0) or it
    was consumed by an incoming connection, in which case `connection_handle`
    identifies the link.
    """

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.ADVERTISING_SET_TERMINATED
    NAME = "LE_Advertising_Set_Terminated"

    def __init__(self, status: int, adv_handle: int, connection_handle: int,
                 num_completed_ext_adv_events: int):
        super().__init__(status=status, adv_handle=adv_handle,
                         connection_handle=connection_handle,
                         num_completed_ext_adv_events=num_completed_ext_adv_events)

    def _serialize_params(self) -> bytes:
        p = self.params
        return bytes([int(self.SUB_EVENT_CODE)]) + struct.pack(
            "<BBHB", p['status'], p['adv_handle'], p['connection_handle'],
            p['num_completed_ext_adv_events'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected 6")
        status, adv_handle, conn_handle, num_events = \
            struct.unpack_from("<BBHB", data, 1)
        return cls(status, adv_handle, conn_handle, num_events)

    def __str__(self) -> str:
        p = self.params
        if p['status'] == 0x00:
            return (f"LE_Advertising_Set_Terminated: set {p['adv_handle']} "
                    f"connected as handle 0x{p['connection_handle']:04X}")
        return (f"LE_Advertising_Set_Terminated: set {p['adv_handle']} stopped, "
                f"{get_status_description(p['status'])} (0x{p['status']:02X}), "
                f"{p['num_completed_ext_adv_events']} events sent")


class LeScanRequestReceivedEvent(HciEvtBasePacket):
    """LE Scan Request Received Event (0x3E / 0x13)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.SCAN_REQUEST_RECEIVED
    NAME = "LE_Scan_Request_Received"

    def __init__(self, adv_handle: int, scanner_address_type: int,
                 scanner_address: bytes):
        super().__init__(adv_handle=adv_handle,
                         scanner_address_type=scanner_address_type,
                         scanner_address=scanner_address,
                         scanner_address_str=_addr_str(scanner_address))

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([int(self.SUB_EVENT_CODE), p['adv_handle'],
                       p['scanner_address_type']])
                + bytes(reversed(p['scanner_address'])))

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 9:
            raise ValueError(f"Invalid data length: {len(data)}, expected 9")
        return cls(data[1], data[2], bytes(reversed(data[3:9])))

    def __str__(self) -> str:
        p = self.params
        return (f"LE_Scan_Request_Received: set {p['adv_handle']} scanned by "
                f"{p['scanner_address_str']}")


class LeChannelSelectionAlgorithmEvent(HciEvtBasePacket):
    """LE Channel Selection Algorithm Event (0x3E / 0x14)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CHANNEL_SELECTION_ALGORITHM
    NAME = "LE_Channel_Selection_Algorithm"

    def __init__(self, connection_handle: int, channel_selection_algorithm: int):
        super().__init__(connection_handle=connection_handle,
                         channel_selection_algorithm=channel_selection_algorithm)

    def _serialize_params(self) -> bytes:
        p = self.params
        return bytes([int(self.SUB_EVENT_CODE)]) + struct.pack(
            "<HB", p['connection_handle'], p['channel_selection_algorithm'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4")
        handle, algorithm = struct.unpack_from("<HB", data, 1)
        return cls(handle, algorithm)

    def __str__(self) -> str:
        p = self.params
        return (f"LE_Channel_Selection_Algorithm: "
                f"Handle=0x{p['connection_handle']:04X}, "
                f"Algorithm=#{p['channel_selection_algorithm'] + 1}")


for _cls in (LeExtendedAdvertisingReportEvent,
             LePeriodicAdvertisingSyncEstablishedEvent,
             LePeriodicAdvertisingReportEvent,
             LePeriodicAdvertisingSyncLostEvent,
             LeScanTimeoutEvent,
             LeAdvertisingSetTerminatedEvent,
             LeScanRequestReceivedEvent,
             LeChannelSelectionAlgorithmEvent):
    register_event(_cls)
del _cls


__all__ = [
    'LeExtendedAdvertisingReportEvent',
    'LePeriodicAdvertisingSyncEstablishedEvent',
    'LePeriodicAdvertisingReportEvent',
    'LePeriodicAdvertisingSyncLostEvent',
    'LeScanTimeoutEvent',
    'LeAdvertisingSetTerminatedEvent',
    'LeScanRequestReceivedEvent',
    'LeChannelSelectionAlgorithmEvent',
    'ext_event_type_str',
    'phy_name',
    'DATA_STATUS_COMPLETE',
    'DATA_STATUS_MORE_TO_COME',
    'DATA_STATUS_TRUNCATED',
]
