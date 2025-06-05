from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QGroupBox, QSplitter
)

from typing import Optional

from PyQt5.QtGui import QTextCursor, QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal

from .hci_main_ui import HciMainUI
from transports.transport import Transport


class HCIControlUI:
    """
    Main HCI Control class - integrates command UI and event handling.
    """
    
    def __init__(self, main_window : Optional[QMainWindow],  transport : Transport, title : Optional[str] = "HCIControlUI"): 
        """Initialize the HCI Control with reference to the main window"""
        self.main_window = main_window
        self._is_destroyed = False
        
        # Create the main UI
        self.main_ui = HciMainUI(main_window, title=title, transport=transport)
        # register destroy method        
        self.main_ui.register_destroy(lambda: self._on_main_ui_closed())

    def __del__(self):
        """Destructor to clean up the instance"""
        if not self._is_destroyed:
            self.cleanup()

    def cleanup(self):
        """Explicit cleanup method"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        print("HCIControlUI instance deleted")
        
        if hasattr(self, 'main_ui') and self.main_ui:
            try:
                self.main_ui.cleanup()
            except (RuntimeError, AttributeError):
                # UI already destroyed
                pass
            self.main_ui = None
            
        if hasattr(self, 'event_handler'):
            self.event_handler = None
     
    @property
    def transport(self) -> Optional[Transport]:
        """Get the transport instance"""
        return self.main_ui.transport if self.main_ui else None
           
    def show_window(self):
        """Show the main UI window"""
        if self.main_ui and hasattr(self.main_ui, 'sub_window'):
            # the order is important here
            self.main_ui.sub_window.show()
            self.main_ui.sub_window.raise_()
            self.main_ui.sub_window.activateWindow()
            
    def hide_window(self):
        """Hide the main UI window"""
        if self.main_ui and hasattr(self.main_ui, 'sub_window'):
            self.main_ui.sub_window.hide()
    
    def is_open(self) -> bool:
        """Check if the main UI window is open"""
        return self.main_ui is not None and hasattr(self.main_ui, 'sub_window') and self.main_ui.sub_window.isVisible()
    
    def is_destroyed(self) -> bool:
        """Check if the main UI instance is destroyed"""
        return self._is_destroyed
    
    def _on_main_ui_closed(self):
        """Handle closing of the main UI"""
        if self._is_destroyed:
            return
            
        print("HCIControlUI closed")
        if hasattr(self, '_destroy_window_handler') and self._destroy_window_handler:
            try:
                self._destroy_window_handler()
            except Exception:
                pass  # Ignore errors in handler
        # Clean up the instance
        self.cleanup()

    
    def register_destroy(self, handler : Optional[callable]):
        """ create a property function that assigned in different methods
        and can be called here above """
        self._destroy_window_handler = handler
        
    def process_hci_event(self, event_data):
        """Process an incoming HCI event packet"""
        if not self._is_destroyed and hasattr(self, 'event_handler') and self.event_handler:
            self.event_handler.process_hci_packet(event_data)
    
    def simulate_event(self, event_code, event_data):
        """Simulate an HCI event for testing purposes"""
        if not self._is_destroyed and hasattr(self, 'event_handler') and self.event_handler:
            self.event_handler.simulate_event(event_code, event_data)
