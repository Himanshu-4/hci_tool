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
    
    _instance = None
    _destroy_window_handler = None
    
    @classmethod
    def is_inited(cls):
        return cls._instance is not None
    
    @classmethod
    def is_open(cls):
        """Check if the HCI Control window is open"""
        return cls._instance is not None and hasattr(cls._instance, 'main_ui') and cls._instance.main_ui.sub_window.isVisible()
    
    @classmethod
    def create_instance(cls, main_wind : QMainWindow):
        """Create a new instance of HCIControl if it doesn't exist"""
        if cls._instance is None:
            cls._instance = cls(main_wind)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """Return the singleton instance of HCIControl"""
        return cls._instance
    
    def __init__(self, main_window : Optional[QMainWindow]): 
        """Initialize the HCI Control with reference to the main window"""
        self.main_window = main_window
        
        # Initialize event handler
        self.event_handler = HCIEventHandler(main_window.mdi_area)
        
        # Create the main UI
        self.main_ui = HciMainUI.create_instance(main_window)
        
        # Connect signal for disconnect
        if hasattr(self.main_ui.sub_window, 'destroyed'):
            self.main_ui.sub_window.destroyed.connect(self._on_main_ui_closed)
    
    def _on_main_ui_closed(self):
        """Handle closing of the main UI"""
        if self.__class__._destroy_window_handler:
            self.__class__._destroy_window_handler()
        HCIControlUI._instance = None
    
    def register_destroy(self, handler : Optional[callable]):
        """ create a property function that assigned in different methods
        and can be called here above """
        self.__class__._destroy_window_handler = handler
        
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