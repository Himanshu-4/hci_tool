"""
Dialogs for the synchronous (SCO / eSCO) connection commands.

    0x0428  Setup Synchronous Connection
    0x0429  Accept Synchronous Connection Request
    0x042A  Reject Synchronous Connection Request
    0x043D  Enhanced Setup Synchronous Connection
    0x043E  Enhanced Accept Synchronous Connection Request

The enhanced pair carries 23 parameters. Rather than 23 bare spin boxes, the
dialog offers codec presets -- CVSD, transparent and mSBC -- that fill the whole
form, with everything still editable underneath. Those three presets cover
essentially every real headset link; the fields matter when one of them does not
work and you need to see why.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton, QWidget

import hci.cmd.link_controller as lc_cmds
from hci.cmd.cmd_opcodes import LinkControlOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI
from .lc_common import (
    AddressReasonUI, address_field, hint, parse_bd_addr, spin,
)


def _voice_setting_combo() -> QComboBox:
    combo = QComboBox()
    for label, value in (
            ("CVSD (0x0060)", lc_cmds.VOICE_SETTING_CVSD),
            ("Transparent (0x0063)", lc_cmds.VOICE_SETTING_TRANSPARENT),
            ("A-law (0x0061)", 0x0061),
            ("u-law (0x0062)", 0x0062)):
        combo.addItem(label, value)
    return combo


def _retransmission_combo() -> QComboBox:
    combo = QComboBox()
    for label, value in (
            ("No retransmissions (0x00)", 0x00),
            ("Optimise for power (0x01)", 0x01),
            ("Optimise for quality (0x02)", 0x02),
            ("Don't care (0xFF)", 0xFF)):
        combo.addItem(label, value)
    combo.setCurrentIndex(2)
    return combo


def _coding_format_combo(default: int) -> QComboBox:
    combo = QComboBox()
    for coding in lc_cmds.CodingFormat:
        combo.addItem(
            f"{coding.name.replace('_', ' ').title()} (0x{int(coding):02X})",
            int(coding))
    index = combo.findData(int(default))
    if index >= 0:
        combo.setCurrentIndex(index)
    return combo


class _SyncPacketTypeMixin:
    """The Packet_Type bitmap, as checkboxes with the inverted bits explained."""

    def add_packet_type_rows(self) -> None:
        self.packet_checks = {}
        allowed = QWidget()
        allowed_layout = QHBoxLayout(allowed)
        allowed_layout.setContentsMargins(0, 0, 0, 0)
        for label, bit, default in (("HV1", 0x0001, False), ("HV2", 0x0002, False),
                                    ("HV3", 0x0004, False), ("EV3", 0x0008, True),
                                    ("EV4", 0x0010, False), ("EV5", 0x0020, False)):
            box = QCheckBox(label)
            box.setChecked(default)
            box.stateChanged.connect(self._update_packet_summary)
            allowed_layout.addWidget(box)
            self.packet_checks[bit] = box
        allowed_layout.addStretch(1)
        self.form_layout.addRow("Packet Types:", allowed)

        excluded = QWidget()
        excluded_layout = QHBoxLayout(excluded)
        excluded_layout.setContentsMargins(0, 0, 0, 0)
        for label, bit in (("no 2-EV3", 0x0040), ("no 3-EV3", 0x0080),
                           ("no 2-EV5", 0x0100), ("no 3-EV5", 0x0200)):
            box = QCheckBox(label)
            box.setChecked(True)
            box.stateChanged.connect(self._update_packet_summary)
            excluded_layout.addWidget(box)
            self.packet_checks[bit] = box
        excluded_layout.addStretch(1)
        self.form_layout.addRow("EDR Exclusions:", excluded)

        self.packet_summary = hint("")
        self.form_layout.addRow("", self.packet_summary)
        self._update_packet_summary()

        self.form_layout.addRow("", hint(
            "The four exclusion bits are inverted: ticking one forbids that "
            "EDR packet type. All four ticked with EV3 is the conservative "
            "setting; untick 'no 2-EV3' for wideband mSBC."))

    def packet_type_value(self) -> int:
        value = 0
        for bit, box in self.packet_checks.items():
            if box.isChecked():
                value |= bit
        return value

    def _update_packet_summary(self) -> None:
        value = self.packet_type_value()
        self.packet_summary.setText(f"Packet_Type = 0x{value:04X}")


class SetupSynchronousConnectionCommandUI(HCICmdUI, _SyncPacketTypeMixin):
    """UI for Setup Synchronous Connection (0x0428)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.SETUP_SYNCHRONOUS_CONNECTION)
    NAME = "Setup Synchronous Connection"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = spin(0x0000, 0x0EFF, 0x0000,
                                 "ACL handle when creating a new SCO link, or "
                                 "the SCO handle when renegotiating one")
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.tx_bw_input = spin(0, 0x7FFFFFFF, 8000,
                                "Transmit bandwidth in bytes per second", " B/s")
        self.rx_bw_input = spin(0, 0x7FFFFFFF, 8000,
                                "Receive bandwidth in bytes per second", " B/s")
        self.form_layout.addRow("Transmit Bandwidth:", self.tx_bw_input)
        self.form_layout.addRow("Receive Bandwidth:", self.rx_bw_input)

        self.latency_input = spin(0x0004, 0xFFFF, 0x000C,
                                  "Max latency in ms; 0xFFFF for don't care",
                                  " ms")
        self.form_layout.addRow("Max Latency:", self.latency_input)

        self.voice_input = _voice_setting_combo()
        self.form_layout.addRow("Voice Setting:", self.voice_input)

        self.retransmission_input = _retransmission_combo()
        self.form_layout.addRow("Retransmission Effort:", self.retransmission_input)

        self.add_packet_type_rows()

        self.form_layout.addRow("", hint(
            "Adds a SCO/eSCO link to an existing ACL connection. The resulting "
            "SCO handle arrives in Synchronous Connection Complete. For "
            "transparent or mSBC audio use the Enhanced form instead."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.SetupSynchronousConnection(
            connection_handle=self.handle_input.value(),
            transmit_bandwidth=self.tx_bw_input.value(),
            receive_bandwidth=self.rx_bw_input.value(),
            max_latency=self.latency_input.value(),
            voice_setting=self.voice_input.currentData(),
            retransmission_effort=self.retransmission_input.currentData(),
            packet_type=self.packet_type_value())


class AcceptSynchronousConnectionRequestCommandUI(HCICmdUI, _SyncPacketTypeMixin):
    """UI for Accept Synchronous Connection Request (0x0429)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.ACCEPT_SYNCHRONOUS_CONNECTION_REQUEST)
    NAME = "Accept Synchronous Connection Request"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)

        self.tx_bw_input = spin(0, 0x7FFFFFFF, 8000, "", " B/s")
        self.rx_bw_input = spin(0, 0x7FFFFFFF, 8000, "", " B/s")
        self.form_layout.addRow("Transmit Bandwidth:", self.tx_bw_input)
        self.form_layout.addRow("Receive Bandwidth:", self.rx_bw_input)

        self.latency_input = spin(0x0004, 0xFFFF, 0x000C, "", " ms")
        self.form_layout.addRow("Max Latency:", self.latency_input)

        self.voice_input = _voice_setting_combo()
        self.form_layout.addRow("Voice Setting:", self.voice_input)

        self.retransmission_input = _retransmission_combo()
        self.form_layout.addRow("Retransmission Effort:", self.retransmission_input)

        self.add_packet_type_rows()

        self.form_layout.addRow("", hint(
            "The answer to a Connection Request whose link type was SCO or "
            "eSCO. Keyed by address, because the connection does not exist yet."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.AcceptSynchronousConnectionRequest(
            bd_addr=parse_bd_addr(self.address_input.text()),
            transmit_bandwidth=self.tx_bw_input.value(),
            receive_bandwidth=self.rx_bw_input.value(),
            max_latency=self.latency_input.value(),
            voice_setting=self.voice_input.currentData(),
            retransmission_effort=self.retransmission_input.currentData(),
            packet_type=self.packet_type_value())


class RejectSynchronousConnectionRequestCommandUI(AddressReasonUI):
    """UI for Reject Synchronous Connection Request (0x042A)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.REJECT_SYNCHRONOUS_CONNECTION_REQUEST)
    NAME = "Reject Synchronous Connection Request"
    COMMAND = lc_cmds.RejectSynchronousConnectionRequest
    DEFAULT_REASON = 0x0D
    HINT = "Refuses an incoming SCO/eSCO connection request."


class _EnhancedSyncUI(HCICmdUI, _SyncPacketTypeMixin):
    """
    Shared form for the two enhanced synchronous commands.

    Both share a 23-field tail; only the first field differs, so the subclass
    adds that and this builds the rest.
    """

    COMMAND = None

    #: Preset name -> the subset of fields it changes.
    PRESETS = {
        "CVSD (narrowband)": dict(
            tx_bw=8000, rx_bw=8000,
            air_coding=int(lc_cmds.CodingFormat.CVSD),
            host_coding=int(lc_cmds.CodingFormat.LINEAR_PCM),
            codec_frame=60, coded_size=16, unit_size=16, host_bw=16000,
            packet_type=lc_cmds.SYNC_PACKET_TYPE_EV3_ONLY),
        "Transparent": dict(
            tx_bw=8000, rx_bw=8000,
            air_coding=int(lc_cmds.CodingFormat.TRANSPARENT),
            host_coding=int(lc_cmds.CodingFormat.TRANSPARENT),
            codec_frame=60, coded_size=8, unit_size=8, host_bw=8000,
            packet_type=lc_cmds.SYNC_PACKET_TYPE_EV3_ONLY),
        "mSBC (wideband)": dict(
            tx_bw=8000, rx_bw=8000,
            air_coding=int(lc_cmds.CodingFormat.TRANSPARENT),
            host_coding=int(lc_cmds.CodingFormat.TRANSPARENT),
            codec_frame=60, coded_size=16, unit_size=16, host_bw=16000,
            packet_type=lc_cmds.SYNC_PACKET_TYPE_2EV3),
    }

    def add_enhanced_rows(self) -> None:
        presets = QWidget()
        preset_layout = QHBoxLayout(presets)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        for name in self.PRESETS:
            button = QPushButton(name)
            button.clicked.connect(lambda _, n=name: self._apply_preset(n))
            preset_layout.addWidget(button)
        preset_layout.addStretch(1)
        self.form_layout.addRow("Presets:", presets)

        self.tx_bw_input = spin(0, 0x7FFFFFFF, 8000, "Air transmit bandwidth",
                                " B/s")
        self.rx_bw_input = spin(0, 0x7FFFFFFF, 8000, "Air receive bandwidth",
                                " B/s")
        self.form_layout.addRow("Transmit Bandwidth:", self.tx_bw_input)
        self.form_layout.addRow("Receive Bandwidth:", self.rx_bw_input)

        self.tx_coding_input = _coding_format_combo(lc_cmds.CodingFormat.CVSD)
        self.rx_coding_input = _coding_format_combo(lc_cmds.CodingFormat.CVSD)
        self.form_layout.addRow("Transmit Coding Format:", self.tx_coding_input)
        self.form_layout.addRow("Receive Coding Format:", self.rx_coding_input)

        self.tx_frame_input = spin(0, 0xFFFF, 60, "", " bytes")
        self.rx_frame_input = spin(0, 0xFFFF, 60, "", " bytes")
        self.form_layout.addRow("Transmit Codec Frame Size:", self.tx_frame_input)
        self.form_layout.addRow("Receive Codec Frame Size:", self.rx_frame_input)

        self.in_bw_input = spin(0, 0x7FFFFFFF, 16000, "Host-side input bandwidth",
                                " B/s")
        self.out_bw_input = spin(0, 0x7FFFFFFF, 16000,
                                 "Host-side output bandwidth", " B/s")
        self.form_layout.addRow("Input Bandwidth:", self.in_bw_input)
        self.form_layout.addRow("Output Bandwidth:", self.out_bw_input)

        self.in_coding_input = _coding_format_combo(lc_cmds.CodingFormat.LINEAR_PCM)
        self.out_coding_input = _coding_format_combo(lc_cmds.CodingFormat.LINEAR_PCM)
        self.form_layout.addRow("Input Coding Format:", self.in_coding_input)
        self.form_layout.addRow("Output Coding Format:", self.out_coding_input)

        self.in_size_input = spin(0, 0xFFFF, 16, "", " bits")
        self.out_size_input = spin(0, 0xFFFF, 16, "", " bits")
        self.form_layout.addRow("Input Coded Data Size:", self.in_size_input)
        self.form_layout.addRow("Output Coded Data Size:", self.out_size_input)

        self.in_pcm_input = self._pcm_format_combo()
        self.out_pcm_input = self._pcm_format_combo()
        self.form_layout.addRow("Input PCM Data Format:", self.in_pcm_input)
        self.form_layout.addRow("Output PCM Data Format:", self.out_pcm_input)

        self.in_msb_input = spin(0, 0xFF, 0,
                                 "Bit position of the PCM sample MSB; 0 when "
                                 "the sample fills the unit")
        self.out_msb_input = spin(0, 0xFF, 0)
        self.form_layout.addRow("Input PCM MSB Position:", self.in_msb_input)
        self.form_layout.addRow("Output PCM MSB Position:", self.out_msb_input)

        self.in_path_input = spin(0, 0xFF, 0,
                                  "0 = HCI, 1..254 vendor, 255 audio test mode")
        self.out_path_input = spin(0, 0xFF, 0)
        self.form_layout.addRow("Input Data Path:", self.in_path_input)
        self.form_layout.addRow("Output Data Path:", self.out_path_input)

        self.in_unit_input = spin(0, 0xFF, 16, "", " bits")
        self.out_unit_input = spin(0, 0xFF, 16, "", " bits")
        self.form_layout.addRow("Input Transport Unit Size:", self.in_unit_input)
        self.form_layout.addRow("Output Transport Unit Size:", self.out_unit_input)

        self.latency_input = spin(0x0004, 0xFFFF, 0x000C,
                                  "0xFFFF for don't care", " ms")
        self.form_layout.addRow("Max Latency:", self.latency_input)

        self.retransmission_input = _retransmission_combo()
        self.form_layout.addRow("Retransmission Effort:", self.retransmission_input)

        self.add_packet_type_rows()

        self.form_layout.addRow("", hint(
            "The air coding and the host PCM path are described separately, so "
            "the controller knows not to run its own codec over data that is "
            "already coded. That is what transparent and mSBC links need."))
        self.setMinimumWidth(560)

    @staticmethod
    def _pcm_format_combo() -> QComboBox:
        combo = QComboBox()
        for fmt in lc_cmds.PcmDataFormat:
            combo.addItem(f"{fmt.name.replace('_', ' ').title()} "
                          f"(0x{int(fmt):02X})", int(fmt))
        combo.setCurrentIndex(2)     # two's complement
        return combo

    def _apply_preset(self, name: str) -> None:
        preset = self.PRESETS[name]
        self.tx_bw_input.setValue(preset["tx_bw"])
        self.rx_bw_input.setValue(preset["rx_bw"])
        for combo in (self.tx_coding_input, self.rx_coding_input):
            index = combo.findData(preset["air_coding"])
            if index >= 0:
                combo.setCurrentIndex(index)
        for combo in (self.in_coding_input, self.out_coding_input):
            index = combo.findData(preset["host_coding"])
            if index >= 0:
                combo.setCurrentIndex(index)
        self.tx_frame_input.setValue(preset["codec_frame"])
        self.rx_frame_input.setValue(preset["codec_frame"])
        self.in_bw_input.setValue(preset["host_bw"])
        self.out_bw_input.setValue(preset["host_bw"])
        self.in_size_input.setValue(preset["coded_size"])
        self.out_size_input.setValue(preset["coded_size"])
        self.in_unit_input.setValue(preset["unit_size"])
        self.out_unit_input.setValue(preset["unit_size"])
        for bit, box in self.packet_checks.items():
            box.setChecked(bool(preset["packet_type"] & bit))

    def enhanced_kwargs(self) -> dict:
        return dict(
            transmit_bandwidth=self.tx_bw_input.value(),
            receive_bandwidth=self.rx_bw_input.value(),
            transmit_coding_format=lc_cmds.pack_coding_format(
                self.tx_coding_input.currentData()),
            receive_coding_format=lc_cmds.pack_coding_format(
                self.rx_coding_input.currentData()),
            transmit_codec_frame_size=self.tx_frame_input.value(),
            receive_codec_frame_size=self.rx_frame_input.value(),
            input_bandwidth=self.in_bw_input.value(),
            output_bandwidth=self.out_bw_input.value(),
            input_coding_format=lc_cmds.pack_coding_format(
                self.in_coding_input.currentData()),
            output_coding_format=lc_cmds.pack_coding_format(
                self.out_coding_input.currentData()),
            input_coded_data_size=self.in_size_input.value(),
            output_coded_data_size=self.out_size_input.value(),
            input_pcm_data_format=self.in_pcm_input.currentData(),
            output_pcm_data_format=self.out_pcm_input.currentData(),
            input_pcm_sample_payload_msb_position=self.in_msb_input.value(),
            output_pcm_sample_payload_msb_position=self.out_msb_input.value(),
            input_data_path=self.in_path_input.value(),
            output_data_path=self.out_path_input.value(),
            input_transport_unit_size=self.in_unit_input.value(),
            output_transport_unit_size=self.out_unit_input.value(),
            max_latency=self.latency_input.value(),
            packet_type=self.packet_type_value(),
            retransmission_effort=self.retransmission_input.currentData(),
        )


class EnhancedSetupSynchronousConnectionCommandUI(_EnhancedSyncUI):
    """UI for Enhanced Setup Synchronous Connection (0x043D)."""

    OPCODE = create_opcode(OGF.LINK_CONTROL,
                           LinkControlOCF.ENHANCED_SETUP_SYNCHRONOUS_CONNECTION)
    NAME = "Enhanced Setup Synchronous Connection"
    COMMAND = lc_cmds.EnhancedSetupSynchronousConnection

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = spin(0x0000, 0x0EFF, 0x0000,
                                 "ACL handle when creating, SCO handle when "
                                 "renegotiating")
        self.form_layout.addRow("Connection Handle:", self.handle_input)
        self.add_enhanced_rows()

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(
            connection_handle=self.handle_input.value(), **self.enhanced_kwargs())


class EnhancedAcceptSynchronousConnectionCommandUI(_EnhancedSyncUI):
    """UI for Enhanced Accept Synchronous Connection Request (0x043E)."""

    OPCODE = create_opcode(
        OGF.LINK_CONTROL, LinkControlOCF.ENHANCED_ACCEPT_SYNCHRONOUS_CONNECTION)
    NAME = "Enhanced Accept Synchronous Connection Request"
    COMMAND = lc_cmds.EnhancedAcceptSynchronousConnectionRequest

    def setup_ui(self):
        super().setup_ui()
        self.address_input = address_field()
        self.form_layout.addRow("BD_ADDR:", self.address_input)
        self.add_enhanced_rows()

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(
            bd_addr=parse_bd_addr(self.address_input.text()),
            **self.enhanced_kwargs())


for _cls in (SetupSynchronousConnectionCommandUI,
             AcceptSynchronousConnectionRequestCommandUI,
             RejectSynchronousConnectionRequestCommandUI,
             EnhancedSetupSynchronousConnectionCommandUI,
             EnhancedAcceptSynchronousConnectionCommandUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'SetupSynchronousConnectionCommandUI',
    'AcceptSynchronousConnectionRequestCommandUI',
    'RejectSynchronousConnectionRequestCommandUI',
    'EnhancedSetupSynchronousConnectionCommandUI',
    'EnhancedAcceptSynchronousConnectionCommandUI',
]
