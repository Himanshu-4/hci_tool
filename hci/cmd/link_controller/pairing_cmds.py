"""
Link Control commands that answer the controller's pairing requests.

    0x040B  Link_Key_Request_Reply             0x042E  User_Passkey_Request_Reply
    0x040C  Link_Key_Request_Negative_Reply    0x042F  User_Passkey_Request_Neg_Reply
    0x040D  PIN_Code_Request_Reply             0x0430  Remote_OOB_Data_Request_Reply
    0x040E  PIN_Code_Request_Negative_Reply    0x0433  Remote_OOB_Data_Request_Neg_Reply
    0x042B  IO_Capability_Request_Reply        0x0434  IO_Capability_Request_Neg_Reply
    0x042C  User_Confirmation_Request_Reply    0x0445  Remote_OOB_Extended_Data_Reply
    0x042D  User_Confirmation_Request_Neg_Reply

Every one of these is a *reply*: the controller asked, and pairing is blocked
until the host answers. Sending one unprompted gets Command Disallowed, and
never answering leaves the link half-paired until it times out -- which is why
each has a negative reply, and why the negative reply is the right thing to
send when a request cannot be satisfied.

Which request arrives depends on Secure Simple Pairing: legacy pairing asks for
a PIN code, SSP asks for IO capability and then confirmation or a passkey.
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
class IoCapability(IntEnum):
    """
    What the local device can do during pairing.

    This plus the peer's capability decides the association model: two
    DISPLAY_YES_NO devices get numeric comparison, a KEYBOARD_ONLY paired with a
    DISPLAY_ONLY gets passkey entry, and anything involving NO_INPUT_NO_OUTPUT
    falls back to Just Works with no MITM protection.
    """

    DISPLAY_ONLY = 0x00
    DISPLAY_YES_NO = 0x01
    KEYBOARD_ONLY = 0x02
    NO_INPUT_NO_OUTPUT = 0x03


@unique
class OobDataPresent(IntEnum):
    """Whether out-of-band pairing data was received from the peer."""

    NOT_PRESENT = 0x00
    P192_PRESENT = 0x01
    P256_PRESENT = 0x02
    P192_AND_P256_PRESENT = 0x03


@unique
class AuthenticationRequirements(IntEnum):
    """
    Bonding and MITM requirements.

    The MITM variants make the controller refuse an association model that
    cannot authenticate, rather than silently downgrading to Just Works.
    """

    NO_BONDING = 0x00
    NO_BONDING_MITM = 0x01
    DEDICATED_BONDING = 0x02
    DEDICATED_BONDING_MITM = 0x03
    GENERAL_BONDING = 0x04
    GENERAL_BONDING_MITM = 0x05


def _coerce_addr(addr: Union[bytes, str]) -> bytes:
    if isinstance(addr, str):
        return bd_addr_str_to_bytes(addr)
    addr = bytes(addr)
    if len(addr) != 6:
        raise ValueError(f"Invalid address length {len(addr)}, must be 6 bytes")
    return addr


class _AddressReply(HciCmdBasePacket):
    """Shared body for the replies whose only parameter is a BD_ADDR."""

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


class LinkKeyRequestReply(HciCmdBasePacket):
    """
    Link Key Request Reply Command (0x040B).

    Hands the controller the stored link key for a device it is reconnecting
    to. If there is no stored key, send the negative reply instead -- that is
    what triggers fresh pairing.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.LINK_KEY_REQUEST_REPLY)
    NAME = "Link_Key_Request_Reply"

    LINK_KEY_LENGTH = 16

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 link_key: bytes = b"\x00" * 16):
        super().__init__(bd_addr=_coerce_addr(bd_addr), link_key=bytes(link_key))

    def _validate_params(self) -> None:
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}")
        if len(self.params['link_key']) != self.LINK_KEY_LENGTH:
            raise ValueError(f"link_key must be {self.LINK_KEY_LENGTH} bytes, "
                             f"got {len(self.params['link_key'])}")

    def _serialize_params(self) -> bytes:
        # The key goes out in the order given -- unlike BD_ADDR, it is not
        # reversed.
        return bytes(reversed(self.params['bd_addr'])) + self.params['link_key']

    @classmethod
    def from_bytes(cls, data: bytes) -> "LinkKeyRequestReply":
        if len(data) < 22:
            raise ValueError(f"Invalid data length: {len(data)}, expected 22")
        return cls(bytes(reversed(data[:6])), data[6:22])


