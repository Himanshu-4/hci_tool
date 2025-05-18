from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QGroupBox, QSplitter
)

from PyQt5.QtGui import QTextCursor, QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal

from hci_ui.hci_main_ui import HciMainUI
from hci_ui.hci_event_handler import HCIEventHandler

class HCIControl:
    """
    Main HCI Control class - integrates command UI and event handling.
    """
    
    _instance = None
    
    @classmethod
    def is_inited(cls):
        return cls._instance is not None
    
    @classmethod
    def is_open(cls):
        """Check if the HCI Control window is open"""
        return cls._instance is not None and hasattr(cls._instance, 'main_ui') and cls._instance.main_ui.sub_window.isVisible()
    
    @classmethod
    def create_instance(cls, main_wind):
        """Create a new instance of HCIControl if it doesn't exist"""
        if cls._instance is None:
            cls._instance = cls(main_wind)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """Return the singleton instance of HCIControl"""
        return cls._instance
    
    def __init__(self, main_window):
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
        HCIControl._instance = None
    
    def process_hci_event(self, event_data):
        """Process an incoming HCI event packet"""
        if self.event_handler:
            self.event_handler.process_hci_packet(event_data)
    
    def simulate_event(self, event_code, event_data):
        """Simulate an HCI event for testing purposes"""
        if self.event_handler:
            self.event_handler.simulate_event(event_code, event_data)


class ConnectWindow(QWidget):
    """A window for connecting to a device."""
    
    _instance = None
    
    def __init__(self, main_wind=None):
        """Initialize the Connect Window"""
        print("[ConnectWindow].__init__")
        if ConnectWindow._instance is not None:
            raise Exception("Only one instance of ConnectWindow is allowed")
        
        # Initialize the base class
        super().__init__()
        
        ConnectWindow._instance = self
        
        # Initialize the main window reference
        self.main_wind = main_wind
        
        # Create the sub-window
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWindowTitle("Connect")
        self.sub_window.setWindowIconText("Connect Window")
        self.sub_window.setWidget(self)
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)
        
        # Set window properties
        self.sub_window.resize(200, 300)
        self.sub_window.setMinimumSize(200, 300)
        self.sub_window.setMaximumSize(200, 300)
        self.sub_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set window flags
        self.sub_window.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        # Connect close signal
        self.sub_window.destroyed.connect(
            lambda _: (setattr(self, "sub_window", None), self._on_subwindow_closed())
        )
        
        # Create the UI layout
        layout = QVBoxLayout()
        
        # Transport type selection
        self.transport_type = QComboBox()
        self.transport_type.addItem("UART")
        self.transport_type.addItem("SDIO")
        self.transport_type.addItem("USB")
        layout.addWidget(self.transport_type)
        
        # COM Port input
        self.com_port = QLineEdit()
        self.com_port.setPlaceholderText("COM Port")
        self.com_port.setValidator(QIntValidator())
        layout.addWidget(self.com_port)
        
        # Baudrate input
        self.baudrate = QLineEdit()
        self.baudrate.setPlaceholderText("Baudrate")
        self.baudrate.setValidator(QIntValidator())
        layout.addWidget(self.baudrate)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_device)
        layout.addWidget(self.connect_button)
        
        # Add a log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # Set the layout
        self.setLayout(layout)
        
        # Set the style
        self.setStyleSheet("background-color: lightblue;")
        
        # Connect signals
        self.transport_type.currentTextChanged.connect(self.update_transport_options)
        
        # Show the window
        self.main_wind.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.raise_()
        self.sub_window.activateWindow()
        self.sub_window.setFocus()
        self.sub_window.show()
    
    def _on_subwindow_closed(self):
        """Handle subwindow closed event"""
        if self.sub_window is not None:
            self.sub_window.close()
            self.sub_window.deleteLater()
            self.sub_window = None
        ConnectWindow._instance = None
        self.deleteLater()
        print("[ConnectWindow] subwindow closed, instance reset.")
    
    def __del__(self):
        """Destructor"""
        if ConnectWindow._instance is not None:
            self._on_subwindow_closed()
        # Call base class destructor if available
        if hasattr(super(), "__del__"):
            super().__del__()
        print("[ConnectWindow] __del__")
    
    def update_transport_options(self, transport_name):
        """Update UI based on selected transport type"""
        self.log_area.clear()
        
        # Enable/disable controls based on transport type
        if transport_name == "UART":
            self.com_port.setEnabled(True)
            self.baudrate.setEnabled(True)
        elif transport_name == "SDIO":
            self.com_port.setEnabled(False)
            self.baudrate.setEnabled(False)
        elif transport_name == "USB":
            self.com_port.setEnabled(True)
            self.baudrate.setEnabled(False)
        
        self.connect_button.setEnabled(True)
    
    def connect_to_device(self):
        """Handle connect button click"""
        transport_type = self.transport_type.currentText()
        com_port = self.com_port.text() if self.com_port.isEnabled() else ""
        baudrate = self.baudrate.text() if self.baudrate.isEnabled() else ""
        
        # Log connection attempt
        self.log_area.append(f"Connecting to device using {transport_type}...")
        if com_port:
            self.log_area.append(f"COM Port: {com_port}")
        if baudrate:
            self.log_area.append(f"Baudrate: {baudrate}")
        
        # In a real application, you would connect to the device here
        # For now, we'll just simulate success
        self.log_area.append("Connected successfully!")
        
        # Move cursor to end of log
        self.log_area.moveCursor(QTextCursor.End)
    
    def log(self, message):
        """Add a message to the log area"""
        self.log_area.append(message)
        self.log_area.moveCursor(QTextCursor.End)


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