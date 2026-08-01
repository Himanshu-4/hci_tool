"""
Additional LE meta events needed by the LE connect flow.

`LE_Enhanced_Connection_Complete` matters most: controllers that support LE
privacy report connections with subevent 0x0A instead of 0x01, so a stack that
only handles 0x01 silently never sees the connection come up.
"""

from __future__ import annotations

import struct
from typing import Optional, Union

from .. import register_event
from ..error_codes import StatusCode, get_status_description
from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode, LeMetaEventSubCode


def _addr_str(addr: bytes) -> str:
    return ":".join(f"{b:02X}" for b in addr)


class LeEnhancedConnectionCompleteEvent(HciEvtBasePacket):
    """LE Enhanced Connection Complete Event (0x3E / 0x0A)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.ENHANCED_CONNECTION_COMPLETE
    NAME = "LE_Enhanced_Connection_Complete"

    def __init__(self, status: int, connection_handle: int, role: int,
                 peer_address_type: int, peer_address: bytes,
                 local_resolvable_private_address: bytes,
                 peer_resolvable_private_address: bytes,
                 conn_interval: int, conn_latency: int,
                 supervision_timeout: int, central_clock_accuracy: int):
        if isinstance(status, StatusCode):
            status = status.value
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            role=role,
            peer_address_type=peer_address_type,
            peer_address=peer_address,
            peer_address_str=_addr_str(peer_address),
            local_resolvable_private_address=local_resolvable_private_address,
            peer_resolvable_private_address=peer_resolvable_private_address,
            conn_interval=conn_interval,
            conn_latency=conn_latency,
            supervision_timeout=supervision_timeout,
            central_clock_accuracy=central_clock_accuracy,
        )

    def _serialize_params(self) -> bytes:
        return (
            bytes([int(self.SUB_EVENT_CODE)])
            + struct.pack("<BHBB", self.params['status'],
                          self.params['connection_handle'], self.params['role'],
                          self.params['peer_address_type'])
            + bytes(reversed(self.params['peer_address']))
            + bytes(reversed(self.params['local_resolvable_private_address']))
            + bytes(reversed(self.params['peer_resolvable_private_address']))
            + struct.pack("<HHHB", self.params['conn_interval'],
                          self.params['conn_latency'],
                          self.params['supervision_timeout'],
                          self.params['central_clock_accuracy'])
        )

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 31:
            raise ValueError(f"LE_Enhanced_Connection_Complete too short: {len(data)}")
        _, status, handle, role, peer_type = struct.unpack_from("<BBHBB", data, 0)
        peer = bytes(reversed(data[6:12]))
        local_rpa = bytes(reversed(data[12:18]))
        peer_rpa = bytes(reversed(data[18:24]))
        interval, latency, timeout, accuracy = struct.unpack_from("<HHHB", data, 24)
        return cls(status, handle, role, peer_type, peer, local_rpa, peer_rpa,
                   interval, latency, timeout, accuracy)

    def __str__(self) -> str:
        if self.params['status'] != 0:
            return (f"LE_Enhanced_Connection_Complete: FAILED "
                    f"{get_status_description(self.params['status'])} "
                    f"(0x{self.params['status']:02X})")
        role = "central" if self.params['role'] == 0 else "peripheral"
        return (f"LE_Enhanced_Connection_Complete: Handle="
                f"0x{self.params['connection_handle']:04X}, "
                f"Peer={self.params['peer_address_str']}, Role={role}, "
                f"Interval={self.params['conn_interval'] * 1.25:.2f}ms, "
                f"Latency={self.params['conn_latency']}, "
                f"Timeout={self.params['supervision_timeout'] * 10}ms")


class LeDataLengthChangeEvent(HciEvtBasePacket):
    """LE Data Length Change Event (0x3E / 0x07)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.DATA_LENGTH_CHANGE
    NAME = "LE_Data_Length_Change"

    def __init__(self, connection_handle: int, max_tx_octets: int, max_tx_time: int,
                 max_rx_octets: int, max_rx_time: int):
        super().__init__(connection_handle=connection_handle,
                         max_tx_octets=max_tx_octets, max_tx_time=max_tx_time,
                         max_rx_octets=max_rx_octets, max_rx_time=max_rx_time)

    def _serialize_params(self) -> bytes:
        return bytes([int(self.SUB_EVENT_CODE)]) + struct.pack(
            "<HHHHH", self.params['connection_handle'], self.params['max_tx_octets'],
            self.params['max_tx_time'], self.params['max_rx_octets'],
            self.params['max_rx_time'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 11:
            raise ValueError(f"LE_Data_Length_Change too short: {len(data)}")
        handle, tx_o, tx_t, rx_o, rx_t = struct.unpack_from("<HHHHH", data, 1)
        return cls(handle, tx_o, tx_t, rx_o, rx_t)

    def __str__(self) -> str:
        return (f"LE_Data_Length_Change: Handle=0x{self.params['connection_handle']:04X}, "
                f"TX={self.params['max_tx_octets']}B/{self.params['max_tx_time']}us, "
                f"RX={self.params['max_rx_octets']}B/{self.params['max_rx_time']}us")


class LePhyUpdateCompleteEvent(HciEvtBasePacket):
    """LE PHY Update Complete Event (0x3E / 0x0C)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.PHY_UPDATE_COMPLETE
    NAME = "LE_PHY_Update_Complete"

    _PHY = {0x01: "1M", 0x02: "2M", 0x03: "Coded"}

    def __init__(self, status: int, connection_handle: int, tx_phy: int, rx_phy: int):
        super().__init__(status=status, connection_handle=connection_handle,
                         tx_phy=tx_phy, rx_phy=rx_phy)

    def _serialize_params(self) -> bytes:
        return bytes([int(self.SUB_EVENT_CODE)]) + struct.pack(
            "<BHBB", self.params['status'], self.params['connection_handle'],
            self.params['tx_phy'], self.params['rx_phy'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 6:
            raise ValueError(f"LE_PHY_Update_Complete too short: {len(data)}")
        status, handle, tx, rx = struct.unpack_from("<BHBB", data, 1)
        return cls(status, handle, tx, rx)

    def __str__(self) -> str:
        return (f"LE_PHY_Update_Complete: Handle=0x{self.params['connection_handle']:04X}, "
                f"TX={self._PHY.get(self.params['tx_phy'], '?')}, "
                f"RX={self._PHY.get(self.params['rx_phy'], '?')}, "
                f"Status={get_status_description(self.params['status'])}")


register_event(LeEnhancedConnectionCompleteEvent)
register_event(LeDataLengthChangeEvent)
register_event(LePhyUpdateCompleteEvent)


__all__ = [
    'LeEnhancedConnectionCompleteEvent',
    'LeDataLengthChangeEvent',
    'LePhyUpdateCompleteEvent',
]
