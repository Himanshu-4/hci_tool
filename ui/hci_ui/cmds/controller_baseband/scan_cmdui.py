"""
Command dialogs for BR/EDR discoverability, connectability and paging.

    0x0C16  Write Connection Accept Timeout
    0x0C18  Write Page Timeout
    0x0C1A  Write Scan Enable
    0x0C1C  Write Page Scan Activity
    0x0C1E  Write Inquiry Scan Activity
    0x0C24  Write Class Of Device
    0x0C43  Write Inquiry Scan Type
    0x0C47  Write Page Scan Type

Every timing field here is in 0.625 ms slots, so each dialog shows the
millisecond value live next to the raw number -- the slot count is what goes on
the wire, but nobody thinks in slots.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QWidget,
)

import hci.cmd.controller_baseband as cb_cmds
from hci.cmd.cmd_opcodes import ControllerBasebandOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI

#: 1 slot = 0.625 ms.
SLOT_MS = 0.625


def _slot_spin(minimum: int, maximum: int, value: int, tip: str = "") -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    if tip:
        box.setToolTip(tip)
    return box


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: gray; font-size: 10pt;")
    label.setWordWrap(True)
    return label


def _ms_label() -> QLabel:
    label = QLabel("-")
    label.setStyleSheet("color: gray;")
    return label


def _fmt_ms(slots: int) -> str:
    ms = slots * SLOT_MS
    return f"{ms / 1000:.3f} s" if ms >= 1000 else f"{ms:.2f} ms"


class _SlotTimeoutUI(HCICmdUI):
    """Shared dialog for the commands that are one 16-bit slot count."""

    COMMAND = None
    FIELD_LABEL = "Timeout"
    DEFAULT = 0x2000
    MINIMUM = 0x0001
    MAXIMUM = 0xFFFF

    def setup_ui(self):
        super().setup_ui()

        self.value_input = _slot_spin(self.MINIMUM, self.MAXIMUM, self.DEFAULT,
                                      "In 0.625 ms slots")
        self.value_input.valueChanged.connect(self._update_ms)
        self.form_layout.addRow(f"{self.FIELD_LABEL} (slots):", self.value_input)

        self.ms_label = _ms_label()
        self.form_layout.addRow("", self.ms_label)
        self._update_ms()

    def _update_ms(self) -> None:
        self.ms_label.setText(f"= {_fmt_ms(self.value_input.value())}")

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(self.value_input.value())


class WritePageTimeoutUI(_SlotTimeoutUI):
    """UI for Write Page Timeout (0x0C18)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_PAGE_TIMEOUT)
    NAME = "Write Page Timeout"

    COMMAND = cb_cmds.WritePageTimeout
    FIELD_LABEL = "Page Timeout"
    DEFAULT = 0x2000        # 5.12 s

    def setup_ui(self):
        super().setup_ui()

        presets = QWidget()
        layout = QHBoxLayout(presets)
        layout.setContentsMargins(0, 0, 0, 0)
        for label, value in (("Default 5.12 s", 0x2000),
                             ("Fast 1.28 s", 0x0800),
                             ("Patient 10.24 s", 0x4000)):
            button = QPushButton(label)
            button.clicked.connect(lambda _, v=value: self.value_input.setValue(v))
            layout.addWidget(button)
        layout.addStretch(1)
        self.form_layout.addRow("Presets:", presets)

        self.form_layout.addRow("", _hint(
            "How long Create Connection keeps paging before it gives up. On "
            "expiry, Connection Complete comes back with Page Timeout (0x04). "
            "A short timeout fails faster on absent devices but can also miss a "
            "device that is only scanning occasionally."))


