"""
LE Channel Sounding commands (Core 6.0).

    0x2082  LE_CS_Read_Local_Supported_Capabilities
    0x2083  LE_CS_Read_Remote_Supported_Capabilities
    0x2086  LE_CS_Write_Cached_Remote_Supported_Capabilities
    0x2087  LE_CS_Security_Enable
    0x2088  LE_CS_Set_Default_Settings
    0x2089  LE_CS_Read_Remote_FAE_Table
    0x208A  LE_CS_Write_Cached_Remote_FAE_Table
    0x208B  LE_CS_Create_Config
    0x208C  LE_CS_Remove_Config
    0x208D  LE_CS_Set_Channel_Classification
    0x208E  LE_CS_Set_Procedure_Parameters
    0x208F  LE_CS_Procedure_Enable
    0x2090  LE_CS_Test
    0x2091  LE_CS_Test_End

Channel Sounding measures distance between two connected devices, so every
command except the local capability read and the test commands takes a
connection handle: the ranging runs on an existing ACL link, not standalone.

The order that actually works on a controller is:

    1. LE_CS_Read_Local_Supported_Capabilities / _Remote_ (what is possible)
    2. LE_CS_Security_Enable                              (once per link)
    3. LE_CS_Set_Default_Settings                         (roles, antenna, power)
    4. LE_CS_Create_Config                                (a config id, 0..3)
    5. LE_CS_Set_Procedure_Parameters                     (timings for that id)
    6. LE_CS_Procedure_Enable                             (start/stop)

Skipping step 3 or 5 gets Command Disallowed on step 6, which is the usual
reason a first attempt goes nowhere.

The two big commands (Create_Config, Set_Procedure_Parameters) carry a lot of
fields; the defaults here are a working single-antenna configuration, so callers
normally override only the handful they care about.
"""

from __future__ import annotations

import struct
from enum import IntEnum, IntFlag, unique

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode


@unique
class CsRole(IntEnum):
    INITIATOR = 0x00
    REFLECTOR = 0x01


class CsRoleMask(IntFlag):
    INITIATOR = 0x01
    REFLECTOR = 0x02


@unique
class CsSyncPhy(IntEnum):
    LE_1M = 0x01
    LE_2M = 0x02
    LE_2M_2BT = 0x03


@unique
class CsMainMode(IntEnum):
    """Main CS step mode. Mode-2 (phase-based) is the usual ranging choice."""

    MODE_1 = 0x01   # RTT only
    MODE_2 = 0x02   # phase-based ranging
    MODE_3 = 0x03   # RTT + phase-based


@unique
class CsSubMode(IntEnum):
    MODE_1 = 0x01
    MODE_2 = 0x02
    MODE_3 = 0x03
    UNUSED = 0xFF


@unique
class CsRttType(IntEnum):
    AA_ONLY = 0x00
    SOUNDING_32BIT = 0x01
    SOUNDING_96BIT = 0x02
    RANDOM_32BIT = 0x03
    RANDOM_64BIT = 0x04
    RANDOM_96BIT = 0x05
    RANDOM_128BIT = 0x06


@unique
class CsChannelSelectionType(IntEnum):
    ALGO_3B = 0x00
    ALGO_3C = 0x01


@unique
class CsCh3cShape(IntEnum):
    HAT = 0x00
    X_SHAPE = 0x01


def _check_handle(handle: int, name: str = "connection_handle") -> None:
    if not (0x0000 <= handle <= 0x0EFF):
        raise ValueError(f"Invalid {name}: 0x{handle:04X} (0x0000..0x0EFF)")


