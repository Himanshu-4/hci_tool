#!/usr/bin/env python3
"""
Example usage of the Transport Connection Dialog System

This file demonstrates how to use the transport system both through
the GUI dialog and programmatically.
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QLineEdit
from PyQt5.QtCore import QTimer

import os
import sys 


from transports.transport import Transport
from ui.exts.connect_window import ConnectionDialog

class ConnectWindow(QWidget):
    """A window for connecting to a device.
        this window contains information like COM_PORT, Baudrate, and Transport type.
        basis on the transport type, the window will show different options.
    """
    _instance = None
    def __init__(self, main_wind: QMainWindow = None):
        print("[ConnectWindow].__init__")
        if ConnectWindow._instance is not None:
            raise Exception("Only one instance of ConnectWindow is allowed")
        # init base class
        super().__init__()
        
        ConnectWindow._instance = self
        
        # init the main window
        self.main_wind: QMainWindow = main_wind
        # init the connect window
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWindowTitle("Connect")
        self.sub_window.setWindowIconText("Connect Window")  # Set window icon text
        self.sub_window.setWidget(self)
        # self.sub_window.setWindowFlags(Qt.Window)
        self.sub_window.setWindowModality(Qt.ApplicationModal)
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)  # Enable deletion on close
        
        self.sub_window.resize(200, 300)
        self.sub_window.setMinimumSize(200, 300)  # Set minimum size
        self.sub_window.setMaximumSize(200, 300)  # Set maximum size
        self.sub_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set window flags to make it a top-level window
        # self.sub_window.setWindowFlags(Qt.Window)
        # Set window modality to application modal
        # Set window flags to make it a top-level window
        # self.sub_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        # Set window modality to application modal
        # self.sub_window.setWindowModality(Qt.ApplicationModal)  # Set window modality to application modal
        self.sub_window.setWindowFlags(Qt.Dialog
                           | Qt.WindowTitleHint
                           | Qt.WindowCloseButtonHint)
        # auto-delete on close
        self.sub_window.destroyed.connect(
            lambda _: (setattr(self, "sub_window", None),
                   self._on_subwindow_closed())
        )
        
        
        layout = QVBoxLayout()

        # Transport type
        self.transport_type = QComboBox()
        # for transport in transport_type:
        #     self.transport_type.addItem(transport.name)
        layout.addWidget(self.transport_type)

        # COM Port
        self.com_port = QLineEdit()
        self.com_port.setPlaceholderText("COM Port")
        self.com_port.setValidator(QIntValidator())
        layout.addWidget(self.com_port)

        # Baudrate
        self.baudrate = QLineEdit()
        self.baudrate.setPlaceholderText("Baudrate")
        self.baudrate.setValidator(QIntValidator())
        layout.addWidget(self.baudrate)

        # Connect button
        self.connect_button = QPushButton("Connect")
        layout.addWidget(self.connect_button)


        # Set the layout
        self.setLayout(layout)
        # Set the size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set the background color
        self.setStyleSheet("background-color: lightblue;")  # Set background color
        # Set the window icon text
        self.setWindowIconText("Connect Window")  # Set window icon text
        # Set the attribute to delete on close
        self.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close
        # Connect the transport type selection to the update function
        self.transport_type.currentTextChanged.connect(self.update_transport_options)
        # Connect the connect button to the connect function
        self.connect_button.clicked.connect(self.connect_to_device)
        # Set the initial transport type
        self.transport_type.setCurrentText("SDIO")
        # Update the transport options based on the initial selection
        # self.update_transport_options(self.transport_type.currentText())
        # Set the initial transport type
        self.transport = None
        self.transport_type.setCurrentText("UART")
        # Update the transport options based on the initial selection
        # self.update_transport_options(self.transport_type.currentText())
        # Set the initial transport type
        
        # show the subwindow in the main window's MDI area
        self.main_wind.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.raise_()  # Bring the subwindow to the front
        self.sub_window.activateWindow()  # Activate the subwindow
        self.sub_window.setFocus()  # Set focus to the subwindow
        self.sub_window.show()
        
    
    def _on_subwindow_closed(self):
        """
        Called when the QMdiSubWindow is destroyed—
        cleans up the ConnectWindow singleton and widget.
        """
        if self.sub_window is not None:
            self.sub_window.close()
            self.sub_window.deleteLater()
            self.sub_window = None
        ConnectWindow._instance = None
        self.deleteLater()
        print("[ConnectWindow] subwindow closed, instance reset.")
        
    def __del__(self):
        if ConnectWindow._instance is not None:
            self._on_subwindow_closed()
        # clean up in base class
        if hasattr(super(), "__del__"):
            super().__del__()
        print("[ConnectWindow] __del__")
        

    def update_transport_options(self, transport_name):         
        """Update the transport options based on the selected transport type."""
        # Clear the log area
        self.log_area.clear()
        # Get the selected transport type
        selected_transport = next((t for t in transport_type if t.name == transport_name), None)
        if selected_transport:
            # Update the transport options based on the selected transport type
            self.com_port.setEnabled(selected_transport.supports_com_port)
            self.baudrate.setEnabled(selected_transport.supports_baudrate)
            self.connect_button.setEnabled(True)
        else:
            # Disable the options if no valid transport type is selected
            self.com_port.setEnabled(False)
            self.baudrate.setEnabled(False)
            self.connect_button.setEnabled(False)
    def connect_to_device(self):
        """Connect to the device using the selected transport type."""
        # Get the selected transport type
        selected_transport = next((t for t in transport_type if t.name == self.transport_type.currentText()), None)
        if selected_transport:
            # Create a new transport instance
            self.transport = transport(selected_transport, self.com_port.text(), int(self.baudrate.text()))
            # Connect to the device
            if self.transport.connect():
                self.log_area.append("Connected to device.")
            else:
                self.log_area.append("Failed to connect to device.")
        else:
            self.log_area.append("Invalid transport type selected.")
    def log(self, message):
        """Log a message to the log area."""
        self.log_area.append(message)
        # Scroll to the bottom of the log area
        self.log_area.moveCursor(QTextCursor.End)
        # Set the focus to the log area
        self.log_area.setFocus()
        # Set the size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set the background color
        self.setStyleSheet("background-color: lightblue;")



class ExampleMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transport System Example")
        self.setGeometry(100, 100, 600, 500)
        
        # Transport instance
        self.transport = None
        
        # Setup UI
        self.setup_ui()
        
        # Timer for reading data
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.read_data)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Connection button
        self.connect_btn = QPushButton("Open Connection Dialog")
        self.connect_btn.clicked.connect(self.open_connection_dialog)
        layout.addWidget(self.connect_btn)
        
        # Send test data button
        self.send_btn = QPushButton("Send Test Data")
        self.send_btn.clicked.connect(self.send_test_data)
        layout.addWidget(self.send_btn)
        
        # create a input field for the user to enter the data
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter data to send")
        layout.addWidget(self.input_field)
        
        # Disconnect button
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_transport)
        layout.addWidget(self.disconnect_btn)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Example programmatic usage button
        self.programmatic_btn = QPushButton("Programmatic Example")
        self.programmatic_btn.clicked.connect(self.programmatic_example)
        layout.addWidget(self.programmatic_btn)
    
    def log_message(self, message):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def open_connection_dialog(self):
        """Open the connection dialog"""
        dialog = ConnectionDialog(self)
        if dialog.exec_() == ConnectionDialog.Accepted:
            self.transport = dialog.get_transport()
            if self.transport and self.transport.is_connected():
                self.log_message(f"Connected via {self.transport.get_interface_type()}")
                self.setup_callbacks()
                self.connect_btn.setText("Reconnect")
                # self.send_btn.setEnabled(True)
                # self.disconnect_btn.setEnabled(True)
                self.read_timer.start(100)  # Read every 100ms
            else:
                self.log_message("Connection failed")
        else:
            self.log_message("Connection cancelled")
    
    def setup_callbacks(self):
        """Setup transport callbacks"""
        if not self.transport:
            return
        
        def on_read(data):
            self.log_message(f"Received: {data.hex()}")
        
        def on_write(data):
            self.log_message(f"Sent: {data.hex()}")
        
        def on_connect(transport):
            self.log_message("Transport connected callback triggered")
        
        def on_disconnect(transport):
            self.log_message("Transport disconnected callback triggered")
        
        self.transport.add_callback('read', on_read)
        self.transport.add_callback('write', on_write)
        self.transport.add_callback('connect', on_connect)
        self.transport.add_callback('disconnect', on_disconnect)
    
    def send_test_data(self):
        """Send test data through transport"""
        
        test_data = self.input_field.text().encode('utf-8')  # Get data from input field
        # user should enter the data in hex format
        # convert the data to byte array
        try:
            test_data = bytearray.fromhex(test_data.decode('utf-8'))
        except ValueError:
            self.log_message("Invalid hex data format")
            return
        #convert the data to byte array
        if not test_data:
            self.log_message("No data to send")
            return
        # Send data
        self.log_message(f"Sending: {[hex(data) for data in test_data]}")
        
        if not self.transport or not self.transport.is_connected():
            self.log_message("Not connected!")
            return
        
        if self.transport.write(test_data):
            self.log_message(f"Test data sent successfully")
        else:
            self.log_message("Failed to send test data")
    
    def read_data(self):
        """Read available data from transport"""
        if not self.transport or not self.transport.is_connected():
            return
        
        data = self.transport.read()
        if data:
            try:
                # Try to decode as text for display
                text = data.decode('utf-8', errors='ignore')
                self.log_message(f"Received text: {text.strip()}")
            except:
                self.log_message(f"Received binary: {data.hex()}")
    
    def disconnect_transport(self):
        """Disconnect the transport"""
        if self.transport:
            self.read_timer.stop()
            if self.transport.disconnect():
                self.log_message("Disconnected successfully")
            else:
                self.log_message("Disconnect failed")
            
            # self.connect_btn.setText("Open Connection Dialog")
            # self.send_btn.setEnabled(False)
            # self.disconnect_btn.setEnabled(False)
    
    def programmatic_example(self):
        """Example of using transport programmatically without dialog"""
        self.log_message("=== Programmatic Example ===")
        
        try:
            # Create transport instance
            transport = Transport()
            
            # Select UART interface
            transport.select_interface('UART')
            self.log_message("Selected UART interface")
            
            # Get available ports (this will work even without connection)
            if hasattr(transport.transport_instance, 'get_available_ports'):
                ports = transport.transport_instance.get_available_ports()
                self.log_message(f"Available ports: {[port[0] for port in ports]}")
            
            # Try to configure with a common port (this might fail if port doesn't exist)
            config = {
                'port': 'COM3',  # Change this to an available port
                'baudrate': 9600,
                'timeout': 1
            }
            
            if transport.configure(config):
                self.log_message("Configuration successful")
                
                # Try to connect (this will likely fail without actual hardware)
                try:
                    if transport.connect():
                        self.log_message("Programmatic connection successful!")
                        # Send test data
                        transport.write(b"Programmatic test\r\n")
                        time.sleep(0.1)
                        data = transport.read()
                        if data:
                            self.log_message(f"Programmatic read: {data}")
                        transport.disconnect()
                    else:
                        self.log_message("Programmatic connection failed (expected without hardware)")
                except Exception as e:
                    self.log_message(f"Programmatic connection error: {e}")
            else:
                self.log_message("Configuration failed")
                
        except Exception as e:
            self.log_message(f"Programmatic example error: {e}")
        
        self.log_message("=== End Programmatic Example ===")

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Create and show main window
    window = ExampleMainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()