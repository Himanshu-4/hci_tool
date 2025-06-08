from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QSpinBox, QLabel, QPushButton, QGridLayout, QGroupBox,
    QCheckBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt
import struct

from typing import Optional
from transports.transport import Transport

from hci.cmd.cmd_opcodes import create_opcode, OGF, LinkPolicyOCF
import hci.cmd.link_policy as lp_cmds
from hci import bd_addr_str_to_bytes

from ..cmd_baseui import HCICmdUI
from .. import register_command_ui


class HoldModeCommandUI(HCICmdUI):
    """UI for HCI Hold Mode command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.HOLD_MODE)
    NAME = "HCI Hold Mode Command"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        """ validate the Hold mode cmd by the hci.cmd.link_policy.HoldModeCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        max_interval = self.max_interval.value()
        min_interval = self.min_interval.value()
        
        try:
            lp_cmds.HoldMode(
                connection_handle, max_interval, min_interval
            )._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Hold Mode command data bytes from the hci.cmd.link_policy.HoldModeCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        max_interval = self.max_interval.value()
        min_interval = self.min_interval.value()
        
        return lp_cmds.HoldMode(
                connection_handle, max_interval, min_interval
            ).to_bytes()

       
class SniffModeCommandUI(HCICmdUI):
    """UI for HCI Sniff Mode command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.SNIFF_MODE)
    NAME = "HCI Sniff Mode Command"
    def __init__(self):
        super().__init__("HCI Sniff Mode Command")
        
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
        """ validate the Sniff mode cmd by the hci.cmd.link_policy.SniffModeCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        max_interval = self.max_interval.value()
        min_interval = self.min_interval.value()
        sniff_attempt = self.sniff_attempt.value()
        sniff_timeout = self.sniff_timeout.value()
        
        try:
            lp_cmds.SniffMode(
                connection_handle, max_interval, min_interval, sniff_attempt, sniff_timeout
            )._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Sniff Mode command data bytes from the hci.cmd.link_policy.SniffModeCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        max_interval = self.max_interval.value()
        min_interval = self.min_interval.value()
        sniff_attempt = self.sniff_attempt.value()
        sniff_timeout = self.sniff_timeout.value()
        
        return lp_cmds.SniffMode(
                connection_handle, max_interval, min_interval, sniff_attempt, sniff_timeout
            ).to_bytes()


class ExitSniffModeCommandUI(HCICmdUI):
    """UI for HCI Exit Sniff Mode command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.EXIT_SNIFF_MODE)
    NAME = "HCI Exit Sniff Mode Command"
    def __init__(self):
        super().__init__("HCI Exit Sniff Mode Command")
        
    def setup_ui(self):
        """Add Exit Sniff Mode command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
    def validate_parameters(self):
        """ validate the Exit Sniff Mode cmd by the hci.cmd.link_policy.ExitSniffModeCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        
        try:
            lp_cmds.ExitSniffMode(connection_handle)._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Exit Sniff Mode command data bytes from the hci.cmd.link_policy.ExitSniffModeCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        
        return lp_cmds.ExitSniffMode(connection_handle).to_bytes()

class QosSetupCommandUI(HCICmdUI):
    """UI for HCI QoS Setup command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.QOS_SETUP)
    NAME = "HCI QoS Setup Command"
    def __init__(self):
        super().__init__("HCI QoS Setup Command")
        
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
        
        # Token Rate
        self.token_rate = QSpinBox()
        self.token_rate.setRange(0, 0xFFFFFFFF)
        self.token_rate.setValue(0)
        self.token_rate.setToolTip("Token Rate (bytes/second)")
        self.form_layout.addRow( "Token Rate (B/s):", self.token_rate)
        
        # Peak Bandwidth
        self.peak_bandwidth = QSpinBox()
        self.peak_bandwidth.setRange(0, 0xFFFFFFFF)
        self.peak_bandwidth.setValue(0)
        self.peak_bandwidth.setToolTip("Peak Bandwidth (bytes/second)")
        self.form_layout.addRow( "Peak Bandwidth (B/s):", self.peak_bandwidth)
        
        # Latency
        self.latency = QSpinBox()
        self.latency.setRange(0, 0xFFFFFFFF)
        self.latency.setValue(0xFFFFFFFF)
        self.latency.setToolTip("Latency (microseconds)")
        self.form_layout.addRow( "Latency (μs):", self.latency)
        
        # Delay Variation
        self.delay_variation = QSpinBox()
        self.delay_variation.setRange(0, 0xFFFFFFFF)
        self.delay_variation.setValue(0xFFFFFFFF)
        self.delay_variation.setToolTip("Delay Variation (microseconds)")
        self.form_layout.addRow( "Delay Variation (μs):", self.delay_variation)
        
    def validate_parameters(self):
        """ validate the QoS Setup cmd by the hci.cmd.link_policy.QosSetupCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        flags = self.flags.value()
        service_type = self.service_type.currentData()
        token_rate = self.token_rate.value()
        peak_bandwidth = self.peak_bandwidth.value()
        latency = self.latency.value()
        delay_variation = self.delay_variation.value()
        
        try:
            lp_cmds.QosSetup(
                connection_handle, flags, service_type, token_rate,
                peak_bandwidth, latency, delay_variation
            )._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True

    def get_data_bytes(self):
        """ get the QoS Setup command data bytes from the hci.cmd.link_policy.QosSetupCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        flags = self.flags.value()
        service_type = self.service_type.currentData()
        token_rate = self.token_rate.value()
        peak_bandwidth = self.peak_bandwidth.value()
        latency = self.latency.value()
        delay_variation = self.delay_variation.value()
        
        return lp_cmds.QosSetup(
                connection_handle, flags, service_type, token_rate,
                peak_bandwidth, latency, delay_variation
            ).to_bytes()

