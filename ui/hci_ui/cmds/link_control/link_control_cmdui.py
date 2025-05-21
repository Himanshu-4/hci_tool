from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QComboBox,
    QSpinBox, QLabel, QPushButton, QGridLayout, QGroupBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt
import struct

from ...hci_base_ui import HciCommandUI

from hci.cmd.cmd_opcodes import create_opcode, OGF, LinkControlOCF
from .. import register_command_ui



class InquiryCommandUI(HciCommandUI):
    """UI for HCI Inquiry command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.INQUIRY)
    NAME = "Inquiry Command"
    def __init__(self):
        super().__init__("HCI Inquiry Command")
        
    def add_command_ui(self):
        """Add Inquiry command specific UI components"""
        super().add_command_ui()
        
        # LAP (Lower Address Part)
        row = 0
        self.lap_field = QLineEdit("33:8B:9E")  # Default General/Unlimited Inquiry Access Code
        self.lap_field.setToolTip("Lower Address Part (LAP) of the General Inquiry Access Code (GIAC)")
        self.add_parameter(row, "LAP (Inquiry Access Code):", self.lap_field)
        
        # Inquiry Length
        row += 1
        self.inquiry_length = QSpinBox()
        self.inquiry_length.setRange(1, 0xFF)
        self.inquiry_length.setValue(10)  # Default value (10 * 1.28s = 12.8s)
        self.inquiry_length.setToolTip("Inquiry Length (N * 1.28 seconds)")
        self.add_parameter(row, "Inquiry Length:", self.inquiry_length)
        
        # Num Responses
        row += 1
        self.num_responses = QSpinBox()
        self.num_responses.setRange(0, 0xFF)
        self.num_responses.setValue(0)  # 0 = unlimited responses
        self.num_responses.setToolTip("Maximum number of responses (0 = unlimited)")
        self.add_parameter(row, "Num Responses:", self.num_responses)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Inquiry command"""
        lap_str = self.lap_field.text().replace(':', '')
        lap = int(lap_str, 16) & 0x00FFFFFF  # Extract 24-bit LAP value
        
        inquiry_length = self.inquiry_length.value()
        num_responses = self.num_responses.value()
        
        # Create command parameters
        cmd_params = struct.pack("<LBB", lap, inquiry_length, num_responses)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_INQUIRY, cmd_params)


class CreateConnectionCommandUI(HciCommandUI):
    """UI for HCI Create Connection command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CREATE_CONNECTION)
    NAME = "Create Connection Command"
    def __init__(self):
        super().__init__("HCI Create Connection Command")
        
    def add_command_ui(self):
        """Add Create Connection command specific UI components"""
        super().add_command_ui()
        
        # BD_ADDR
        row = 0
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to connect to")
        self.add_parameter(row, "BD_ADDR:", self.bd_addr)
        
        # Packet Type
        row += 1
        self.packet_type = QSpinBox()
        self.packet_type.setRange(0, 0xFFFF)
        self.packet_type.setValue(0xCC18)  # Default: DM1, DH1, DM3, DH3, DM5, DH5
        self.packet_type.setToolTip("Packet types allowed for this connection")
        self.add_parameter(row, "Packet Type:", self.packet_type)
        
        # Page Scan Repetition Mode
        row += 1
        self.page_scan_repetition = QComboBox()
        self.page_scan_repetition.addItem("R0", 0)
        self.page_scan_repetition.addItem("R1", 1)
        self.page_scan_repetition.addItem("R2", 2)
        self.add_parameter(row, "Page Scan Repetition Mode:", self.page_scan_repetition)
        
        # Clock Offset
        row += 1
        self.clock_offset = QSpinBox()
        self.clock_offset.setRange(0, 0xFFFF)
        self.clock_offset.setValue(0)
        self.add_parameter(row, "Clock Offset:", self.clock_offset)
        
        # Allow Role Switch
        row += 1
        self.allow_role_switch = QComboBox()
        self.allow_role_switch.addItem("Don't Allow (Master)", 0)
        self.allow_role_switch.addItem("Allow (Master or Slave)", 1)
        self.add_parameter(row, "Allow Role Switch:", self.allow_role_switch)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Create Connection command"""
        # Get BD_ADDR
        bd_addr_bytes = bd_addr_str_to_bytes(self.bd_addr.text())
        
        # Get other parameters
        packet_type = self.packet_type.value()
        page_scan_repetition = self.page_scan_repetition.currentData()
        reserved = 0  # Reserved
        clock_offset = self.clock_offset.value()
        allow_role_switch = self.allow_role_switch.currentData()
        
        # Create command parameters
        cmd_params = bd_addr_bytes + struct.pack("<HBBBHB", 
                                                packet_type,
                                                page_scan_repetition,
                                                reserved,
                                                reserved,
                                                clock_offset,
                                                allow_role_switch)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_CREATE_CONNECTION, cmd_params)


