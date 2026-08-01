from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QSpinBox, QLabel, QPushButton, QGridLayout, QGroupBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt

from typing import Optional

from hci.cmd.cmd_opcodes import create_opcode, OGF, LinkControlOCF
import hci.cmd.link_controller as lc_cmds

from ..cmd_baseui import HCICmdUI
from .. import register_command_ui



class InquiryCommandUI(HCICmdUI):
    """UI for HCI Inquiry command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.INQUIRY)
    NAME = "Inquiry Command"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Inquiry command specific UI components"""
        super().setup_ui()
        
        # LAP (Lower Address Part)
        self.lap_field = QLineEdit("33:8B:9E")  # Default General/Unlimited Inquiry Access Code
        self.lap_field.setToolTip("Lower Address Part (LAP) of the General Inquiry Access Code (GIAC)")
        self.form_layout.addRow("LAP (Inquiry Access Code):", self.lap_field)
        
        # Inquiry Length
        self.inquiry_length = QSpinBox()
        self.inquiry_length.setRange(1, 0xFF)
        self.inquiry_length.setValue(10)  # Default value (10 * 1.28s = 12.8s)
        self.inquiry_length.setToolTip("Inquiry Length (N * 1.28 seconds)")
        self.form_layout.addRow( "Inquiry Length:", self.inquiry_length)
        
        # Num Responses
        self.num_responses = QSpinBox()
        self.num_responses.setRange(0, 0xFF)
        self.num_responses.setValue(0)  # 0 = unlimited responses
        self.num_responses.setToolTip("Maximum number of responses (0 = unlimited)")
        self.form_layout.addRow( "Num Responses:", self.num_responses)
        
    def validate_parameters(self) -> bool:
        lap_str = self.lap_field.text().replace(':', '')
        lap = int(lap_str, 16) & 0x00FFFFFF  # Extract 24-bit LAP value
        

        self._cmd_instance = lc_cmds.Inquiry(lap=lap, inquiry_length=self.inquiry_length.value(),
                    num_responses=self.num_responses.value())
    


class CreateConnectionCommandUI(HCICmdUI):
    """UI for HCI Create Connection command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CREATE_CONNECTION)
    NAME = "Create Connection Command"
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Create Connection command specific UI components"""
        super().setup_ui()
        
        # BD_ADDR
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to connect to")
        self.form_layout.addRow( "BD_ADDR:", self.bd_addr)
        
        # Packet Type
        self.packet_type = QSpinBox()
        self.packet_type.setRange(0, 0xFFFF)
        self.packet_type.setValue(0xCC18)  # Default: DM1, DH1, DM3, DH3, DM5, DH5
        self.packet_type.setToolTip("Packet types allowed for this connection")
        self.form_layout.addRow( "Packet Type:", self.packet_type)
        
        # Page Scan Repetition Mode
        self.page_scan_repetition = QComboBox()
        self.page_scan_repetition.addItem("R0", 0)
        self.page_scan_repetition.addItem("R1", 1)
        self.page_scan_repetition.addItem("R2", 2)
        self.form_layout.addRow("Page Scan Repetition Mode:", self.page_scan_repetition)
        
        # Clock Offset
        self.clock_offset = QSpinBox()
        self.clock_offset.setRange(0, 0xFFFF)
        self.clock_offset.setValue(0)
        self.form_layout.addRow( "Clock Offset:", self.clock_offset)
        
        # Allow Role Switch
        self.allow_role_switch = QComboBox()
        self.allow_role_switch.addItem("Don't Allow (Master)", 0)
        self.allow_role_switch.addItem("Allow (Master or Slave)", 1)
        self.form_layout.addRow("Allow Role Switch:", self.allow_role_switch)
        
    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.CreateConnection(
                bd_addr = self.bd_addr.text().strip(),
                packet_type=self.packet_type.value(),
                page_scan_repetition_mode=self.page_scan_repetition.currentData(),
                clock_offset=self.clock_offset.value(),
                allow_role_switch=self.allow_role_switch.currentData()
            )
       


class AcceptConnectionCommandUI(HCICmdUI):
    """UI for HCI Accept Connection Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.ACCEPT_CONNECTION_REQUEST)
    NAME = "Accept Connection Command"
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Accept Connection Request command specific UI components"""
        super().setup_ui()
        
        # BD_ADDR
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to accept connection from")
        self.form_layout.addRow( "BD_ADDR:", self.bd_addr)
        
        # Role
        self.role = QComboBox()
        self.role.addItem("Master", 0)
        self.role.addItem("Slave", 1)
        self.form_layout.addRow( "Role:", self.role)
     
    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.AcceptConnectionRequest(
            bd_addr=self.bd_addr.text().strip(),
                role=self.role.currentData())



