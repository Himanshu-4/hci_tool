"""
Generic Command UI Module

This module provides generic UI components for HCI commands that don't have
specific UI implementations.
"""


from transports.transport import Transport
from PyQt5.QtWidgets import QGroupBox, QFormLayout
from abc import abstractmethod
from typing import  Union, Optional, List

from ..hci_base_ui import HCICmdBaseUI

class HCICmdUI(HCICmdBaseUI):
    """Generic UI for HCI commands with automatic parameter input fields"""
    
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        self.title = title
        self.transport = transport
    
    def setup_ui(self):
        """Initialize the command UI"""
        super().setup_ui()
        
        self.param_group = QGroupBox("Command Parameters")
        self.form_layout = QFormLayout()
        self.param_group.setLayout(self.form_layout)
        
        # # Add command info
        # info_group = QGroupBox("Command Information")
        # info_layout = QFormLayout()
        # info_layout.addRow("Command:", QLabel(self.cmd_name))
        # info_layout.addRow("OGF:", QLabel(f"0x{self.ogf:02X}"))
        # info_layout.addRow("OCF:", QLabel(f"0x{self.ocf:02X}"))
        # info_layout.addRow("OpCode:", QLabel(f"0x{(self.ogf << 10) | self.ocf:04X}"))
        # info_group.setLayout(info_layout)
        
        # Add groups to content layout
        # self.content_layout.addWidget(info_group)

        self.content_layout.addWidget(self.param_group)
        

    
    @abstractmethod
    def pre_send_func(self):
        """Pre-send function to validate and prepare data"""
        pass
    
    def on_ok_button_clicked(self):
        """Handle OK button click"""
        # Collect parameter values
        self.pre_send_func()
        return super().on_ok_button_clicked()    
