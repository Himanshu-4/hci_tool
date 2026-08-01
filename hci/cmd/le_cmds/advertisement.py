"""
LE advertising commands.

Covers what the advertise flow needs beyond `controller_config.py`
(LE_Set_Advertising_Parameters / LE_Set_Advertising_Data already live there):

    0x2005  LE_Set_Random_Address
    0x2007  LE_Read_Advertising_Channel_Tx_Power
    0x2009  LE_Set_Scan_Response_Data
    0x200A  LE_Set_Advertise_Enable
"""

from __future__ import annotations

from typing import Optional, Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode


def _coerce_addr(addr: Union[bytes, str]) -> bytes:
    """
    Accept 'AA:BB:CC:DD:EE:FF' or 6 raw bytes, returning **display order**
    (most significant byte first).

    This is the convention used throughout the package: `params` hold a BD_ADDR
    the way you would read it out loud, and `_serialize_params` reverses it for
    the little-endian wire format. Mixing the two conventions silently pages the
    wrong device, so it is worth being strict about.
    """
    if isinstance(addr, str):
        parts = addr.replace("-", ":").split(":")
        if len(parts) != 6:
            raise ValueError(f"Invalid BD_ADDR: {addr!r}, expected XX:XX:XX:XX:XX:XX")
        return bytes(int(p, 16) for p in parts)
    addr = bytes(addr)
    if len(addr) != 6:
        raise ValueError(f"Invalid address length {len(addr)}, must be 6 bytes")
    return addr


class LeSetRandomAddress(HciCmdBasePacket):
    """LE Set Random Address Command (0x2005)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_RANDOM_ADDRESS)
    NAME = "LE_Set_Random_Address"

    def __init__(self, random_address: Union[bytes, str]):
        super().__init__(random_address=_coerce_addr(random_address))

    def _validate_params(self) -> None:
        addr = self.params['random_address']
        if len(addr) != 6:
            raise ValueError(f"random_address must be 6 bytes, got {len(addr)}")

    def _serialize_params(self) -> bytes:
        return bytes(reversed(self.params['random_address']))

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetRandomAddress":
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected 6")
        return cls(random_address=bytes(reversed(data[:6])))


class LeReadAdvertisingChannelTxPower(HciCmdBasePacket):
    """LE Read Advertising Channel TX Power Command (0x2007)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_ADVERTISING_CHANNEL_TX_POWER)
    NAME = "LE_Read_Advertising_Channel_Tx_Power"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadAdvertisingChannelTxPower":
        return cls()


class LeSetScanResponseData(HciCmdBasePacket):
    """
    LE Set Scan Response Data Command (0x2009).

    The payload always goes out as 31 zero-padded bytes preceded by a length
    byte. Sending a short parameter block instead is a common cause of
    "Invalid HCI Command Parameters".
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_SCAN_RESPONSE_DATA)
    NAME = "LE_Set_Scan_Response_Data"
    MAX_DATA = 31

    def __init__(self, data: bytes = b'', length: Optional[int] = None):
        data = bytes(data)
        super().__init__(data=data, length=len(data) if length is None else length)

    def _validate_params(self) -> None:
        if self.params['length'] > self.MAX_DATA:
            raise ValueError(
                f"scan response data is {self.params['length']} bytes, max {self.MAX_DATA}"
            )

    def _serialize_params(self) -> bytes:
        return bytes([self.params['length']]) + \
            self.params['data'].ljust(self.MAX_DATA, b'\x00')

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetScanResponseData":
        if len(data) < 1:
            raise ValueError("LE_Set_Scan_Response_Data: empty parameters")
        length = data[0]
        return cls(data=bytes(data[1:1 + length]), length=length)


class LeSetAdvertiseEnable(HciCmdBasePacket):
    """LE Set Advertise Enable Command (0x200A)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_ADVERTISE_ENABLE)
    NAME = "LE_Set_Advertise_Enable"

    def __init__(self, enable: Union[bool, int] = True):
        super().__init__(enable=int(bool(enable)))

    def _validate_params(self) -> None:
        if self.params['enable'] not in (0, 1):
            raise ValueError(f"enable must be 0 or 1, got {self.params['enable']}")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['enable']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetAdvertiseEnable":
        if len(data) < 1:
            raise ValueError("LE_Set_Advertise_Enable: empty parameters")
        return cls(enable=data[0])


# ------------------------------------------------------------ helper builders

def le_set_random_address(random_address: Union[bytes, str]) -> LeSetRandomAddress:
    return LeSetRandomAddress(random_address)


def le_read_advertising_channel_tx_power() -> LeReadAdvertisingChannelTxPower:
    return LeReadAdvertisingChannelTxPower()


def le_set_scan_response_data(data: bytes = b'') -> LeSetScanResponseData:
    return LeSetScanResponseData(data)


def le_set_advertise_enable(enable: bool = True) -> LeSetAdvertiseEnable:
    return LeSetAdvertiseEnable(enable)


register_command(LeSetRandomAddress)
register_command(LeReadAdvertisingChannelTxPower)
register_command(LeSetScanResponseData)
register_command(LeSetAdvertiseEnable)


__all__ = [
    'LeSetRandomAddress',
    'LeReadAdvertisingChannelTxPower',
    'LeSetScanResponseData',
    'LeSetAdvertiseEnable',
    'le_set_random_address',
    'le_read_advertising_channel_tx_power',
    'le_set_scan_response_data',
    'le_set_advertise_enable',
]