class LinkKeyRequestNegativeReply(_AddressReply):
    """
    Link Key Request Negative Reply Command (0x040C).

    "I have no key for this device" -- which starts pairing from scratch.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.LINK_KEY_REQUEST_NEGATIVE_REPLY)
    NAME = "Link_Key_Request_Negative_Reply"


class PinCodeRequestReply(HciCmdBasePacket):
    """
    PIN Code Request Reply Command (0x040D).

    Legacy pairing. The PIN field is always 16 bytes on the wire, zero-padded
    past `pin_code_length`; most devices use the 4-digit ASCII "0000" or "1234".
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.PIN_CODE_REQUEST_REPLY)
    NAME = "PIN_Code_Request_Reply"

    PIN_FIELD_LENGTH = 16

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 pin_code: Union[bytes, str] = "0000"):
        if isinstance(pin_code, str):
            pin_code = pin_code.encode("ascii", "strict")
        pin_code = bytes(pin_code)
        super().__init__(bd_addr=_coerce_addr(bd_addr),
                         pin_code_length=len(pin_code),
                         pin_code=pin_code)

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        if not (1 <= p['pin_code_length'] <= self.PIN_FIELD_LENGTH):
            raise ValueError(f"pin_code_length {p['pin_code_length']} out of range "
                             f"(1..{self.PIN_FIELD_LENGTH})")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes(reversed(p['bd_addr']))
                + bytes([p['pin_code_length']])
                + p['pin_code'].ljust(self.PIN_FIELD_LENGTH, b"\x00"))

    @classmethod
    def from_bytes(cls, data: bytes) -> "PinCodeRequestReply":
        if len(data) < 23:
            raise ValueError(f"Invalid data length: {len(data)}, expected 23")
        length = data[6]
        return cls(bytes(reversed(data[:6])), data[7:7 + length])

    def __str__(self) -> str:
        addr = ":".join(f"{b:02X}" for b in self.params['bd_addr'])
        return (f"{self.NAME} : 0x{self.OPCODE:04X} ({addr}, "
                f"{self.params['pin_code_length']}-digit PIN)")


class PinCodeRequestNegativeReply(_AddressReply):
    """PIN Code Request Negative Reply Command (0x040E). Rejects pairing."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.PIN_CODE_REQUEST_NEGATIVE_REPLY)
    NAME = "PIN_Code_Request_Negative_Reply"


class IoCapabilityRequestReply(HciCmdBasePacket):
    """
    IO Capability Request Reply Command (0x042B).

    The first step of Secure Simple Pairing. What is declared here decides
    which association model runs, so declaring DISPLAY_YES_NO on a device with
    no display produces a confirmation prompt nobody can answer.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.IO_CAPABILITY_REQUEST_REPLY)
    NAME = "IO_Capability_Request_Reply"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 io_capability: int = IoCapability.NO_INPUT_NO_OUTPUT,
                 oob_data_present: int = OobDataPresent.NOT_PRESENT,
                 authentication_requirements: int =
                 AuthenticationRequirements.GENERAL_BONDING):
        super().__init__(
            bd_addr=_coerce_addr(bd_addr),
            io_capability=int(io_capability),
            oob_data_present=int(oob_data_present),
            authentication_requirements=int(authentication_requirements),
        )

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        if not (0x00 <= p['io_capability'] <= 0x03):
            raise ValueError(f"Invalid io_capability: {p['io_capability']}")
        if not (0x00 <= p['oob_data_present'] <= 0x03):
            raise ValueError(f"Invalid oob_data_present: {p['oob_data_present']}")
        if not (0x00 <= p['authentication_requirements'] <= 0x05):
            raise ValueError("Invalid authentication_requirements: "
                             f"{p['authentication_requirements']}")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes(reversed(p['bd_addr']))
                + bytes([p['io_capability'], p['oob_data_present'],
                         p['authentication_requirements']]))

    @classmethod
    def from_bytes(cls, data: bytes) -> "IoCapabilityRequestReply":
        if len(data) < 9:
            raise ValueError(f"Invalid data length: {len(data)}, expected 9")
        return cls(bytes(reversed(data[:6])), data[6], data[7], data[8])


class IoCapabilityRequestNegativeReply(HciCmdBasePacket):
    """IO Capability Request Negative Reply Command (0x0434). Refuses SSP."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.IO_CAPABILITY_REQUEST_NEGATIVE_REPLY)
    NAME = "IO_Capability_Request_Negative_Reply"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 reason: int = 0x1A):     # Unsupported Remote Feature
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
    def from_bytes(cls, data: bytes) -> "IoCapabilityRequestNegativeReply":
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected 7")
        return cls(bytes(reversed(data[:6])), data[6])


class UserConfirmationRequestReply(_AddressReply):
    """
    User Confirmation Request Reply Command (0x042C).

    Numeric comparison: the user said the two six-digit numbers matched. For
    Just Works the controller still asks, and the host answers immediately
    without showing anything.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.USER_CONFIRMATION_REQUEST_REPLY)
    NAME = "User_Confirmation_Request_Reply"


