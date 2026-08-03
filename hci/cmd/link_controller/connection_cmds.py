"""
Link Control commands for connection management and remote-device queries.

    0x0403  Periodic_Inquiry_Mode              0x041B  Read_Remote_Supported_Features
    0x0404  Exit_Periodic_Inquiry_Mode         0x041C  Read_Remote_Extended_Features
    0x0408  Create_Connection_Cancel           0x041D  Read_Remote_Version_Information
    0x0411  Authentication_Requested           0x041F  Read_Clock_Offset
    0x0413  Set_Connection_Encryption          0x0420  Read_LMP_Handle
    0x0415  Change_Connection_Link_Key         0x043F  Truncated_Page
    0x0417  Link_Key_Selection                 0x0440  Truncated_Page_Cancel
    0x041A  Remote_Name_Request_Cancel

Most of these answer with Command Status and then a dedicated completion event
later -- Authentication Requested becomes Authentication Complete, Read Remote
Supported Features becomes Read Remote Supported Features Complete, and so on.
Only the cancels and Link Key Selection answer with a Command Complete.

BD_ADDR is stored in display order in `params` and reversed on the wire, which
is the convention throughout this package.
"""

from __future__ import annotations

import struct
from enum import IntEnum, unique
from typing import Union

from hci import bd_addr_str_to_bytes

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LinkControlOCF, OGF, create_opcode


@unique
class PageScanRepetitionMode(IntEnum):
    """
    How often the remote device page scans, learned from an inquiry result.

    Passing the wrong mode makes paging take much longer than it should, so use
    what the Inquiry Result reported rather than guessing R0.
    """

    R0 = 0x00
    R1 = 0x01
    R2 = 0x02


@unique
class KeyFlag(IntEnum):
    """`Key_Flag` for Link Key Selection (0x0417)."""

    USE_SEMI_PERMANENT_LINK_KEY = 0x00
    USE_TEMPORARY_LINK_KEY = 0x01


def _coerce_addr(addr: Union[bytes, str]) -> bytes:
    """Accept 'AA:BB:...' or 6 raw bytes, returning display order."""
    if isinstance(addr, str):
        return bd_addr_str_to_bytes(addr)
    addr = bytes(addr)
    if len(addr) != 6:
        raise ValueError(f"Invalid address length {len(addr)}, must be 6 bytes")
    return addr


def _check_handle(handle: int, name: str = "connection_handle") -> None:
    if not (0x0000 <= handle <= 0x0EFF):
        raise ValueError(f"Invalid {name}: 0x{handle:04X} (0x0000..0x0EFF)")


class _AddressOnlyCommand(HciCmdBasePacket):
    """Shared body for the commands whose only parameter is a BD_ADDR."""

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6):
        super().__init__(bd_addr=_coerce_addr(bd_addr))

    def _validate_params(self) -> None:
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}")

    def _serialize_params(self) -> bytes:
        return bytes(reversed(self.params['bd_addr']))

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected 6")
        return cls(bytes(reversed(data[:6])))

    def __str__(self) -> str:
        addr = ":".join(f"{b:02X}" for b in self.params['bd_addr'])
        return f"{self.NAME} : 0x{self.OPCODE:04X} ({addr})"


class _HandleOnlyCommand(HciCmdBasePacket):
    """Shared body for the commands whose only parameter is a connection handle."""

    def __init__(self, connection_handle: int = 0x0000):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])

    def __str__(self) -> str:
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"(handle 0x{self.params['connection_handle']:04X})")


