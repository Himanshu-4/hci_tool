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


from hci.cmd.cmd_opcodes import create_opcode, OGF, ControllerBasebandOCF
import hci.cmd.controller_baseband as cb_cmds

from typing import Optional, Union, List

from ..cmd_baseui import HCICmdUI

from .. import register_command_ui

#MARK: setEventMAsk
class SetEventMaskUI(HCICmdUI):
    """UI for the Set Event Mask command"""
    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND, ControllerBasebandOCF.SET_EVENT_MASK)
    NAME = "Set Event Mask"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Initialize the Set Event Mask command UI"""
        super().setup_ui()

        # Event Mask (8 bytes)
        self.event_mask_input = QLineEdit()
        self.event_mask_input.setPlaceholderText("Enter 8-byte hex value (e.g., 00001FFFFFFFFFFF)")
        self.event_mask_input.setText("00001FFFFFFFFFFF")  # Default from spec
        self.form_layout.addRow("Event Mask:", self.event_mask_input)
        
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
        self.form_layout.addRow("Event Mask Info:", help_label)
    
    def get_data_bytes(self) -> bytes:
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

class WriteLocalNameUI(HCICmdUI):
    """UI for the Write Local Name command"""
    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND, ControllerBasebandOCF.WRITE_LOCAL_NAME)
    NAME = "Write Local Name"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Add ui specific to Write Local Name command"""
        super().setup_ui()
        # Local Name (up to 248 bytes)
        self.local_name_input = QLineEdit()
        self.local_name_input.setPlaceholderText("Enter device name (e.g., My Bluetooth Device)")
        self.local_name_input.setMaxLength(248)  # Maximum allowed by the spec
        self.form_layout.addRow("Local Name:", self.local_name_input)
        
        # Show character count
        self.char_count_label = QLabel("0 / 248 characters")
        self.local_name_input.textChanged.connect(self._update_char_count)
        self.form_layout.addRow("", self.char_count_label)
    
    def _update_char_count(self):
        """Update the character count label"""
        count = len(self.local_name_input.text())
        self.char_count_label.setText(f"{count} / 248 characters")
    
    def validate_parameters(self) -> bool:
        """Validate parameters before sending by the WritelocalName command"""
        try:
            cb_cmds.WriteLocalName(self.local_name_input.text().strip())._validate_params()
        except ValueError as e:
            self.log_error(f"Validation error: {str(e)}")
            return False
        return True

    
    def get_data_bytes(self) -> Optional[bytes]:
        """Get parameter values"""
        local_name = self.local_name_input.text().strip()
        if not local_name:
            self.log_error("Local Name cannot be empty")
            return

        return cb_cmds.WriteLocalName(local_name).to_bytes()
        


# Additional UI classes can be added for other Controller & Baseband commands


# Add any additional command UI registrations here
register_command_ui(SetEventMaskUI)
register_command_ui(WriteLocalNameUI)   