class AcceptConnectionCommandUI(HciCommandUI):
    """UI for HCI Accept Connection Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.ACCEPT_CONNECTION_REQUEST)
    NAME = "Accept Connection Command"
    def __init__(self):
        super().__init__("HCI Accept Connection Request Command")
        
    def add_command_ui(self):
        """Add Accept Connection Request command specific UI components"""
        super().add_command_ui()
        
        # BD_ADDR
        row = 0
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to accept connection from")
        self.add_parameter(row, "BD_ADDR:", self.bd_addr)
        
        # Role
        row += 1
        self.role = QComboBox()
        self.role.addItem("Master", 0)
        self.role.addItem("Slave", 1)
        self.add_parameter(row, "Role:", self.role)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Accept Connection Request command"""
        # Get BD_ADDR
        bd_addr_bytes = bd_addr_str_to_bytes(self.bd_addr.text())
        
        # Get role
        role = self.role.currentData()
        
        # Create command parameters
        cmd_params = bd_addr_bytes + struct.pack("<B", role)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_ACCEPT_CONNECTION, cmd_params)


class DisconnectCommandUI(HciCommandUI):
    """UI for HCI Disconnect command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.DISCONNECT)
    NAME = "Disconnect Command"
    def __init__(self):
        super().__init__("HCI Disconnect Command")
        
    def add_command_ui(self):
        """Add Disconnect command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
        # Reason
        row += 1
        self.reason = QComboBox()
        self.reason.addItem("Authentication Failure (0x05)", 0x05)
        self.reason.addItem("Remote User Terminated Connection (0x13)", 0x13)
        self.reason.addItem("Remote Device Terminated Connection (0x14)", 0x14)
        self.reason.addItem("Remote Device Terminated Connection - Low Resources (0x15)", 0x15)
        self.reason.addItem("Remote Device Terminated Connection - Power Off (0x16)", 0x16)
        self.reason.addItem("Unsupported Remote Feature (0x1A)", 0x1A)
        self.reason.addItem("Unacceptable Connection Parameters (0x3B)", 0x3B)
        self.add_parameter(row, "Reason:", self.reason)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Disconnect command"""
        connection_handle = self.connection_handle.value()
        reason = self.reason.currentData()
        
        # Create command parameters
        cmd_params = struct.pack("<HB", connection_handle, reason)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_DISCONNECT, cmd_params)



class RejectConnectionCommandUI(HciCommandUI):
    """UI for HCI Reject Connection Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REJECT_CONNECTION_REQUEST)
    NAME = "Reject Connection Command"
    def __init__(self):
        super().__init__("HCI Reject Connection Request Command")
        
    def add_command_ui(self):
        """Add Reject Connection Request command specific UI components"""
        super().add_command_ui()
        
        # BD_ADDR
        row = 0
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to reject connection from")
        self.add_parameter(row, "BD_ADDR:", self.bd_addr)
        
        # Reason
        row += 1
        self.reason = QComboBox()
        self.reason.addItem("Limited Resources (0x0D)", 0x0D)
        self.reason.addItem("Security Reasons (0x0E)", 0x0E)
        self.reason.addItem("Unacceptable BD_ADDR (0x0F)", 0x0F)
        self.add_parameter(row, "Reason:", self.reason)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Reject Connection Request command"""
        # Get BD_ADDR
        bd_addr_bytes = bd_addr_str_to_bytes(self.bd_addr.text())
        
        # Get reason
        reason = self.reason.currentData()
        
        # Create command parameters
        cmd_params = bd_addr_bytes + struct.pack("<B", reason)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_REJECT_CONNECTION, cmd_params)


class ChangeConnectionPacketTypeCommandUI(HciCommandUI):
    """UI for HCI Change Connection Packet Type command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CHANGE_CONNECTION_PACKET_TYPE)
    NAME = "Change Connection Packet Type Command"
    def __init__(self):
        super().__init__("HCI Change Connection Packet Type Command")
        
    def add_command_ui(self):
        """Add Change Connection Packet Type command specific UI components"""
        super().add_command_ui()
        
        # Connection Handle
        row = 0
        self.connection_handle = QSpinBox()
        self.connection_handle.setRange(0, 0x0EFF)  # Valid connection handles
        self.connection_handle.setValue(0)
        self.add_parameter(row, "Connection Handle:", self.connection_handle)
        
        # Packet Type
        row += 1
        self.packet_type = QSpinBox()
        self.packet_type.setRange(0, 0xFFFF)
        self.packet_type.setValue(0xCC18)  # Default: DM1, DH1, DM3, DH3, DM5, DH5
        self.packet_type.setToolTip("Packet types allowed for this connection")
        self.add_parameter(row, "Packet Type:", self.packet_type)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Change Connection Packet Type command"""
        connection_handle = self.connection_handle.value()
        packet_type = self.packet_type.value()
        
        # Create command parameters
        cmd_params = struct.pack("<HH", connection_handle, packet_type)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_CHANGE_CONNECTION_PACKET_TYPE, cmd_params)


class RemoteNameRequestCommandUI(HciCommandUI):
    """UI for HCI Remote Name Request command"""
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REMOTE_NAME_REQUEST)
    NAME = "Remote Name Request Command"
    def __init__(self):
        super().__init__("HCI Remote Name Request Command")
        
    def add_command_ui(self):
        """Add Remote Name Request command specific UI components"""
        super().add_command_ui()
        
        # BD_ADDR
        row = 0
        self.bd_addr = QLineEdit("00:11:22:33:44:55")
        self.bd_addr.setToolTip("Bluetooth Device Address of the device to request name from")
        self.add_parameter(row, "BD_ADDR:", self.bd_addr)
        
        # Page Scan Repetition Mode
        row += 1
        self.page_scan_repetition = QComboBox()
        self.page_scan_repetition.addItem("R0", 0)
        self.page_scan_repetition.addItem("R1", 1)
        self.page_scan_repetition.addItem("R2", 2)
        self.add_parameter(row, "Page Scan Repetition Mode:", self.page_scan_repetition)
        
        # Clock Offset
        row += 1
        self.clock_offset = QSpinBox()
        self.clock_offset.setRange(0, 0xFFFF)
        self.clock_offset.setValue(0)
        self.add_parameter(row, "Clock Offset:", self.clock_offset)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs for the Remote Name Request command"""
        # Get BD_ADDR
        bd_addr_bytes = bd_addr_str_to_bytes(self.bd_addr.text())
        
        # Get other parameters
        page_scan_repetition = self.page_scan_repetition.currentData()
        reserved = 0  # Reserved
        clock_offset = self.clock_offset.value()
        
        # Create command parameters
        cmd_params = bd_addr_bytes + struct.pack("<BBBH", 
                                                page_scan_repetition,
                                                reserved,
                                                reserved,
                                                clock_offset)
        
        # Create and return the complete command packet
        return create_hci_command_packet(HCI_OPCODE_REMOTE_NAME_REQUEST, cmd_params)
    
    
# register the UI classes with the command handler
register_command_ui(InquiryCommandUI)
register_command_ui(CreateConnectionCommandUI)
register_command_ui(AcceptConnectionCommandUI)
register_command_ui(DisconnectCommandUI)
register_command_ui(RejectConnectionCommandUI)
register_command_ui(ChangeConnectionPacketTypeCommandUI)
register_command_ui(RemoteNameRequestCommandUI)