class LeCsReadLocalSupportedCapabilities(HciCmdBasePacket):
    """LE CS Read Local Supported Capabilities Command (0x2082)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_READ_LOCAL_SUPPORTED_CAPABILITIES)
    NAME = "LE_CS_Read_Local_Supported_Capabilities"

    def __init__(self):
        super().__init__()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsReadLocalSupportedCapabilities":
        return cls()


class LeCsReadRemoteSupportedCapabilities(HciCmdBasePacket):
    """LE CS Read Remote Supported Capabilities Command (0x2083)."""

    OPCODE = create_opcode(OGF.LE,
                           LEControllerOCF.CS_READ_REMOTE_SUPPORTED_CAPABILITIES)
    NAME = "LE_CS_Read_Remote_Supported_Capabilities"

    def __init__(self, connection_handle: int):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsReadRemoteSupportedCapabilities":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


class LeCsWriteCachedRemoteSupportedCapabilities(HciCmdBasePacket):
    """
    LE CS Write Cached Remote Supported Capabilities Command (0x2086).

    Feeds the controller capabilities learned on an earlier connection so the
    remote read can be skipped. The blob is passed through verbatim: its layout
    is exactly the return parameters of the remote-capabilities complete event.
    """

    OPCODE = create_opcode(
        OGF.LE, LEControllerOCF.CS_WRITE_CACHED_REMOTE_SUPPORTED_CAPABILITIES)
    NAME = "LE_CS_Write_Cached_Remote_Supported_Capabilities"

    def __init__(self, connection_handle: int, capabilities: bytes = b''):
        super().__init__(connection_handle=connection_handle,
                         capabilities=bytes(capabilities))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return (struct.pack("<H", self.params['connection_handle'])
                + self.params['capabilities'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsWriteCachedRemoteSupportedCapabilities":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 2")
        return cls(struct.unpack_from("<H", data, 0)[0], data[2:])


class LeCsSecurityEnable(HciCmdBasePacket):
    """LE CS Security Enable Command (0x2087)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SECURITY_ENABLE)
    NAME = "LE_CS_Security_Enable"

    def __init__(self, connection_handle: int):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsSecurityEnable":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


class LeCsSetDefaultSettings(HciCmdBasePacket):
    """
    LE CS Set Default Settings Command (0x2088).

    `role_enable` is a CsRoleMask; `cs_sync_antenna_selection` 0xFF lets the
    controller choose. Transmit power is in dBm, 0x7F for "no preference".
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SET_DEFAULT_SETTINGS)
    NAME = "LE_CS_Set_Default_Settings"

    def __init__(self, connection_handle: int,
                 role_enable: int = int(CsRoleMask.INITIATOR | CsRoleMask.REFLECTOR),
                 cs_sync_antenna_selection: int = 0xFF,
                 max_tx_power: int = 0x00):
        super().__init__(connection_handle=connection_handle,
                         role_enable=int(role_enable),
                         cs_sync_antenna_selection=cs_sync_antenna_selection,
                         max_tx_power=max_tx_power)

    def _validate_params(self) -> None:
        p = self.params
        _check_handle(p['connection_handle'])
        if not (0x00 <= p['role_enable'] <= 0x03):
            raise ValueError(f"Invalid role_enable: 0x{p['role_enable']:02X}")
        if p['cs_sync_antenna_selection'] not in (0x01, 0x02, 0x03, 0x04, 0xFE, 0xFF):
            raise ValueError("cs_sync_antenna_selection must be 0x01..0x04, "
                             "0xFE (repeat) or 0xFF (controller's choice)")

    def _serialize_params(self) -> bytes:
        p = self.params
        return struct.pack("<HBBB", p['connection_handle'], p['role_enable'],
                           p['cs_sync_antenna_selection'],
                           p['max_tx_power'] & 0xFF)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsSetDefaultSettings":
        if len(data) < 5:
            raise ValueError(f"Invalid data length: {len(data)}, expected 5")
        handle, roles, antenna, power = struct.unpack_from("<HBBB", data, 0)
        return cls(handle, roles, antenna,
                   power - 256 if power > 0x7F else power)


class LeCsReadRemoteFaeTable(HciCmdBasePacket):
    """LE CS Read Remote FAE Table Command (0x2089)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_READ_REMOTE_FAE_TABLE)
    NAME = "LE_CS_Read_Remote_FAE_Table"

    def __init__(self, connection_handle: int):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsReadRemoteFaeTable":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


