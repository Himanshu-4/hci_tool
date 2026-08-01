"""
Controller & Baseband commands needed by the connection flows.

    0x0C03  Reset                  <- was missing entirely
    0x0C1A  Write_Scan_Enable
    0x0C24  Write_Class_Of_Device
    0x0C56  Write_Simple_Pairing_Mode
    0x0C14  Read_Local_Name
    0x1005  Read_Buffer_Size       (Informational OGF, kept here for convenience)

`Reset` is the first command of every init sequence, so its absence blocked all
four flows.
"""

from __future__ import annotations

import struct
from enum import IntFlag, unique
from typing import Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import (
    ControllerBasebandOCF,
    InformationOCF,
    OGF,
    create_opcode,
)


@unique
class ScanEnable(IntFlag):
    """Discoverability / connectability bits for Write_Scan_Enable."""

    NONE = 0x00
    INQUIRY_SCAN = 0x01           # discoverable
    PAGE_SCAN = 0x02              # connectable
    BOTH = 0x03                   # discoverable + connectable


class Reset(HciCmdBasePacket):
    """
    HCI Reset Command (0x0C03).

    Resets the controller's link manager, baseband and state machines. Every
    init sequence starts here; expect a Command Complete and then a settling
    period on some parts before further commands are accepted.
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND, ControllerBasebandOCF.RESET)
    NAME = "Reset"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "Reset":
        return cls()


class WriteScanEnable(HciCmdBasePacket):
    """Write Scan Enable Command (0x0C1A)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND, ControllerBasebandOCF.WRITE_SCAN_ENABLE)
    NAME = "Write_Scan_Enable"

    def __init__(self, scan_enable: Union[int, ScanEnable] = ScanEnable.BOTH):
        super().__init__(scan_enable=int(scan_enable))

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['scan_enable'] <= 0x03):
            raise ValueError(
                f"Invalid scan_enable: 0x{self.params['scan_enable']:02X}, must be 0x00..0x03"
            )

    def _serialize_params(self) -> bytes:
        return bytes([self.params['scan_enable']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "WriteScanEnable":
        if len(data) < 1:
            raise ValueError("Write_Scan_Enable: empty parameters")
        return cls(scan_enable=data[0])

    def __str__(self) -> str:
        value = self.params['scan_enable']
        names = {0x00: "none", 0x01: "inquiry scan (discoverable)",
                 0x02: "page scan (connectable)",
                 0x03: "inquiry + page scan"}
        return f"Write_Scan_Enable : 0x{self.OPCODE:04X} ({names.get(value, hex(value))})"


class WriteClassOfDevice(HciCmdBasePacket):
    """Write Class of Device Command (0x0C24)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_CLASS_OF_DEVICE)
    NAME = "Write_Class_Of_Device"

    def __init__(self, class_of_device: int = 0x000000):
        super().__init__(class_of_device=class_of_device)

    def _validate_params(self) -> None:
        cod = self.params['class_of_device']
        if not (0x000000 <= cod <= 0xFFFFFF):
            raise ValueError(f"class_of_device 0x{cod:X} does not fit in 3 bytes")

    def _serialize_params(self) -> bytes:
        return self.params['class_of_device'].to_bytes(3, 'little')

    @classmethod
    def from_bytes(cls, data: bytes) -> "WriteClassOfDevice":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        return cls(int.from_bytes(data[:3], 'little'))


class WriteSimplePairingMode(HciCmdBasePacket):
    """
    Write Simple Pairing Mode Command (0x0C56).

    Not used by the POC flows themselves, but controllers reject
    Extended Inquiry Result reporting unless SSP is enabled, so it is worth
    having during BR/EDR bring-up.
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_SIMPLE_PAIRING_MODE)
    NAME = "Write_Simple_Pairing_Mode"

    def __init__(self, enabled: Union[bool, int] = True):
        super().__init__(simple_pairing_mode=int(bool(enabled)))

    def _serialize_params(self) -> bytes:
        return bytes([self.params['simple_pairing_mode']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "WriteSimplePairingMode":
        if len(data) < 1:
            raise ValueError("Write_Simple_Pairing_Mode: empty parameters")
        return cls(enabled=data[0])


class ReadLocalName(HciCmdBasePacket):
    """Read Local Name Command (0x0C14)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND, ControllerBasebandOCF.READ_LOCAL_NAME)
    NAME = "Read_Local_Name"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "ReadLocalName":
        return cls()


class ReadBufferSize(HciCmdBasePacket):
    """Read Buffer Size Command (0x1005) -- ACL/SCO buffer geometry."""

    OPCODE = create_opcode(OGF.INFORMATION, InformationOCF.READ_BUFFER_SIZE)
    NAME = "Read_Buffer_Size"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "ReadBufferSize":
        return cls()


# ------------------------------------------------------------ helper builders

def reset() -> Reset:
    return Reset()


def write_scan_enable(scan_enable: Union[int, ScanEnable] = ScanEnable.BOTH) -> WriteScanEnable:
    return WriteScanEnable(scan_enable)


def write_class_of_device(class_of_device: int) -> WriteClassOfDevice:
    return WriteClassOfDevice(class_of_device)


def write_simple_pairing_mode(enabled: bool = True) -> WriteSimplePairingMode:
    return WriteSimplePairingMode(enabled)


def read_local_name() -> ReadLocalName:
    return ReadLocalName()


def read_buffer_size() -> ReadBufferSize:
    return ReadBufferSize()


register_command(Reset)
register_command(WriteScanEnable)
register_command(WriteClassOfDevice)
register_command(WriteSimplePairingMode)
register_command(ReadLocalName)
register_command(ReadBufferSize)


__all__ = [
    'ScanEnable',
    'Reset',
    'WriteScanEnable',
    'WriteClassOfDevice',
    'WriteSimplePairingMode',
    'ReadLocalName',
    'ReadBufferSize',
    'reset',
    'write_scan_enable',
    'write_class_of_device',
    'write_simple_pairing_mode',
    'read_local_name',
    'read_buffer_size',
]
