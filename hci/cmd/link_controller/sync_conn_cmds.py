"""
Synchronous (SCO / eSCO) connection commands.

    0x0428  Setup_Synchronous_Connection
    0x0429  Accept_Synchronous_Connection_Request
    0x042A  Reject_Synchronous_Connection_Request
    0x043D  Enhanced_Setup_Synchronous_Connection
    0x043E  Enhanced_Accept_Synchronous_Connection_Request

The plain and enhanced forms do the same job. The difference is where the audio
is coded: the plain form assumes the controller does it and only takes a
`Voice_Setting` word, while the enhanced form describes both the air coding and
the host-side PCM path explicitly, which is what a transparent/mSBC link needs.

Bandwidths are in bytes per second: 8000 for narrowband CVSD, 16000 for mSBC.
`max_latency` is in milliseconds, 0xFFFF for "don't care".
"""

from __future__ import annotations

import struct
from enum import IntEnum, IntFlag, unique
from typing import Union

from hci import bd_addr_str_to_bytes

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LinkControlOCF, OGF, create_opcode


class SyncPacketType(IntFlag):
    """
    `Packet_Type` for the synchronous commands.

    The top four bits are inverted: setting them *excludes* the corresponding
    eSCO packet type. `EV3 | NO_2_EV3 | NO_3_EV3` therefore means "EV3 only, no
    EDR variants", which is the usual conservative choice.
    """

    HV1 = 0x0001
    HV2 = 0x0002
    HV3 = 0x0004
    EV3 = 0x0008
    EV4 = 0x0010
    EV5 = 0x0020
    NO_2_EV3 = 0x0040
    NO_3_EV3 = 0x0080
    NO_2_EV5 = 0x0100
    NO_3_EV5 = 0x0200


#: Everything a controller may pick, with no EDR exclusions.
SYNC_PACKET_TYPE_ANY = 0x003F
#: The safe eSCO default most stacks use for CVSD.
SYNC_PACKET_TYPE_EV3_ONLY = 0x0008 | 0x0040 | 0x0080 | 0x0100 | 0x0200
#: mSBC wideband: 2-EV3 allowed, everything else excluded.
SYNC_PACKET_TYPE_2EV3 = 0x0008 | 0x0080 | 0x0100 | 0x0200


@unique
class RetransmissionEffort(IntEnum):
    NO_RETRANSMISSION = 0x00
    OPTIMISE_POWER = 0x01
    OPTIMISE_QUALITY = 0x02
    DONT_CARE = 0xFF


#: Common `Voice_Setting` words: input coding, data format, sample size and the
#: air coding format packed into 10 bits.
VOICE_SETTING_CVSD = 0x0060        # 16-bit signed linear PCM in, CVSD on air
VOICE_SETTING_TRANSPARENT = 0x0063  # host supplies already-coded audio
VOICE_SETTING_ALAW = 0x0061
VOICE_SETTING_ULAW = 0x0062


@unique
class CodingFormat(IntEnum):
    """`Coding_Format` byte inside an enhanced coding-format structure."""

    U_LAW = 0x00
    A_LAW = 0x01
    CVSD = 0x02
    TRANSPARENT = 0x03
    LINEAR_PCM = 0x04
    MSBC = 0x05
    LC3 = 0x06
    G_729A = 0x07
    VENDOR_SPECIFIC = 0xFF


@unique
class PcmDataFormat(IntEnum):
    NOT_APPLICABLE = 0x00
    ONES_COMPLEMENT = 0x01
    TWOS_COMPLEMENT = 0x02
    SIGN_MAGNITUDE = 0x03
    UNSIGNED = 0x04


@unique
class AudioDataPath(IntEnum):
    """`Input_Data_Path` / `Output_Data_Path`; 1..254 are vendor-defined."""

    HCI = 0x00
    AUDIO_TEST_MODE = 0xFF


