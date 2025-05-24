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
from .hci_event_handler import HCIEventHandler

class HCIControlUI:
    """
    Main HCI Control class - integrates command UI and event handling.
    """
    
    def __init__(self, main_window : Optional[QMainWindow], name : str = "HCIControlUI"): 
        """Initialize the HCI Control with reference to the main window"""
        self.main_window = main_window
        
        # Create the main UI
        self.main_ui = HciMainUI(main_window, name)
        # register destroy method        
        self.main_ui.register_destroy(lambda: self._on_main_ui_closed())

    def __del__(self):
        """Destructor to clean up the instance"""
        print("HCIControlUI instance deleted")

        
    def _on_main_ui_closed(self):
        """Handle closing of the main UI"""
        print("HCIControlUI closed")
        if self._destroy_window_handler:
            self._destroy_window_handler()
        self.main_ui = None
        self.event_handler = None

    
    def register_destroy(self, handler : Optional[callable]):
        """ create a property function that assigned in different methods
        and can be called here above """
        self._destroy_window_handler = handler
        
    def process_hci_event(self, event_data):
        """Process an incoming HCI event packet"""
        if self.event_handler:
            self.event_handler.process_hci_packet(event_data)
    
    def simulate_event(self, event_code, event_data):
        """Simulate an HCI event for testing purposes"""
        if self.event_handler:
            self.event_handler.simulate_event(event_code, event_data)

# Class for the HCI Control Window interface
class HCIControlWindow(QWidget):
    """User interface for the HCI Control functionality"""
    
    def __init__(self, main_wind=None):
        """Initialize the HCI Control Window"""
        super().__init__()
        
        self.main_wind = main_wind
        self.init_ui()
    
    def init_ui(self):
        """Set up the UI layout and components"""
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header section
        header_layout = QHBoxLayout()
        header_label = QLabel("HCI Control")
        header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)
        main_layout.addLayout(header_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Command selection
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Add connect button
        connect_button = QPushButton("Connect Device")
        connect_button.clicked.connect(self.open_connect_window)
        left_layout.addWidget(connect_button)
        
        # Add commands button
        commands_button = QPushButton("HCI Commands")
        commands_button.clicked.connect(self.open_hci_command_window)
        left_layout.addWidget(commands_button)
        
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)
        
        # Right panel - Log area
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Add log area
        log_group = QGroupBox("HCI Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # Add event simulation section (for testing)
        sim_group = QGroupBox("Event Simulation")
        sim_layout = QGridLayout()
        
        sim_layout.addWidget(QLabel("Event Code (hex):"), 0, 0)
        self.event_code_input = QLineEdit("03")  # Default: Connection Complete
        sim_layout.addWidget(self.event_code_input, 0, 1)
        
        sim_layout.addWidget(QLabel("Event Data (hex):"), 1, 0)
        self.event_data_input = QLineEdit("00 0001 112233445566 01 00")  # Default data for Connection Complete
        sim_layout.addWidget(self.event_data_input, 1, 1)
        
        simulate_button = QPushButton("Simulate Event")
        simulate_button.clicked.connect(self.simulate_event)
        sim_layout.addWidget(simulate_button, 2, 0, 1, 2)
        
        sim_group.setLayout(sim_layout)
        right_layout.addWidget(sim_group)
        
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        
        # Set initial sizes
        splitter.setSizes([200, 400])
        
        main_layout.addWidget(splitter)
        
        # Set the main layout
        self.setLayout(main_layout)
    
    def open_connect_window(self):
        """Open the Connect Window"""
        if not ConnectWindow.is_instance():
            ConnectWindow(self.main_wind)
    
    def open_hci_command_window(self):
        """Open the HCI Command Window"""
        if HCIControl.is_inited():
            if not HCIControl.is_open():
                # Recreate the window if it's not visible
                HCIControl.create_instance(self.main_wind)
        else:
            # Create a new instance
            HCIControl.create_instance(self.main_wind)
    
    def simulate_event(self):
        """Simulate an HCI event for testing"""
        try:
            # Parse event code from hex
            event_code = int(self.event_code_input.text(), 16)
            
            # Parse event data from hex
            hex_data = self.event_data_input.text().replace(" ", "")
            if len(hex_data) % 2 != 0:
                raise ValueError("Hex data must have an even number of characters")
            
            event_data = bytearray.fromhex(hex_data)
            
            # Log the simulation
            self.log_area.append(f"Simulating HCI event 0x{event_code:02X} with data: {event_data.hex()}")
            
            # If HCI Control is initialized, send the event
            if HCIControl.is_inited():
                hci_control = HCIControl.get_instance()
                hci_control.simulate_event(event_code, event_data)
            else:
                self.log_area.append("Error: HCI Control not initialized. Open the HCI Commands window first.")
        
        except ValueError as e:
            self.log_area.append(f"Error parsing input: {str(e)}")
    
    @staticmethod
    def is_instance():
        """Check if ConnectWindow instance exists"""
        return ConnectWindow._instance is not None
    
    
    
"""
HCI SubWindow Module

This module defines an MDI subwindow class that can be used in the HCI tool UI.
It provides a container for HCI-related UI components and handles window management.
"""

from PyQt5.QtWidgets import QMdiSubWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent

class HciSubWindow(QMdiSubWindow):
    """
    A customized MDI subwindow for the HCI tool.
    
    This class provides a standardized container for HCI UI components, with consistent
    window behavior, styling, and lifecycle management.
    """
    
    # Signal emitted when the window is closed
    closed = pyqtSignal(str)  # Emits the window title
    
    def __init__(self, widget: QWidget = None, window_title: str = "", parent=None):
        """
        Initialize the HCI SubWindow.
        
        Args:
            widget: The main widget to display in the subwindow
            window_title: The title for the window
            parent: The parent widget
        """
        super().__init__(parent)
        
        # Save the title for reference
        self.window_title = window_title
        
        # Set window properties
        self.setWindowTitle(window_title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        self.windowIconText(window_title)  # Set window icon text
        
        # Configure the layout if a widget is provided
        if widget:
            self.setWidget(widget)
        
        # Default size
        self.resize(600, 400)
    
    def closeEvent(self, event: QCloseEvent):
        """
        Handle the window close event.
        
        Args:
            event: The close event
        """
        # Emit the closed signal with the window title
        self.closed.emit(self.window_title)
        
        # Call the parent class closeEvent
        super().closeEvent(event)
    
    def maximize(self):
        """
        Maximize the subwindow.
        """
        self.setWindowState(Qt.WindowMaximized)
    
    def restore(self):
        """
        Restore the window to its normal state.
        """
        self.setWindowState(Qt.WindowNoState)
    
    def center_in_parent(self):
        """
        Center the window within its parent MDI area.
        """
        if self.parentWidget():
            parent_rect = self.parentWidget().rect()
            self_rect = self.rect()
            
            x = (parent_rect.width() - self_rect.width()) // 2
            y = (parent_rect.height() - self_rect.height()) // 2
            
            self.move(x, y)
