"""
Dialogs for the Link Control pairing replies.

    0x040B  Link Key Request Reply          0x042E  User Passkey Request Reply
    0x040C  Link Key Request Neg Reply      0x042F  User Passkey Request Neg Reply
    0x040D  PIN Code Request Reply          0x0430  Remote OOB Data Request Reply
    0x040E  PIN Code Request Neg Reply      0x0433  Remote OOB Data Request Neg Reply
    0x042B  IO Capability Request Reply     0x0434  IO Capability Request Neg Reply
    0x042C  User Confirmation Reply         0x0445  Remote OOB Extended Data Reply
    0x042D  User Confirmation Neg Reply

These are answers to something the controller asked. The address to put in each
one is the address from the request event -- which is why every dialog defaults
to an empty address rather than a plausible-looking one.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QComboBox, QLineEdit

import hci.cmd.link_controller as lc_cmds
from hci.cmd.cmd_opcodes import LinkControlOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI
from .lc_common import (
    AddressOnlyUI, address_field, hex_bytes, hint, parse_bd_addr, spin,
)


class LinkKeyRequestReplyCommandUI(HCICmdUI):
    """UI for Link Key Request Reply (0x040B)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.LINK_KEY_REQUEST_REPLY)
    NAME = "Link Key Request Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.link_key_input = QLineEdit()
        self.link_key_input.setPlaceholderText("16-byte link key, hex")
        self.form_layout.addRow("Link Key:", self.link_key_input)

        self.form_layout.addRow("", hint(
            "The stored key for a device that is reconnecting. If there is no "
            "stored key send the negative reply instead -- that is what starts "
            "fresh pairing. Unlike BD_ADDR, the key is sent in the order given."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.LinkKeyRequestReply(
            bd_addr=parse_bd_addr(self.address_input.text()),
            link_key=hex_bytes(self.link_key_input.text(), "link key", 16))


class LinkKeyRequestNegativeReplyCommandUI(AddressOnlyUI):
    """UI for Link Key Request Negative Reply (0x040C)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.LINK_KEY_REQUEST_NEGATIVE_REPLY)
    NAME = "Link Key Request Negative Reply"
    COMMAND = lc_cmds.LinkKeyRequestNegativeReply
    HINT = "\"I have no key for this device\" -- starts pairing from scratch."


class PinCodeRequestReplyCommandUI(HCICmdUI):
    """UI for PIN Code Request Reply (0x040D)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.PIN_CODE_REQUEST_REPLY)
    NAME = "PIN Code Request Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.pin_input = QLineEdit("0000")
        self.pin_input.setMaxLength(16)
        self.pin_input.setToolTip("ASCII digits; most devices use 0000 or 1234")
        self.pin_input.textChanged.connect(self._update_length)
        self.form_layout.addRow("PIN Code:", self.pin_input)

        self.length_label = hint("")
        self.form_layout.addRow("", self.length_label)
        self._update_length()

        self.form_layout.addRow("", hint(
            "Legacy pairing. The PIN is sent as ASCII in a 16-byte field, "
            "zero-padded past its length."))

    def _update_length(self) -> None:
        self.length_label.setText(f"= {len(self.pin_input.text())} of 16 bytes")

    def validate_parameters(self) -> bool:
        pin = self.pin_input.text()
        if not pin:
            raise ValueError("PIN code cannot be empty -- use the negative "
                             "reply to refuse pairing")
        try:
            pin.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("PIN code must be ASCII")
        self._cmd_instance = lc_cmds.PinCodeRequestReply(
            bd_addr=parse_bd_addr(self.address_input.text()), pin_code=pin)


class PinCodeRequestNegativeReplyCommandUI(AddressOnlyUI):
    """UI for PIN Code Request Negative Reply (0x040E)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.PIN_CODE_REQUEST_NEGATIVE_REPLY)
    NAME = "PIN Code Request Negative Reply"
    COMMAND = lc_cmds.PinCodeRequestNegativeReply
    HINT = "Refuses legacy pairing; the link is then dropped."


class IoCapabilityRequestReplyCommandUI(HCICmdUI):
    """UI for IO Capability Request Reply (0x042B)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.IO_CAPABILITY_REQUEST_REPLY)
    NAME = "IO Capability Request Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.io_input = QComboBox()
        for label, value in (
                ("Display only", int(lc_cmds.IoCapability.DISPLAY_ONLY)),
                ("Display with yes/no", int(lc_cmds.IoCapability.DISPLAY_YES_NO)),
                ("Keyboard only", int(lc_cmds.IoCapability.KEYBOARD_ONLY)),
                ("No input, no output",
                 int(lc_cmds.IoCapability.NO_INPUT_NO_OUTPUT))):
            self.io_input.addItem(label, value)
        self.io_input.setCurrentIndex(3)
        self.io_input.currentIndexChanged.connect(self._update_model)
        self.form_layout.addRow("IO Capability:", self.io_input)

        self.oob_input = QComboBox()
        for label, value in (
                ("Not present", int(lc_cmds.OobDataPresent.NOT_PRESENT)),
                ("P-192 present", int(lc_cmds.OobDataPresent.P192_PRESENT)),
                ("P-256 present", int(lc_cmds.OobDataPresent.P256_PRESENT)),
                ("P-192 and P-256 present",
                 int(lc_cmds.OobDataPresent.P192_AND_P256_PRESENT))):
            self.oob_input.addItem(label, value)
        self.form_layout.addRow("OOB Data Present:", self.oob_input)

        self.auth_input = QComboBox()
        for label, value in (
                ("No bonding", 0x00),
                ("No bonding, MITM protection required", 0x01),
                ("Dedicated bonding", 0x02),
                ("Dedicated bonding, MITM protection required", 0x03),
                ("General bonding", 0x04),
                ("General bonding, MITM protection required", 0x05)):
            self.auth_input.addItem(label, value)
        self.auth_input.setCurrentIndex(4)
        self.auth_input.currentIndexChanged.connect(self._update_model)
        self.form_layout.addRow("Authentication Requirements:", self.auth_input)

        self.model_label = hint("")
        self.form_layout.addRow("", self.model_label)
        self._update_model()

        self.form_layout.addRow("", hint(
            "The first step of Secure Simple Pairing. What is declared here "
            "decides the association model, so claiming a display this device "
            "does not have produces a prompt nobody can answer."))

    def _update_model(self) -> None:
        # Rough version of the association-model table: enough to warn when the
        # declared capability cannot give the MITM protection being demanded.
        io = self.io_input.currentData()
        mitm = self.auth_input.currentData() in (0x01, 0x03, 0x05)
        if io == int(lc_cmds.IoCapability.NO_INPUT_NO_OUTPUT):
            model = "Just Works (no MITM protection possible)"
            if mitm:
                model += "  -- but MITM protection is being required, so " \
                         "pairing will fail"
        elif io == int(lc_cmds.IoCapability.DISPLAY_YES_NO):
            model = "numeric comparison, or Just Works against a peer with no IO"
        elif io == int(lc_cmds.IoCapability.KEYBOARD_ONLY):
            model = "passkey entry (this side types)"
        else:
            model = "passkey entry (this side displays)"
        self.model_label.setText(f"likely association model: {model}")

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.IoCapabilityRequestReply(
            bd_addr=parse_bd_addr(self.address_input.text()),
            io_capability=self.io_input.currentData(),
            oob_data_present=self.oob_input.currentData(),
            authentication_requirements=self.auth_input.currentData())


