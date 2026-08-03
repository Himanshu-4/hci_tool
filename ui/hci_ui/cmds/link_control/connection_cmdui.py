"""
Dialogs for the Link Control connection-management and remote-query commands.

    0x0403  Periodic Inquiry Mode          0x041B  Read Remote Supported Features
    0x0408  Create Connection Cancel       0x041C  Read Remote Extended Features
    0x0411  Authentication Requested       0x041D  Read Remote Version Information
    0x0413  Set Connection Encryption      0x041F  Read Clock Offset
    0x0415  Change Connection Link Key     0x0420  Read LMP Handle
    0x0417  Link Key Selection             0x043F  Truncated Page
    0x041A  Remote Name Request Cancel     0x0440  Truncated Page Cancel

Exit Periodic Inquiry Mode (0x0404) takes no parameters, so it has no dialog --
the command factory sends it straight out when the list row is activated.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit

import hci.cmd.link_controller as lc_cmds
from hci.cmd.cmd_opcodes import LinkControlOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI
from .lc_common import (
    AddressOnlyUI, HandleOnlyUI, address_field, hint,
    page_scan_repetition_combo, parse_bd_addr, spin,
)


class PeriodicInquiryModeCommandUI(HCICmdUI):
    """UI for Periodic Inquiry Mode (0x0403)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.PERIODIC_INQUIRY_MODE)
    NAME = "Periodic Inquiry Mode"

    def setup_ui(self):
        super().setup_ui()

        self.max_period_input = spin(0x0003, 0xFFFF, 0x0060,
                                     "Maximum period between inquiries "
                                     "(N * 1.28 s)")
        self.min_period_input = spin(0x0002, 0xFFFE, 0x0040,
                                     "Minimum period between inquiries "
                                     "(N * 1.28 s)")
        self.form_layout.addRow("Max Period Length:", self.max_period_input)
        self.form_layout.addRow("Min Period Length:", self.min_period_input)

        self.period_label = hint("")
        self.max_period_input.valueChanged.connect(self._update_summary)
        self.min_period_input.valueChanged.connect(self._update_summary)
        self.form_layout.addRow("", self.period_label)

        self.lap_input = QLineEdit("33:8B:9E")
        self.lap_input.setToolTip("33:8B:9E is the General Inquiry Access Code; "
                                  "00:8B:9E is the Limited one")
        self.form_layout.addRow("LAP:", self.lap_input)

        self.inquiry_length_input = spin(0x01, 0x30, 0x30,
                                         "Length of each inquiry (N * 1.28 s)")
        self.inquiry_length_input.valueChanged.connect(self._update_summary)
        self.form_layout.addRow("Inquiry Length:", self.inquiry_length_input)

        self.num_responses_input = spin(0x00, 0xFF, 0x00,
                                        "0 = unlimited responses")
        self.form_layout.addRow("Num Responses:", self.num_responses_input)

        self.form_layout.addRow("", hint(
            "Runs inquiries automatically on a random period between min and "
            "max until Exit Periodic Inquiry Mode. The controller requires "
            "max > min > inquiry length, or it rejects the command."))
        self._update_summary()

    def _update_summary(self) -> None:
        self.period_label.setText(
            f"= inquiry {self.inquiry_length_input.value() * 1.28:.1f} s every "
            f"{self.min_period_input.value() * 1.28:.1f}-"
            f"{self.max_period_input.value() * 1.28:.1f} s")

    def validate_parameters(self) -> bool:
        lap_text = self.lap_input.text().replace(":", "").replace(" ", "")
        try:
            lap = int(lap_text, 16) & 0x00FFFFFF
        except ValueError:
            raise ValueError(f"LAP is not valid hex: {self.lap_input.text()!r}")

        self._cmd_instance = lc_cmds.PeriodicInquiryMode(
            max_period_length=self.max_period_input.value(),
            min_period_length=self.min_period_input.value(),
            lap=lap,
            inquiry_length=self.inquiry_length_input.value(),
            num_responses=self.num_responses_input.value(),
        )