class LeCsWriteCachedRemoteFaeTable(HciCmdBasePacket):
    """LE CS Write Cached Remote FAE Table Command (0x208A). Table is 72 bytes."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_WRITE_CACHED_REMOTE_FAE_TABLE)
    NAME = "LE_CS_Write_Cached_Remote_FAE_Table"

    TABLE_LENGTH = 72

    def __init__(self, connection_handle: int, remote_fae_table: bytes = b''):
        super().__init__(connection_handle=connection_handle,
                         remote_fae_table=bytes(remote_fae_table))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        table = self.params['remote_fae_table']
        if len(table) != self.TABLE_LENGTH:
            raise ValueError(f"remote_fae_table must be {self.TABLE_LENGTH} bytes, "
                             f"got {len(table)}")

    def _serialize_params(self) -> bytes:
        return (struct.pack("<H", self.params['connection_handle'])
                + self.params['remote_fae_table'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsWriteCachedRemoteFaeTable":
        if len(data) < 2 + cls.TABLE_LENGTH:
            raise ValueError(f"Invalid data length: {len(data)}, "
                             f"expected {2 + cls.TABLE_LENGTH}")
        return cls(struct.unpack_from("<H", data, 0)[0], data[2:2 + cls.TABLE_LENGTH])


class LeCsCreateConfig(HciCmdBasePacket):
    """
    LE CS Create Config Command (0x208B).

    Defines one of up to four CS configurations on a link. `channel_map` is a
    10-octet bitmap over channels 0..78 with the CS-reserved channels cleared;
    the default below is a map a controller accepts without further tuning.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_CREATE_CONFIG)
    NAME = "LE_CS_Create_Config"

    CHANNEL_MAP_LENGTH = 10

    #: Channels 0-1, 23-25 and 77-78 are excluded, as the spec requires.
    DEFAULT_CHANNEL_MAP = bytes.fromhex("FC7FFFFFFFFFFFFF7F3F")

    def __init__(self, connection_handle: int,
                 config_id: int = 0x00,
                 create_context: int = 0x01,        # 0: local only, 1: both sides
                 main_mode_type: int = CsMainMode.MODE_2,
                 sub_mode_type: int = CsSubMode.UNUSED,
                 min_main_mode_steps: int = 0x02,
                 max_main_mode_steps: int = 0x05,
                 main_mode_repetition: int = 0x00,
                 mode_0_steps: int = 0x03,
                 role: int = CsRole.INITIATOR,
                 rtt_type: int = CsRttType.AA_ONLY,
                 cs_sync_phy: int = CsSyncPhy.LE_1M,
                 channel_map: bytes = None,
                 channel_map_repetition: int = 0x01,
                 channel_selection_type: int = CsChannelSelectionType.ALGO_3B,
                 ch3c_shape: int = CsCh3cShape.HAT,
                 ch3c_jump: int = 0x02,
                 reserved: int = 0x00):
        super().__init__(
            connection_handle=connection_handle,
            config_id=config_id,
            create_context=create_context,
            main_mode_type=int(main_mode_type),
            sub_mode_type=int(sub_mode_type),
            min_main_mode_steps=min_main_mode_steps,
            max_main_mode_steps=max_main_mode_steps,
            main_mode_repetition=main_mode_repetition,
            mode_0_steps=mode_0_steps,
            role=int(role),
            rtt_type=int(rtt_type),
            cs_sync_phy=int(cs_sync_phy),
            channel_map=bytes(channel_map if channel_map is not None
                              else self.DEFAULT_CHANNEL_MAP),
            channel_map_repetition=channel_map_repetition,
            channel_selection_type=int(channel_selection_type),
            ch3c_shape=int(ch3c_shape),
            ch3c_jump=ch3c_jump,
            reserved=reserved,
        )

    def _validate_params(self) -> None:
        p = self.params
        _check_handle(p['connection_handle'])
        if not (0x00 <= p['config_id'] <= 0x03):
            raise ValueError(f"config_id {p['config_id']} out of range (0..3)")
        if p['main_mode_type'] not in (0x01, 0x02, 0x03):
            raise ValueError(f"Invalid main_mode_type: {p['main_mode_type']}")
        if p['sub_mode_type'] not in (0x01, 0x02, 0x03, 0xFF):
            raise ValueError(f"Invalid sub_mode_type: {p['sub_mode_type']}")
        if p['sub_mode_type'] != 0xFF and p['sub_mode_type'] == p['main_mode_type']:
            raise ValueError("sub_mode_type must differ from main_mode_type")
        if p['role'] not in (0x00, 0x01):
            raise ValueError(f"Invalid role: {p['role']}")
        if p['min_main_mode_steps'] > p['max_main_mode_steps']:
            raise ValueError("min_main_mode_steps must be <= max_main_mode_steps")
        if not (0x02 <= p['min_main_mode_steps'] <= 0xFF):
            raise ValueError("min_main_mode_steps must be >= 2")
        if not (0x01 <= p['mode_0_steps'] <= 0x03):
            raise ValueError(f"mode_0_steps {p['mode_0_steps']} out of range (1..3)")
        if len(p['channel_map']) != self.CHANNEL_MAP_LENGTH:
            raise ValueError(f"channel_map must be {self.CHANNEL_MAP_LENGTH} bytes, "
                             f"got {len(p['channel_map'])}")
        if not (0x01 <= p['channel_map_repetition'] <= 0xFF):
            raise ValueError("channel_map_repetition must be >= 1")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (
            struct.pack("<HBBBBBBBBBBB", p['connection_handle'], p['config_id'],
                        p['create_context'], p['main_mode_type'], p['sub_mode_type'],
                        p['min_main_mode_steps'], p['max_main_mode_steps'],
                        p['main_mode_repetition'], p['mode_0_steps'], p['role'],
                        p['rtt_type'], p['cs_sync_phy'])
            + p['channel_map']
            + bytes([p['channel_map_repetition'], p['channel_selection_type'],
                     p['ch3c_shape'], p['ch3c_jump'], p['reserved']])
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsCreateConfig":
        expected = 13 + cls.CHANNEL_MAP_LENGTH + 5
        if len(data) < expected:
            raise ValueError(f"Invalid data length: {len(data)}, expected {expected}")
        (handle, config_id, context, main_mode, sub_mode, min_steps, max_steps,
         repetition, mode0, role, rtt, phy) = struct.unpack_from("<HBBBBBBBBBBB",
                                                                 data, 0)
        channel_map = data[13:13 + cls.CHANNEL_MAP_LENGTH]
        (map_rep, selection, shape, jump, reserved) = \
            data[13 + cls.CHANNEL_MAP_LENGTH:expected]
        return cls(handle, config_id, context, main_mode, sub_mode, min_steps,
                   max_steps, repetition, mode0, role, rtt, phy, channel_map,
                   map_rep, selection, shape, jump, reserved)


class LeCsRemoveConfig(HciCmdBasePacket):
    """LE CS Remove Config Command (0x208C)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_REMOVE_CONFIG)
    NAME = "LE_CS_Remove_Config"

    def __init__(self, connection_handle: int, config_id: int = 0x00):
        super().__init__(connection_handle=connection_handle, config_id=config_id)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        if not (0x00 <= self.params['config_id'] <= 0x03):
            raise ValueError(f"config_id {self.params['config_id']} out of range")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['connection_handle'],
                           self.params['config_id'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsRemoveConfig":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, config_id = struct.unpack_from("<HB", data, 0)
        return cls(handle, config_id)


class LeCsSetChannelClassification(HciCmdBasePacket):
    """LE CS Set Channel Classification Command (0x208D). 10-octet bitmap."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SET_CHANNEL_CLASSIFICATION)
    NAME = "LE_CS_Set_Channel_Classification"

    CHANNEL_MAP_LENGTH = 10

    def __init__(self, channel_classification: bytes = None):
        super().__init__(channel_classification=bytes(
            channel_classification if channel_classification is not None
            else LeCsCreateConfig.DEFAULT_CHANNEL_MAP))

    def _validate_params(self) -> None:
        table = self.params['channel_classification']
        if len(table) != self.CHANNEL_MAP_LENGTH:
            raise ValueError(f"channel_classification must be "
                             f"{self.CHANNEL_MAP_LENGTH} bytes, got {len(table)}")

    def _serialize_params(self) -> bytes:
        return self.params['channel_classification']

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsSetChannelClassification":
        if len(data) < cls.CHANNEL_MAP_LENGTH:
            raise ValueError(f"Invalid data length: {len(data)}, "
                             f"expected {cls.CHANNEL_MAP_LENGTH}")
        return cls(data[:cls.CHANNEL_MAP_LENGTH])


class LeCsSetProcedureParameters(HciCmdBasePacket):
    """
    LE CS Set Procedure Parameters Command (0x208E).

    The timing envelope for a configuration: how long a procedure may run, how
    often it repeats, and which antenna/PHY/power to use. `max_procedure_len` is
    in 0.625 ms units, the procedure intervals in connection events, and the
    subevent lengths in microseconds (3 octets each).
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SET_PROCEDURE_PARAMETERS)
    NAME = "LE_CS_Set_Procedure_Parameters"

    def __init__(self, connection_handle: int,
                 config_id: int = 0x00,
                 max_procedure_len: int = 0x2710,     # 6.25 s
                 min_procedure_interval: int = 0x0001,
                 max_procedure_interval: int = 0x0001,
                 max_procedure_count: int = 0x0001,   # 0 = repeat until disabled
                 min_subevent_len: int = 0x0004E2,    # 1250 us
                 max_subevent_len: int = 0x0F4240,    # 1 s
                 tone_antenna_config_selection: int = 0x00,
                 phy: int = CsSyncPhy.LE_1M,
                 tx_power_delta: int = 0x00,
                 preferred_peer_antenna: int = 0x01,
                 snr_control_initiator: int = 0xFF,   # 0xFF: SNR control off
                 snr_control_reflector: int = 0xFF):
        super().__init__(
            connection_handle=connection_handle,
            config_id=config_id,
            max_procedure_len=max_procedure_len,
            min_procedure_interval=min_procedure_interval,
            max_procedure_interval=max_procedure_interval,
            max_procedure_count=max_procedure_count,
            min_subevent_len=min_subevent_len,
            max_subevent_len=max_subevent_len,
            tone_antenna_config_selection=tone_antenna_config_selection,
            phy=int(phy),
            tx_power_delta=tx_power_delta,
            preferred_peer_antenna=preferred_peer_antenna,
            snr_control_initiator=snr_control_initiator,
            snr_control_reflector=snr_control_reflector,
        )

    def _validate_params(self) -> None:
        p = self.params
        _check_handle(p['connection_handle'])
        if not (0x00 <= p['config_id'] <= 0x03):
            raise ValueError(f"config_id {p['config_id']} out of range (0..3)")
        if not (0x0001 <= p['max_procedure_len'] <= 0xFFFF):
            raise ValueError("max_procedure_len must be >= 1")
        if p['min_procedure_interval'] > p['max_procedure_interval']:
            raise ValueError("min_procedure_interval must be <= "
                             "max_procedure_interval")
        if p['min_subevent_len'] > p['max_subevent_len']:
            raise ValueError("min_subevent_len must be <= max_subevent_len")
        if not (0x0000004E <= p['min_subevent_len'] <= 0xFFFFFF):
            raise ValueError(f"min_subevent_len {p['min_subevent_len']} out of "
                             "range (78..16777215 microseconds)")
        if not (0x00 <= p['tone_antenna_config_selection'] <= 0x07):
            raise ValueError("tone_antenna_config_selection must be 0x00..0x07")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (
            struct.pack("<HBHHHH", p['connection_handle'], p['config_id'],
                        p['max_procedure_len'], p['min_procedure_interval'],
                        p['max_procedure_interval'], p['max_procedure_count'])
            + p['min_subevent_len'].to_bytes(3, "little")
            + p['max_subevent_len'].to_bytes(3, "little")
            + bytes([p['tone_antenna_config_selection'], p['phy'],
                     p['tx_power_delta'] & 0xFF, p['preferred_peer_antenna'],
                     p['snr_control_initiator'], p['snr_control_reflector']])
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsSetProcedureParameters":
        if len(data) < 23:
            raise ValueError(f"Invalid data length: {len(data)}, expected 23")
        (handle, config_id, max_len, min_itv, max_itv, count) = \
            struct.unpack_from("<HBHHHH", data, 0)
        min_sub = int.from_bytes(data[11:14], "little")
        max_sub = int.from_bytes(data[14:17], "little")
        (antenna, phy, delta, peer_antenna, snr_i, snr_r) = data[17:23]
        return cls(handle, config_id, max_len, min_itv, max_itv, count,
                   min_sub, max_sub, antenna, phy,
                   delta - 256 if delta > 0x7F else delta,
                   peer_antenna, snr_i, snr_r)


class LeCsProcedureEnable(HciCmdBasePacket):
    """LE CS Procedure Enable Command (0x208F). Starts or stops the ranging."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_PROCEDURE_ENABLE)
    NAME = "LE_CS_Procedure_Enable"

    def __init__(self, connection_handle: int, config_id: int = 0x00,
                 enable: bool = True):
        super().__init__(connection_handle=connection_handle,
                         config_id=config_id, enable=bool(enable))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        if not (0x00 <= self.params['config_id'] <= 0x03):
            raise ValueError(f"config_id {self.params['config_id']} out of range")

    def _serialize_params(self) -> bytes:
        p = self.params
        return struct.pack("<HBB", p['connection_handle'], p['config_id'],
                           0x01 if p['enable'] else 0x00)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsProcedureEnable":
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4")
        handle, config_id, enable = struct.unpack_from("<HBB", data, 0)
        return cls(handle, config_id, bool(enable))


class LeCsTest(HciCmdBasePacket):
    """
    LE CS Test Command (0x2090).

    Standalone transmit/receive test -- no connection involved, which is why it
    takes no handle. Used for RF bring-up rather than ranging.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_TEST)
    NAME = "LE_CS_Test"

    def __init__(self,
                 main_mode_type: int = CsMainMode.MODE_2,
                 sub_mode_type: int = CsSubMode.UNUSED,
                 main_mode_repetition: int = 0x00,
                 mode_0_steps: int = 0x03,
                 role: int = CsRole.INITIATOR,
                 rtt_type: int = CsRttType.AA_ONLY,
                 cs_sync_phy: int = CsSyncPhy.LE_1M,
                 cs_sync_antenna_selection: int = 0x01,
                 subevent_len: int = 0x0004E2,
                 subevent_interval: int = 0x0000,
                 max_num_subevents: int = 0x01,
                 transmit_power_level: int = 0x00,
                 t_ip1_time: int = 0x0A,
                 t_ip2_time: int = 0x0A,
                 t_fcs_time: int = 0x0F,
                 t_pm_time: int = 0x0A,
                 t_sw_time: int = 0x00,
                 tone_antenna_config_selection: int = 0x00,
                 reserved: int = 0x00,
                 snr_control_initiator: int = 0xFF,
                 snr_control_reflector: int = 0xFF,
                 drbg_nonce: int = 0x0000,
                 channel_map_repetition: int = 0x01,
                 override_config: int = 0x0000,
                 override_parameters: bytes = b''):
        super().__init__(
            main_mode_type=int(main_mode_type), sub_mode_type=int(sub_mode_type),
            main_mode_repetition=main_mode_repetition, mode_0_steps=mode_0_steps,
            role=int(role), rtt_type=int(rtt_type), cs_sync_phy=int(cs_sync_phy),
            cs_sync_antenna_selection=cs_sync_antenna_selection,
            subevent_len=subevent_len, subevent_interval=subevent_interval,
            max_num_subevents=max_num_subevents,
            transmit_power_level=transmit_power_level,
            t_ip1_time=t_ip1_time, t_ip2_time=t_ip2_time, t_fcs_time=t_fcs_time,
            t_pm_time=t_pm_time, t_sw_time=t_sw_time,
            tone_antenna_config_selection=tone_antenna_config_selection,
            reserved=reserved,
            snr_control_initiator=snr_control_initiator,
            snr_control_reflector=snr_control_reflector,
            drbg_nonce=drbg_nonce,
            channel_map_repetition=channel_map_repetition,
            override_config=override_config,
            override_parameters=bytes(override_parameters),
        )

    def _validate_params(self) -> None:
        p = self.params
        if p['main_mode_type'] not in (0x01, 0x02, 0x03):
            raise ValueError(f"Invalid main_mode_type: {p['main_mode_type']}")
        if p['role'] not in (0x00, 0x01):
            raise ValueError(f"Invalid role: {p['role']}")
        if not (0x01 <= p['mode_0_steps'] <= 0x03):
            raise ValueError(f"mode_0_steps {p['mode_0_steps']} out of range (1..3)")
        if len(p['override_parameters']) > 0xFF:
            raise ValueError("override_parameters too long for a one-byte length")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (
            bytes([p['main_mode_type'], p['sub_mode_type'],
                   p['main_mode_repetition'], p['mode_0_steps'], p['role'],
                   p['rtt_type'], p['cs_sync_phy'],
                   p['cs_sync_antenna_selection']])
            + p['subevent_len'].to_bytes(3, "little")
            + struct.pack("<HB", p['subevent_interval'], p['max_num_subevents'])
            + bytes([p['transmit_power_level'] & 0xFF, p['t_ip1_time'],
                     p['t_ip2_time'], p['t_fcs_time'], p['t_pm_time'],
                     p['t_sw_time'], p['tone_antenna_config_selection'],
                     p['reserved'], p['snr_control_initiator'],
                     p['snr_control_reflector']])
            + struct.pack("<HB", p['drbg_nonce'], p['channel_map_repetition'])
            + struct.pack("<HB", p['override_config'],
                          len(p['override_parameters']))
            + p['override_parameters']
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsTest":
        if len(data) < 30:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 30")
        (main_mode, sub_mode, repetition, mode0, role, rtt, phy, antenna) = data[:8]
        subevent_len = int.from_bytes(data[8:11], "little")
        subevent_interval, max_subevents = struct.unpack_from("<HB", data, 11)
        (power, ip1, ip2, fcs, pm, sw, tone_cfg, reserved, snr_i, snr_r) = data[14:24]
        nonce, map_rep = struct.unpack_from("<HB", data, 24)
        override_config, override_len = struct.unpack_from("<HB", data, 27)
        override = data[30:30 + override_len]
        return cls(main_mode, sub_mode, repetition, mode0, role, rtt, phy,
                   antenna, subevent_len, subevent_interval, max_subevents,
                   power - 256 if power > 0x7F else power,
                   ip1, ip2, fcs, pm, sw, tone_cfg, reserved, snr_i, snr_r,
                   nonce, map_rep, override_config, override)


class LeCsTestEnd(HciCmdBasePacket):
    """LE CS Test End Command (0x2091)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_TEST_END)
    NAME = "LE_CS_Test_End"

    def __init__(self):
        super().__init__()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCsTestEnd":
        return cls()


