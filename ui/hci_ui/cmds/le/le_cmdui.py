"""
LE Commands UI Module

This module provides UI components for LE HCI commands.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QSpinBox, QComboBox, QCheckBox,
    QHBoxLayout, QGridLayout
)
from PyQt5.QtGui import QIntValidator, QFont
from PyQt5.QtCore import Qt, pyqtSignal


from typing import Optional
from transports.transport import Transport

from hci.cmd.cmd_opcodes import create_opcode, OGF, LEControllerOCF
import hci.cmd.le_cmds as le_cmds
from hci.cmd.cmd_parser import bd_addr_str_to_bytes

from ..cmd_baseui import HCICmdUI
from .. import register_command_ui


class LeSetAdvParamsUI(HCICmdUI):
    """UI for the LE Set Advertising Parameters command"""
    OPCODE = create_opcode(OGF.LE_CONTROLLER, LEControllerOCF.SET_ADVERTISING_PARAMETERS)
    NAME = "LE Set Advertising Parameters"
    
    AdressType = le_cmds.AddressType
    AdvertisingType = le_cmds.AdvertisingType
    
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
    
    def setup_ui(self):
        """Add parameters specific to LE Set Advertising Parameters command"""
        super().setup_ui()
        # Advertising Interval Min
        self.min_interval_input = QSpinBox()
        self.min_interval_input.setRange(0x0020, 0x4000)
        self.min_interval_input.setValue(0x0800)  # Default: 1.28s
        self.min_interval_input.setToolTip("Minimum advertising interval (N * 0.625 ms)")
        self.form_layout.addRow("Advertising Interval Min:", self.min_interval_input)
        
        # Advertising Interval Max
        self.max_interval_input = QSpinBox()
        self.max_interval_input.setRange(0x0020, 0x4000)
        self.max_interval_input.setValue(0x0800)  # Default: 1.28s
        self.max_interval_input.setToolTip("Maximum advertising interval (N * 0.625 ms)")
        self.form_layout.addRow("Advertising Interval Max:", self.max_interval_input)
        
        # Advertising Type
        self.adv_type_input = QComboBox()
        for adv_type in le_cmds.AdvertisingType:
            self.adv_type_input.addItem(adv_type.name, adv_type.value)
        self.form_layout.addRow("Advertising Type:", self.adv_type_input)
        
        # Own Address Type
        self.own_addr_type_input = QComboBox()
        for addr_type in le_cmds.AddressType:
            self.own_addr_type_input.addItem(addr_type.name, addr_type.value)
        self.form_layout.addRow("Own Address Type:", self.own_addr_type_input)
        
        # Peer Address Type
        self.peer_addr_type_input = QComboBox()
        for addr_type in le_cmds.AddressType:
            self.peer_addr_type_input.addItem(addr_type.name, addr_type.value)
        self.form_layout.addRow("Peer Address Type:", self.peer_addr_type_input)
        
        # Peer Address
        self.peer_addr_input = QLineEdit()
        self.peer_addr_input.setPlaceholderText("Enter hex bytes (e.g., 112233445566)")
        self.peer_addr_input.setText("000000000000")  # Default: all zeros
        self.form_layout.addRow("Peer Address:", self.peer_addr_input)
        
        # Advertising Channel Map
        channel_map_widget = QWidget()
        channel_map_layout = QHBoxLayout(channel_map_widget)
        channel_map_layout.setContentsMargins(0, 0, 0, 0)
        
        self.channel_37_check = QCheckBox("Channel 37")
        self.channel_37_check.setChecked(True)
        self.channel_38_check = QCheckBox("Channel 38")
        self.channel_38_check.setChecked(True)
        self.channel_39_check = QCheckBox("Channel 39")
        self.channel_39_check.setChecked(True)
        
        channel_map_layout.addWidget(self.channel_37_check)
        channel_map_layout.addWidget(self.channel_38_check)
        channel_map_layout.addWidget(self.channel_39_check)
        
        self.form_layout.addRow("Advertising Channel Map:", channel_map_widget)
        
        # Advertising Filter Policy
        self.filter_policy_input = QComboBox()
        self.filter_policy_input.addItem("Process scan and connection requests from all devices", 0x00)
        self.filter_policy_input.addItem("Process connection requests from all devices, scan requests only from White List", 0x01)
        self.filter_policy_input.addItem("Process scan requests from all devices, connection requests only from White List", 0x02)
        self.filter_policy_input.addItem("Process scan and connection requests only from White List", 0x03)
        self.form_layout.addRow("Advertising Filter Policy:", self.filter_policy_input)
    
    def get_parameter_values(self):
        """Get parameter values"""
        # Calculate channel map
        channel_map = 0
        if self.channel_37_check.isChecked():
            channel_map |= 0x01
        if self.channel_38_check.isChecked():
            channel_map |= 0x02
        if self.channel_39_check.isChecked():
            channel_map |= 0x04
        
        # Convert peer address from hex string to bytes
        peer_addr_hex = self.peer_addr_input.text().strip()
        # Remove any spaces and '0x' prefixes
        peer_addr_hex = peer_addr_hex.replace(' ', '').replace('0x', '')
        # Add leading zeros if needed to make 12 hex digits (6 bytes)
        peer_addr_hex = peer_addr_hex.zfill(12)
        peer_addr = bytes.fromhex(peer_addr_hex)
        
        return {
            'adv_interval_min': self.min_interval_input.value(),
            'adv_interval_max': self.max_interval_input.value(),
            'adv_type': self.adv_type_input.currentData(),
            'own_addr_type': self.own_addr_type_input.currentData(),
            'peer_addr_type': self.peer_addr_type_input.currentData(),
            'peer_addr': peer_addr,
            'adv_channel_map': channel_map,
            'adv_filter_policy': self.filter_policy_input.currentData()
        }

class LeSetAdvDataUI(HCICmdUI):
    """UI for the LE Set Advertising Data command"""
    OPCODE = create_opcode(OGF.LE_CONTROLLER, LEControllerOCF.SET_ADVERTISING_DATA)
    NAME = "LE Set Advertising Data"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
    
    def setup_ui(self):
        """Add parameters specific to LE Set Advertising Data command"""
        super().setup_ui()
        # Data Length (auto-calculated)
        self.data_length_label = QLabel("0 bytes")
        self.form_layout.addRow("Data Length:", self.data_length_label)
        
        # Advertising Data
        self.adv_data_input = QLineEdit()
        self.adv_data_input.setPlaceholderText("Enter hex bytes (e.g., 020106070967616C61787920)")
        self.adv_data_input.textChanged.connect(self._update_data_length)
        
        # Add help text
        help_label = QLabel("Common formats: 0201XX (Flags), 09XX..XX (Complete Local Name)")
        help_label.setStyleSheet("color: gray; font-size: 10pt;")
        
        self.form_layout.addRow("Advertising Data:", self.adv_data_input)
        self.form_layout.addRow("", help_label)
        
        # Example buttons
        examples_widget = QWidget()
        examples_layout = QHBoxLayout(examples_widget)
        examples_layout.setContentsMargins(0, 0, 0, 0)
        
        # Example 1: General Discoverable, BR/EDR not supported
        example1_btn = QPushButton("General Discoverable")
        example1_btn.clicked.connect(lambda: self._set_example("020106"))
        examples_layout.addWidget(example1_btn)
        
        # Example 2: General Discoverable + Name
        example2_btn = QPushButton("With Device Name")
        example2_btn.clicked.connect(lambda: self._set_example("02010607094C452044657669636520"))
        examples_layout.addWidget(example2_btn)
        
        self.form_layout.addRow("Examples:", examples_widget)
    
    def _update_data_length(self):
        """Update the data length label based on the input"""
        hex_str = self.adv_data_input.text().strip()
        # Remove any spaces and '0x' prefixes
        hex_str = hex_str.replace(' ', '').replace('0x', '')
        
        # Calculate length in bytes (2 hex digits = 1 byte)
        length = len(hex_str) // 2
        if len(hex_str) % 2 != 0:
            length += 1  # Account for odd number of digits
        
        self.data_length_label.setText(f"{length} bytes")
    
    def _set_example(self, example_hex):
        """Set an example advertising data value"""
        self.adv_data_input.setText(example_hex)
    
    def get_parameter_values(self):
        """Get parameter values"""
        # Get advertising data from hex string
        hex_str = self.adv_data_input.text().strip()
        # Remove any spaces and '0x' prefixes
        hex_str = hex_str.replace(' ', '').replace('0x', '')
        # Add leading zero if odd length
        if len(hex_str) % 2 != 0:
            hex_str = '0' + hex_str
        
        adv_data = bytes.fromhex(hex_str)
        
        return {
            'data': adv_data,
            'data_length': len(adv_data)
        }

class LeSetScanParametersUI(HCICmdUI):
    """UI for the LE Set Scan Parameters command"""
    OPCODE = create_opcode(OGF.LE_CONTROLLER, LEControllerOCF.SET_SCAN_PARAMETERS)
    NAME = "LE Set Scan Parameters"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
    
    def setup_ui(self):
        """Add parameters specific to LE Set Scan Parameters command"""
        super().setup_ui()
        # Scan Type
        self.scan_type_input = QComboBox()
        self.scan_type_input.addItem("Passive Scanning", 0x00)
        self.scan_type_input.addItem("Active Scanning", 0x01)
        self.scan_type_input.setCurrentIndex(1)  # Default: Active
        self.form_layout.addRow("Scan Type:", self.scan_type_input)
        
        # Scan Interval
        self.scan_interval_input = QSpinBox()
        self.scan_interval_input.setRange(0x0004, 0x4000)
        self.scan_interval_input.setValue(0x0010)  # Default: 10ms
        self.scan_interval_input.setToolTip("Scan interval (N * 0.625 ms)")
        self.form_layout.addRow("Scan Interval:", self.scan_interval_input)
        
        # Scan Window
        self.scan_window_input = QSpinBox()
        self.scan_window_input.setRange(0x0004, 0x4000)
        self.scan_window_input.setValue(0x0010)  # Default: 10ms
        self.scan_window_input.setToolTip("Scan window (N * 0.625 ms)")
        self.form_layout.addRow("Scan Window:", self.scan_window_input)
        
        # Own Address Type
        self.own_addr_type_input = QComboBox()
        for addr_type in AddressType:
            self.own_addr_type_input.addItem(addr_type.name, addr_type.value)
        self.form_layout.addRow("Own Address Type:", self.own_addr_type_input)
        
        # Scanning Filter Policy
        self.filter_policy_input = QComboBox()
        self.filter_policy_input.addItem("Accept all advertisements", 0x00)
        self.filter_policy_input.addItem("Accept only from devices in White List", 0x01)
        self.filter_policy_input.addItem("Accept all (use extended scan_request filtering)", 0x02)
        self.filter_policy_input.addItem("Accept only from White List (use extended scan_request filtering)", 0x03)
        self.form_layout.addRow("Scanning Filter Policy:", self.filter_policy_input)
    
    def get_parameter_values(self):
        """Get parameter values"""
        return {
            'scan_type': self.scan_type_input.currentData(),
            'scan_interval': self.scan_interval_input.value(),
            'scan_window': self.scan_window_input.value(),
            'own_addr_type': self.own_addr_type_input.currentData(),
            'scanning_filter_policy': self.filter_policy_input.currentData()
        }

class LeSetScanEnableUI(HCICmdUI):
    """UI for the LE Set Scan Enable command"""
    OPCODE = create_opcode(OGF.LE_CONTROLLER, LEControllerOCF.SET_SCAN_ENABLE)
    NAME = "LE Set Scan Enable"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
    
    def setup_ui(self):
        """Add parameters specific to LE Set Scan Enable command"""
        super().setup_ui()
        # Scan Enable
        self.scan_enable_input = QCheckBox("Enable Scanning")
        self.scan_enable_input.setChecked(True)
        self.form_layout.addRow("Scan Enable:", self.scan_enable_input)
        
        # Filter Duplicates
        self.filter_duplicates_input = QCheckBox("Filter Duplicates")
        self.filter_duplicates_input.setChecked(True)
        self.form_layout.addRow("Filter Duplicates:", self.filter_duplicates_input)
    
    def get_parameter_values(self):
        """Get parameter values"""
        return {
            'scan_enable': self.scan_enable_input.isChecked(),
            'filter_duplicates': self.filter_duplicates_input.isChecked()
        }

# Additional UI classes can be added for other LE commands



# register the UI classes 
register_command_ui(LeSetAdvParamsUI)
register_command_ui(LeSetAdvDataUI)
register_command_ui(LeSetScanParametersUI)
register_command_ui(LeSetScanEnableUI)
# Add more UI classes as needed