class PeriodicInquiryMode(HciCmdBasePacket):
    """
    Periodic Inquiry Mode Command (0x0403).

    Runs inquiries automatically on a random period between the min and max,
    until Exit Periodic Inquiry Mode. The spec requires
    `min_period_length > inquiry_length`, and max > min, or the controller
    rejects the command.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.PERIODIC_INQUIRY_MODE)
    NAME = "Periodic_Inquiry_Mode"

    IAC_GIAC = b'\x33\x8B\x9E'
    IAC_LIAC = b'\x00\x8B\x9E'

    def __init__(self, max_period_length: int = 0x0060,   # N * 1.28 s
                 min_period_length: int = 0x0040,
                 lap: Union[bytes, int] = IAC_GIAC,
                 inquiry_length: int = 0x30,
                 num_responses: int = 0x00):
        if isinstance(lap, int):
            lap = lap.to_bytes(3, byteorder='little')
        super().__init__(max_period_length=max_period_length,
                         min_period_length=min_period_length,
                         lap=bytes(lap),
                         inquiry_length=inquiry_length,
                         num_responses=num_responses)

    def _validate_params(self) -> None:
        p = self.params
        if len(p['lap']) != 3:
            raise ValueError(f"Invalid lap length: {len(p['lap'])}, must be 3 bytes")
        if not (0x0002 <= p['min_period_length'] <= 0xFFFE):
            raise ValueError(f"min_period_length 0x{p['min_period_length']:04X} out "
                             "of range (0x0002..0xFFFE)")
        if not (0x0003 <= p['max_period_length'] <= 0xFFFF):
            raise ValueError(f"max_period_length 0x{p['max_period_length']:04X} out "
                             "of range (0x0003..0xFFFF)")
        if p['max_period_length'] <= p['min_period_length']:
            raise ValueError("max_period_length must be greater than "
                             "min_period_length")
        if not (0x01 <= p['inquiry_length'] <= 0x30):
            raise ValueError(f"inquiry_length {p['inquiry_length']} out of range "
                             "(0x01..0x30)")
        if p['min_period_length'] <= p['inquiry_length']:
            raise ValueError("min_period_length must be greater than "
                             "inquiry_length, or the inquiries would overlap")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (struct.pack("<HH", p['max_period_length'], p['min_period_length'])
                + p['lap']
                + bytes([p['inquiry_length'], p['num_responses']]))

    @classmethod
    def from_bytes(cls, data: bytes) -> "PeriodicInquiryMode":
        if len(data) < 9:
            raise ValueError(f"Invalid data length: {len(data)}, expected 9")
        max_period, min_period = struct.unpack_from("<HH", data, 0)
        return cls(max_period, min_period, data[4:7], data[7], data[8])


class ExitPeriodicInquiryMode(HciCmdBasePacket):
    """Exit Periodic Inquiry Mode Command (0x0404)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.EXIT_PERIODIC_INQUIRY_MODE)
    NAME = "Exit_Periodic_Inquiry_Mode"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "ExitPeriodicInquiryMode":
        return cls()


class CreateConnectionCancel(_AddressOnlyCommand):
    """
    Create Connection Cancel Command (0x0408).

    Aborts a paging attempt. The connection attempt still finishes with a
    Connection Complete carrying Unknown Connection Identifier, so a host
    waiting on that event does not hang.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.CREATE_CONNECTION_CANCEL)
    NAME = "Create_Connection_Cancel"


class AuthenticationRequested(_HandleOnlyCommand):
    """
    Authentication Requested Command (0x0411).

    Starts pairing/authentication on an existing link. Expect PIN Code Request
    or IO Capability Request next, depending on whether Secure Simple Pairing
    is enabled -- the replies for those live in `pairing_cmds`.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.AUTHENTICATION_REQUESTED)
    NAME = "Authentication_Requested"


class SetConnectionEncryption(HciCmdBasePacket):
    """
    Set Connection Encryption Command (0x0413).

    The link has to be authenticated first; on an unauthenticated link the
    controller answers Command Disallowed.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.SET_CONNECTION_ENCRYPTION)
    NAME = "Set_Connection_Encryption"

    def __init__(self, connection_handle: int = 0x0000,
                 encryption_enable: Union[bool, int] = True):
        super().__init__(connection_handle=connection_handle,
                         encryption_enable=int(bool(encryption_enable)))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['connection_handle'],
                           self.params['encryption_enable'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "SetConnectionEncryption":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, enable = struct.unpack_from("<HB", data, 0)
        return cls(handle, enable)


class ChangeConnectionLinkKey(_HandleOnlyCommand):
    """Change Connection Link Key Command (0x0415)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.CHANGE_CONNECTION_LINK_KEY)
    NAME = "Change_Connection_Link_Key"