class IoCapabilityRequestNegativeReplyCommandUI(HCICmdUI):
    """UI for IO Capability Request Negative Reply (0x0434)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.IO_CAPABILITY_REQUEST_NEGATIVE_REPLY)
    NAME = "IO Capability Request Negative Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.reason_input = QComboBox()
        for label, value in (
                ("Unsupported remote feature (0x1A)", 0x1A),
                ("Pairing not allowed (0x18)", 0x18),
                ("Host busy - pairing (0x38)", 0x38)):
            self.reason_input.addItem(label, value)
        self.form_layout.addRow("Reason:", self.reason_input)

        self.form_layout.addRow("", hint(
            "Refuses Secure Simple Pairing with this device."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.IoCapabilityRequestNegativeReply(
            bd_addr=parse_bd_addr(self.address_input.text()),
            reason=self.reason_input.currentData())


class UserConfirmationRequestReplyCommandUI(AddressOnlyUI):
    """UI for User Confirmation Request Reply (0x042C)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.USER_CONFIRMATION_REQUEST_REPLY)
    NAME = "User Confirmation Request Reply"
    COMMAND = lc_cmds.UserConfirmationRequestReply
    HINT = ("Numeric comparison: the user confirmed the two six-digit numbers "
            "matched. Under Just Works the controller still asks, and the host "
            "answers immediately without showing anything.")


class UserConfirmationRequestNegativeReplyCommandUI(AddressOnlyUI):
    """UI for User Confirmation Request Negative Reply (0x042D)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.USER_CONFIRMATION_REQUEST_NEGATIVE_REPLY)
    NAME = "User Confirmation Request Negative Reply"
    COMMAND = lc_cmds.UserConfirmationRequestNegativeReply
    HINT = "The numbers did not match, or the user declined."


class UserPasskeyRequestReplyCommandUI(HCICmdUI):
    """UI for User Passkey Request Reply (0x042E)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.USER_PASSKEY_REQUEST_REPLY)
    NAME = "User Passkey Request Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.passkey_input = spin(0, 999999, 0,
                                  "The six digits the user entered")
        self.form_layout.addRow("Passkey:", self.passkey_input)

        self.passkey_label = hint("")
        self.passkey_input.valueChanged.connect(self._update_display)
        self.form_layout.addRow("", self.passkey_label)
        self._update_display()

        self.form_layout.addRow("", hint(
            "Sent as a number, not ASCII -- a passkey shown as 001234 is the "
            "number 1234."))

    def _update_display(self) -> None:
        self.passkey_label.setText(f"displayed as {self.passkey_input.value():06d}")

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.UserPasskeyRequestReply(
            bd_addr=parse_bd_addr(self.address_input.text()),
            numeric_value=self.passkey_input.value())


