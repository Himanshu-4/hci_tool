""" 
    this module contains the ConnectWindow class, which is a PyQt5 window for connecting to a serial device.
    It includes a list of available devices and allows the user to select one for connection.
    The window also includes a button to refresh the list of devices and a button to connect to the selected device.
    The ConnectWindow class is a subclass of QWidget and uses a QVBoxLayout to arrange its widgets.
    The list of available devices is displayed in a QListWidget, and the user can select a device by clicking on it.
    The window also includes a QLabel to display the status of the connection and a QPushButton to refresh the list of devices.
    The ConnectWindow class includes methods for refreshing the list of devices, connecting to a selected device,
    and handling the connection process.
    
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
import serial.tools.list_ports
from typing import List, Optional
from serial import SerialException
from serial import Serial
from serial import SerialTimeoutException
from serial import SerialException


class ConnectWindow(QWidget):
    """
    ConnectWindow is a PyQt5 widget that allows the user to connect to a serial device.
    
    Attributes:
        available_ports (List[str]): List of available serial ports.
        selected_port (Optional[str]): The currently selected port.
        connection_status (str): The status of the connection.
    """
    
    # Signal emitted when a connection is established
    connection_established = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        self.available_ports: List[str] = []
        self.selected_port: Optional[str] = None
        self.connection_status: str = "Disconnected"
        
        self.init_ui()
        self.refresh_ports()
        self.connect_button.clicked.connect(self.connect_to_device)
        

# class ConnectWindow(QWidget):
#     """A window for connecting to a device.
#         this window contains information like COM_PORT, Baudrate, and Transport type.
#         basis on the transport type, the window will show different options.
#     """
#     _instance = None
#     def __init__(self, main_wind: QMainWindow = None):
#         print("[ConnectWindow].__init__")
#         if ConnectWindow._instance is not None:
#             raise Exception("Only one instance of ConnectWindow is allowed")
#         # init base class
#         super().__init__()
        
#         ConnectWindow._instance = self
        
#         # init the main window
#         self.main_wind: QMainWindow = main_wind
#         # init the connect window
#         self.sub_window = QMdiSubWindow()
#         self.sub_window.setWindowTitle("Connect")
#         self.sub_window.setWindowIconText("Connect Window")  # Set window icon text
#         self.sub_window.setWidget(self)
#         # self.sub_window.setWindowFlags(Qt.Window)
#         self.sub_window.setWindowModality(Qt.ApplicationModal)
#         self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)  # Enable deletion on close
        
#         self.sub_window.resize(200, 300)
#         self.sub_window.setMinimumSize(200, 300)  # Set minimum size
#         self.sub_window.setMaximumSize(200, 300)  # Set maximum size
#         self.sub_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         # Set window flags to make it a top-level window
#         # self.sub_window.setWindowFlags(Qt.Window)
#         # Set window modality to application modal
#         # Set window flags to make it a top-level window
#         # self.sub_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
#         # Set window modality to application modal
#         # self.sub_window.setWindowModality(Qt.ApplicationModal)  # Set window modality to application modal
#         self.sub_window.setWindowFlags(Qt.Dialog
#                            | Qt.WindowTitleHint
#                            | Qt.WindowCloseButtonHint)
#         # auto-delete on close
#         self.sub_window.destroyed.connect(
#             lambda _: (setattr(self, "sub_window", None),
#                    self._on_subwindow_closed())
#         )
        
        
#         layout = QVBoxLayout()

#         # Transport type
#         self.transport_type = QComboBox()
#         # for transport in transport_type:
#         #     self.transport_type.addItem(transport.name)
#         layout.addWidget(self.transport_type)

#         # COM Port
#         self.com_port = QLineEdit()
#         self.com_port.setPlaceholderText("COM Port")
#         self.com_port.setValidator(QIntValidator())
#         layout.addWidget(self.com_port)

#         # Baudrate
#         self.baudrate = QLineEdit()
#         self.baudrate.setPlaceholderText("Baudrate")
#         self.baudrate.setValidator(QIntValidator())
#         layout.addWidget(self.baudrate)

#         # Connect button
#         self.connect_button = QPushButton("Connect")
#         layout.addWidget(self.connect_button)


