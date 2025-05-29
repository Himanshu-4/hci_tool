
"""
    HCI Event Factory
    This module provides a factory for creating HCI event windows.
    It manages the creation, positioning, and lifecycle of event windows.
    Each event window is associated with a specific HCI event type.
    The factory ensures that event windows are opened in a consistent manner,
    and provides functionality to close all event windows when needed.
    The event windows are created based on the event code and are positioned
    relative to the main window. The factory also keeps track of all open event
    windows, allowing for easy management and cleanup.
    The event windows are created using the appropriate classes from the
    hci_ui.evts module, which contains the definitions for each event type.
    The event types include:
    - Link Control events
    - Link Policy events
    - Controller and Baseband events
    - Information events
    - Status events
    - Testing events
    - LE events
    - Vendor-specific events
    The event windows are displayed in a cascading manner, with each new window
    offset from the previous one. This provides a clear and organized layout for
    the user to interact with multiple event windows simultaneously.
    The factory also provides a method to close all open event windows, ensuring
    that resources are properly released when the user is done with the HCI events.
"""
import traceback
import weakref

from PyQt5.QtWidgets import (QMdiSubWindow)

# import the hci event for processing
from hci.evt import get_event_class
from hci.evt import hci_evt_parse_from_bytes, HciEvtBasePacket
from hci.evt.event_types import EventCategory, EVENT_CODE_TO_CATEGORY

from .evts import get_event_ui_class
from .evts import HCIEvtUI

from transports.transport import Transport
from typing import ClassVar, Optional, Dict, Type


