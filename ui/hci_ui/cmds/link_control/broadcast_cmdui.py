"""
Dialogs for Connectionless Peripheral Broadcast and the synchronization train.

    0x0441  Set Connectionless Peripheral Broadcast
    0x0442  Set Connectionless Peripheral Broadcast Receive
    0x0444  Receive Synchronization Train

Start Synchronization Train (0x0443) takes no parameters, so it has no dialog --
the command factory sends it directly.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QWidget

import hci.cmd.link_controller as lc_cmds
from hci.cmd.cmd_opcodes import LinkControlOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI
from .lc_common import address_field, hex_bytes, hint, parse_bd_addr, spin


def _packet_type_row(form_layout, on_change) -> dict:
    """Six ACL packet-type checkboxes; returns {bit: checkbox}."""
    checks = {}
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    for label, bit in (("DM1", 0x0008), ("DH1", 0x0010), ("DM3", 0x0400),
                       ("DH3", 0x0800), ("DM5", 0x4000), ("DH5", 0x8000)):
        box = QCheckBox(label)
        box.setChecked(True)
        box.stateChanged.connect(on_change)
        layout.addWidget(box)
        checks[bit] = box
    layout.addStretch(1)
    form_layout.addRow("Packet Types:", holder)
    return checks


class SetConnectionlessPeripheralBroadcastCommandUI(HCICmdUI):
    """UI for Set Connectionless Peripheral Broadcast (0x0441)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.SET_CONNECTIONLESS_PERIPHERAL_BROADCAST)
    NAME = "Set Connectionless Peripheral Broadcast"

    def setup_ui(self):
        super().setup_ui()

        self.enable_input = QCheckBox("Enable the broadcast")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.lt_addr_input = spin(0x01, 0x07, 0x01,
                                  "Must already be reserved with "
                                  "Set_Reserved_LT_ADDR (0x0C66)")
        self.form_layout.addRow("LT_ADDR:", self.lt_addr_input)

        self.lpo_input = QCheckBox("Allow the low power oscillator between broadcasts")
        self.lpo_input.setChecked(True)
        self.form_layout.addRow("LPO Allowed:", self.lpo_input)

        self.packet_checks = _packet_type_row(self.form_layout,
                                              self._update_summary)

        self.interval_min_input = spin(0x0002, 0xFFFE, 0x0050,
                                       "Minimum broadcast interval, in "
                                       "0.625 ms slots; must be even")
        self.interval_max_input = spin(0x0002, 0xFFFE, 0x0070,
                                       "Maximum broadcast interval, in "
                                       "0.625 ms slots; must be even")
        self.interval_min_input.setSingleStep(2)
        self.interval_max_input.setSingleStep(2)
        self.interval_min_input.valueChanged.connect(self._update_summary)
        self.interval_max_input.valueChanged.connect(self._update_summary)
        self.form_layout.addRow("Interval Min:", self.interval_min_input)
        self.form_layout.addRow("Interval Max:", self.interval_max_input)

        self.timeout_input = spin(0x0002, 0xFFFE, 0x0BB8,
                                  "Supervision timeout, in 0.625 ms slots")
        self.timeout_input.valueChanged.connect(self._update_summary)
        self.form_layout.addRow("Supervision Timeout:", self.timeout_input)

        self.summary_label = hint("")
        self.form_layout.addRow("", self.summary_label)
        self._update_summary()

        self.form_layout.addRow("", hint(
            "Transmitter side. The LT_ADDR has to be reserved first, and a "
            "synchronization train has to be started before receivers can find "
            "the broadcast. Intervals must be even -- they are counted in pairs "
            "of slots."))

    def _packet_type(self) -> int:
        value = 0
        for bit, box in self.packet_checks.items():
            if box.isChecked():
                value |= bit
        return value

    def _update_summary(self) -> None:
        self.summary_label.setText(
            f"interval {self.interval_min_input.value() * 0.625:.1f}-"
            f"{self.interval_max_input.value() * 0.625:.1f} ms, "
            f"timeout {self.timeout_input.value() * 0.625:.0f} ms, "
            f"Packet_Type = 0x{self._packet_type():04X}")

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.SetConnectionlessPeripheralBroadcast(
            enable=self.enable_input.isChecked(),
            lt_addr=self.lt_addr_input.value(),
            lpo_allowed=self.lpo_input.isChecked(),
            packet_type=self._packet_type(),
            interval_min=self.interval_min_input.value(),
            interval_max=self.interval_max_input.value(),
            supervision_timeout=self.timeout_input.value())


