"""
Connectionless Peripheral Broadcast and synchronization train commands.

    0x0441  Set_Connectionless_Peripheral_Broadcast
    0x0442  Set_Connectionless_Peripheral_Broadcast_Receive
    0x0443  Start_Synchronization_Train
    0x0444  Receive_Synchronization_Train

These implement the BR/EDR broadcast mechanism used by Bluetooth audio
broadcast profiles. The transmitter enables a broadcast on a reserved LT_ADDR
and starts a synchronization train advertising it; receivers first find that
train (Receive_Synchronization_Train) and then join the broadcast
(Set_Connectionless_Peripheral_Broadcast_Receive) using the timing it carried.

The LT_ADDR has to be reserved first with Set_Reserved_LT_ADDR (0x0C66,
Controller & Baseband), or the enable is rejected.
"""

from __future__ import annotations

import struct
from typing import Union

from hci import bd_addr_str_to_bytes

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LinkControlOCF, OGF, create_opcode

#: Broadcast packet types, same bits as an ACL packet type mask.
CPB_PACKET_TYPE_DM1 = 0x0008
CPB_PACKET_TYPE_DH1 = 0x0010
CPB_PACKET_TYPE_DM3 = 0x0400
CPB_PACKET_TYPE_DH3 = 0x0800
CPB_PACKET_TYPE_DM5 = 0x4000
CPB_PACKET_TYPE_DH5 = 0x8000

#: A safe default: the basic-rate types every controller supports.
CPB_PACKET_TYPE_DEFAULT = (CPB_PACKET_TYPE_DM1 | CPB_PACKET_TYPE_DH1
                           | CPB_PACKET_TYPE_DM3 | CPB_PACKET_TYPE_DH3
                           | CPB_PACKET_TYPE_DM5 | CPB_PACKET_TYPE_DH5)

#: All 79 BR/EDR channels enabled, as a 10-octet AFH map.
AFH_CHANNEL_MAP_ALL = b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F"


def _coerce_addr(addr: Union[bytes, str]) -> bytes:
    if isinstance(addr, str):
        return bd_addr_str_to_bytes(addr)
    addr = bytes(addr)
    if len(addr) != 6:
        raise ValueError(f"Invalid address length {len(addr)}, must be 6 bytes")
    return addr


