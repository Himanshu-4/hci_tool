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


class LeSetHostChannelClassification(HciCmdBasePacket):
    """
    LE Set Host Channel Classification Command (0x2014).

    Tells the controller which of the 37 data channels the host believes are
    usable, as a 5-octet bitmap (bit 0 = channel 0). Channels 37-39 are the
    advertising channels and are not covered.

    The controller only applies this to connections where it is the central, and
    the spec requires at least two channels to remain enabled -- a map with
    fewer is rejected with Invalid HCI Command Parameters.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_HOST_CHANNEL_CLASSIFICATION)
    NAME = "LE_Set_Host_Channel_Classification"

    CHANNEL_MAP_LENGTH = 5
    NUM_CHANNELS = 37

    #: All 37 data channels enabled -- the controller's own default.
    ALL_CHANNELS = b"\xFF\xFF\xFF\xFF\x1F"

    def __init__(self, channel_map: bytes = ALL_CHANNELS):
        super().__init__(channel_map=bytes(channel_map))

    def _validate_params(self) -> None:
        channel_map = self.params['channel_map']
        if len(channel_map) != self.CHANNEL_MAP_LENGTH:
            raise ValueError(f"channel_map must be {self.CHANNEL_MAP_LENGTH} bytes, "
                             f"got {len(channel_map)}")

        value = int.from_bytes(channel_map, "little")
        if value >> self.NUM_CHANNELS:
            raise ValueError(
                "channel_map sets bits above channel 36; the top 3 bits of the "
                "last octet are reserved")
        if bin(value).count("1") < 2:
            raise ValueError(
                f"at least 2 channels must stay enabled, got {bin(value).count('1')}")

    def _serialize_params(self) -> bytes:
        return self.params['channel_map']

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetHostChannelClassification":
        if len(data) < cls.CHANNEL_MAP_LENGTH:
            raise ValueError(f"Invalid data length: {len(data)}, "
                             f"expected {cls.CHANNEL_MAP_LENGTH}")
        return cls(data[:cls.CHANNEL_MAP_LENGTH])

    @classmethod
    def from_channels(cls, channels) -> "LeSetHostChannelClassification":
        """Build the bitmap from an iterable of enabled channel numbers."""
        value = 0
        for channel in channels:
            if not (0 <= channel < cls.NUM_CHANNELS):
                raise ValueError(f"channel {channel} out of range (0..36)")
            value |= 1 << channel
        return cls(value.to_bytes(cls.CHANNEL_MAP_LENGTH, "little"))

    def enabled_channels(self) -> list:
        """The channel numbers this map enables."""
        value = int.from_bytes(self.params['channel_map'], "little")
        return [ch for ch in range(self.NUM_CHANNELS) if value >> ch & 1]

    def __str__(self) -> str:
        enabled = self.enabled_channels()
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"({len(enabled)}/{self.NUM_CHANNELS} channels enabled)")


class LeReadChannelMap(HciCmdBasePacket):
    """
    LE Read Channel Map Command (0x2015).

    Returns the map actually in use on a connection, which is the intersection
    of the host classification above and the controller's own assessment -- so
    it is the way to check whether a classification took effect.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_CHANNEL_MAP)
    NAME = "LE_Read_Channel_Map"

    def __init__(self, connection_handle: int = 0x0000):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        handle = self.params['connection_handle']
        if not (0x0000 <= handle <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: 0x{handle:04X}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadChannelMap":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


def le_set_event_mask(event_mask: int = LeSetEventMask.DEFAULT_MASK) -> LeSetEventMask:
    return LeSetEventMask(event_mask)


def le_read_buffer_size() -> LeReadBufferSize:
    return LeReadBufferSize()


def le_read_local_supported_features() -> LeReadLocalSupportedFeatures:
    return LeReadLocalSupportedFeatures()


def le_read_supported_states() -> LeReadSupportedStates:
    return LeReadSupportedStates()


def le_set_host_channel_classification(
        channel_map: bytes = LeSetHostChannelClassification.ALL_CHANNELS
) -> LeSetHostChannelClassification:
    return LeSetHostChannelClassification(channel_map)


def le_read_channel_map(connection_handle: int) -> LeReadChannelMap:
    return LeReadChannelMap(connection_handle)


register_command(LeSetEventMask)
register_command(LeReadBufferSize)
register_command(LeReadLocalSupportedFeatures)
register_command(LeReadSupportedStates)
register_command(LeSetHostChannelClassification)
register_command(LeReadChannelMap)


__all__ = [
    'LeSetEventMask',
    'LeReadBufferSize',
    'LeReadLocalSupportedFeatures',
    'LeReadSupportedStates',
    'LeSetHostChannelClassification',
    'LeReadChannelMap',
    'le_set_event_mask',
    'le_read_buffer_size',
    'le_read_local_supported_features',
    'le_read_supported_states',
    'le_set_host_channel_classification',
    'le_read_channel_map',
]