#         # Set the layout
#         self.setLayout(layout)
#         # Set the size policy
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         # Set the background color
#         self.setStyleSheet("background-color: lightblue;")  # Set background color
#         # Set the window icon text
#         self.setWindowIconText("Connect Window")  # Set window icon text
#         # Set the attribute to delete on close
#         self.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close
#         # Connect the transport type selection to the update function
#         self.transport_type.currentTextChanged.connect(self.update_transport_options)
#         # Connect the connect button to the connect function
#         self.connect_button.clicked.connect(self.connect_to_device)
#         # Set the initial transport type
#         self.transport_type.setCurrentText("SDIO")
#         # Update the transport options based on the initial selection
#         # self.update_transport_options(self.transport_type.currentText())
#         # Set the initial transport type
#         self.transport = None
#         self.transport_type.setCurrentText("UART")
#         # Update the transport options based on the initial selection
#         # self.update_transport_options(self.transport_type.currentText())
#         # Set the initial transport type
        
#         # show the subwindow in the main window's MDI area
#         self.main_wind.mdi_area.addSubWindow(self.sub_window)
#         self.sub_window.raise_()  # Bring the subwindow to the front
#         self.sub_window.activateWindow()  # Activate the subwindow
#         self.sub_window.setFocus()  # Set focus to the subwindow
#         self.sub_window.show()
        
    
#     def _on_subwindow_closed(self):
#         """
#         Called when the QMdiSubWindow is destroyed—
#         cleans up the ConnectWindow singleton and widget.
#         """
#         if self.sub_window is not None:
#             self.sub_window.close()
#             self.sub_window.deleteLater()
#             self.sub_window = None
#         ConnectWindow._instance = None
#         self.deleteLater()
#         print("[ConnectWindow] subwindow closed, instance reset.")
        
#     def __del__(self):
#         if ConnectWindow._instance is not None:
#             self._on_subwindow_closed()
#         # clean up in base class
#         if hasattr(super(), "__del__"):
#             super().__del__()
#         print("[ConnectWindow] __del__")
        

#     def update_transport_options(self, transport_name):         
#         """Update the transport options based on the selected transport type."""
#         # Clear the log area
#         self.log_area.clear()
#         # Get the selected transport type
#         selected_transport = next((t for t in transport_type if t.name == transport_name), None)
#         if selected_transport:
#             # Update the transport options based on the selected transport type
#             self.com_port.setEnabled(selected_transport.supports_com_port)
#             self.baudrate.setEnabled(selected_transport.supports_baudrate)
#             self.connect_button.setEnabled(True)
#         else:
#             # Disable the options if no valid transport type is selected
#             self.com_port.setEnabled(False)
#             self.baudrate.setEnabled(False)
#             self.connect_button.setEnabled(False)
#     def connect_to_device(self):
#         """Connect to the device using the selected transport type."""
#         # Get the selected transport type
#         selected_transport = next((t for t in transport_type if t.name == self.transport_type.currentText()), None)
#         if selected_transport:
#             # Create a new transport instance
#             self.transport = transport(selected_transport, self.com_port.text(), int(self.baudrate.text()))
#             # Connect to the device
#             if self.transport.connect():
#                 self.log_area.append("Connected to device.")
#             else:
#                 self.log_area.append("Failed to connect to device.")
#         else:
#             self.log_area.append("Invalid transport type selected.")
#     def log(self, message):
#         """Log a message to the log area."""
#         self.log_area.append(message)
#         # Scroll to the bottom of the log area
#         self.log_area.moveCursor(QTextCursor.End)
#         # Set the focus to the log area
#         self.log_area.setFocus()
#         # Set the size policy
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         # Set the background color
#         self.setStyleSheet("background-color: lightblue;")




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



from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QRadioButton, QLabel, QComboBox, QCheckBox, QPushButton,
                             QButtonGroup, QGridLayout, QSpinBox)
from PyQt5.QtCore import Qt
import serial.tools.list_ports
from transports.transport import Transport