class SetConnectionlessPeripheralBroadcast(HciCmdBasePacket):
    """
    Set Connectionless Peripheral Broadcast Command (0x0441). Transmitter side.

    `lt_addr` must already be reserved with Set_Reserved_LT_ADDR. Disabling
    takes the same LT_ADDR; the other parameters are then ignored.
    """

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.SET_CONNECTIONLESS_PERIPHERAL_BROADCAST)
    NAME = "Set_Connectionless_Peripheral_Broadcast"

    def __init__(self, enable: Union[bool, int] = True,
                 lt_addr: int = 0x01,
                 lpo_allowed: Union[bool, int] = True,
                 packet_type: int = CPB_PACKET_TYPE_DEFAULT,
                 interval_min: int = 0x0050,        # in 0.625 ms slots
                 interval_max: int = 0x0070,
                 supervision_timeout: int = 0x0BB8):
        super().__init__(enable=int(bool(enable)), lt_addr=lt_addr,
                         lpo_allowed=int(bool(lpo_allowed)),
                         packet_type=packet_type,
                         interval_min=interval_min, interval_max=interval_max,
                         supervision_timeout=supervision_timeout)

    def _validate_params(self) -> None:
        p = self.params
        if not (0x01 <= p['lt_addr'] <= 0x07):
            raise ValueError(f"lt_addr {p['lt_addr']} out of range (1..7)")
        for name in ("interval_min", "interval_max"):
            if not (0x0002 <= p[name] <= 0xFFFE):
                raise ValueError(f"{name} 0x{p[name]:04X} out of range "
                                 "(0x0002..0xFFFE)")
            if p[name] % 2:
                raise ValueError(f"{name} must be even -- the interval is "
                                 "measured in pairs of slots")
        if p['interval_min'] > p['interval_max']:
            raise ValueError("interval_min must be <= interval_max")
        if not (0x0002 <= p['supervision_timeout'] <= 0xFFFE):
            raise ValueError(f"supervision_timeout 0x{p['supervision_timeout']:04X} "
                             "out of range (0x0002..0xFFFE)")

    def _serialize_params(self) -> bytes:
        p = self.params
        return struct.pack("<BBBHHHH", p['enable'], p['lt_addr'],
                           p['lpo_allowed'], p['packet_type'],
                           p['interval_min'], p['interval_max'],
                           p['supervision_timeout'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "SetConnectionlessPeripheralBroadcast":
        if len(data) < 11:
            raise ValueError(f"Invalid data length: {len(data)}, expected 11")
        (enable, lt_addr, lpo, packet_type, itv_min, itv_max,
         timeout) = struct.unpack_from("<BBBHHHH", data, 0)
        return cls(enable, lt_addr, lpo, packet_type, itv_min, itv_max, timeout)

    def __str__(self) -> str:
        p = self.params
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"({'enable' if p['enable'] else 'disable'} LT_ADDR "
                f"{p['lt_addr']})")


class SetConnectionlessPeripheralBroadcastReceive(HciCmdBasePacket):
    """
    Set Connectionless Peripheral Broadcast Receive Command (0x0442). Receiver.

    Every timing parameter here comes from the Synchronization Train Received
    event -- this command does not discover anything, it just joins a broadcast
    whose schedule is already known.
    """

    OPCODE = create_opcode(
        OGF.LINK_CONTROL,
        LinkControlOCF.SET_CONNECTIONLESS_PERIPHERAL_BROADCAST_RECIEVE)
    NAME = "Set_Connectionless_Peripheral_Broadcast_Receive"

    AFH_CHANNEL_MAP_LENGTH = 10

    def __init__(self, enable: Union[bool, int] = True,
                 bd_addr: Union[bytes, str] = b"\x00" * 6,
                 lt_addr: int = 0x01,
                 interval: int = 0x0050,
                 clock_offset: int = 0x00000000,
                 next_cpb_clock: int = 0x00000000,
                 supervision_timeout: int = 0x0BB8,
                 remote_timing_accuracy: int = 0x00,
                 skip: int = 0x00,
                 packet_type: int = CPB_PACKET_TYPE_DEFAULT,
                 afh_channel_map: bytes = AFH_CHANNEL_MAP_ALL):
        super().__init__(enable=int(bool(enable)), bd_addr=_coerce_addr(bd_addr),
                         lt_addr=lt_addr, interval=interval,
                         clock_offset=clock_offset, next_cpb_clock=next_cpb_clock,
                         supervision_timeout=supervision_timeout,
                         remote_timing_accuracy=remote_timing_accuracy,
                         skip=skip, packet_type=packet_type,
                         afh_channel_map=bytes(afh_channel_map))

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        if not (0x01 <= p['lt_addr'] <= 0x07):
            raise ValueError(f"lt_addr {p['lt_addr']} out of range (1..7)")
        if not (0x0002 <= p['interval'] <= 0xFFFE):
            raise ValueError(f"interval 0x{p['interval']:04X} out of range")
        # Both clocks are 28-bit fields carried in 4 octets.
        for name in ("clock_offset", "next_cpb_clock"):
            if not (0 <= p[name] <= 0x0FFFFFFF):
                raise ValueError(f"{name} 0x{p[name]:X} does not fit in 28 bits")
        if len(p['afh_channel_map']) != self.AFH_CHANNEL_MAP_LENGTH:
            raise ValueError(f"afh_channel_map must be "
                             f"{self.AFH_CHANNEL_MAP_LENGTH} bytes, got "
                             f"{len(p['afh_channel_map'])}")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([p['enable']])
                + bytes(reversed(p['bd_addr']))
                + bytes([p['lt_addr']])
                + struct.pack("<HIIHBBH", p['interval'], p['clock_offset'],
                              p['next_cpb_clock'], p['supervision_timeout'],
                              p['remote_timing_accuracy'], p['skip'],
                              p['packet_type'])
                + p['afh_channel_map'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "SetConnectionlessPeripheralBroadcastReceive":
        if len(data) < 34:
            raise ValueError(f"Invalid data length: {len(data)}, expected 34")
        enable = data[0]
        bd_addr = bytes(reversed(data[1:7]))
        lt_addr = data[7]
        (interval, clock_offset, next_clock, timeout, accuracy, skip,
         packet_type) = struct.unpack_from("<HIIHBBH", data, 8)
        return cls(enable, bd_addr, lt_addr, interval, clock_offset, next_clock,
                   timeout, accuracy, skip, packet_type, data[24:34])


class StartSynchronizationTrain(HciCmdBasePacket):
    """
    Start Synchronization Train Command (0x0443).

    Broadcasts the timing receivers need to find the CPB. Answers with Command
    Status and later a Synchronization Train Complete.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.START_SYNCHRNONIZATION_TRAIN)
    NAME = "Start_Synchronization_Train"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "StartSynchronizationTrain":
        return cls()


class ReceiveSynchronizationTrain(HciCmdBasePacket):
    """
    Receive Synchronization Train Command (0x0444). Receiver side.

    Scans for the transmitter's synchronization train. On success the
    Synchronization Train Received event carries the timing that
    Set_Connectionless_Peripheral_Broadcast_Receive then needs.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_SYNCHRONIZATION_TRAIN)
    NAME = "Receive_Synchronization_Train"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 sync_scan_timeout: int = 0x2710,     # 6.4 s, in 0.625 ms slots
                 sync_scan_window: int = 0x0100,
                 sync_scan_interval: int = 0x0200):
        super().__init__(bd_addr=_coerce_addr(bd_addr),
                         sync_scan_timeout=sync_scan_timeout,
                         sync_scan_window=sync_scan_window,
                         sync_scan_interval=sync_scan_interval)

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        if not (0x0002 <= p['sync_scan_timeout'] <= 0xFFFE):
            raise ValueError(f"sync_scan_timeout 0x{p['sync_scan_timeout']:04X} "
                             "out of range (0x0002..0xFFFE)")
        if not (0x0004 <= p['sync_scan_window'] <= 0xFFFE):
            raise ValueError(f"sync_scan_window 0x{p['sync_scan_window']:04X} "
                             "out of range (0x0004..0xFFFE)")
        if not (0x0004 <= p['sync_scan_interval'] <= 0xFFFE):
            raise ValueError(f"sync_scan_interval 0x{p['sync_scan_interval']:04X} "
                             "out of range (0x0004..0xFFFE)")
        if p['sync_scan_window'] > p['sync_scan_interval']:
            raise ValueError("sync_scan_window must be <= sync_scan_interval")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes(reversed(p['bd_addr']))
                + struct.pack("<HHH", p['sync_scan_timeout'],
                              p['sync_scan_window'], p['sync_scan_interval']))

    @classmethod
    def from_bytes(cls, data: bytes) -> "ReceiveSynchronizationTrain":
        if len(data) < 12:
            raise ValueError(f"Invalid data length: {len(data)}, expected 12")
        timeout, window, interval = struct.unpack_from("<HHH", data, 6)
        return cls(bytes(reversed(data[:6])), timeout, window, interval)