class CreateConnectionCancelCommandUI(AddressOnlyUI):
    """UI for Create Connection Cancel (0x0408)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.CREATE_CONNECTION_CANCEL)
    NAME = "Create Connection Cancel"
    COMMAND = lc_cmds.CreateConnectionCancel
    HINT = ("Aborts a paging attempt. A Connection Complete still arrives, "
            "carrying Unknown Connection Identifier, so anything waiting on "
            "that event does not hang.")


class AuthenticationRequestedCommandUI(HandleOnlyUI):
    """UI for Authentication Requested (0x0411)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.AUTHENTICATION_REQUESTED)
    NAME = "Authentication Requested"
    COMMAND = lc_cmds.AuthenticationRequested
    HINT = ("Starts pairing on an existing link. Expect a PIN Code Request "
            "(legacy) or an IO Capability Request (Secure Simple Pairing) "
            "next -- both need a reply before anything else happens.")


class SetConnectionEncryptionCommandUI(HCICmdUI):
    """UI for Set Connection Encryption (0x0413)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.SET_CONNECTION_ENCRYPTION)
    NAME = "Set Connection Encryption"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.enable_input = QCheckBox("Enable link-level encryption")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Encryption:", self.enable_input)

        self.form_layout.addRow("", hint(
            "The link must be authenticated first -- on an unauthenticated "
            "link the controller answers Command Disallowed."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.SetConnectionEncryption(
            connection_handle=self.handle_input.value(),
            encryption_enable=self.enable_input.isChecked())


class ChangeConnectionLinkKeyCommandUI(HandleOnlyUI):
    """UI for Change Connection Link Key (0x0415)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.CHANGE_CONNECTION_LINK_KEY)
    NAME = "Change Connection Link Key"
    COMMAND = lc_cmds.ChangeConnectionLinkKey
    HINT = "Regenerates the link key; completes with Change Connection Link Key Complete."


class LinkKeySelectionCommandUI(HCICmdUI):
    """UI for Link Key Selection (0x0417), historically Master Link Key."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.MASTER_LINK_KEY)
    NAME = "Link Key Selection"

    def setup_ui(self):
        super().setup_ui()

        self.key_flag_input = QComboBox()
        self.key_flag_input.addItem("Use the semi-permanent link key", 0x00)
        self.key_flag_input.addItem("Use the temporary link key", 0x01)
        self.form_layout.addRow("Key Flag:", self.key_flag_input)

        self.form_layout.addRow("", hint(
            "Switches every link to the temporary key or back. Only used by "
            "the legacy broadcast encryption scheme."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.LinkKeySelection(
            key_flag=self.key_flag_input.currentData())


class RemoteNameRequestCancelCommandUI(AddressOnlyUI):
    """UI for Remote Name Request Cancel (0x041A)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.REMOTE_NAME_REQUEST_CANCEL)
    NAME = "Remote Name Request Cancel"
    COMMAND = lc_cmds.RemoteNameRequestCancel