def _coerce_addr(addr: Union[bytes, str]) -> bytes:
    if isinstance(addr, str):
        return bd_addr_str_to_bytes(addr)
    addr = bytes(addr)
    if len(addr) != 6:
        raise ValueError(f"Invalid address length {len(addr)}, must be 6 bytes")
    return addr


def _check_handle(handle: int) -> None:
    if not (0x0000 <= handle <= 0x0EFF):
        raise ValueError(f"Invalid connection_handle: 0x{handle:04X}")


def pack_coding_format(coding_format: int = CodingFormat.CVSD,
                       company_id: int = 0x0000,
                       vendor_codec_id: int = 0x0000) -> bytes:
    """The 5-octet coding-format structure the enhanced commands repeat six times."""
    return struct.pack("<BHH", int(coding_format), company_id, vendor_codec_id)


def unpack_coding_format(data: bytes, offset: int) -> tuple:
    return struct.unpack_from("<BHH", data, offset)


class _SyncSetupCommon(HciCmdBasePacket):
    """Shared validation for the plain setup/accept pair."""

    def _validate_sync_common(self) -> None:
        p = self.params
        for name in ("transmit_bandwidth", "receive_bandwidth"):
            if not (0 <= p[name] <= 0xFFFFFFFF):
                raise ValueError(f"{name} {p[name]} does not fit in 4 octets")
        if not (0x0004 <= p['max_latency'] <= 0xFFFE) and p['max_latency'] != 0xFFFF:
            raise ValueError(f"max_latency 0x{p['max_latency']:04X} out of range "
                             "(0x0004..0xFFFE, or 0xFFFF for don't care)")
        if p['retransmission_effort'] not in (0x00, 0x01, 0x02, 0xFF):
            raise ValueError("retransmission_effort must be 0x00, 0x01, 0x02 "
                             f"or 0xFF, got {p['retransmission_effort']}")
        if not (0x0001 <= p['packet_type'] <= 0xFFFF):
            raise ValueError(f"packet_type 0x{p['packet_type']:04X} must set at "
                             "least one packet type bit")

    def _serialize_sync_tail(self) -> bytes:
        p = self.params
        return struct.pack("<IIHHBH", p['transmit_bandwidth'],
                           p['receive_bandwidth'], p['max_latency'],
                           p['voice_setting'], p['retransmission_effort'],
                           p['packet_type'])