# ------------------------------------------------------------ helper builders

def set_connectionless_peripheral_broadcast(enable=True, lt_addr=1, **kwargs):
    return SetConnectionlessPeripheralBroadcast(enable, lt_addr, **kwargs)


def set_connectionless_peripheral_broadcast_receive(enable=True, bd_addr=b"\x00" * 6,
                                                    **kwargs):
    return SetConnectionlessPeripheralBroadcastReceive(enable, bd_addr, **kwargs)


def start_synchronization_train():
    return StartSynchronizationTrain()


def receive_synchronization_train(bd_addr, **kwargs):
    return ReceiveSynchronizationTrain(bd_addr, **kwargs)


for _cls in (SetConnectionlessPeripheralBroadcast,
             SetConnectionlessPeripheralBroadcastReceive,
             StartSynchronizationTrain, ReceiveSynchronizationTrain):
    register_command(_cls)
del _cls


__all__ = [
    'CPB_PACKET_TYPE_DM1',
    'CPB_PACKET_TYPE_DH1',
    'CPB_PACKET_TYPE_DM3',
    'CPB_PACKET_TYPE_DH3',
    'CPB_PACKET_TYPE_DM5',
    'CPB_PACKET_TYPE_DH5',
    'CPB_PACKET_TYPE_DEFAULT',
    'AFH_CHANNEL_MAP_ALL',
    'SetConnectionlessPeripheralBroadcast',
    'SetConnectionlessPeripheralBroadcastReceive',
    'StartSynchronizationTrain',
    'ReceiveSynchronizationTrain',
    'set_connectionless_peripheral_broadcast',
    'set_connectionless_peripheral_broadcast_receive',
    'start_synchronization_train',
    'receive_synchronization_train',
]
