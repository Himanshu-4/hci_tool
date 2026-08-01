from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QSpinBox, QLabel, QPushButton, QGridLayout, QGroupBox,
    QCheckBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt
import struct

from typing import Optional

from hci.cmd.cmd_opcodes import create_opcode, OGF, LinkPolicyOCF
import hci.cmd.link_policy as lp_cmds
from hci import bd_addr_str_to_bytes

from ..cmd_baseui import HCICmdUI
from .. import register_command_ui


def _u32_field(default: str, tooltip: str) -> QLineEdit:
    """A text field for a 32-bit value -- QSpinBox cannot hold one."""
    field = QLineEdit(default)
    field.setToolTip(f"{tooltip}. Decimal, or hex with a 0x prefix.")
    return field


def _parse_u32(text: str, label: str) -> int:
    """Parse a decimal or 0x-hex string into a 32-bit unsigned value."""
    raw = text.strip()
    try:
        value = int(raw, 16) if raw.lower().startswith("0x") else int(raw, 10)
    except ValueError:
        raise ValueError(f"{label}: '{raw}' is not a number")
    if not (0 <= value <= 0xFFFFFFFF):
        raise ValueError(f"{label}: {value} does not fit in 32 bits")
    return value


class HoldModeCommandUI(HCICmdUI):
    """UI for HCI Hold Mode command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.HOLD_MODE)
    NAME = "HCI Hold Mode Command"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Hold Mode command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
        # Hold Mode Max Interval
        self.max_interval = QSpinBox()
        self.max_interval.setRange(0x0002, 0xFFFE)
        self.max_interval.setValue(0x0080)  # Default value (128 * 0.625ms = 80ms)
        self.max_interval.setToolTip("Maximum Hold Interval (N * 0.625 ms)")
        self.form_layout.addRow( "Hold Mode Max Interval:", self.max_interval)
        
        # Hold Mode Min Interval
        self.min_interval = QSpinBox()
        self.min_interval.setRange(0x0001, 0xFFFE)
        self.min_interval.setValue(0x0040)  # Default value (64 * 0.625ms = 40ms)
        self.min_interval.setToolTip("Minimum Hold Interval (N * 0.625 ms)")
        self.form_layout.addRow( "Hold Mode Min Interval:", self.min_interval)
        
    def validate_parameters(self):
        """Build the Hold Mode command; the packet validates its own parameters"""
        self._cmd_instance = lp_cmds.HoldMode(
            connection_handle=self.connection_handle.value(),
            hold_mode_max_interval=self.max_interval.value(),
            hold_mode_min_interval=self.min_interval.value(),
        )



class SniffModeCommandUI(HCICmdUI):
    """UI for HCI Sniff Mode command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.SNIFF_MODE)
    NAME = "HCI Sniff Mode Command"
    def setup_ui(self):
        """Add Sniff Mode command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
        # Sniff Max Interval
        self.max_interval = QSpinBox()
        self.max_interval.setRange(0x0002, 0xFFFE)
        self.max_interval.setValue(0x0320)  # Default value (800 * 0.625ms = 500ms)
        self.max_interval.setToolTip("Maximum Sniff Interval (N * 0.625 ms)")
        self.form_layout.addRow( "Sniff Max Interval:", self.max_interval)
        
        # Sniff Min Interval
        self.min_interval = QSpinBox()
        self.min_interval.setRange(0x0002, 0xFFFE)
        self.min_interval.setValue(0x0190)  # Default value (400 * 0.625ms = 250ms)
        self.min_interval.setToolTip("Minimum Sniff Interval (N * 0.625 ms)")
        self.form_layout.addRow( "Sniff Min Interval:", self.min_interval)
        
        # Sniff Attempt
        self.sniff_attempt = QSpinBox()
        self.sniff_attempt.setRange(0x0001, 0x7FFF)
        self.sniff_attempt.setValue(4)
        self.sniff_attempt.setToolTip("Number of Baseband receive slots for sniff attempt")
        self.form_layout.addRow( "Sniff Attempt:", self.sniff_attempt)
        
        # Sniff Timeout
        self.sniff_timeout = QSpinBox()
        self.sniff_timeout.setRange(0x0000, 0x7FFF)
        self.sniff_timeout.setValue(1)
        self.sniff_timeout.setToolTip("Number of Baseband receive slots for sniff timeout")
        self.form_layout.addRow( "Sniff Timeout:", self.sniff_timeout)
        
    def validate_parameters(self):
        """Build the Sniff Mode command from the inputs"""
        self._cmd_instance = lp_cmds.SniffMode(
            connection_handle=self.connection_handle.value(),
            sniff_max_interval=self.max_interval.value(),
            sniff_min_interval=self.min_interval.value(),
            sniff_attempt=self.sniff_attempt.value(),
            sniff_timeout=self.sniff_timeout.value(),
        )


class ExitSniffModeCommandUI(HCICmdUI):
    """UI for HCI Exit Sniff Mode command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.EXIT_SNIFF_MODE)
    NAME = "HCI Exit Sniff Mode Command"
    def setup_ui(self):
        """Add Exit Sniff Mode command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
    def validate_parameters(self):
        """Build the Exit Sniff Mode command from the inputs"""
        self._cmd_instance = lp_cmds.ExitSniffMode(
            connection_handle=self.connection_handle.value())

class QosSetupCommandUI(HCICmdUI):
    """UI for HCI QoS Setup command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.QOS_SETUP)
    NAME = "HCI QoS Setup Command"
    def setup_ui(self):
        """Add QoS Setup command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
        # Flags
        self.flags = QSpinBox()
        self.flags.setRange(0, 0xFF)
        self.flags.setValue(0)  # Default: No flags set
        self.flags.setToolTip("Reserved for future use (set to 0)")
        self.form_layout.addRow( "Flags:", self.flags)
        
        # Service Type
        self.service_type = QComboBox()
        self.service_type.addItem("No Traffic", 0)
        self.service_type.addItem("Best Effort", 1)
        self.service_type.addItem("Guaranteed", 2)
        self.form_layout.addRow( "Service Type:", self.service_type)
        
        # These four are 32-bit; QSpinBox tops out at int32, so they are
        # free-text fields accepting decimal or 0x-prefixed hex.
        self.token_rate = _u32_field("0", "Token Rate (bytes/second)")
        self.form_layout.addRow( "Token Rate (B/s):", self.token_rate)

        self.peak_bandwidth = _u32_field("0", "Peak Bandwidth (bytes/second)")
        self.form_layout.addRow( "Peak Bandwidth (B/s):", self.peak_bandwidth)

        self.latency = _u32_field("0xFFFFFFFF", "Latency (microseconds)")
        self.form_layout.addRow( "Latency (μs):", self.latency)

        self.delay_variation = _u32_field("0xFFFFFFFF", "Delay Variation (microseconds)")
        self.form_layout.addRow( "Delay Variation (μs):", self.delay_variation)

    def validate_parameters(self):
        """Build the QoS Setup command from the inputs"""
        self._cmd_instance = lp_cmds.QosSetup(
            connection_handle=self.connection_handle.value(),
            flags=self.flags.value(),
            service_type=self.service_type.currentData(),
            token_rate=_parse_u32(self.token_rate.text(), "Token Rate"),
            peak_bandwidth=_parse_u32(self.peak_bandwidth.text(), "Peak Bandwidth"),
            latency=_parse_u32(self.latency.text(), "Latency"),
            delay_variation=_parse_u32(self.delay_variation.text(), "Delay Variation"),
        )

class RoleDiscoveryCommandUI(HCICmdUI):
    """UI for HCI Role Discovery command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.ROLE_DISCOVERY)
    NAME = "HCI Role Discovery Command"
    def setup_ui(self):
        """Add Role Discovery command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
    def validate_parameters(self):
        """Build the Role Discovery command from the inputs"""
        self._cmd_instance = lp_cmds.RoleDiscovery(
            connection_handle=self.connection_handle.value())

class SwitchRoleCommandUI(HCICmdUI):
    """UI for HCI Switch Role command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.SWITCH_ROLE)
    NAME = "HCI Switch Role Command"
    
    def setup_ui(self):
        """Add Switch Role command specific UI components"""
        super().setup_ui()
        
        # BD_ADDR
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device")
        self.form_layout.addRow( "BD_ADDR:", self.bd_addr)
        
        # Role
        self.role = QComboBox()
        self.role.addItem("Master", 0)
        self.role.addItem("Slave", 1)
        self.form_layout.addRow( "Role:", self.role)
        
    def validate_parameters(self):
        """Build the Switch Role command from the inputs"""
        self._cmd_instance = lp_cmds.SwitchRole(
            bd_addr=self.bd_addr.text().strip(),
            role=self.role.currentData())


