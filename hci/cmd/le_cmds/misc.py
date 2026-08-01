"""
LE controller information / setup commands.

    0x2001  LE_Set_Event_Mask
    0x2002  LE_Read_Buffer_Size
    0x2003  LE_Read_Local_Supported_Features
    0x201C  LE_Read_Supported_States
"""

from __future__ import annotations

import struct

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode


class LeSetEventMask(HciCmdBasePacket):
    """
    LE Set Event Mask Command (0x2001).

    The controller masks *all* LE meta events except LE Connection Complete by
    default on some parts, so this has to be sent during init or advertising
    reports never arrive.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EVENT_MASK)
    NAME = "LE_Set_Event_Mask"

    #: Bits 0..12: connection complete, advertising report, connection update,
    #: read remote features, LTK request, remote conn param req, data length
    #: change, key gen complete, generate DHKey complete, enhanced connection
    #: complete, directed advertising report, PHY update, extended adv report.
    DEFAULT_MASK = 0x00000000000001FF
    ALL_EVENTS = 0x000000000000FFFF

    def __init__(self, event_mask: int = DEFAULT_MASK):
        super().__init__(event_mask=event_mask)

    def _validate_params(self) -> None:
        mask = self.params['event_mask']
        if not (0 <= mask <= 0xFFFFFFFFFFFFFFFF):
            raise ValueError(f"event_mask 0x{mask:X} does not fit in 8 bytes")

    def _serialize_params(self) -> bytes:
        return struct.pack("<Q", self.params['event_mask'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetEventMask":
        if len(data) < 8:
            raise ValueError(f"Invalid data length: {len(data)}, expected 8")
        return cls(struct.unpack_from("<Q", data, 0)[0])


class LeReadBufferSize(HciCmdBasePacket):
    """LE Read Buffer Size Command (0x2002)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_BUFFER_SIZE)
    NAME = "LE_Read_Buffer_Size"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadBufferSize":
        return cls()


class LeReadLocalSupportedFeatures(HciCmdBasePacket):
    """LE Read Local Supported Features Command (0x2003)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_LOCAL_SUPPORTED_FEATURES)
    NAME = "LE_Read_Local_Supported_Features"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadLocalSupportedFeatures":
        return cls()


class LeReadSupportedStates(HciCmdBasePacket):
    """LE Read Supported States Command (0x201C)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_SUPPORTED_STATES)
    NAME = "LE_Read_Supported_States"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadSupportedStates":
        return cls()


def le_set_event_mask(event_mask: int = LeSetEventMask.DEFAULT_MASK) -> LeSetEventMask:
    return LeSetEventMask(event_mask)


def le_read_buffer_size() -> LeReadBufferSize:
    return LeReadBufferSize()


def le_read_local_supported_features() -> LeReadLocalSupportedFeatures:
    return LeReadLocalSupportedFeatures()


def le_read_supported_states() -> LeReadSupportedStates:
    return LeReadSupportedStates()


register_command(LeSetEventMask)
register_command(LeReadBufferSize)
register_command(LeReadLocalSupportedFeatures)
register_command(LeReadSupportedStates)


__all__ = [
    'LeSetEventMask',
    'LeReadBufferSize',
    'LeReadLocalSupportedFeatures',
    'LeReadSupportedStates',
    'le_set_event_mask',
    'le_read_buffer_size',
    'le_read_local_supported_features',
    'le_read_supported_states',
]