class RoleDiscoveryCommandUI(HCICmdUI):
    """UI for HCI Role Discovery command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.ROLE_DISCOVERY)
    NAME = "HCI Role Discovery Command"
    def __init__(self):
        super().__init__("HCI Role Discovery Command")
        
    def setup_ui(self):
        """Add Role Discovery command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
    def validate_parameters(self):
        """ validate the Role Discovery cmd by the hci.cmd.link_policy.RoleDiscoveryCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        
        try:
            lp_cmds.RoleDiscovery(connection_handle)._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Role Discovery command data bytes from the hci.cmd.link_policy.RoleDiscoveryCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        
        return lp_cmds.RoleDiscovery(connection_handle).to_bytes()

class SwitchRoleCommandUI(HCICmdUI):
    """UI for HCI Switch Role command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.SWITCH_ROLE)
    NAME = "HCI Switch Role Command"
    
    def __init__(self):
        super().__init__("HCI Switch Role Command")
        
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
        """ validate the Switch Role cmd by the hci.cmd.link_policy.SwitchRoleCmd.validate_parameters()"""
        bd_addr = self.bd_addr.text().strip()
        role = self.role.currentData()
        
        try:
            lp_cmds.SwitchRole(bd_addr_str_to_bytes(bd_addr), role)._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Switch Role command data bytes from the hci.cmd.link_policy.SwitchRoleCmd.to_bytes()"""
        bd_addr = self.bd_addr.text().strip()
        role = self.role.currentData()
        
        return lp_cmds.SwitchRole(bd_addr_str_to_bytes(bd_addr), role).to_bytes()


class ReadLinkPolicySettingsCommandUI(HCICmdUI):
    """UI for HCI Read Link Policy Settings command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.READ_LINK_POLICY_SETTINGS)
    NAME = "HCI Read Link Policy Settings Command"
    
    def __init__(self):
        super().__init__("HCI Read Link Policy Settings Command")
        
    def setup_ui(self):
        """Add Read Link Policy Settings command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
    def validate_parameters(self):
        """ validate the Read Link Policy Settings cmd by the hci.cmd.link_policy.ReadLinkPolicySettingsCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        
        try:
            lp_cmds.ReadLinkPolicySettings(connection_handle)._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Read Link Policy Settings command data bytes from the hci.cmd.link_policy.ReadLinkPolicySettingsCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        
        return lp_cmds.ReadLinkPolicySettings(connection_handle).to_bytes()

class WriteLinkPolicySettingsCommandUI(HCICmdUI):
    """UI for HCI Write Link Policy Settings command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.WRITE_LINK_POLICY_SETTINGS)
    NAME = "HCI Write Link Policy Settings Command"
    
    def __init__(self):
        super().__init__("HCI Write Link Policy Settings Command")
        
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
        """ validate the Write Link Policy Settings cmd by the hci.cmd.link_policy.WriteLinkPolicySettingsCmd.validate_parameters()"""
        connection_handle = self.connection_handle.value()
        
        try:
            lp_cmds.WriteLinkPolicySettings(
                connection_handle,
                self.enable_role_switch.isChecked(),
                self.enable_hold_mode.isChecked(),
                self.enable_sniff_mode.isChecked(),
                self.enable_park_mode.isChecked()
            )._validate_params()
        except ValueError as e:
            self.log_error(f"Inavalid parametrs: {e}")
            return False
        return True
    
    def get_data_bytes(self):
        """ get the Write Link Policy Settings command data bytes from the hci.cmd.link_policy.WriteLinkPolicySettingsCmd.to_bytes()"""
        connection_handle = self.connection_handle.value()
        
        return lp_cmds.WriteLinkPolicySettings(
                connection_handle,
                self.enable_role_switch.isChecked(),
                self.enable_hold_mode.isChecked(),
                self.enable_sniff_mode.isChecked(),
                self.enable_park_mode.isChecked()
            ).to_bytes()
    
# Register the command UIs
register_command_ui(HoldModeCommandUI)
register_command_ui(SniffModeCommandUI)
register_command_ui(ExitSniffModeCommandUI)
register_command_ui(QosSetupCommandUI)
register_command_ui(RoleDiscoveryCommandUI)
register_command_ui(SwitchRoleCommandUI)
register_command_ui(ReadLinkPolicySettingsCommandUI)
register_command_ui(WriteLinkPolicySettingsCommandUI)
        # Get the event code and data from the input fields