class SetupSynchronousConnection(_SyncSetupCommon):
    """
    Setup Synchronous Connection Command (0x0428).

    Adds a SCO/eSCO link to an existing ACL connection, or renegotiates one.
    The handle is the *ACL* handle when creating; the resulting SCO handle
    arrives in Synchronous Connection Complete.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.SETUP_SYNCHRONOUS_CONNECTION)
    NAME = "Setup_Synchronous_Connection"

    def __init__(self, connection_handle: int = 0x0000,
                 transmit_bandwidth: int = 8000,
                 receive_bandwidth: int = 8000,
                 max_latency: int = 0x000C,        # 12 ms
                 voice_setting: int = VOICE_SETTING_CVSD,
                 retransmission_effort: int = RetransmissionEffort.OPTIMISE_QUALITY,
                 packet_type: int = SYNC_PACKET_TYPE_EV3_ONLY):
        super().__init__(connection_handle=connection_handle,
                         transmit_bandwidth=transmit_bandwidth,
                         receive_bandwidth=receive_bandwidth,
                         max_latency=max_latency,
                         voice_setting=voice_setting,
                         retransmission_effort=int(retransmission_effort),
                         packet_type=int(packet_type))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        self._validate_sync_common()

    def _serialize_params(self) -> bytes:
        return (struct.pack("<H", self.params['connection_handle'])
                + self._serialize_sync_tail())

    @classmethod
    def from_bytes(cls, data: bytes) -> "SetupSynchronousConnection":
        if len(data) < 17:
            raise ValueError(f"Invalid data length: {len(data)}, expected 17")
        handle = struct.unpack_from("<H", data, 0)[0]
        (tx_bw, rx_bw, latency, voice, effort,
         packet_type) = struct.unpack_from("<IIHHBH", data, 2)
        return cls(handle, tx_bw, rx_bw, latency, voice, effort, packet_type)

    def __str__(self) -> str:
        p = self.params
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"(handle 0x{p['connection_handle']:04X}, "
                f"{p['transmit_bandwidth']}/{p['receive_bandwidth']} B/s, "
                f"voice 0x{p['voice_setting']:04X})")


class AcceptSynchronousConnectionRequest(_SyncSetupCommon):
    """
    Accept Synchronous Connection Request Command (0x0429).

    The answer to Connection Request with a link type of SCO or eSCO. Keyed by
    address, not handle, because the connection does not exist yet.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.ACCEPT_SYNCHRONOUS_CONNECTION_REQUEST)
    NAME = "Accept_Synchronous_Connection_Request"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 transmit_bandwidth: int = 8000,
                 receive_bandwidth: int = 8000,
                 max_latency: int = 0x000C,
                 voice_setting: int = VOICE_SETTING_CVSD,
                 retransmission_effort: int = RetransmissionEffort.OPTIMISE_QUALITY,
                 packet_type: int = SYNC_PACKET_TYPE_EV3_ONLY):
        super().__init__(bd_addr=_coerce_addr(bd_addr),
                         transmit_bandwidth=transmit_bandwidth,
                         receive_bandwidth=receive_bandwidth,
                         max_latency=max_latency,
                         voice_setting=voice_setting,
                         retransmission_effort=int(retransmission_effort),
                         packet_type=int(packet_type))

    def _validate_params(self) -> None:
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}")
        self._validate_sync_common()

    def _serialize_params(self) -> bytes:
        return (bytes(reversed(self.params['bd_addr']))
                + self._serialize_sync_tail())

    @classmethod
    def from_bytes(cls, data: bytes) -> "AcceptSynchronousConnectionRequest":
        if len(data) < 21:
            raise ValueError(f"Invalid data length: {len(data)}, expected 21")
        (tx_bw, rx_bw, latency, voice, effort,
         packet_type) = struct.unpack_from("<IIHHBH", data, 6)
        return cls(bytes(reversed(data[:6])), tx_bw, rx_bw, latency, voice,
                   effort, packet_type)


