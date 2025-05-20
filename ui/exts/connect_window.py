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