# ------------------------------------------------------------ helper builders

def le_cs_read_local_supported_capabilities():
    return LeCsReadLocalSupportedCapabilities()


def le_cs_read_remote_supported_capabilities(connection_handle):
    return LeCsReadRemoteSupportedCapabilities(connection_handle)


def le_cs_security_enable(connection_handle):
    return LeCsSecurityEnable(connection_handle)


def le_cs_set_default_settings(connection_handle, **kwargs):
    return LeCsSetDefaultSettings(connection_handle, **kwargs)


def le_cs_read_remote_fae_table(connection_handle):
    return LeCsReadRemoteFaeTable(connection_handle)


def le_cs_create_config(connection_handle, **kwargs):
    return LeCsCreateConfig(connection_handle, **kwargs)


def le_cs_remove_config(connection_handle, config_id=0x00):
    return LeCsRemoveConfig(connection_handle, config_id)


def le_cs_set_channel_classification(channel_classification=None):
    return LeCsSetChannelClassification(channel_classification)


def le_cs_set_procedure_parameters(connection_handle, **kwargs):
    return LeCsSetProcedureParameters(connection_handle, **kwargs)


def le_cs_procedure_enable(connection_handle, config_id=0x00, enable=True):
    return LeCsProcedureEnable(connection_handle, config_id, enable)