class WriteConnectionAcceptTimeoutUI(_SlotTimeoutUI):
    """UI for Write Connection Accept Timeout (0x0C16)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_CONNECTION_ACCEPT_TIMEOUT)
    NAME = "Write Connection Accept Timeout"

    COMMAND = cb_cmds.WriteConnectionAcceptTimeout
    FIELD_LABEL = "Connection Accept Timeout"
    DEFAULT = 0x1FA0        # 5 s
    MAXIMUM = 0xB540

    def setup_ui(self):
        super().setup_ui()
        self.form_layout.addRow("", _hint(
            "How long the controller waits for the host to answer an incoming "
            "Connection Request before rejecting it itself."))


class WriteScanEnableUI(HCICmdUI):
    """UI for Write Scan Enable (0x0C1A)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_SCAN_ENABLE)
    NAME = "Write Scan Enable"

    def setup_ui(self):
        super().setup_ui()

        self.inquiry_scan_input = QCheckBox("Inquiry scan (discoverable)")
        self.inquiry_scan_input.setToolTip(
            "The device answers inquiries, so it shows up in other devices' scans")
        self.inquiry_scan_input.stateChanged.connect(self._update_summary)
        self.form_layout.addRow("Scan Enable:", self.inquiry_scan_input)

        self.page_scan_input = QCheckBox("Page scan (connectable)")
        self.page_scan_input.setToolTip(
            "The device answers pages, so others can connect to it")
        self.page_scan_input.setChecked(True)
        self.page_scan_input.stateChanged.connect(self._update_summary)
        self.form_layout.addRow("", self.page_scan_input)

        self.summary_label = _ms_label()
        self.form_layout.addRow("Value:", self.summary_label)
        self._update_summary()

        self.form_layout.addRow("", _hint(
            "How often and for how long each scan actually listens is set by "
            "Write Page Scan Activity and Write Inquiry Scan Activity."))

    def _update_summary(self) -> None:
        value = self._value()
        names = {0x00: "no scans", 0x01: "inquiry scan only",
                 0x02: "page scan only", 0x03: "inquiry + page scan"}
        self.summary_label.setText(f"0x{value:02X} - {names[value]}")

    def _value(self) -> int:
        value = 0
        if self.inquiry_scan_input.isChecked():
            value |= int(cb_cmds.ScanEnable.INQUIRY_SCAN)
        if self.page_scan_input.isChecked():
            value |= int(cb_cmds.ScanEnable.PAGE_SCAN)
        return value

    def validate_parameters(self) -> bool:
        self._cmd_instance = cb_cmds.WriteScanEnable(scan_enable=self._value())


class _ScanActivityUI(HCICmdUI):
    """Shared dialog for the page/inquiry scan activity commands."""

    COMMAND = None
    KIND = "Scan"

    def setup_ui(self):
        super().setup_ui()

        self.interval_input = _slot_spin(0x0012, 0x1000, 0x0800,
                                         "How often the scan starts, in "
                                         "0.625 ms slots")
        self.interval_input.valueChanged.connect(self._update_summary)
        self.form_layout.addRow(f"{self.KIND} Interval (slots):", self.interval_input)

        self.window_input = _slot_spin(0x0011, 0x1000, 0x0012,
                                       "How long each scan lasts, in "
                                       "0.625 ms slots")
        self.window_input.valueChanged.connect(self._update_summary)
        self.form_layout.addRow(f"{self.KIND} Window (slots):", self.window_input)

        self.summary_label = _ms_label()
        self.form_layout.addRow("", self.summary_label)

        presets = QWidget()
        layout = QHBoxLayout(presets)
        layout.setContentsMargins(0, 0, 0, 0)
        for label, (interval, window) in (
                ("Spec default", cb_cmds.SCAN_ACTIVITY_DEFAULT),
                ("Fast 50%", cb_cmds.SCAN_ACTIVITY_FAST),
                ("Continuous", cb_cmds.SCAN_ACTIVITY_CONTINUOUS)):
            button = QPushButton(label)
            button.clicked.connect(
                lambda _, i=interval, w=window: self._set(i, w))
            layout.addWidget(button)
        layout.addStretch(1)
        self.form_layout.addRow("Presets:", presets)

        self._update_summary()

    def _set(self, interval: int, window: int) -> None:
        # Interval first: the window is clamped against it in the summary, and
        # setting a large window against a stale small interval looks like an
        # error the user did not make.
        self.interval_input.setValue(interval)
        self.window_input.setValue(window)

    def _update_summary(self) -> None:
        interval = self.interval_input.value()
        window = self.window_input.value()
        text = (f"interval {_fmt_ms(interval)}, window {_fmt_ms(window)} "
                f"({window / interval * 100:.0f}% duty cycle)")
        if window > interval:
            text += "  -- window must not exceed interval"
            self.summary_label.setStyleSheet("color: red;")
        else:
            self.summary_label.setStyleSheet("color: gray;")
        self.summary_label.setText(text)

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(self.interval_input.value(),
                                          self.window_input.value())


class WritePageScanActivityUI(_ScanActivityUI):
    """UI for Write Page Scan Activity (0x0C1C)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_PAGE_SCAN_ACTIVITY)
    NAME = "Write Page Scan Activity"

    COMMAND = cb_cmds.WritePageScanActivity
    KIND = "Page Scan"

    def setup_ui(self):
        super().setup_ui()
        self.form_layout.addRow("", _hint(
            "How quickly this device can be connected to. Needs page scan "
            "enabled in Write Scan Enable to have any effect."))


class WriteInquiryScanActivityUI(_ScanActivityUI):
    """UI for Write Inquiry Scan Activity (0x0C1E)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_INQUIRY_SCAN_ACTIVITY)
    NAME = "Write Inquiry Scan Activity"

    COMMAND = cb_cmds.WriteInquiryScanActivity
    KIND = "Inquiry Scan"

    def setup_ui(self):
        super().setup_ui()
        self.form_layout.addRow("", _hint(
            "How quickly this device is discovered. Needs inquiry scan enabled "
            "in Write Scan Enable to have any effect."))


