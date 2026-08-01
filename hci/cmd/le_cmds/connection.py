"""
LE connection commands.

    0x200D  LE_Create_Connection
    0x200E  LE_Create_Connection_Cancel
    0x2013  LE_Connection_Update
    0x2016  LE_Read_Remote_Features
"""

from __future__ import annotations

import struct
from typing import Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode
from .advertisement import _coerce_addr


class LeCreateConnection(HciCmdBasePacket):
    """
    LE Create Connection Command (0x200D).

    Note the controller will reject this with "Command Disallowed" (0x0C) if
    scanning is still enabled, so callers must disable scan first.

    Units: scan/connection intervals are 0.625 ms and 1.25 ms respectively;
    supervision timeout is 10 ms.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_CONNECTION)
    NAME = "LE_Create_Connection"

    def __init__(self,
                 peer_address: Union[bytes, str],
                 peer_address_type: int = 0x00,
                 own_address_type: int = 0x00,
                 scan_interval: int = 0x0060,          # 60 ms
                 scan_window: int = 0x0030,            # 30 ms
                 initiator_filter_policy: int = 0x00,  # use peer address
                 conn_interval_min: int = 0x0018,      # 30 ms
                 conn_interval_max: int = 0x0028,      # 50 ms
                 conn_latency: int = 0x0000,
                 supervision_timeout: int = 0x01F4,    # 5 s
                 min_ce_length: int = 0x0000,
                 max_ce_length: int = 0x0000):
        super().__init__(
            scan_interval=scan_interval,
            scan_window=scan_window,
            initiator_filter_policy=initiator_filter_policy,
            peer_address_type=peer_address_type,
            peer_address=_coerce_addr(peer_address),
            own_address_type=own_address_type,
            conn_interval_min=conn_interval_min,
            conn_interval_max=conn_interval_max,
            conn_latency=conn_latency,
            supervision_timeout=supervision_timeout,
            min_ce_length=min_ce_length,
            max_ce_length=max_ce_length,
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x0004 <= p['scan_interval'] <= 0x4000):
            raise ValueError(f"scan_interval 0x{p['scan_interval']:04X} out of range "
                             "(0x0004..0x4000)")
        if not (0x0004 <= p['scan_window'] <= 0x4000):
            raise ValueError(f"scan_window 0x{p['scan_window']:04X} out of range "
                             "(0x0004..0x4000)")
        if p['scan_window'] > p['scan_interval']:
            raise ValueError("scan_window must be <= scan_interval")
        if not (0x0006 <= p['conn_interval_min'] <= 0x0C80):
            raise ValueError(f"conn_interval_min 0x{p['conn_interval_min']:04X} out of "
                             "range (0x0006..0x0C80)")
        if not (0x0006 <= p['conn_interval_max'] <= 0x0C80):
            raise ValueError(f"conn_interval_max 0x{p['conn_interval_max']:04X} out of "
                             "range (0x0006..0x0C80)")
        if p['conn_interval_min'] > p['conn_interval_max']:
            raise ValueError("conn_interval_min must be <= conn_interval_max")
        if not (0x0000 <= p['conn_latency'] <= 0x01F3):
            raise ValueError(f"conn_latency {p['conn_latency']} out of range (0..499)")
        if not (0x000A <= p['supervision_timeout'] <= 0x0C80):
            raise ValueError(f"supervision_timeout 0x{p['supervision_timeout']:04X} out "
                             "of range (0x000A..0x0C80)")
        # Core spec constraint: timeout must exceed the effective connection interval.
        effective = (1 + p['conn_latency']) * p['conn_interval_max'] * 2
        if p['supervision_timeout'] * 8 <= effective:
            raise ValueError(
                "supervision_timeout too small for the requested interval/latency "
                f"(need > {effective / 8:.0f} in 10ms units, got {p['supervision_timeout']})"
            )
        if p['peer_address_type'] not in (0x00, 0x01, 0x02, 0x03):
            raise ValueError(f"Invalid peer_address_type: {p['peer_address_type']}")
        if p['own_address_type'] not in (0x00, 0x01, 0x02, 0x03):
            raise ValueError(f"Invalid own_address_type: {p['own_address_type']}")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (
            struct.pack("<HHBB", p['scan_interval'], p['scan_window'],
                        p['initiator_filter_policy'], p['peer_address_type'])
            + bytes(reversed(p['peer_address']))
            + struct.pack("<BHHHHHH", p['own_address_type'],
                          p['conn_interval_min'], p['conn_interval_max'],
                          p['conn_latency'], p['supervision_timeout'],
                          p['min_ce_length'], p['max_ce_length'])
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCreateConnection":
        if len(data) < 25:
            raise ValueError(f"Invalid data length: {len(data)}, expected 25")
        scan_itv, scan_win, policy, peer_type = struct.unpack_from("<HHBB", data, 0)
        peer = bytes(reversed(data[6:12]))
        own_type, itv_min, itv_max, latency, timeout, min_ce, max_ce = \
            struct.unpack_from("<BHHHHHH", data, 12)
        return cls(peer_address=peer, peer_address_type=peer_type,
                   own_address_type=own_type, scan_interval=scan_itv,
                   scan_window=scan_win, initiator_filter_policy=policy,
                   conn_interval_min=itv_min, conn_interval_max=itv_max,
                   conn_latency=latency, supervision_timeout=timeout,
                   min_ce_length=min_ce, max_ce_length=max_ce)


class LeCreateConnectionCancel(HciCmdBasePacket):
    """LE Create Connection Cancel Command (0x200E)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_CONNECTION_CANCEL)
    NAME = "LE_Create_Connection_Cancel"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCreateConnectionCancel":
        return cls()


