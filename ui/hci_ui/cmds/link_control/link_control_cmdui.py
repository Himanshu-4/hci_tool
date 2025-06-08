from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QSpinBox, QLabel, QPushButton, QGridLayout, QGroupBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt

from typing import Optional
from transports.transport import Transport

from hci.cmd.cmd_opcodes import create_opcode, OGF, LinkControlOCF
import hci.cmd.link_controller as lc_cmds
from hci import bd_addr_str_to_bytes

from ..cmd_baseui import HCICmdUI
from .. import register_command_ui



class InquiryCommandUI(HCICmdUI):
    """UI for HCI Inquiry command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.INQUIRY)
    NAME = "Inquiry Command"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        
        inquiry_length = self.inquiry_length.value()
        num_responses = self.num_responses.value()
        try:
            lc_cmds.Inquiry(lap=lap, inquiry_length=inquiry_length,
                    num_responses=num_responses)._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True
    
    def get_data_bytes(self) -> bytes:
        """ get the parameter values from the UI and create a bytearray for the command"""
        lap_str = self.lap_field.text().replace(':', '')
        lap = int(lap_str, 16) & 0x00FFFFFF  # Extract 24-bit LAP value
        
        inquiry_length = self.inquiry_length.value()
        num_responses = self.num_responses.value()
        
        return lc_cmds.Inquiry(
            lap=lap,
            inquiry_length=inquiry_length,
            num_responses=num_responses
        ).to_bytes()


class CreateConnectionCommandUI(HCICmdUI):
    """UI for HCI Create Connection command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CREATE_CONNECTION)
    NAME = "Create Connection Command"
    
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        bd_addr = self.bd_addr.text().strip()
        if not bd_addr or len(bd_addr) != 17 or not all(c in "0123456789ABCDEF:" for c in bd_addr.upper()):
            self.log_error("Invalid BD_ADDR format. Use XX:XX:XX:XX:XX:XX")
            return False
        
        packet_type = self.packet_type.value()
        if packet_type < 0 or packet_type > 0xFFFF:
            self.log_error("Packet Type must be between 0 and 0xFFFF")
            return False
        
        page_scan_repetition = self.page_scan_repetition.currentData()
        clock_offset = self.clock_offset.value()
        
        try:
            lc_cmds.CreateConnection(
                bd_addr=bd_addr_str_to_bytes(bd_addr),
                packet_type=packet_type,
                page_scan_repetition=page_scan_repetition,
                clock_offset=clock_offset,
                allow_role_switch=self.allow_role_switch.currentData()
            )._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True

    def get_data_bytes(self) -> bytes:
        """Get the parameter values from the UI and create a bytearray for the command"""
        bd_addr = self.bd_addr.text().strip()
        packet_type = self.packet_type.value()
        page_scan_repetition = self.page_scan_repetition.currentData()
        clock_offset = self.clock_offset.value()
        allow_role_switch = self.allow_role_switch.currentData()

        return lc_cmds.CreateConnection(
            bd_addr=bd_addr_str_to_bytes(bd_addr),
            packet_type=packet_type,
            page_scan_repetition=page_scan_repetition,
            clock_offset=clock_offset,
            allow_role_switch=allow_role_switch
        ).to_bytes()
        
class AcceptConnectionCommandUI(HCICmdUI):
    """UI for HCI Accept Connection Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.ACCEPT_CONNECTION_REQUEST)
    NAME = "Accept Connection Command"
    
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        bd_addr = self.bd_addr.text().strip()
        if not bd_addr or len(bd_addr) != 17 or not all(c in "0123456789ABCDEF:" for c in bd_addr.upper()):
            self.log_error("Invalid BD_ADDR format. Use XX:XX:XX:XX:XX:XX")
            return False
        
        role = self.role.currentData()
        try:
            lc_cmds.AcceptConnectionRequest(
                bd_addr=bd_addr_str_to_bytes(bd_addr),
                role=role
            )._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True

    def get_data_bytes(self) -> bytes:
        """Get the parameter values from the UI and create a bytearray for the command"""
        bd_addr = self.bd_addr.text().strip()
        role = self.role.currentData()

        return lc_cmds.AcceptConnectionRequest(
            bd_addr=bd_addr_str_to_bytes(bd_addr),
            role=role
        ).to_bytes()
        

class DisconnectCommandUI(HCICmdUI):
    """UI for HCI Disconnect command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.DISCONNECT)
    NAME = "Disconnect Command"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        connection_handle = self.connection_handle.value()
        if connection_handle < 0 or connection_handle > 0x0EFF:
            self.log_error("Connection Handle must be between 0 and 0x0EFF")
            return False
        
        reason = self.reason.currentData()
        try:
            lc_cmds.Disconnect(
                connection_handle=connection_handle,
                reason=reason
            )._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True
    
    def get_data_bytes(self) -> bytes:
        """Get the parameter values from the UI and create a bytearray for the command"""
        connection_handle = self.connection_handle.value()
        reason = self.reason.currentData()

        return lc_cmds.Disconnect(
            connection_handle=connection_handle,
            reason=reason
        ).to_bytes()