class LinkKeySelection(HciCmdBasePacket):
    """
    Link Key Selection Command (0x0417), historically Master Link Key.

    Switches every link to the temporary key or back to the semi-permanent one.
    Only used for the legacy broadcast encryption scheme.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.MASTER_LINK_KEY)
    NAME = "Link_Key_Selection"

    def __init__(self, key_flag: Union[int, KeyFlag] =
                 KeyFlag.USE_SEMI_PERMANENT_LINK_KEY):
        super().__init__(key_flag=int(key_flag))

    def _validate_params(self) -> None:
        if self.params['key_flag'] not in (0x00, 0x01):
            raise ValueError(f"Invalid key_flag: {self.params['key_flag']}; "
                             "0 = semi-permanent, 1 = temporary")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['key_flag']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LinkKeySelection":
        if not data:
            raise ValueError("Link_Key_Selection: empty parameters")
        return cls(data[0])


class RemoteNameRequestCancel(_AddressOnlyCommand):
    """Remote Name Request Cancel Command (0x041A)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.REMOTE_NAME_REQUEST_CANCEL)
    NAME = "Remote_Name_Request_Cancel"


class ReadRemoteSupportedFeatures(_HandleOnlyCommand):
    """Read Remote Supported Features Command (0x041B). LMP feature page 0."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_REMOTE_SUPPORTED_FEATURES)
    NAME = "Read_Remote_Supported_Features"


class ReadRemoteExtendedFeatures(HciCmdBasePacket):
    """
    Read Remote Extended Features Command (0x041C).

    Page 0 is the same as Read Remote Supported Features; page 1 carries the
    host features (SSP, LE support), which is what you usually want.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_REMOTE_EXTENDED_FEATURES)
    NAME = "Read_Remote_Extended_Features"

    def __init__(self, connection_handle: int = 0x0000, page_number: int = 0x01):
        super().__init__(connection_handle=connection_handle,
                         page_number=page_number)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        if not (0x00 <= self.params['page_number'] <= 0xFF):
            raise ValueError(f"page_number {self.params['page_number']} out of range")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['connection_handle'],
                           self.params['page_number'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "ReadRemoteExtendedFeatures":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, page = struct.unpack_from("<HB", data, 0)
        return cls(handle, page)


class ReadRemoteVersionInformation(_HandleOnlyCommand):
    """Read Remote Version Information Command (0x041D)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_REMOTE_VERSION_INFORMATION)
    NAME = "Read_Remote_Version_Information"


class ReadClockOffset(_HandleOnlyCommand):
    """
    Read Clock Offset Command (0x041F).

    The offset makes a later page much faster, so it is worth caching alongside
    the address and page scan repetition mode.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.READ_CLOCK_OFFSET)
    NAME = "Read_Clock_Offset"


class ReadLmpHandle(_HandleOnlyCommand):
    """Read LMP Handle Command (0x0420). Maps a SCO handle to its LMP handle."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.READ_LMP_HANDLE)
    NAME = "Read_LMP_Handle"


class TruncatedPage(HciCmdBasePacket):
    """
    Truncated Page Command (0x043F).

    Pages a device and drops the connection as soon as the ID response arrives:
    used to wake a peripheral, not to connect to it. Completes with Truncated
    Page Complete.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.TRUNCATED_PAGE_MODE)
    NAME = "Truncated_Page"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 page_scan_repetition_mode: int = PageScanRepetitionMode.R1,
                 clock_offset: int = 0x0000):
        super().__init__(bd_addr=_coerce_addr(bd_addr),
                         page_scan_repetition_mode=int(page_scan_repetition_mode),
                         clock_offset=clock_offset)

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        if not (0x00 <= p['page_scan_repetition_mode'] <= 0x02):
            raise ValueError(f"Invalid page_scan_repetition_mode: "
                             f"{p['page_scan_repetition_mode']} (R0/R1/R2 only)")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes(reversed(p['bd_addr']))
                + bytes([p['page_scan_repetition_mode']])
                + struct.pack("<H", p['clock_offset']))

    @classmethod
    def from_bytes(cls, data: bytes) -> "TruncatedPage":
        if len(data) < 9:
            raise ValueError(f"Invalid data length: {len(data)}, expected 9")
        return cls(bytes(reversed(data[:6])), data[6],
                   struct.unpack_from("<H", data, 7)[0])