class ReadRemoteSupportedFeaturesCommandUI(HandleOnlyUI):
    """UI for Read Remote Supported Features (0x041B)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_REMOTE_SUPPORTED_FEATURES)
    NAME = "Read Remote Supported Features"
    COMMAND = lc_cmds.ReadRemoteSupportedFeatures
    HINT = ("LMP feature page 0. For the host features -- SSP, LE support -- "
            "read extended feature page 1 instead.")


class ReadRemoteExtendedFeaturesCommandUI(HCICmdUI):
    """UI for Read Remote Extended Features (0x041C)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_REMOTE_EXTENDED_FEATURES)
    NAME = "Read Remote Extended Features"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.page_input = spin(0x00, 0xFF, 0x01,
                               "Page 0 is the LMP features, page 1 the host "
                               "features, page 2 the Secure Connections ones")
        self.form_layout.addRow("Page Number:", self.page_input)

        self.form_layout.addRow("", hint(
            "Page 1 is usually what you want -- it carries the SSP and LE "
            "support bits. Page 0 is identical to Read Remote Supported "
            "Features."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.ReadRemoteExtendedFeatures(
            connection_handle=self.handle_input.value(),
            page_number=self.page_input.value())


class ReadRemoteVersionInformationCommandUI(HandleOnlyUI):
    """UI for Read Remote Version Information (0x041D)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_REMOTE_VERSION_INFORMATION)
    NAME = "Read Remote Version Information"
    COMMAND = lc_cmds.ReadRemoteVersionInformation
    HINT = "Returns the peer's LMP version, manufacturer and subversion."


class ReadClockOffsetCommandUI(HandleOnlyUI):
    """UI for Read Clock Offset (0x041F)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.READ_CLOCK_OFFSET)
    NAME = "Read Clock Offset"
    COMMAND = lc_cmds.ReadClockOffset
    HINT = ("Worth caching with the address and page scan repetition mode -- "
            "supplying it to Create Connection makes a later page much faster.")


class ReadLmpHandleCommandUI(HandleOnlyUI):
    """UI for Read LMP Handle (0x0420)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.READ_LMP_HANDLE)
    NAME = "Read LMP Handle"
    COMMAND = lc_cmds.ReadLmpHandle
    HANDLE_LABEL = "SCO Connection Handle:"
    HINT = "Maps a synchronous connection handle to its LMP handle."


class TruncatedPageCommandUI(HCICmdUI):
    """UI for Truncated Page (0x043F)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.TRUNCATED_PAGE_MODE)
    NAME = "Truncated Page"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.psrm_input = page_scan_repetition_combo()
        self.form_layout.addRow("Page Scan Repetition Mode:", self.psrm_input)

        self.clock_offset_input = spin(0x0000, 0xFFFF, 0x0000,
                                       "Clock offset from an earlier inquiry "
                                       "result; 0 if unknown")
        self.form_layout.addRow("Clock Offset:", self.clock_offset_input)

        self.form_layout.addRow("", hint(
            "Pages the device and drops the link as soon as it answers -- used "
            "to wake a peripheral, not to connect to it. Completes with "
            "Truncated Page Complete."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.TruncatedPage(
            bd_addr=parse_bd_addr(self.address_input.text()),
            page_scan_repetition_mode=self.psrm_input.currentData(),
            clock_offset=self.clock_offset_input.value())


class TruncatedPageCancelCommandUI(AddressOnlyUI):
    """UI for Truncated Page Cancel (0x0440)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.TRUNCATED_PAGE_MODE_CANCEL)
    NAME = "Truncated Page Cancel"
    COMMAND = lc_cmds.TruncatedPageCancel


for _cls in (PeriodicInquiryModeCommandUI,
             CreateConnectionCancelCommandUI,
             AuthenticationRequestedCommandUI,
             SetConnectionEncryptionCommandUI,
             ChangeConnectionLinkKeyCommandUI,
             LinkKeySelectionCommandUI,
             RemoteNameRequestCancelCommandUI,
             ReadRemoteSupportedFeaturesCommandUI,
             ReadRemoteExtendedFeaturesCommandUI,
             ReadRemoteVersionInformationCommandUI,
             ReadClockOffsetCommandUI,
             ReadLmpHandleCommandUI,
             TruncatedPageCommandUI,
             TruncatedPageCancelCommandUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'PeriodicInquiryModeCommandUI',
    'CreateConnectionCancelCommandUI',
    'AuthenticationRequestedCommandUI',
    'SetConnectionEncryptionCommandUI',
    'ChangeConnectionLinkKeyCommandUI',
    'LinkKeySelectionCommandUI',
    'RemoteNameRequestCancelCommandUI',
    'ReadRemoteSupportedFeaturesCommandUI',
    'ReadRemoteExtendedFeaturesCommandUI',
    'ReadRemoteVersionInformationCommandUI',
    'ReadClockOffsetCommandUI',
    'ReadLmpHandleCommandUI',
    'TruncatedPageCommandUI',
    'TruncatedPageCancelCommandUI',
]