class RejectSynchronousConnectionRequest(HciCmdBasePacket):
    """Reject Synchronous Connection Request Command (0x042A)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.REJECT_SYNCHRONOUS_CONNECTION_REQUEST)
    NAME = "Reject_Synchronous_Connection_Request"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 reason: int = 0x0D):     # Connection Rejected: Limited Resources
        super().__init__(bd_addr=_coerce_addr(bd_addr), reason=reason)

    def _validate_params(self) -> None:
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}")
        if not (0x00 <= self.params['reason'] <= 0xFF):
            raise ValueError(f"Invalid reason: {self.params['reason']}")

    def _serialize_params(self) -> bytes:
        return (bytes(reversed(self.params['bd_addr']))
                + bytes([self.params['reason']]))

    @classmethod
    def from_bytes(cls, data: bytes) -> "RejectSynchronousConnectionRequest":
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected 7")
        return cls(bytes(reversed(data[:6])), data[6])


class _EnhancedSyncCommon(HciCmdBasePacket):
    """
    Shared body for the two enhanced synchronous commands.

    They differ only in their first field -- a connection handle for setup, a
    BD_ADDR for accept -- and share a 57-octet tail describing the air coding
    and both PCM paths.
    """

    #: Everything after the handle/address, in wire order.
    TAIL_LENGTH = 57

    def _init_tail(self, transmit_bandwidth, receive_bandwidth,
                   transmit_coding_format, receive_coding_format,
                   transmit_codec_frame_size, receive_codec_frame_size,
                   input_bandwidth, output_bandwidth,
                   input_coding_format, output_coding_format,
                   input_coded_data_size, output_coded_data_size,
                   input_pcm_data_format, output_pcm_data_format,
                   input_pcm_sample_payload_msb_position,
                   output_pcm_sample_payload_msb_position,
                   input_data_path, output_data_path,
                   input_transport_unit_size, output_transport_unit_size,
                   max_latency, packet_type, retransmission_effort) -> dict:
        return dict(
            transmit_bandwidth=transmit_bandwidth,
            receive_bandwidth=receive_bandwidth,
            transmit_coding_format=bytes(transmit_coding_format),
            receive_coding_format=bytes(receive_coding_format),
            transmit_codec_frame_size=transmit_codec_frame_size,
            receive_codec_frame_size=receive_codec_frame_size,
            input_bandwidth=input_bandwidth,
            output_bandwidth=output_bandwidth,
            input_coding_format=bytes(input_coding_format),
            output_coding_format=bytes(output_coding_format),
            input_coded_data_size=input_coded_data_size,
            output_coded_data_size=output_coded_data_size,
            input_pcm_data_format=int(input_pcm_data_format),
            output_pcm_data_format=int(output_pcm_data_format),
            input_pcm_sample_payload_msb_position=input_pcm_sample_payload_msb_position,
            output_pcm_sample_payload_msb_position=output_pcm_sample_payload_msb_position,
            input_data_path=int(input_data_path),
            output_data_path=int(output_data_path),
            input_transport_unit_size=input_transport_unit_size,
            output_transport_unit_size=output_transport_unit_size,
            max_latency=max_latency,
            packet_type=int(packet_type),
            retransmission_effort=int(retransmission_effort),
        )

    def _validate_tail(self) -> None:
        p = self.params
        for name in ("transmit_coding_format", "receive_coding_format",
                     "input_coding_format", "output_coding_format"):
            if len(p[name]) != 5:
                raise ValueError(f"{name} must be a 5-octet coding format "
                                 f"structure, got {len(p[name])} bytes")
        if p['retransmission_effort'] not in (0x00, 0x01, 0x02, 0xFF):
            raise ValueError("retransmission_effort must be 0x00, 0x01, 0x02 or 0xFF")
        if not (0x0004 <= p['max_latency'] <= 0xFFFE) and p['max_latency'] != 0xFFFF:
            raise ValueError(f"max_latency 0x{p['max_latency']:04X} out of range "
                             "(0x0004..0xFFFE, or 0xFFFF for don't care)")
        if not (0x0001 <= p['packet_type'] <= 0xFFFF):
            raise ValueError("packet_type must set at least one packet type bit")
        if p['input_pcm_data_format'] > 0x04 or p['output_pcm_data_format'] > 0x04:
            raise ValueError("PCM data format must be 0x00..0x04")

    def _serialize_tail(self) -> bytes:
        p = self.params
        return (struct.pack("<II", p['transmit_bandwidth'], p['receive_bandwidth'])
                + p['transmit_coding_format'] + p['receive_coding_format']
                + struct.pack("<HH", p['transmit_codec_frame_size'],
                              p['receive_codec_frame_size'])
                + struct.pack("<II", p['input_bandwidth'], p['output_bandwidth'])
                + p['input_coding_format'] + p['output_coding_format']
                + struct.pack("<HH", p['input_coded_data_size'],
                              p['output_coded_data_size'])
                + bytes([p['input_pcm_data_format'], p['output_pcm_data_format'],
                         p['input_pcm_sample_payload_msb_position'],
                         p['output_pcm_sample_payload_msb_position'],
                         p['input_data_path'], p['output_data_path'],
                         p['input_transport_unit_size'],
                         p['output_transport_unit_size']])
                + struct.pack("<HHB", p['max_latency'], p['packet_type'],
                              p['retransmission_effort']))

    @staticmethod
    def _parse_tail(data: bytes, offset: int) -> dict:
        tx_bw, rx_bw = struct.unpack_from("<II", data, offset)
        tx_coding = data[offset + 8:offset + 13]
        rx_coding = data[offset + 13:offset + 18]
        tx_frame, rx_frame = struct.unpack_from("<HH", data, offset + 18)
        in_bw, out_bw = struct.unpack_from("<II", data, offset + 22)
        in_coding = data[offset + 30:offset + 35]
        out_coding = data[offset + 35:offset + 40]
        in_size, out_size = struct.unpack_from("<HH", data, offset + 40)
        (in_fmt, out_fmt, in_msb, out_msb, in_path, out_path,
         in_unit, out_unit) = data[offset + 44:offset + 52]
        latency, packet_type, effort = struct.unpack_from("<HHB", data, offset + 52)
        return dict(
            transmit_bandwidth=tx_bw, receive_bandwidth=rx_bw,
            transmit_coding_format=tx_coding, receive_coding_format=rx_coding,
            transmit_codec_frame_size=tx_frame, receive_codec_frame_size=rx_frame,
            input_bandwidth=in_bw, output_bandwidth=out_bw,
            input_coding_format=in_coding, output_coding_format=out_coding,
            input_coded_data_size=in_size, output_coded_data_size=out_size,
            input_pcm_data_format=in_fmt, output_pcm_data_format=out_fmt,
            input_pcm_sample_payload_msb_position=in_msb,
            output_pcm_sample_payload_msb_position=out_msb,
            input_data_path=in_path, output_data_path=out_path,
            input_transport_unit_size=in_unit, output_transport_unit_size=out_unit,
            max_latency=latency, packet_type=packet_type,
            retransmission_effort=effort,
        )


#: Keyword defaults shared by both enhanced commands -- a narrowband CVSD link
#: with 16-bit linear PCM over HCI, which is the configuration that works
#: everywhere.
ENHANCED_CVSD_DEFAULTS = dict(
    transmit_bandwidth=8000,
    receive_bandwidth=8000,
    transmit_coding_format=pack_coding_format(CodingFormat.CVSD),
    receive_coding_format=pack_coding_format(CodingFormat.CVSD),
    transmit_codec_frame_size=60,
    receive_codec_frame_size=60,
    input_bandwidth=16000,
    output_bandwidth=16000,
    input_coding_format=pack_coding_format(CodingFormat.LINEAR_PCM),
    output_coding_format=pack_coding_format(CodingFormat.LINEAR_PCM),
    input_coded_data_size=16,
    output_coded_data_size=16,
    input_pcm_data_format=PcmDataFormat.TWOS_COMPLEMENT,
    output_pcm_data_format=PcmDataFormat.TWOS_COMPLEMENT,
    input_pcm_sample_payload_msb_position=0,
    output_pcm_sample_payload_msb_position=0,
    input_data_path=AudioDataPath.HCI,
    output_data_path=AudioDataPath.HCI,
    input_transport_unit_size=16,
    output_transport_unit_size=16,
    max_latency=0x000C,
    packet_type=SYNC_PACKET_TYPE_EV3_ONLY,
    retransmission_effort=RetransmissionEffort.OPTIMISE_QUALITY,
)


class EnhancedSetupSynchronousConnection(_EnhancedSyncCommon):
    """
    Enhanced Setup Synchronous Connection Command (0x043D).

    The form to use for transparent or mSBC audio: it describes the air coding
    and the host PCM path separately, so the controller knows not to run its own
    CVSD codec over already-coded data.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.ENHANCED_SETUP_SYNCHRONOUS_CONNECTION)
    NAME = "Enhanced_Setup_Synchronous_Connection"

    def __init__(self, connection_handle: int = 0x0000, **kwargs):
        settings = dict(ENHANCED_CVSD_DEFAULTS)
        unknown = set(kwargs) - set(settings)
        if unknown:
            raise TypeError(f"unexpected parameters: {sorted(unknown)}")
        settings.update(kwargs)
        super().__init__(connection_handle=connection_handle,
                         **self._init_tail(**settings))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        self._validate_tail()

    def _serialize_params(self) -> bytes:
        return (struct.pack("<H", self.params['connection_handle'])
                + self._serialize_tail())

    @classmethod
    def from_bytes(cls, data: bytes) -> "EnhancedSetupSynchronousConnection":
        needed = 2 + cls.TAIL_LENGTH
        if len(data) < needed:
            raise ValueError(f"Invalid data length: {len(data)}, expected {needed}")
        handle = struct.unpack_from("<H", data, 0)[0]
        return cls(handle, **cls._parse_tail(data, 2))