class TruncatedPageCancel(_AddressOnlyCommand):
    """Truncated Page Cancel Command (0x0440)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.TRUNCATED_PAGE_MODE_CANCEL)
    NAME = "Truncated_Page_Cancel"


# ------------------------------------------------------------ helper builders

def periodic_inquiry_mode(**kwargs):
    return PeriodicInquiryMode(**kwargs)


def exit_periodic_inquiry_mode():
    return ExitPeriodicInquiryMode()


def create_connection_cancel(bd_addr):
    return CreateConnectionCancel(bd_addr)


def authentication_requested(connection_handle):
    return AuthenticationRequested(connection_handle)


def set_connection_encryption(connection_handle, encryption_enable=True):
    return SetConnectionEncryption(connection_handle, encryption_enable)


def change_connection_link_key(connection_handle):
    return ChangeConnectionLinkKey(connection_handle)


def link_key_selection(key_flag=KeyFlag.USE_SEMI_PERMANENT_LINK_KEY):
    return LinkKeySelection(key_flag)


def remote_name_request_cancel(bd_addr):
    return RemoteNameRequestCancel(bd_addr)


def read_remote_supported_features(connection_handle):
    return ReadRemoteSupportedFeatures(connection_handle)


def read_remote_extended_features(connection_handle, page_number=1):
    return ReadRemoteExtendedFeatures(connection_handle, page_number)


def read_remote_version_information(connection_handle):
    return ReadRemoteVersionInformation(connection_handle)


def read_clock_offset(connection_handle):
    return ReadClockOffset(connection_handle)


def read_lmp_handle(connection_handle):
    return ReadLmpHandle(connection_handle)


def truncated_page(bd_addr, **kwargs):
    return TruncatedPage(bd_addr, **kwargs)


def truncated_page_cancel(bd_addr):
    return TruncatedPageCancel(bd_addr)


for _cls in (PeriodicInquiryMode, ExitPeriodicInquiryMode, CreateConnectionCancel,
             AuthenticationRequested, SetConnectionEncryption,
             ChangeConnectionLinkKey, LinkKeySelection, RemoteNameRequestCancel,
             ReadRemoteSupportedFeatures, ReadRemoteExtendedFeatures,
             ReadRemoteVersionInformation, ReadClockOffset, ReadLmpHandle,
             TruncatedPage, TruncatedPageCancel):
    register_command(_cls)
del _cls


__all__ = [
    'PageScanRepetitionMode',
    'KeyFlag',
    'PeriodicInquiryMode',
    'ExitPeriodicInquiryMode',
    'CreateConnectionCancel',
    'AuthenticationRequested',
    'SetConnectionEncryption',
    'ChangeConnectionLinkKey',
    'LinkKeySelection',
    'RemoteNameRequestCancel',
    'ReadRemoteSupportedFeatures',
    'ReadRemoteExtendedFeatures',
    'ReadRemoteVersionInformation',
    'ReadClockOffset',
    'ReadLmpHandle',
    'TruncatedPage',
    'TruncatedPageCancel',
    'periodic_inquiry_mode',
    'exit_periodic_inquiry_mode',
    'create_connection_cancel',
    'authentication_requested',
    'set_connection_encryption',
    'change_connection_link_key',
    'link_key_selection',
    'remote_name_request_cancel',
    'read_remote_supported_features',
    'read_remote_extended_features',
    'read_remote_version_information',
    'read_clock_offset',
    'read_lmp_handle',
    'truncated_page',
    'truncated_page_cancel',
]