class UserConfirmationRequestNegativeReply(_AddressReply):
    """User Confirmation Request Negative Reply Command (0x042D)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.USER_CONFIRMATION_REQUEST_NEGATIVE_REPLY)
    NAME = "User_Confirmation_Request_Negative_Reply"


class UserPasskeyRequestReply(HciCmdBasePacket):
    """
    User Passkey Request Reply Command (0x042E).

    Passkey entry: the six digits the user typed, as a number 0..999999 -- not
    as ASCII, and leading zeros are simply a smaller number.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.USER_PASSKEY_REQUEST_REPLY)
    NAME = "User_Passkey_Request_Reply"

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 numeric_value: int = 0):
        super().__init__(bd_addr=_coerce_addr(bd_addr),
                         numeric_value=numeric_value)

    def _validate_params(self) -> None:
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}")
        if not (0 <= self.params['numeric_value'] <= 999999):
            raise ValueError(f"numeric_value {self.params['numeric_value']} out of "
                             "range (0..999999)")

    def _serialize_params(self) -> bytes:
        return (bytes(reversed(self.params['bd_addr']))
                + struct.pack("<I", self.params['numeric_value']))

    @classmethod
    def from_bytes(cls, data: bytes) -> "UserPasskeyRequestReply":
        if len(data) < 10:
            raise ValueError(f"Invalid data length: {len(data)}, expected 10")
        return cls(bytes(reversed(data[:6])), struct.unpack_from("<I", data, 6)[0])

    def __str__(self) -> str:
        addr = ":".join(f"{b:02X}" for b in self.params['bd_addr'])
        return (f"{self.NAME} : 0x{self.OPCODE:04X} ({addr}, passkey "
                f"{self.params['numeric_value']:06d})")


class UserPasskeyRequestNegativeReply(_AddressReply):
    """User Passkey Request Negative Reply Command (0x042F)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.USER_PASSKEY_REQUEST_NEGATIVE_REPLY)
    NAME = "User_Passkey_Request_Negative_Reply"


class RemoteOobDataRequestReply(HciCmdBasePacket):
    """
    Remote OOB Data Request Reply Command (0x0430).

    The P-192 confirmation and randomiser values received out of band, e.g. over
    NFC. Both are 16 bytes.
    """

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.REMOTE_OOB_DATA_REQUEST_REPLY)
    NAME = "Remote_OOB_Data_Request_Reply"

    VALUE_LENGTH = 16

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 c: bytes = b"\x00" * 16, r: bytes = b"\x00" * 16):
        super().__init__(bd_addr=_coerce_addr(bd_addr), c=bytes(c), r=bytes(r))

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        for value, name in ((p['c'], "c"), (p['r'], "r")):
            if len(value) != self.VALUE_LENGTH:
                raise ValueError(f"{name} must be {self.VALUE_LENGTH} bytes, "
                                 f"got {len(value)}")

    def _serialize_params(self) -> bytes:
        p = self.params
        return bytes(reversed(p['bd_addr'])) + p['c'] + p['r']

    @classmethod
    def from_bytes(cls, data: bytes) -> "RemoteOobDataRequestReply":
        if len(data) < 38:
            raise ValueError(f"Invalid data length: {len(data)}, expected 38")
        return cls(bytes(reversed(data[:6])), data[6:22], data[22:38])


class RemoteOobDataRequestNegativeReply(_AddressReply):
    """Remote OOB Data Request Negative Reply Command (0x0433)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.REMOTE_OOB_DATA_REQUEST_NEGATIVE_REPLY)
    NAME = "Remote_OOB_Data_Request_Negative_Reply"


