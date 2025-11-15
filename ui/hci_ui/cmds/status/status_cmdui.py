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


from hci.cmd.cmd_opcodes import create_opcode, OGF, StatusOCF
import hci.cmd.status as st_cmds

from typing import Optional, Union, List

from ..cmd_baseui import HCICmdUI

from .. import register_command_ui



class ReadRssi(HCICmdUI):
    """UI for the Write Local Name command"""
    OPCODE = create_opcode(OGF.STATUS, StatusOCF.READ_RSSI)
    NAME = "Read RSSI"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Add ui specific to Write Local Name command"""
        super().setup_ui()
        # Local Name (up to 248 bytes)
        self.conn_handle_label = QLabel("Connection Handle:")
        self.conn_handle_input = QSpinBox()
        self.conn_handle_input.setRange(0, 0x0EFF)
        self.conn_handle_input.setValue(0)
        # the conn handle ony accept in hex format
        self.conn_handle_input.setDisplayIntegerBase(16)
        # set the size of box 
        self.conn_handle_input.setMinimumWidth(100)
        # self.conn_handle_input.setValidator(QIntValidator(0, 0x0EFF, self))
        self.conn_handle_input.setToolTip("Enter the connection handle to read RSSI for")
        self.form_layout.addRow(self.conn_handle_label, self.conn_handle_input)


    def validate_parameters(self):
        """Validate parameters before sending by the WritelocalName command"""
        try:
            st_cmds.ReadRssi(conn_handle= self.conn_handle_input.value())._validate_params()
        except ValueError as e:
            self.log_error(f"Validation error: {str(e)}")
            return False
        return True

    
    def get_data_bytes(self) -> Optional[bytes]:
        """Get parameter values"""
        conn_handle = self.conn_handle_input.value()
        return st_cmds.ReadRssi(conn_handle).to_bytes()

        


# Additional UI classes can be added for other Controller & Baseband commands


# Add any additional command UI registrations here
register_command_ui(ReadRssi)