class RejectConnectionCommandUI(HCICmdUI):
    """UI for HCI Reject Connection Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REJECT_CONNECTION_REQUEST)
    NAME = "Reject Connection Command"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        bd_addr = self.bd_addr.text().strip()
        if not bd_addr or len(bd_addr) != 17 or not all(c in "0123456789ABCDEF:" for c in bd_addr.upper()):
            self.log_error("Invalid BD_ADDR format. Use XX:XX:XX:XX:XX:XX")
            return False
        
        reason = self.reason.currentData()
        try:
            lc_cmds.RejectConnectionRequest(
                bd_addr=bd_addr_str_to_bytes(bd_addr),
                reason=reason
            )._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True
    
    def get_data_bytes(self) -> bytes:
        """Get the parameter values from the UI and create a bytearray for the command"""
        bd_addr = self.bd_addr.text().strip()
        reason = self.reason.currentData()

        return lc_cmds.RejectConnectionRequest(
            bd_addr=bd_addr_str_to_bytes(bd_addr),
            reason=reason
        ).to_bytes()

class ChangeConnectionPacketTypeCommandUI(HCICmdUI):
    """UI for HCI Change Connection Packet Type command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CHANGE_CONNECTION_PACKET_TYPE)
    NAME = "Change Connection Packet Type Command"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        connection_handle = self.connection_handle.value()
        if connection_handle < 0 or connection_handle > 0x0EFF:
            self.log_error("Connection Handle must be between 0 and 0x0EFF")
            return False
        
        packet_type = self.packet_type.value()
        if packet_type < 0 or packet_type > 0xFFFF:
            self.log_error("Packet Type must be between 0 and 0xFFFF")
            return False
        
        try:
            lc_cmds.ChangeConnectionPacketType(
                connection_handle=connection_handle,
                packet_type=packet_type
            )._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True
    
    def get_data_bytes(self) -> bytes:
        """Get the parameter values from the UI and create a bytearray for the command"""
        connection_handle = self.connection_handle.value()
        packet_type = self.packet_type.value()

        return lc_cmds.ChangeConnectionPacketType(
            connection_handle=connection_handle,
            packet_type=packet_type
        ).to_bytes()
        

class RemoteNameRequestCommandUI(HCICmdUI):
    """UI for HCI Remote Name Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REMOTE_NAME_REQUEST)
    NAME = "Remote Name Request Command"
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        super().__init__(title, parent, transport)
        
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
        bd_addr = self.bd_addr.text().strip()
        if not bd_addr or len(bd_addr) != 17 or not all(c in "0123456789ABCDEF:" for c in bd_addr.upper()):
            self.log_error("Invalid BD_ADDR format. Use XX:XX:XX:XX:XX:XX")
            return False
        
        page_scan_repetition = self.page_scan_repetition.currentData()
        clock_offset = self.clock_offset.value()
        
        try:
            lc_cmds.RemoteNameRequest(
                bd_addr=bd_addr_str_to_bytes(bd_addr),
                page_scan_repetition=page_scan_repetition,
                clock_offset=clock_offset
            )._validate_params()
        except Exception as e:
            self.log_error(f"Invalid parameters: {str(e)}")
            return False
        return True
    
    def get_data_bytes(self) -> bytes:
        """Get the parameter values from the UI and create a bytearray for the command"""
        bd_addr = self.bd_addr.text().strip()
        page_scan_repetition = self.page_scan_repetition.currentData()
        clock_offset = self.clock_offset.value()

        return lc_cmds.RemoteNameRequest(
            bd_addr=bd_addr_str_to_bytes(bd_addr),
            page_scan_repetition=page_scan_repetition,
            clock_offset=clock_offset
        ).to_bytes()
    
# register the UI classes with the command handler
register_command_ui(InquiryCommandUI)
register_command_ui(CreateConnectionCommandUI)
register_command_ui(AcceptConnectionCommandUI)
register_command_ui(DisconnectCommandUI)
register_command_ui(RejectConnectionCommandUI)
register_command_ui(ChangeConnectionPacketTypeCommandUI)
register_command_ui(RemoteNameRequestCommandUI)