class ReadLinkPolicySettingsCommandUI(HCICmdUI):
    """UI for HCI Read Link Policy Settings command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.READ_LINK_POLICY_SETTINGS)
    NAME = "HCI Read Link Policy Settings Command"
    
    def setup_ui(self):
        """Add Read Link Policy Settings command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
    def validate_parameters(self):
        """Build the Read Link Policy Settings command from the inputs"""
        self._cmd_instance = lp_cmds.ReadLinkPolicySettings(
            connection_handle=self.connection_handle.value())

class WriteLinkPolicySettingsCommandUI(HCICmdUI):
    """UI for HCI Write Link Policy Settings command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.WRITE_LINK_POLICY_SETTINGS)
    NAME = "HCI Write Link Policy Settings Command"
    
    def setup_ui(self):
        """Add Write Link Policy Settings command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
        # Policy Settings
        self.settings_group = QGroupBox("Link Policy Settings")
        settings_layout = QVBoxLayout()
        
        self.enable_role_switch = QCheckBox("Enable Role Switch")
        self.enable_hold_mode = QCheckBox("Enable Hold Mode")
        self.enable_sniff_mode = QCheckBox("Enable Sniff Mode")
        self.enable_park_mode = QCheckBox("Enable Park Mode")
        
        settings_layout.addWidget(self.enable_role_switch)
        settings_layout.addWidget(self.enable_hold_mode)
        settings_layout.addWidget(self.enable_sniff_mode)
        settings_layout.addWidget(self.enable_park_mode)
        self.settings_group.setLayout(settings_layout)
        self.form_layout.addRow(self.settings_group)
        
        
    def validate_parameters(self):
        """Build the Write Link Policy Settings command from the checkboxes"""
        cmd = lp_cmds.WriteLinkPolicySettings
        settings = 0x0000
        if self.enable_role_switch.isChecked():
            settings |= cmd.ENABLE_ROLE_SWITCH
        if self.enable_hold_mode.isChecked():
            settings |= cmd.ENABLE_HOLD_MODE
        if self.enable_sniff_mode.isChecked():
            settings |= cmd.ENABLE_SNIFF_MODE
        if self.enable_park_mode.isChecked():
            settings |= cmd.ENABLE_PARK_STATE

        self._cmd_instance = cmd(
            connection_handle=self.connection_handle.value(),
            link_policy_settings=settings)


# Register the command UIs
register_command_ui(HoldModeCommandUI)
register_command_ui(SniffModeCommandUI)
register_command_ui(ExitSniffModeCommandUI)
register_command_ui(QosSetupCommandUI)
register_command_ui(RoleDiscoveryCommandUI)
register_command_ui(SwitchRoleCommandUI)
register_command_ui(ReadLinkPolicySettingsCommandUI)
register_command_ui(WriteLinkPolicySettingsCommandUI)