"""
Controller and Baseband Commands UI Module

This module provides UI components for Controller and Baseband HCI commands.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QSpinBox, QComboBox, QCheckBox,
    QTextEdit
)
from PyQt5.QtGui import QIntValidator, QFont
from PyQt5.QtCore import Qt, pyqtSignal

import hci
import hci.cmd as hci_cmd
from hci.cmd.controller_baseband import (
    Reset, SetEventMask, WriteLocalName, ReadLocalName
)

from hci_ui.hci_base_ui import HciCommandUI

class ResetUI(HciCommandUI):
    """UI for the Reset command"""
    
    def __init__(self, command_class=Reset, parent=None):
        super().__init__("Reset Command", command_class, parent)
    
    def add_command_parameters(self):
        """Reset has no parameters"""
        label = QLabel("This command has no parameters. It will reset the controller.")
        self.params_layout.addRow(label)
    
    def get_parameter_values(self):
        """Get parameter values (none for Reset)"""
        return {}

class SetEventMaskUI(HciCommandUI):
    """UI for the Set Event Mask command"""
    
    def __init__(self, command_class=SetEventMask, parent=None):
        super().__init__("Set Event Mask Command", command_class, parent)
    
    def add_command_parameters(self):
        """Add parameters specific to Set Event Mask command"""
        # Event Mask (8 bytes)
        self.event_mask_input = QLineEdit()
        self.event_mask_input.setPlaceholderText("Enter 8-byte hex value (e.g., 00001FFFFFFFFFFF)")
        self.event_mask_input.setText("00001FFFFFFFFFFF")  # Default from spec
        self.params_layout.addRow("Event Mask:", self.event_mask_input)
        
        # Add help text explaining the mask bits
        help_text = """Event Mask bits (from LSB to MSB):
Bit 0: Inquiry Complete Event
Bit 1: Inquiry Result Event
...
Bit 60: LE Meta Event
...
Default value enables all events except reserved bits."""
        
        help_label = QTextEdit()
        help_label.setPlainText(help_text)
        help_label.setReadOnly(True)
        help_label.setMaximumHeight(150)
        self.params_layout.addRow("Event Mask Info:", help_label)
    
    def get_parameter_values(self):
        """Get parameter values"""
        # Convert hex string to integer
        event_mask_hex = self.event_mask_input.text().strip()
        # Remove any spaces and '0x' prefixes
        event_mask_hex = event_mask_hex.replace(' ', '').replace('0x', '')
        # Add leading zeros if needed to make 16 hex digits (8 bytes)
        event_mask_hex = event_mask_hex.zfill(16)
        event_mask = int(event_mask_hex, 16)
        
        return {
            'event_mask': event_mask
        }

class WriteLocalNameUI(HciCommandUI):
    """UI for the Write Local Name command"""
    
    def __init__(self, command_class=WriteLocalName, parent=None):
        super().__init__("Write Local Name Command", command_class, parent)
    
    def add_command_parameters(self):
        """Add parameters specific to Write Local Name command"""
        # Local Name (up to 248 bytes)
        self.local_name_input = QLineEdit()
        self.local_name_input.setPlaceholderText("Enter device name (e.g., My Bluetooth Device)")
        self.local_name_input.setMaxLength(248)  # Maximum allowed by the spec
        self.params_layout.addRow("Local Name:", self.local_name_input)
        
        # Show character count
        self.char_count_label = QLabel("0 / 248 characters")
        self.local_name_input.textChanged.connect(self._update_char_count)
        self.params_layout.addRow("", self.char_count_label)
    
    def _update_char_count(self):
        """Update the character count label"""
        count = len(self.local_name_input.text())
        self.char_count_label.setText(f"{count} / 248 characters")
    
    def get_parameter_values(self):
        """Get parameter values"""
        return {
            'local_name': self.local_name_input.text()
        }

class ReadLocalNameUI(HciCommandUI):
    """UI for the Read Local Name command"""
    
    def __init__(self, command_class=ReadLocalName, parent=None):
        super().__init__("Read Local Name Command", command_class, parent)
    
    def add_command_parameters(self):
        """Read Local Name has no parameters"""
        label = QLabel("This command has no parameters. It will read the device's local name.")
        self.params_layout.addRow(label)
    
    def get_parameter_values(self):
        """Get parameter values (none for Read Local Name)"""
        return {}

# Additional UI classes can be added for other Controller & Baseband commands


# Add any additional command UI registrations here