class HCIEventFactory:
    """
    Handler for HCI events - processes raw HCI packets and routes them to the appropriate
    event UI manager.
    """
    def __init__(self, title : str, parent_window : QMdiSubWindow, transport : Optional[Transport] = None):
        self.title = title
        self.transport = transport
        self.parent = weakref.ref(parent_window) if parent_window else None
        self._is_destroyed = False
        # create a dictionary to track event windows and structure as {event_code: HCIEvtUI}
        self.event_windows : dict[int, HCIEvtUI] = {}
        # add the process_hci_evt_packet method to the transport's event handler
        if self.transport:
            transport.add_callback('read', lambda data: self.process_hci_evt_packet(data))
            
    def __del__(self):  
        """Destructor to ensure all event windows are closed"""
        if not self._is_destroyed:
            self.cleanup()
        
    def cleanup(self):
        """Explicit cleanup method to be called before destruction"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        self.close_all_event_windows()
        self.remove_from_parent()
    
    def get_parent(self):
        """Safely get the parent window"""
        # parent = self.parent
        # # Check if the parent still exists and hasn't been deleted
        # if parent is None:
        #     return None
        # try:
        #     # Try to access a property to see if the object is still valid
        #     _ = parent.title()
        #     return parent
        # except RuntimeError:
        #     # Object has been deleted by Qt
        #     return None
        return self.parent if self.parent and not self._is_destroyed else None
    
    def __repr__(self):
        return f"<HCIEventFactory parent={self.parent}, windows={len(self.event_windows)}>"
        
    def __str__(self):
        return f"HCIEventFactory(parent={self.parent}, windows={len(self.event_windows)})"
        
    def __len__(self):
        """Return the number of event windows currently managed"""
        return len(self.event_windows)
        
    def __contains__(self, event_code: int) -> bool:
        """Check if an event window with the given event code exists"""
        return event_code in self.event_windows
        
    def __getitem__(self, event_code: int) -> Optional[HCIEvtUI]:
        """Get an event window by its event code"""
        return self.event_windows.get(event_code, None)
    
    def create_event_window(self, event_code : int) -> Optional[HCIEvtUI]:
        """Create an event window based on the event code"""
        if self._is_destroyed:
            return None
            
        event_window = None
        parent = self.get_parent()
        evt_type = get_event_ui_class(event_code)
        
        if evt_type is not None:
            if event_code in self.event_windows:
                # Window already exists, just show and raise it
                existing_window = self.event_windows[event_code]
                existing_window.show()
                existing_window.raise_()
                existing_window.activateWindow()
                return existing_window
            
            # Add to parent's tracking system
            event_window = evt_type(self.title, parent, self.transport)
            event_window.window_closing.connect(lambda : self.close_event_window(event_code))
            # Store in our local tracking
            self.event_windows[event_code] = event_window
            
            # Position the window relative to main window
            self.position_window(event_window)
            
            # Show the window
            event_window.show()
            event_window.raise_()
            event_window.activateWindow()
            
        return event_window
    
    def position_window(self, window : HCIEvtUI):
        """Position the window relative to the main window"""
        parent = self.get_parent()
        if parent:
            try:
                # Get main window geometry
                main_rect = parent.geometry()
                
                # Calculate offset position
                offset_x = 50 + (len(self.event_windows) * 30)
                offset_y = 50 + (len(self.event_windows) * 30)
                
                # Set new position
                new_x = main_rect.x() + offset_x
                new_y = main_rect.y() + offset_y
                
                window.move(new_x, new_y)
            except RuntimeError:
                # Parent window has been deleted, skip positioning
                pass
    
    
    def get_event_window_by_code(self, event_code: int) -> Optional[HCIEvtUI]:
        """Get an event window by its event code"""
        return self.event_windows.get(event_code, None)
    
    def get_event_window_by_name(self, window_name: str) -> Optional[HCIEvtUI]:
        """Get an event window by its name"""
        for window in self.event_windows.values():
            if window.NAME == window_name:
                return window
        return None
    
    def get_event_window_by_type(self, evt_type: Type[HCIEvtUI]) -> Optional[HCIEvtUI]:
        """Get an event window by its type"""
        for window in self.event_windows.values():
            if isinstance(window, evt_type):
                return window
        return None      

    def add_to_parent(self):
        """Add this factory to the parent window's event tracking"""
        parent = self.get_parent()
        if parent and hasattr(parent, 'add_event_factory'):
            try:
                parent.add_event_factory(self)
            except RuntimeError:
                # Parent has been deleted
                pass
            
    def remove_from_parent(self):
        """Remove this factory from the parent window's event tracking"""
        parent = self.get_parent()
        if parent and hasattr(parent, 'remove_event_factory'):
            try:
                parent.remove_event_factory(self)
            except RuntimeError:
                # Parent has been deleted, nothing to do
                pass
    
    
    def get_event_window(self, event_code : int) -> Optional[HCIEvtUI]:
        """Get an event window by its event code"""
        return self.event_windows.get(event_code, None)

    def get_all_event_windows(self) -> list[Optional[HCIEvtUI]]:
        """Get all event windows"""
        return list(self.event_windows.values())
    
    def close_event_window(self, event_code : int):
        """Close a specific event window by its event code"""
        if event_code in self.event_windows:
            window = self.event_windows[event_code]
            try:
                window.close()
            except RuntimeError:
                # Window already deleted
                pass
            del self.event_windows[event_code]
    
    def close_all_event_windows(self):
        """Close all open event windows"""
        for event_code in list(self.event_windows.keys()):
            self.close_event_window(event_code)
        self.event_windows.clear()

    def process_hci_evt_packet(self, packet_data : Optional[bytes]):
        """
        Process an HCI event packet and route it to the appropriate event manager.
        
        Args:
            packet_data: Raw HCI packet data as bytes or bytearray
        
        Returns:
            True if the packet was successfully processed, False otherwise
        """
        try:
            cmd_class = hci_evt_parse_from_bytes(packet_data)
            print(str(cmd_class.from_bytes(packet_data)))
        except Exception as e:
            print(f"Error processing event 0x{e}")

    def default_base_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default base event handler
        This method handles base events based on the event code and event data.
        Args:
            event_code (int): The event code of the base event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        raise NotImplementedError(
            "Default base event handler not implemented. "
            "Please implement this method in the subclass."
        )

    def default_link_control_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default link control event handler
        This method handles link control events based on the event code and event data.
        Args:
            event_code (int): The event code of the link control event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)

    def default_link_policy_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default link policy event handler
        This method handles link policy events based on the event code and event data.
        Args:
            event_code (int): The event code of the link policy event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)

    def default_controller_baseband_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default controller and baseband event handler
        This method handles controller and baseband events based on the event code and event data.
        Args:
            event_code (int): The event code of the controller and baseband event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)
    
    def default_le_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default LE event handler
        This method handles LE events based on the event code and event data.
        Args:
            event_code (int): The event code of the LE event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)
    
    def default_info_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default information event handler
        This method handles information events based on the event code and event data.
        Args:
            event_code (int): The event code of the information event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)
    
    def default_status_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default status event handler
        This method handles status events based on the event code and event data.
        Args:
            event_code (int): The event code of the status event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)
    
    def default_testing_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default testing event handler
        This method handles testing events based on the event code and event data.
        Args:
            event_code (int): The event code of the testing event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)
    
    def default_vendor_event_handler(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """Default vendor event handler
        This method handles vendor-specific events based on the event code and event data.
        Args:
            event_code (int): The event code of the vendor event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        return self.default_base_event_handler(event_code, event_data)

    def default_base_event_handler(self, event_code : int, event_data: Optional[bytearray] = None) -> bool:
        """Default event handler for HCI events
        This method handles an event based on the event code and event data.
        It retrieves the event class from the hci.evt module and processes it.
        Args:
            event_code (int): The event code of the event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        if event_data is None:
            event_data = bytearray()
        
        # Handle the event based on the event code
        # if event is registered event in hci.evt 
        try:
            # For LE Meta Events, we need to extract the sub-event code
            sub_event_code = None
            if event_code == HciEventCode.LE_META_EVENT and len(event_data) > 0:
                sub_event_code = event_data[0]
            
            event_class = get_event_class(event_code, sub_event_code)
            if event_class is None:
                print(f"No event class found for event code 0x{event_code:02X}")
                return False
        
            # Create an instance of the event class
            event_instance = event_class.from_bytes(event_data)
            
            # Process the event (could be logged, displayed, etc.)
            print(f"Processed event: {event_instance.NAME}")
            return True
            
        except Exception as e:
            print(f"Error handling event 0x{event_code:02X}: {e}")
            return False

    def handle_event(self, event_code: int, event_data: Optional[bytearray] = None) -> bool:
        """ Handle an event by selecting the appropriate handler based on event category
        Args:
            event_code (int): The event code of the event to handle.
            event_data (Optional[bytearray]): Additional data for the event.
        Returns:
            bool: True if the event was handled successfully, False otherwise.
        """
        # Get the event category from the event code
        event_category = EVENT_CODE_TO_CATEGORY.get(event_code, None)
        
        # Handle the event based on the category
        if event_category == EventCategory.LINK_CONTROL:
            return self.default_link_control_event_handler(event_code, event_data)
        elif event_category == EventCategory.LINK_POLICY:
            return self.default_link_policy_event_handler(event_code, event_data)
        elif event_category == EventCategory.CONTROLLER_BASEBAND:
            return self.default_controller_baseband_event_handler(event_code, event_data)
        elif event_category == EventCategory.LE:
            return self.default_le_event_handler(event_code, event_data)
        elif event_category == EventCategory.INFORMATION:
            return self.default_info_event_handler(event_code, event_data)
        elif event_category == EventCategory.STATUS:
            return self.default_status_event_handler(event_code, event_data)
        elif event_category == EventCategory.TESTING:
            return self.default_testing_event_handler(event_code, event_data)
        elif event_category == EventCategory.VENDOR_SPECIFIC:
            return self.default_vendor_event_handler(event_code, event_data)
        else:
            # Unknown category, use default handler
            return self.default_base_event_handler(event_code, event_data)
    
    
    