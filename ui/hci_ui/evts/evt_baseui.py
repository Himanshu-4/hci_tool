from transports.transport import Transport
from PyQt5.QtWidgets import QGroupBox, QFormLayout
from abc import abstractmethod
from typing import  Optional,ClassVar, List

from ..hci_base_ui import HCIEvtBaseUI

# Import event UI modules

class HCIEvtUI(HCIEvtBaseUI):
    """
    Handler for HCI events - processes raw HCI packets and routes them to the appropriate
    event UI manager.
    """
    OPCODE: ClassVar[int]  # The command opcde for the successful event or completion (2 bytes)
    
    EVENT_CODE : ClassVar[int]  # The event code (1 byte)
    SUB_EVENT_CODE: Optional[int] = None  # Sub-event code (if applicable, 1 byte)
    NAME: ClassVar[str]    # Human-readable name of the event
    def __init__(self, title, parent=None, transport : Optional[Transport] = None):
        """Initialize the event handler with an MDI area to display event UIs."""
        super().__init__(title, parent, transport)
        self.title = title
        self.transport = transport
      
    def setup_ui(self):
        """Initialize the Event UI"""
        super().setup_ui()
        
        self.param_group = QGroupBox("Event Parameters")
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
        
    def process_hci_packet(self, packet_data : Optional[bytearray]):
        """
        Process an HCI event packet and route it to the appropriate event manager.
        
        Args:
            packet_data: Raw HCI packet data as bytes or bytearray
        
        Returns:
            True if the packet was successfully processed, False otherwise
        """
        if not packet_data or len(packet_data) < 3:
            print("Invalid HCI packet: too short")
            return False
        
        # Check if this is an HCI event packet (type = 0x04)
        if packet_data[0] != 0x04:
            print(f"Not an HCI event packet (type = 0x{packet_data[0]:02X})")
            return False
        
        # Extract event code and parameter length
        event_code = packet_data[1]
        param_length = packet_data[2]
        
        # Check if the packet length is correct
        if len(packet_data) < param_length + 3:
            print("Invalid HCI packet: data length mismatch")
            return False
        
        # Extract event parameters
        event_data = packet_data[3:3+param_length]
        
        print(f"Processing HCI event: 0x{event_code:02X}, length: {param_length}")
        
        # Route the event to the appropriate manager
        if event_code in self.event_managers:
            manager = self.event_managers[event_code]
            manager.process_event(event_code, event_data)
            return True
        else:
            print(f"No handler for event code 0x{event_code:02X}")
            return False
    
    def simulate_event(self, event_code, event_data):
        """
        Simulate an HCI event for testing purposes.
        
        Args:
            event_code: The HCI event code
            event_data: The event parameters as bytes or bytearray
        
        Returns:
            True if the event was successfully processed, False otherwise
        """
        # Create a full HCI event packet
        packet_data = bytearray([0x04, event_code, len(event_data)]) + event_data
        return self.process_hci_packet(packet_data)