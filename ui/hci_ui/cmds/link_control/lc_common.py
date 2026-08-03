"""
Shared widgets and dialog bases for the Link Control command dialogs.

Three shapes account for most of the Link Control group: a command that takes
only a BD_ADDR, one that takes only a connection handle, and one that takes an
address plus a reason code. Giving them a base each keeps the individual
dialogs down to a class docstring and an opcode.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QComboBox, QLabel, QLineEdit, QSpinBox

from ..cmd_baseui import HCICmdUI


def parse_bd_addr(text: str) -> bytes:
    """Accept 'AA:BB:CC:DD:EE:FF', 'AA-BB-...' or bare hex, in display order."""
    clean = text.replace(":", "").replace("-", "").replace(" ", "").strip()
    if len(clean) != 12:
        raise ValueError(
            f"Address must be 6 bytes (12 hex digits), got {len(clean)} digits")
    try:
        return bytes.fromhex(clean)
    except ValueError:
        raise ValueError(f"Address is not valid hex: {text!r}")


def hex_bytes(text: str, field: str, length: int = None) -> bytes:
    """Parse a hex blob, optionally checking an exact length."""
    clean = text.strip().replace(" ", "").replace("0x", "").replace(":", "")
    if not clean:
        value = b''
    else:
        if len(clean) % 2:
            clean = "0" + clean
        try:
            value = bytes.fromhex(clean)
        except ValueError:
            raise ValueError(f"{field} is not valid hex: {text!r}")
    if length is not None and len(value) != length:
        raise ValueError(f"{field} must be {length} bytes, got {len(value)}")
    return value


def spin(minimum: int, maximum: int, value: int, tip: str = "",
         suffix: str = "") -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    if tip:
        box.setToolTip(tip)
    if suffix:
        box.setSuffix(suffix)
    return box


def hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: gray; font-size: 10pt;")
    label.setWordWrap(True)
    return label


def address_field(default: str = "00:00:00:00:00:00") -> QLineEdit:
    field = QLineEdit(default)
    field.setPlaceholderText("AA:BB:CC:DD:EE:FF")
    return field


def page_scan_repetition_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("R0 - continuous page scan", 0x00)
    combo.addItem("R1 - scans within 1.28 s", 0x01)
    combo.addItem("R2 - scans within 2.56 s", 0x02)
    combo.setCurrentIndex(1)
    combo.setToolTip("Use the value the Inquiry Result reported; guessing "
                     "makes paging much slower")
    return combo


def reason_combo(*extra) -> QComboBox:
    """Reason codes that make sense on a rejection, plus any caller-specific ones."""
    combo = QComboBox()
    for label, value in (
            ("Connection rejected: limited resources (0x0D)", 0x0D),
            ("Connection rejected: security reasons (0x0E)", 0x0E),
            ("Connection rejected: unacceptable BD_ADDR (0x0F)", 0x0F),
            ("Remote user terminated (0x13)", 0x13),
            ("Pairing not allowed (0x18)", 0x18),
            ("Unsupported remote feature (0x1A)", 0x1A),
    ) + tuple(extra):
        combo.addItem(label, value)
    return combo


class AddressOnlyUI(HCICmdUI):
    """Dialog for a command whose only parameter is a BD_ADDR."""

    COMMAND = None
    ADDRESS_LABEL = "BD_ADDR:"
    HINT = ""

    def setup_ui(self):
        super().setup_ui()
        self.address_input = address_field()
        self.form_layout.addRow(self.ADDRESS_LABEL, self.address_input)
        if self.HINT:
            self.form_layout.addRow("", hint(self.HINT))

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(
            bd_addr=parse_bd_addr(self.address_input.text()))


class HandleOnlyUI(HCICmdUI):
    """Dialog for a command whose only parameter is a connection handle."""

    COMMAND = None
    HANDLE_LABEL = "Connection Handle:"
    HINT = ""

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = spin(0x0000, 0x0EFF, 0x0000,
                                 "Handle of the ACL connection")
        self.form_layout.addRow(self.HANDLE_LABEL, self.handle_input)
        if self.HINT:
            self.form_layout.addRow("", hint(self.HINT))

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(
            connection_handle=self.handle_input.value())


class AddressReasonUI(HCICmdUI):
    """Dialog for a command taking a BD_ADDR plus a reason code."""

    COMMAND = None
    DEFAULT_REASON = 0x0D
    HINT = ""

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.reason_input = reason_combo()
        index = self.reason_input.findData(self.DEFAULT_REASON)
        if index >= 0:
            self.reason_input.setCurrentIndex(index)
        self.form_layout.addRow("Reason:", self.reason_input)

        if self.HINT:
            self.form_layout.addRow("", hint(self.HINT))

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(
            bd_addr=parse_bd_addr(self.address_input.text()),
            reason=self.reason_input.currentData())


__all__ = [
    "parse_bd_addr",
    "hex_bytes",
    "spin",
    "hint",
    "address_field",
    "page_scan_repetition_combo",
    "reason_combo",
    "AddressOnlyUI",
    "HandleOnlyUI",
    "AddressReasonUI",
]
