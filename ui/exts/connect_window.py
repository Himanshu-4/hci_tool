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

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,QLineEdit,
                             QRadioButton, QLabel, QComboBox, QCheckBox, QPushButton,
                             QButtonGroup, QGridLayout, QSpinBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
import serial.tools.list_ports
from transports.transport import Transport

class ConnectionDialog(QDialog):
    
    connection_done_signal =  pyqtSignal(object)
    def __init__(self, parent=None):
        print("[ConnectionDialog].__init__")
        super().__init__(parent)
        self.setWindowTitle("Connection Configuration")
        self.setModal(True)  # Makes it a high priority window
        self.setFixedSize(450, 400)
        
        # Transport instance
        self.transport = None
        self._name = "ConnectionDialogDeafault"
        
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
        
        self.name_label = QLabel("Transport Name:")
        self.name_input = QLineEdit()
        # set the size of name input
        self.name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.name_input.setPlaceholderText("Enter transport name")
        self.name_input.setToolTip("Enter a name for the transport")
        self.name_input.setWhatsThis("Enter a name for the transport")
        self.name_input.setStatusTip("Enter a name for the transport")
        self.name_input.setFixedWidth(200)  # Set a fixed width for better layout
        # self.name_layout = QHBoxLayout()
        # self.name_layout.addWidget(self.name_label)
        # self.name_layout.addWidget(self.name_input)

        # COM Port
        self.uart_port_label = QLabel("COM Port:")
        self.uart_port_combo = QComboBox()
        self.uart_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        #refresh the ports when box is clicked
        self.uart_port_combo.setEditable(False)  # Make it a dropdown
        self.uart_port_combo.setInsertPolicy(QComboBox.InsertAtTop)
        self.uart_port_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.uart_port_combo.setFixedWidth(200)  # Set a fixed width for better layout
        self.uart_port_combo.setToolTip("Select the COM port for UART connection")
        self.uart_port_combo.setWhatsThis("Select the COM port for UART connection")
        self.uart_port_combo.setStatusTip("Select the COM port for UART connection")
        # call a function when the combo box is clicked to refresh the ports
        self.refresh_com_ports()
        #put a refresh icon on the right side of the combo box
        # ADD THIS:
        # Create refresh button with Unicode icon
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setFixedSize(24, 24)
        self.refresh_button.setToolTip("Refresh COM ports")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                background-color: #f8f8f8;
                font-size: 14px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #a0a0a0;
            }
            QPushButton:pressed {
                background-color: #d8d8d8;
                border-color: #808080;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #c0c0c0;
                border-color: #e0e0e0;
            }
        """)
        
        self.refresh_button.clicked.connect(self.refresh_com_ports)

        
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
        
        # Hardware Flow Control
        self.uart_hw_flow_label = QLabel("HW Flow Control:")
        self.uart_hw_flow_check = QCheckBox()
        
        # Parity
        self.uart_parity_label = QLabel("Parity:")
        self.uart_parity_combo = QComboBox()
        self.uart_parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self.uart_parity_combo.setCurrentText("None")
        
        # Timeout
        self.uart_timeout_label = QLabel("Timeout (s):")
        self.uart_timeout_spin = QSpinBox()
        self.uart_timeout_spin.setMinimum(1)
        self.uart_timeout_spin.setMaximum(60)
        self.uart_timeout_spin.setValue(5)
        
        # Add UART widgets to layout
        row = 0
        # self.parameters_layout.addLayout(self.name_layout, row, 0, 1, 2)
        self.parameters_layout.addWidget(self.name_label, row, 0)
        self.parameters_layout.addWidget(self.name_input, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_port_label, row, 0)
        self.parameters_layout.addWidget(self.uart_port_combo, row, 1)
        self.parameters_layout.addWidget(self.refresh_button, row, 3)
        row += 1
        self.parameters_layout.addWidget(self.uart_baud_label, row, 0)
        self.parameters_layout.addWidget(self.uart_baud_combo, row, 1)
        row += 1
        self.parameters_layout.addWidget(self.uart_data_bits_label, row, 0)
        self.parameters_layout.addWidget(self.uart_data_bits_combo, row, 1)
        self.parameters_layout.addWidget(self.uart_stop_bits_label, row, 2)
        self.parameters_layout.addWidget(self.uart_stop_bits_combo, row, 3)
        row += 1
        self.parameters_layout.addWidget(self.uart_hw_flow_label, row, 0)
        self.parameters_layout.addWidget(self.uart_hw_flow_check, row, 1)
        self.parameters_layout.addWidget(self.uart_timeout_label, row, 2)
        self.parameters_layout.addWidget(self.uart_timeout_spin, row, 3)
        row += 1
        self.parameters_layout.addWidget(self.uart_parity_label, row, 0)
        self.parameters_layout.addWidget(self.uart_parity_combo, row, 1)
        # row += 1
        
        # Store UART widgets for easy access
        self.uart_widgets = [
            self.name_label, self.name_input,
            self.uart_port_label, self.uart_port_combo,self.refresh_button,
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
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        
        # OK and Cancel buttons
        self.ok_btn = QPushButton("Connect")
        self.cancel_btn = QPushButton("Cancel")
        
        self.ok_btn.clicked.connect(self.accept_connection)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Add buttons to layout
        self.button_layout.addWidget(self.test_btn)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_btn)
        self.button_layout.addWidget(self.cancel_btn)
    
    def connect_signals(self):
        # Connect interface selection to parameter update
        self.interface_button_group.buttonClicked.connect(self.update_interface_parameters)
    
    def refresh_com_ports(self):
        """Refresh the list of available COM ports"""
        print("[ConnectionDialog].refresh_com_ports")
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
        print(f"[ConnectionDialog].get_uart_config: port={port}")
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
            transport = Transport(self._name)
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
            self.transport = Transport(self.name_input.text() or self._name)
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
                self.connection_done_signal.emit(self.transport)
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