class SetConnectionlessPeripheralBroadcastReceiveCommandUI(HCICmdUI):
    """UI for Set Connectionless Peripheral Broadcast Receive (0x0442)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL,
        LinkControlOCF.SET_CONNECTIONLESS_PERIPHERAL_BROADCAST_RECIEVE)
    NAME = "Set Connectionless Peripheral Broadcast Receive"

    def setup_ui(self):
        super().setup_ui()

        self.enable_input = QCheckBox("Receive the broadcast")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.address_input = address_field()
        self.form_layout.addRow("Transmitter BD_ADDR:", self.address_input)

        self.lt_addr_input = spin(0x01, 0x07, 0x01)
        self.form_layout.addRow("LT_ADDR:", self.lt_addr_input)

        self.interval_input = spin(0x0002, 0xFFFE, 0x0050,
                                   "Broadcast interval, in 0.625 ms slots")
        self.form_layout.addRow("Interval:", self.interval_input)

        self.clock_offset_input = spin(0, 0x0FFFFFFF, 0,
                                       "28-bit clock offset from the "
                                       "Synchronization Train Received event")
        self.form_layout.addRow("Clock Offset:", self.clock_offset_input)

        self.next_clock_input = spin(0, 0x0FFFFFFF, 0,
                                     "Clock value of the next broadcast instant")
        self.form_layout.addRow("Next CPB Clock:", self.next_clock_input)

        self.timeout_input = spin(0x0002, 0xFFFE, 0x0BB8)
        self.form_layout.addRow("Supervision Timeout:", self.timeout_input)

        self.accuracy_input = spin(0x00, 0xFF, 0x00,
                                   "Remote timing accuracy in ppm; "
                                   "0xFF = unknown")
        self.form_layout.addRow("Remote Timing Accuracy:", self.accuracy_input)

        self.skip_input = spin(0x00, 0xFF, 0x00,
                               "Broadcast instants that may be skipped")
        self.form_layout.addRow("Skip:", self.skip_input)

        self.packet_checks = _packet_type_row(self.form_layout, lambda: None)

        self.afh_input = QLineEdit(lc_cmds.AFH_CHANNEL_MAP_ALL.hex().upper())
        self.afh_input.setToolTip("10-octet AFH channel map from the "
                                  "synchronization train")
        self.form_layout.addRow("AFH Channel Map:", self.afh_input)

        self.form_layout.addRow("", hint(
            "Receiver side. Every timing value here comes from the "
            "Synchronization Train Received event -- this command joins a "
            "broadcast whose schedule is already known, it does not discover "
            "one. Use Receive Synchronization Train first."))
        self.setMinimumWidth(520)

    def _packet_type(self) -> int:
        value = 0
        for bit, box in self.packet_checks.items():
            if box.isChecked():
                value |= bit
        return value

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.SetConnectionlessPeripheralBroadcastReceive(
            enable=self.enable_input.isChecked(),
            bd_addr=parse_bd_addr(self.address_input.text()),
            lt_addr=self.lt_addr_input.value(),
            interval=self.interval_input.value(),
            clock_offset=self.clock_offset_input.value(),
            next_cpb_clock=self.next_clock_input.value(),
            supervision_timeout=self.timeout_input.value(),
            remote_timing_accuracy=self.accuracy_input.value(),
            skip=self.skip_input.value(),
            packet_type=self._packet_type(),
            afh_channel_map=hex_bytes(self.afh_input.text(),
                                      "AFH channel map", 10))


class ReceiveSynchronizationTrainCommandUI(HCICmdUI):
    """UI for Receive Synchronization Train (0x0444)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.READ_SYNCHRONIZATION_TRAIN)
    NAME = "Receive Synchronization Train"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("Transmitter BD_ADDR:", self.address_input)

        self.timeout_input = spin(0x0002, 0xFFFE, 0x2710,
                                  "How long to scan, in 0.625 ms slots")
        self.window_input = spin(0x0004, 0xFFFE, 0x0100,
                                 "Scan window, in 0.625 ms slots")
        self.interval_input = spin(0x0004, 0xFFFE, 0x0200,
                                   "Scan interval, in 0.625 ms slots")
        self.form_layout.addRow("Sync Scan Timeout:", self.timeout_input)
        self.form_layout.addRow("Sync Scan Window:", self.window_input)
        self.form_layout.addRow("Sync Scan Interval:", self.interval_input)

        self.summary_label = hint("")
        for widget in (self.timeout_input, self.window_input, self.interval_input):
            widget.valueChanged.connect(self._update_summary)
        self.form_layout.addRow("", self.summary_label)
        self._update_summary()

        self.form_layout.addRow("", hint(
            "Scans for the transmitter's synchronization train. On success the "
            "Synchronization Train Received event carries the timing that "
            "Set Connectionless Peripheral Broadcast Receive then needs."))

    def _update_summary(self) -> None:
        window = self.window_input.value()
        interval = self.interval_input.value()
        text = (f"scan {window * 0.625:.1f} ms every {interval * 0.625:.1f} ms "
                f"for up to {self.timeout_input.value() * 0.625 / 1000:.2f} s")
        if window > interval:
            text += "  -- window must not exceed interval"
        self.summary_label.setText(text)

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.ReceiveSynchronizationTrain(
            bd_addr=parse_bd_addr(self.address_input.text()),
            sync_scan_timeout=self.timeout_input.value(),
            sync_scan_window=self.window_input.value(),
            sync_scan_interval=self.interval_input.value())


for _cls in (SetConnectionlessPeripheralBroadcastCommandUI,
             SetConnectionlessPeripheralBroadcastReceiveCommandUI,
             ReceiveSynchronizationTrainCommandUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'SetConnectionlessPeripheralBroadcastCommandUI',
    'SetConnectionlessPeripheralBroadcastReceiveCommandUI',
    'ReceiveSynchronizationTrainCommandUI',
]