class ConnectionDialog(QDialog):
    def __init__(self, parent=None):
        print("[ConnectionDialog].__init__")
        super().__init__(parent)
        self.setWindowTitle("Connection Configuration")
        # self.setModal(True)  # Makes it a high priority window
        self.setFixedSize(450, 400)
        
        # Transport instance
        self.transport = None
        
        # Setup UI
        self.setup_ui()
        self.connect_signals()
        self.update_interface_parameters()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Interface Selection Group
        self.setup_interface_group()
        layout.addWidget(self.interface_group)
        
        # Parameters Group
        self.setup_parameters_group()
        layout.addWidget(self.parameters_group)
        
        # Buttons
        self.setup_buttons()
        layout.addLayout(self.button_layout)
    
    def setup_interface_group(self):
        self.interface_group = QGroupBox("Interface Selection")
        layout = QHBoxLayout()
        self.interface_group.setLayout(layout)
        
        # Radio buttons for interface selection
        self.interface_button_group = QButtonGroup()
        
        self.sdio_radio = QRadioButton("SDIO")
        self.uart_radio = QRadioButton("UART")
        self.usb_radio = QRadioButton("USB")
        
        # Set UART as default
        self.uart_radio.setChecked(True)
        
        # Add to button group
        self.interface_button_group.addButton(self.sdio_radio, 0)
        self.interface_button_group.addButton(self.uart_radio, 1)
        self.interface_button_group.addButton(self.usb_radio, 2)
        
        # Add to layout
        layout.addWidget(self.sdio_radio)
        layout.addWidget(self.uart_radio)
        layout.addWidget(self.usb_radio)
    
    def setup_parameters_group(self):
        self.parameters_group = QGroupBox("Connection Parameters")
        self.parameters_layout = QGridLayout()
        self.parameters_group.setLayout(self.parameters_layout)
        
        # UART Parameters
        self.setup_uart_parameters()
        
        # SDIO Parameters (placeholder)
        self.setup_sdio_parameters()
        
        # USB Parameters (placeholder)
        self.setup_usb_parameters()
    
    def setup_uart_parameters(self):
        # COM Port
        self.uart_port_label = QLabel("COM Port:")
        self.uart_port_combo = QComboBox()
        self.refresh_com_ports()
        
        # Baud Rate
        self.uart_baud_label = QLabel("Baud Rate:")
        self.uart_baud_combo = QComboBox()
        baud_rates = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
        self.uart_baud_combo.addItems(baud_rates)
        self.uart_baud_combo.setCurrentText("115200")
        
        # Data Bits
        self.uart_data_bits_label = QLabel("Data Bits:")
        self.uart_data_bits_combo = QComboBox()
        self.uart_data_bits_combo.addItems(["5", "6", "7", "8"])
        self.uart_data_bits_combo.setCurrentText("8")
        
        # Stop Bits
        self.uart_stop_bits_label = QLabel("Stop Bits:")
        self.uart_stop_bits_combo = QComboBox()
        self.uart_stop_bits_combo.addItems(["1", "1.5", "2"])
        self.uart_stop_bits_combo.setCurrentText("1")
        
        # Parity
        self.uart_parity_label = QLabel("Parity:")
        self.uart_parity_combo = QComboBox()
        self.uart_parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self.uart_parity_combo.setCurrentText("None")
        
        # Hardware Flow Control
        self.uart_hw_flow_label = QLabel("HW Flow Control:")
        self.uart_hw_flow_check = QCheckBox()
        
        # Timeout
        self.uart_timeout_label = QLabel("Timeout (s):")
        self.uart_timeout_spin = QSpinBox()
        self.uart_timeout_spin.setMinimum(1)
        self.uart_timeout_spin.setMaximum(60)
        self.uart_timeout_spin.setValue(5)
        
        # Add UART widgets to layout
        row = 0
        self.parameters_layout.addWidget(self.uart_port_label, row, 0)
        self.parameters_layout.addWidget(self.uart_port_combo, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_baud_label, row, 0)
        self.parameters_layout.addWidget(self.uart_baud_combo, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_data_bits_label, row, 0)
        self.parameters_layout.addWidget(self.uart_data_bits_combo, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_stop_bits_label, row, 0)
        self.parameters_layout.addWidget(self.uart_stop_bits_combo, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_parity_label, row, 0)
        self.parameters_layout.addWidget(self.uart_parity_combo, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_hw_flow_label, row, 0)
        self.parameters_layout.addWidget(self.uart_hw_flow_check, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_timeout_label, row, 0)
        self.parameters_layout.addWidget(self.uart_timeout_spin, row, 1)
        
        # Store UART widgets for easy access
        self.uart_widgets = [
            self.uart_port_label, self.uart_port_combo,
            self.uart_baud_label, self.uart_baud_combo,
            self.uart_data_bits_label, self.uart_data_bits_combo,
            self.uart_stop_bits_label, self.uart_stop_bits_combo,
            self.uart_parity_label, self.uart_parity_combo,
            self.uart_hw_flow_label, self.uart_hw_flow_check,
            self.uart_timeout_label, self.uart_timeout_spin
        ]
    
    def setup_sdio_parameters(self):
        # Placeholder for SDIO parameters
        self.sdio_label = QLabel("SDIO Configuration (Not Implemented)")
        self.parameters_layout.addWidget(self.sdio_label, 10, 0, 1, 2)
        
        self.sdio_widgets = [self.sdio_label]
    
    def setup_usb_parameters(self):
        # Placeholder for USB parameters
        self.usb_label = QLabel("USB Configuration (Not Implemented)")
        self.parameters_layout.addWidget(self.usb_label, 11, 0, 1, 2)
        
        self.usb_widgets = [self.usb_label]
    
    def setup_buttons(self):
        self.button_layout = QHBoxLayout()
        
        # Refresh button for COM ports
        self.refresh_btn = QPushButton("Refresh Ports")
        self.refresh_btn.clicked.connect(self.refresh_com_ports)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        
        # OK and Cancel buttons
        self.ok_btn = QPushButton("Connect")
        self.cancel_btn = QPushButton("Cancel")
        
        self.ok_btn.clicked.connect(self.accept_connection)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Add buttons to layout
        self.button_layout.addWidget(self.refresh_btn)
        self.button_layout.addWidget(self.test_btn)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_btn)
        self.button_layout.addWidget(self.cancel_btn)
    
    def connect_signals(self):
        # Connect interface selection to parameter update
        self.interface_button_group.buttonClicked.connect(self.update_interface_parameters)
    
    def refresh_com_ports(self):
        """Refresh the list of available COM ports"""
        self.uart_port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.uart_port_combo.addItem(f"{port.device} - {port.description}")
    
    def update_interface_parameters(self):
        """Show/hide parameters based on selected interface"""
        selected_id = self.interface_button_group.checkedId()
        
        # Hide all parameter widgets first
        for widget in self.uart_widgets + self.sdio_widgets + self.usb_widgets:
            widget.hide()
        
        # Show relevant parameters
        if selected_id == 1:  # UART
            for widget in self.uart_widgets:
                widget.show()
        elif selected_id == 0:  # SDIO
            for widget in self.sdio_widgets:
                widget.show()
        elif selected_id == 2:  # USB
            for widget in self.usb_widgets:
                widget.show()
    
    def get_selected_interface(self):
        """Get the currently selected interface"""
        selected_id = self.interface_button_group.checkedId()
        interfaces = {0: "SDIO", 1: "UART", 2: "USB"}
        return interfaces.get(selected_id, "UART")
    
    def get_uart_config(self):
        """Get UART configuration parameters"""
        port = self.uart_port_combo.currentText().split(" - ")[0] if self.uart_port_combo.currentText() else ""
        
        # Map parity strings to pyserial constants
        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }
        
        # Map stop bits strings to pyserial constants
        stopbits_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO
        }
        
        config = {
            'port': port,
            'baudrate': int(self.uart_baud_combo.currentText()),
            'bytesize': int(self.uart_data_bits_combo.currentText()),
            'parity': parity_map[self.uart_parity_combo.currentText()],
            'stopbits': stopbits_map[self.uart_stop_bits_combo.currentText()],
            'rtscts': self.uart_hw_flow_check.isChecked(),
            'timeout': self.uart_timeout_spin.value()
        }
        return config
    
    def test_connection(self):
        """Test the connection with current parameters"""
        try:
            interface = self.get_selected_interface()
            transport = Transport()
            transport.select_interface(interface)
            
            if interface == "UART":
                config = self.get_uart_config()
                transport.configure(config)
            
            if transport.connect():
                self.show_message("Connection test successful!")
                transport.disconnect()
            else:
                self.show_message("Connection test failed!")
                
        except Exception as e:
            self.show_message(f"Connection test error: {str(e)}")
    
    def accept_connection(self):
        """Accept the connection and create transport instance"""
        try:
            interface = self.get_selected_interface()
            self.transport = Transport()
            self.transport.select_interface(interface)
            
            if interface == "UART":
                config = self.get_uart_config()
                if not config['port']:
                    self.show_message("Please select a COM port!")
                    return
                self.transport.configure(config)
            elif interface in ["SDIO", "USB"]:
                self.show_message(f"{interface} interface is not yet implemented!")
                return
            
            if self.transport.connect():
                self.accept()
            else:
                self.show_message("Failed to establish connection!")
                
        except Exception as e:
            self.show_message(f"Connection error: {str(e)}")
    
    def get_transport(self):
        """Return the configured transport instance"""
        return self.transport
    
    def show_message(self, message):
        """Show a simple message (could be enhanced with QMessageBox)"""
        print(f"Connection Dialog: {message}")  # For now, just print