class UserPasskeyRequestNegativeReplyCommandUI(AddressOnlyUI):
    """UI for User Passkey Request Negative Reply (0x042F)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.USER_PASSKEY_REQUEST_NEGATIVE_REPLY)
    NAME = "User Passkey Request Negative Reply"
    COMMAND = lc_cmds.UserPasskeyRequestNegativeReply


class RemoteOobDataRequestReplyCommandUI(HCICmdUI):
    """UI for Remote OOB Data Request Reply (0x0430)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.REMOTE_OOB_DATA_REQUEST_REPLY)
    NAME = "Remote OOB Data Request Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.c_input = QLineEdit()
        self.c_input.setPlaceholderText("16-byte confirmation value C, hex")
        self.form_layout.addRow("C (confirmation):", self.c_input)

        self.r_input = QLineEdit()
        self.r_input.setPlaceholderText("16-byte randomiser R, hex")
        self.form_layout.addRow("R (randomiser):", self.r_input)

        self.form_layout.addRow("", hint(
            "The P-192 values received out of band, e.g. over NFC. For Secure "
            "Connections use Remote OOB Extended Data Request Reply, which "
            "carries the P-256 pair as well."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.RemoteOobDataRequestReply(
            bd_addr=parse_bd_addr(self.address_input.text()),
            c=hex_bytes(self.c_input.text(), "C", 16),
            r=hex_bytes(self.r_input.text(), "R", 16))


class RemoteOobDataRequestNegativeReplyCommandUI(AddressOnlyUI):
    """UI for Remote OOB Data Request Negative Reply (0x0433)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.REMOTE_OOB_DATA_REQUEST_NEGATIVE_REPLY)
    NAME = "Remote OOB Data Request Negative Reply"
    COMMAND = lc_cmds.RemoteOobDataRequestNegativeReply
    HINT = "No out-of-band data is available for this device."


class RemoteOobExtendedDataRequestReplyCommandUI(HCICmdUI):
    """UI for Remote OOB Extended Data Request Reply (0x0445)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.REMOTE_OOB_EXTENDED_DATA_REQUEST_REPLY)
    NAME = "Remote OOB Extended Data Request Reply"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.c192_input = QLineEdit()
        self.c192_input.setPlaceholderText("16-byte C-192, hex")
        self.form_layout.addRow("C-192:", self.c192_input)

        self.r192_input = QLineEdit()
        self.r192_input.setPlaceholderText("16-byte R-192, hex")
        self.form_layout.addRow("R-192:", self.r192_input)

        self.c256_input = QLineEdit()
        self.c256_input.setPlaceholderText("16-byte C-256, hex")
        self.form_layout.addRow("C-256:", self.c256_input)

        self.r256_input = QLineEdit()
        self.r256_input.setPlaceholderText("16-byte R-256, hex")
        self.form_layout.addRow("R-256:", self.r256_input)

        self.form_layout.addRow("", hint(
            "The Secure Connections form: both the P-192 and P-256 "
            "confirmation/randomiser pairs, 16 bytes each."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.RemoteOobExtendedDataRequestReply(
            bd_addr=parse_bd_addr(self.address_input.text()),
            c_192=hex_bytes(self.c192_input.text(), "C-192", 16),
            r_192=hex_bytes(self.r192_input.text(), "R-192", 16),
            c_256=hex_bytes(self.c256_input.text(), "C-256", 16),
            r_256=hex_bytes(self.r256_input.text(), "R-256", 16))


for _cls in (LinkKeyRequestReplyCommandUI,
             LinkKeyRequestNegativeReplyCommandUI,
             PinCodeRequestReplyCommandUI,
             PinCodeRequestNegativeReplyCommandUI,
             IoCapabilityRequestReplyCommandUI,
             IoCapabilityRequestNegativeReplyCommandUI,
             UserConfirmationRequestReplyCommandUI,
             UserConfirmationRequestNegativeReplyCommandUI,
             UserPasskeyRequestReplyCommandUI,
             UserPasskeyRequestNegativeReplyCommandUI,
             RemoteOobDataRequestReplyCommandUI,
             RemoteOobDataRequestNegativeReplyCommandUI,
             RemoteOobExtendedDataRequestReplyCommandUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'LinkKeyRequestReplyCommandUI',
    'LinkKeyRequestNegativeReplyCommandUI',
    'PinCodeRequestReplyCommandUI',
    'PinCodeRequestNegativeReplyCommandUI',
    'IoCapabilityRequestReplyCommandUI',
    'IoCapabilityRequestNegativeReplyCommandUI',
    'UserConfirmationRequestReplyCommandUI',
    'UserConfirmationRequestNegativeReplyCommandUI',
    'UserPasskeyRequestReplyCommandUI',
    'UserPasskeyRequestNegativeReplyCommandUI',
    'RemoteOobDataRequestReplyCommandUI',
    'RemoteOobDataRequestNegativeReplyCommandUI',
    'RemoteOobExtendedDataRequestReplyCommandUI',
]
