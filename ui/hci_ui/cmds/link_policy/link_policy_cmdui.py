from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QSpinBox, QLabel, QPushButton, QGridLayout, QGroupBox,
    QCheckBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt
import struct

from hci_ui.hci_base_ui import HCICommandUI

# HCI opcodes for Link Policy commands
HCI_OPCODE_HOLD_MODE = 0x0801
HCI_OPCODE_SNIFF_MODE = 0x0803
HCI_OPCODE_EXIT_SNIFF_MODE = 0x0804
HCI_OPCODE_QOS_SETUP = 0x0807
HCI_OPCODE_ROLE_DISCOVERY = 0x0809
HCI_OPCODE_SWITCH_ROLE = 0x080B
HCI_OPCODE_READ_LINK_POLICY_SETTINGS = 0x080C
HCI_OPCODE_WRITE_LINK_POLICY_SETTINGS = 0x080D

# Command structure functions
def create_hci_command_packet(opcode, data):
    """Create an HCI command packet with the specified opcode and data"""
    length = len(data)
    header = struct.pack("<BHB", 0x01, opcode, length)  # 0x01 is HCI command packet type
    return bytearray(header + data)

def bd_addr_str_to_bytes(addr_str):
    """Convert a BD_ADDR string (e.g., '00:11:22:33:44:55') to bytes"""
    # Remove any colons or other separators
    clean_addr = addr_str.replace(':', '').replace('-', '')
    
    if len(clean_addr) != 12:
        raise ValueError("Invalid BD_ADDR format. Expected 12 hex characters.")
    
    # Convert each byte and reverse the order (Bluetooth addresses are little-endian)
    addr_bytes = bytearray.fromhex(clean_addr)
    addr_bytes.reverse()  # Reverse for little-endian format
    
    return addr_bytes


class HoldModeCommandUI(HCICommandUI):
    """UI for HCI Hold Mode command"""
    
    def __init__(self):
        super().__init__("HCI Hold Mode Command")
        
    def add_command_ui(self):
        """Add Hold Mode command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
        # Hold Mode Max Interval
        row += 1
        self.max_interval = QSpinBox()
        self.max_interval.setRange(0x0002, 0xFFFE)
        self.max_interval.setValue(0x0080)  # Default value (128 * 0.625ms = 80ms)
        self.max_interval.setToolTip("Maximum Hold Interval (N * 0.625 ms)")
        self.add_parameter(row, "Hold Mode Max Interval:", self.max_interval)
        
        # Hold Mode Min Interval
        row += 1
        self.min_interval = QSpinBox()
        self.min_interval.setRange(0x0001, 0xFFFE)
        self.min_interval.setValue(0x0040)  # Default value (64 * 0.625ms = 40ms)
        self.min_interval.setToolTip("Minimum Hold Interval (N * 0.625 ms)")
        self.add_parameter(row, "Hold Mode Min Interval:", self.min_interval)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Hold Mode command"""
        connection_handle = self.connection_handle.value()
        max_interval = self.max_interval.value()
        min_interval = self.min_interval.value()
        
        # Create command parameters
        cmd_params = struct.pack("<HHH", connection_handle, max_interval, min_interval)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_HOLD_MODE, cmd_params)