class EnhancedAcceptSynchronousConnectionRequest(_EnhancedSyncCommon):
    """Enhanced Accept Synchronous Connection Request Command (0x043E)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.ENHANCED_ACCEPT_SYNCHRONOUS_CONNECTION)
    NAME = "Enhanced_Accept_Synchronous_Connection_Request"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6, **kwargs):
        settings = dict(ENHANCED_CVSD_DEFAULTS)
        unknown = set(kwargs) - set(settings)
        if unknown:
            raise TypeError(f"unexpected parameters: {sorted(unknown)}")
        settings.update(kwargs)
        super().__init__(bd_addr=_coerce_addr(bd_addr),
                         **self._init_tail(**settings))

    def _validate_params(self) -> None:
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}")
        self._validate_tail()

    def _serialize_params(self) -> bytes:
        return bytes(reversed(self.params['bd_addr'])) + self._serialize_tail()

    @classmethod
    def from_bytes(cls, data: bytes) -> "EnhancedAcceptSynchronousConnectionRequest":
        needed = 6 + cls.TAIL_LENGTH
        if len(data) < needed:
            raise ValueError(f"Invalid data length: {len(data)}, expected {needed}")
        return cls(bytes(reversed(data[:6])), **cls._parse_tail(data, 6))


# ------------------------------------------------------------ helper builders

def setup_synchronous_connection(connection_handle, **kwargs):
    return SetupSynchronousConnection(connection_handle, **kwargs)


def accept_synchronous_connection_request(bd_addr, **kwargs):
    return AcceptSynchronousConnectionRequest(bd_addr, **kwargs)


def reject_synchronous_connection_request(bd_addr, reason=0x0D):
    return RejectSynchronousConnectionRequest(bd_addr, reason)


def enhanced_setup_synchronous_connection(connection_handle, **kwargs):
    return EnhancedSetupSynchronousConnection(connection_handle, **kwargs)


def enhanced_accept_synchronous_connection_request(bd_addr, **kwargs):
    return EnhancedAcceptSynchronousConnectionRequest(bd_addr, **kwargs)


for _cls in (SetupSynchronousConnection, AcceptSynchronousConnectionRequest,
             RejectSynchronousConnectionRequest,
             EnhancedSetupSynchronousConnection,
             EnhancedAcceptSynchronousConnectionRequest):
    register_command(_cls)
del _cls


__all__ = [
    'SyncPacketType',
    'SYNC_PACKET_TYPE_ANY',
    'SYNC_PACKET_TYPE_EV3_ONLY',
    'SYNC_PACKET_TYPE_2EV3',
    'RetransmissionEffort',
    'VOICE_SETTING_CVSD',
    'VOICE_SETTING_TRANSPARENT',
    'VOICE_SETTING_ALAW',
    'VOICE_SETTING_ULAW',
    'CodingFormat',
    'PcmDataFormat',
    'AudioDataPath',
    'ENHANCED_CVSD_DEFAULTS',
    'pack_coding_format',
    'unpack_coding_format',
    'SetupSynchronousConnection',
    'AcceptSynchronousConnectionRequest',
    'RejectSynchronousConnectionRequest',
    'EnhancedSetupSynchronousConnection',
    'EnhancedAcceptSynchronousConnectionRequest',
    'setup_synchronous_connection',
    'accept_synchronous_connection_request',
    'reject_synchronous_connection_request',
    'enhanced_setup_synchronous_connection',
    'enhanced_accept_synchronous_connection_request',
]