def le_cs_test(**kwargs):
    return LeCsTest(**kwargs)


def le_cs_test_end():
    return LeCsTestEnd()


for _cls in (LeCsReadLocalSupportedCapabilities, LeCsReadRemoteSupportedCapabilities,
             LeCsWriteCachedRemoteSupportedCapabilities, LeCsSecurityEnable,
             LeCsSetDefaultSettings, LeCsReadRemoteFaeTable,
             LeCsWriteCachedRemoteFaeTable, LeCsCreateConfig, LeCsRemoveConfig,
             LeCsSetChannelClassification, LeCsSetProcedureParameters,
             LeCsProcedureEnable, LeCsTest, LeCsTestEnd):
    register_command(_cls)
del _cls


__all__ = [
    'CsRole',
    'CsRoleMask',
    'CsSyncPhy',
    'CsMainMode',
    'CsSubMode',
    'CsRttType',
    'CsChannelSelectionType',
    'CsCh3cShape',
    'LeCsReadLocalSupportedCapabilities',
    'LeCsReadRemoteSupportedCapabilities',
    'LeCsWriteCachedRemoteSupportedCapabilities',
    'LeCsSecurityEnable',
    'LeCsSetDefaultSettings',
    'LeCsReadRemoteFaeTable',
    'LeCsWriteCachedRemoteFaeTable',
    'LeCsCreateConfig',
    'LeCsRemoveConfig',
    'LeCsSetChannelClassification',
    'LeCsSetProcedureParameters',
    'LeCsProcedureEnable',
    'LeCsTest',
    'LeCsTestEnd',
    'le_cs_read_local_supported_capabilities',
    'le_cs_read_remote_supported_capabilities',
    'le_cs_security_enable',
    'le_cs_set_default_settings',
    'le_cs_read_remote_fae_table',
    'le_cs_create_config',
    'le_cs_remove_config',
    'le_cs_set_channel_classification',
    'le_cs_set_procedure_parameters',
    'le_cs_procedure_enable',
    'le_cs_test',
    'le_cs_test_end',
]