class _ScanTypeUI(HCICmdUI):
    """Shared dialog for the two scan type commands."""

    COMMAND = None

    def setup_ui(self):
        super().setup_ui()

        self.type_input = QComboBox()
        self.type_input.addItem("Standard (mandatory)",
                                int(cb_cmds.ScanType.STANDARD))
        self.type_input.addItem("Interlaced (optional)",
                                int(cb_cmds.ScanType.INTERLACED))
        self.form_layout.addRow("Scan Type:", self.type_input)

        self.form_layout.addRow("", _hint(
            "Interlaced scanning roughly halves how long the other side waits, "
            "at the cost of more radio time. It is optional -- a controller "
            "without it answers Unsupported Feature Or Parameter Value (0x11)."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(self.type_input.currentData())


class WritePageScanTypeUI(_ScanTypeUI):
    """UI for Write Page Scan Type (0x0C47)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_PAGE_SCAN_TYPE)
    NAME = "Write Page Scan Type"
    COMMAND = cb_cmds.WritePageScanType


class WriteInquiryScanTypeUI(_ScanTypeUI):
    """UI for Write Inquiry Scan Type (0x0C43)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_INQUIRY_SCAN_TYPE)
    NAME = "Write Inquiry Scan Type"
    COMMAND = cb_cmds.WriteInquiryScanType


class WriteClassOfDeviceUI(HCICmdUI):
    """UI for Write Class Of Device (0x0C24)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_CLASS_OF_DEVICE)
    NAME = "Write Class Of Device"

    #: (label, CoD) for the device types this tool is usually pretending to be.
    PRESETS = (
        ("Computer / laptop", 0x0C010C),
        ("Phone / smartphone", 0x5A020C),
        ("Audio headset", 0x240404),
        ("Audio speaker", 0x200414),
        ("Keyboard", 0x002540),
        ("Mouse", 0x002580),
        ("Uncategorised", 0x000000),
    )

    def setup_ui(self):
        super().setup_ui()

        self.preset_input = QComboBox()
        for label, value in self.PRESETS:
            self.preset_input.addItem(f"{label}  (0x{value:06X})", value)
        self.preset_input.currentIndexChanged.connect(self._apply_preset)
        self.form_layout.addRow("Preset:", self.preset_input)

        self.cod_input = QLineEdit(f"{self.PRESETS[0][1]:06X}")
        self.cod_input.setPlaceholderText("3-byte hex, e.g. 0C010C")
        self.cod_input.textChanged.connect(self._update_summary)
        self.form_layout.addRow("Class Of Device:", self.cod_input)

        self.summary_label = _ms_label()
        self.form_layout.addRow("", self.summary_label)
        self._update_summary()

    def _apply_preset(self) -> None:
        self.cod_input.setText(f"{self.preset_input.currentData():06X}")

    def _update_summary(self) -> None:
        try:
            value = int(self.cod_input.text().strip().replace("0x", "") or "0", 16)
        except ValueError:
            self.summary_label.setText("invalid hex")
            return
        # Bits 8-12 are the major device class, 13-23 the major service classes.
        major_device = (value >> 8) & 0x1F
        major_service = (value >> 13) & 0x7FF
        names = {0x00: "Miscellaneous", 0x01: "Computer", 0x02: "Phone",
                 0x03: "LAN/Network access point", 0x04: "Audio/Video",
                 0x05: "Peripheral", 0x06: "Imaging", 0x07: "Wearable",
                 0x08: "Toy", 0x09: "Health"}
        self.summary_label.setText(
            f"major device class: {names.get(major_device, f'0x{major_device:02X}')}, "
            f"service bits 0x{major_service:03X}")

    def validate_parameters(self) -> bool:
        text = self.cod_input.text().strip().replace("0x", "").replace(" ", "")
        try:
            value = int(text or "0", 16)
        except ValueError:
            raise ValueError(f"class of device is not valid hex: {text!r}")
        self._cmd_instance = cb_cmds.WriteClassOfDevice(class_of_device=value)


for _cls in (WritePageTimeoutUI,
             WriteConnectionAcceptTimeoutUI,
             WriteScanEnableUI,
             WritePageScanActivityUI,
             WriteInquiryScanActivityUI,
             WritePageScanTypeUI,
             WriteInquiryScanTypeUI,
             WriteClassOfDeviceUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'WritePageTimeoutUI',
    'WriteConnectionAcceptTimeoutUI',
    'WriteScanEnableUI',
    'WritePageScanActivityUI',
    'WriteInquiryScanActivityUI',
    'WritePageScanTypeUI',
    'WriteInquiryScanTypeUI',
    'WriteClassOfDeviceUI',
]