class LeConnectionUpdate(HciCmdBasePacket):
    """LE Connection Update Command (0x2013)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CONNECTION_UPDATE)
    NAME = "LE_Connection_Update"

    def __init__(self, connection_handle: int,
                 conn_interval_min: int = 0x0018,
                 conn_interval_max: int = 0x0028,
                 conn_latency: int = 0x0000,
                 supervision_timeout: int = 0x01F4,
                 min_ce_length: int = 0x0000,
                 max_ce_length: int = 0x0000):
        super().__init__(connection_handle=connection_handle,
                         conn_interval_min=conn_interval_min,
                         conn_interval_max=conn_interval_max,
                         conn_latency=conn_latency,
                         supervision_timeout=supervision_timeout,
                         min_ce_length=min_ce_length,
                         max_ce_length=max_ce_length)

    def _validate_params(self) -> None:
        handle = self.params['connection_handle']
        if not (0x0000 <= handle <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: 0x{handle:04X}")
        if self.params['conn_interval_min'] > self.params['conn_interval_max']:
            raise ValueError("conn_interval_min must be <= conn_interval_max")

    def _serialize_params(self) -> bytes:
        p = self.params
        return struct.pack("<HHHHHHH", p['connection_handle'],
                           p['conn_interval_min'], p['conn_interval_max'],
                           p['conn_latency'], p['supervision_timeout'],
                           p['min_ce_length'], p['max_ce_length'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeConnectionUpdate":
        if len(data) < 14:
            raise ValueError(f"Invalid data length: {len(data)}, expected 14")
        (handle, itv_min, itv_max, latency, timeout, min_ce, max_ce) = \
            struct.unpack_from("<HHHHHHH", data, 0)
        return cls(handle, itv_min, itv_max, latency, timeout, min_ce, max_ce)


class LeReadRemoteFeatures(HciCmdBasePacket):
    """LE Read Remote Features Command (0x2016)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_REMOTE_USED_FEATURES)
    NAME = "LE_Read_Remote_Features"

    def __init__(self, connection_handle: int):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        handle = self.params['connection_handle']
        if not (0x0000 <= handle <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: 0x{handle:04X}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadRemoteFeatures":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


# ------------------------------------------------------------ helper builders

def le_create_connection(peer_address, **kwargs) -> LeCreateConnection:
    return LeCreateConnection(peer_address, **kwargs)


def le_create_connection_cancel() -> LeCreateConnectionCancel:
    return LeCreateConnectionCancel()


def le_connection_update(connection_handle: int, **kwargs) -> LeConnectionUpdate:
    return LeConnectionUpdate(connection_handle, **kwargs)


def le_read_remote_features(connection_handle: int) -> LeReadRemoteFeatures:
    return LeReadRemoteFeatures(connection_handle)


register_command(LeCreateConnection)
register_command(LeCreateConnectionCancel)
register_command(LeConnectionUpdate)
register_command(LeReadRemoteFeatures)


__all__ = [
    'LeCreateConnection',
    'LeCreateConnectionCancel',
    'LeConnectionUpdate',
    'LeReadRemoteFeatures',
    'le_create_connection',
    'le_create_connection_cancel',
    'le_connection_update',
    'le_read_remote_features',
]