class SniffModeCommandUI(HCICommandUI):
    """UI for HCI Sniff Mode command"""
    
    def __init__(self):
        super().__init__("HCI Sniff Mode Command")
        
    def add_command_ui(self):
        """Add Sniff Mode command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
        # Sniff Max Interval
        row += 1
        self.max_interval = QSpinBox()
        self.max_interval.setRange(0x0002, 0xFFFE)
        self.max_interval.setValue(0x0320)  # Default value (800 * 0.625ms = 500ms)
        self.max_interval.setToolTip("Maximum Sniff Interval (N * 0.625 ms)")
        self.add_parameter(row, "Sniff Max Interval:", self.max_interval)
        
        # Sniff Min Interval
        row += 1
        self.min_interval = QSpinBox()
        self.min_interval.setRange(0x0002, 0xFFFE)
        self.min_interval.setValue(0x0190)  # Default value (400 * 0.625ms = 250ms)
        self.min_interval.setToolTip("Minimum Sniff Interval (N * 0.625 ms)")
        self.add_parameter(row, "Sniff Min Interval:", self.min_interval)
        
        # Sniff Attempt
        row += 1
        self.sniff_attempt = QSpinBox()
        self.sniff_attempt.setRange(0x0001, 0x7FFF)
        self.sniff_attempt.setValue(4)
        self.sniff_attempt.setToolTip("Number of Baseband receive slots for sniff attempt")
        self.add_parameter(row, "Sniff Attempt:", self.sniff_attempt)
        
        # Sniff Timeout
        row += 1
        self.sniff_timeout = QSpinBox()
        self.sniff_timeout.setRange(0x0000, 0x7FFF)
        self.sniff_timeout.setValue(1)
        self.sniff_timeout.setToolTip("Number of Baseband receive slots for sniff timeout")
        self.add_parameter(row, "Sniff Timeout:", self.sniff_timeout)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Sniff Mode command"""
        connection_handle = self.connection_handle.value()
        max_interval = self.max_interval.value()
        min_interval = self.min_interval.value()
        sniff_attempt = self.sniff_attempt.value()
        sniff_timeout = self.sniff_timeout.value()
        
        # Create command parameters
        cmd_params = struct.pack("<HHHHH", 
                               connection_handle, 
                               max_interval, 
                               min_interval,
                               sniff_attempt,
                               sniff_timeout)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_SNIFF_MODE, cmd_params)


class ExitSniffModeCommandUI(HCICommandUI):
    """UI for HCI Exit Sniff Mode command"""
    
    def __init__(self):
        super().__init__("HCI Exit Sniff Mode Command")
        
    def add_command_ui(self):
        """Add Exit Sniff Mode command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Exit Sniff Mode command"""
        connection_handle = self.connection_handle.value()
        
        # Create command parameters
        cmd_params = struct.pack("<H", connection_handle)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_EXIT_SNIFF_MODE, cmd_params)


class QosSetupCommandUI(HCICommandUI):
    """UI for HCI QoS Setup command"""
    
    def __init__(self):
        super().__init__("HCI QoS Setup Command")
        
    def add_command_ui(self):
        """Add QoS Setup command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
        # Flags
        row += 1
        self.flags = QSpinBox()
        self.flags.setRange(0, 0xFF)
        self.flags.setValue(0)  # Default: No flags set
        self.flags.setToolTip("Reserved for future use (set to 0)")
        self.add_parameter(row, "Flags:", self.flags)
        
        # Service Type
        row += 1
        self.service_type = QComboBox()
        self.service_type.addItem("No Traffic", 0)
        self.service_type.addItem("Best Effort", 1)
        self.service_type.addItem("Guaranteed", 2)
        self.add_parameter(row, "Service Type:", self.service_type)
        
        # Token Rate
        row += 1
        self.token_rate = QSpinBox()
        self.token_rate.setRange(0, 0xFFFFFFFF)
        self.token_rate.setValue(0)
        self.token_rate.setToolTip("Token Rate (bytes/second)")
        self.add_parameter(row, "Token Rate (B/s):", self.token_rate)
        
        # Peak Bandwidth
        row += 1
        self.peak_bandwidth = QSpinBox()
        self.peak_bandwidth.setRange(0, 0xFFFFFFFF)
        self.peak_bandwidth.setValue(0)
        self.peak_bandwidth.setToolTip("Peak Bandwidth (bytes/second)")
        self.add_parameter(row, "Peak Bandwidth (B/s):", self.peak_bandwidth)
        
        # Latency
        row += 1
        self.latency = QSpinBox()
        self.latency.setRange(0, 0xFFFFFFFF)
        self.latency.setValue(0xFFFFFFFF)
        self.latency.setToolTip("Latency (microseconds)")
        self.add_parameter(row, "Latency (μs):", self.latency)
        
        # Delay Variation
        row += 1
        self.delay_variation = QSpinBox()
        self.delay_variation.setRange(0, 0xFFFFFFFF)
        self.delay_variation.setValue(0xFFFFFFFF)
        self.delay_variation.setToolTip("Delay Variation (microseconds)")
        self.add_parameter(row, "Delay Variation (μs):", self.delay_variation)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the QoS Setup command"""
        connection_handle = self.connection_handle.value()
        flags = self.flags.value()
        service_type = self.service_type.currentData()
        token_rate = self.token_rate.value()
        peak_bandwidth = self.peak_bandwidth.value()
        latency = self.latency.value()
        delay_variation = self.delay_variation.value()
        
        # Create command parameters
        cmd_params = struct.pack("<HBBLLLI", 
                               connection_handle, 
                               flags, 
                               service_type,
                               token_rate,
                               peak_bandwidth,
                               latency,
                               delay_variation)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_QOS_SETUP, cmd_params)