class RemoteOobExtendedDataRequestReply(HciCmdBasePacket):
    """
    Remote OOB Extended Data Request Reply Command (0x0445).

    The Secure Connections form: P-192 *and* P-256 confirmation/randomiser
    values, 16 bytes each.
    """

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.REMOTE_OOB_EXTENDED_DATA_REQUEST_REPLY)
    NAME = "Remote_OOB_Extended_Data_Request_Reply"

    VALUE_LENGTH = 16

    def __init__(self, bd_addr: Union[bytes, str] = b"\x00" * 6,
                 c_192: bytes = b"\x00" * 16, r_192: bytes = b"\x00" * 16,
                 c_256: bytes = b"\x00" * 16, r_256: bytes = b"\x00" * 16):
        super().__init__(bd_addr=_coerce_addr(bd_addr), c_192=bytes(c_192),
                         r_192=bytes(r_192), c_256=bytes(c_256),
                         r_256=bytes(r_256))

    def _validate_params(self) -> None:
        p = self.params
        if len(p['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(p['bd_addr'])}")
        for name in ("c_192", "r_192", "c_256", "r_256"):
            if len(p[name]) != self.VALUE_LENGTH:
                raise ValueError(f"{name} must be {self.VALUE_LENGTH} bytes, "
                                 f"got {len(p[name])}")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes(reversed(p['bd_addr']))
                + p['c_192'] + p['r_192'] + p['c_256'] + p['r_256'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "RemoteOobExtendedDataRequestReply":
        if len(data) < 70:
            raise ValueError(f"Invalid data length: {len(data)}, expected 70")
        return cls(bytes(reversed(data[:6])), data[6:22], data[22:38],
                   data[38:54], data[54:70])


# ------------------------------------------------------------ helper builders

def link_key_request_reply(bd_addr, link_key):
    return LinkKeyRequestReply(bd_addr, link_key)


def link_key_request_negative_reply(bd_addr):
    return LinkKeyRequestNegativeReply(bd_addr)


def pin_code_request_reply(bd_addr, pin_code="0000"):
    return PinCodeRequestReply(bd_addr, pin_code)


def pin_code_request_negative_reply(bd_addr):
    return PinCodeRequestNegativeReply(bd_addr)


def io_capability_request_reply(bd_addr, **kwargs):
    return IoCapabilityRequestReply(bd_addr, **kwargs)


def io_capability_request_negative_reply(bd_addr, reason=0x1A):
    return IoCapabilityRequestNegativeReply(bd_addr, reason)


def user_confirmation_request_reply(bd_addr):
    return UserConfirmationRequestReply(bd_addr)


def user_confirmation_request_negative_reply(bd_addr):
    return UserConfirmationRequestNegativeReply(bd_addr)


def user_passkey_request_reply(bd_addr, numeric_value):
    return UserPasskeyRequestReply(bd_addr, numeric_value)


def user_passkey_request_negative_reply(bd_addr):
    return UserPasskeyRequestNegativeReply(bd_addr)


def remote_oob_data_request_reply(bd_addr, c, r):
    return RemoteOobDataRequestReply(bd_addr, c, r)


def remote_oob_data_request_negative_reply(bd_addr):
    return RemoteOobDataRequestNegativeReply(bd_addr)


def remote_oob_extended_data_request_reply(bd_addr, **kwargs):
    return RemoteOobExtendedDataRequestReply(bd_addr, **kwargs)


for _cls in (LinkKeyRequestReply, LinkKeyRequestNegativeReply,
             PinCodeRequestReply, PinCodeRequestNegativeReply,
             IoCapabilityRequestReply, IoCapabilityRequestNegativeReply,
             UserConfirmationRequestReply, UserConfirmationRequestNegativeReply,
             UserPasskeyRequestReply, UserPasskeyRequestNegativeReply,
             RemoteOobDataRequestReply, RemoteOobDataRequestNegativeReply,
             RemoteOobExtendedDataRequestReply):
    register_command(_cls)
del _cls


__all__ = [
    'IoCapability',
    'OobDataPresent',
    'AuthenticationRequirements',
    'LinkKeyRequestReply',
    'LinkKeyRequestNegativeReply',
    'PinCodeRequestReply',
    'PinCodeRequestNegativeReply',
    'IoCapabilityRequestReply',
    'IoCapabilityRequestNegativeReply',
    'UserConfirmationRequestReply',
    'UserConfirmationRequestNegativeReply',
    'UserPasskeyRequestReply',
    'UserPasskeyRequestNegativeReply',
    'RemoteOobDataRequestReply',
    'RemoteOobDataRequestNegativeReply',
    'RemoteOobExtendedDataRequestReply',
    'link_key_request_reply',
    'link_key_request_negative_reply',
    'pin_code_request_reply',
    'pin_code_request_negative_reply',
    'io_capability_request_reply',
    'io_capability_request_negative_reply',
    'user_confirmation_request_reply',
    'user_confirmation_request_negative_reply',
    'user_passkey_request_reply',
    'user_passkey_request_negative_reply',
    'remote_oob_data_request_reply',
    'remote_oob_data_request_negative_reply',
    'remote_oob_extended_data_request_reply',
]
