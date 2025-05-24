from PyQt5.QtWidgets import QMdiArea
import struct
from typing import Optional


# Import event UI modules
from .evt.link_control.link_control_evtui import HCIEventManager as LinkControlEventManager

class HCIEventHandler:
    """
    Handler for HCI events - processes raw HCI packets and routes them to the appropriate
    event UI manager.
    """
    
    def __init__(self, mdi_area):
        """Initialize the event handler with an MDI area to display event UIs."""
        self.mdi_area = mdi_area
        
        # Initialize event managers for different HCI event categories
        self.link_control_manager = LinkControlEventManager(mdi_area)
        
        # Mapping of event codes to the appropriate manager
        # Each manager handles a specific category of events
        self.event_managers = {
            # Link Control events (0x01 - 0x07, 0x22)
            0x01: self.link_control_manager,  # Inquiry Complete
            0x02: self.link_control_manager,  # Inquiry Result
            0x03: self.link_control_manager,  # Connection Complete
            0x04: self.link_control_manager,  # Connection Request
            0x05: self.link_control_manager,  # Disconnection Complete
            0x07: self.link_control_manager,  # Remote Name Request Complete
            0x22: self.link_control_manager,  # Inquiry Result with RSSI
            
            # Add more event codes and managers here as needed
            # For example:
            # Link Policy events (0x08 - 0x0B)
            # Controller & Baseband events (0x0C - 0x16)
            # etc.
        }
    
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
    
    
    