class RoleDiscoveryCommandUI(HCICommandUI):
    """UI for HCI Role Discovery command"""
    
    def __init__(self):
        super().__init__("HCI Role Discovery Command")
        
    def add_command_ui(self):
        """Add Role Discovery command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Role Discovery command"""
        connection_handle = self.connection_handle.value()
        
        # Create command parameters
        cmd_params = struct.pack("<H", connection_handle)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_ROLE_DISCOVERY, cmd_params)


class SwitchRoleCommandUI(HCICommandUI):
    """UI for HCI Switch Role command"""
    
    def __init__(self):
        super().__init__("HCI Switch Role Command")
        
    def add_command_ui(self):
        """Add Switch Role command specific UI components"""
        super().add_command_ui()
        
        # BD_ADDR
        row = 0
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device")
        self.add_parameter(row, "BD_ADDR:", self.bd_addr)
        
        # Role
        row += 1
        self.role = QComboBox()
        self.role.addItem("Master", 0)
        self.role.addItem("Slave", 1)
        self.add_parameter(row, "Role:", self.role)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Switch Role command"""
        # Get BD_ADDR
        bd_addr_bytes = bd_addr_str_to_bytes(self.bd_addr.text())
        
        # Get role
        role = self.role.currentData()
        
        # Create command parameters
        cmd_params = bd_addr_bytes + struct.pack("<B", role)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_SWITCH_ROLE, cmd_params)


class ReadLinkPolicySettingsCommandUI(HCICommandUI):
    """UI for HCI Read Link Policy Settings command"""
    
    def __init__(self):
        super().__init__("HCI Read Link Policy Settings Command")
        
    def add_command_ui(self):
        """Add Read Link Policy Settings command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Read Link Policy Settings command"""
        connection_handle = self.connection_handle.value()
        
        # Create command parameters
        cmd_params = struct.pack("<H", connection_handle)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_READ_LINK_POLICY_SETTINGS, cmd_params)


class WriteLinkPolicySettingsCommandUI(HCICommandUI):
    """UI for HCI Write Link Policy Settings command"""
    
    def __init__(self):
        super().__init__("HCI Write Link Policy Settings Command")
        
    def add_command_ui(self):
        """Add Write Link Policy Settings command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
        # Policy Settings
        row += 1
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
        self.params_layout.addWidget(self.settings_group, row, 0, 1, 2)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Write Link Policy Settings command"""
        connection_handle = self.connection_handle.value()
        
        # Calculate link policy settings bitmask
        policy_settings = 0
        if self.enable_role_switch.isChecked():
            policy_settings |= 0x0001
        if self.enable_hold_mode.isChecked():
            policy_settings |= 0x0002
        if self.enable_sniff_mode.isChecked():
            policy_settings |= 0x0004
        if self.enable_park_mode.isChecked():
            policy_settings |= 0x0008
        
        # Create command parameters
        cmd_params = struct.pack("<HH", connection_handle, policy_settings)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_WRITE_LINK_POLICY_SETTINGS, cmd_params)