class DisconnectCommandUI(HCICmdUI):
    """UI for HCI Disconnect command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.DISCONNECT)
    NAME = "Disconnect Command"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

    def setup_ui(self):
        """Add Disconnect command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
        # Reason
        self.reason = QComboBox()
        self.reason.addItem("Authentication Failure (0x05)", 0x05)
        self.reason.addItem("Remote User Terminated Connection (0x13)", 0x13)
        self.reason.addItem("Remote Device Terminated Connection (0x14)", 0x14)
        self.reason.addItem("Remote Device Terminated Connection - Low Resources (0x15)", 0x15)
        self.reason.addItem("Remote Device Terminated Connection - Power Off (0x16)", 0x16)
        self.reason.addItem("Unsupported Remote Feature (0x1A)", 0x1A)
        self.reason.addItem("Unacceptable Connection Parameters (0x3B)", 0x3B)
        self.form_layout.addRow( "Reason:", self.reason)
        
    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.Disconnect(
                connection_handle=self.connection_handle.value(),
                reason=self.reason.currentData())


class RejectConnectionCommandUI(HCICmdUI):
    """UI for HCI Reject Connection Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REJECT_CONNECTION_REQUEST)
    NAME = "Reject Connection Command"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Reject Connection Request command specific UI components"""
        super().setup_ui()
        
        # BD_ADDR
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to reject connection from")
        self.form_layout.addRow( "BD_ADDR:", self.bd_addr)
        
        # Reason
        self.reason = QComboBox()
        self.reason.addItem("Limited Resources (0x0D)", 0x0D)
        self.reason.addItem("Security Reasons (0x0E)", 0x0E)
        self.reason.addItem("Unacceptable BD_ADDR (0x0F)", 0x0F)
        self.form_layout.addRow( "Reason:", self.reason)
        
    def validate_parameters(self) -> bool:
        self._cmd_instance =  lc_cmds.RejectConnectionRequest(
                bd_addr = self.bd_addr.text().strip(),
                reason=self.reason.currentData())
    

class ChangeConnectionPacketTypeCommandUI(HCICmdUI):
    """UI for HCI Change Connection Packet Type command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CHANGE_CONNECTION_PACKET_TYPE)
    NAME = "Change Connection Packet Type Command"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Change Connection Packet Type command specific UI components"""
        super().setup_ui()
        
        # Connection Handle
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.form_layout.addRow( "Connection Handle:", self.connection_handle)
        
        # Packet Type
        self.packet_type = QSpinBox()
        self.packet_type.setRange(0, 0xFFFF)
        self.packet_type.setValue(0xCC18)  # Default: DM1, DH1, DM3, DH3, DM5, DH5
        self.packet_type.setToolTip("Packet types allowed for this connection")
        self.form_layout.addRow( "Packet Type:", self.packet_type)
        
    def validate_parameters(self) -> bool:
        self._cmd_instance = lc_cmds.ChangeConnectionPacketType(
                connection_handle=self.connection_handle.value(),
                packet_type=self.packet_type.value())
        

class RemoteNameRequestCommandUI(HCICmdUI):
    """UI for HCI Remote Name Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REMOTE_NAME_REQUEST)
    NAME = "Remote Name Request Command"
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Add Remote Name Request command specific UI components"""
        super().setup_ui()
        
        # BD_ADDR
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to request name from")
        self.form_layout.addRow( "BD_ADDR:", self.bd_addr)
        
        # Page Scan Repetition Mode
        self.page_scan_repetition = QComboBox()
        self.page_scan_repetition.addItem("R0", 0)
        self.page_scan_repetition.addItem("R1", 1)
        self.page_scan_repetition.addItem("R2", 2)
        self.form_layout.addRow( "Page Scan Repetition Mode:", self.page_scan_repetition)
        
        # Clock Offset
        self.clock_offset = QSpinBox()
        self.clock_offset.setRange(0, 0xFFFF)
        self.clock_offset.setValue(0)
        self.form_layout.addRow( "Clock Offset:", self.clock_offset)
    
    def validate_parameters(self) -> bool:        
        self._cmd_instance = lc_cmds.RemoteNameRequest(
                bd_addr=self.bd_addr.text().strip(),
                page_scan_repetition_mode=self.page_scan_repetition.currentData(),
                clock_offset=self.clock_offset.value())
    
# register the UI classes with the command handler
register_command_ui(InquiryCommandUI)
register_command_ui(CreateConnectionCommandUI)
register_command_ui(AcceptConnectionCommandUI)
register_command_ui(DisconnectCommandUI)
register_command_ui(RejectConnectionCommandUI)
register_command_ui(ChangeConnectionPacketTypeCommandUI)
register_command_ui(RemoteNameRequestCommandUI)

