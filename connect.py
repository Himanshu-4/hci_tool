#!/usr/bin/env python3
"""
Example usage of the Transport Connection Dialog System

This file demonstrates how to use the transport system both through
the GUI dialog and programmatically.
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PyQt5.QtCore import QTimer

from ui.exts.connect_window import ConnectionDialog
from transports import Transport

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
        self.send_btn.setEnabled(False)
        layout.addWidget(self.send_btn)
        
        # Disconnect button
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_transport)
        self.disconnect_btn.setEnabled(False)
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
                self.send_btn.setEnabled(True)
                self.disconnect_btn.setEnabled(True)
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
        if not self.transport or not self.transport.is_connected():
            self.log_message("Not connected!")
            return
        
        test_data = b"Hello Transport World!\r\n"
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
            
            self.connect_btn.setText("Open Connection Dialog")
            self.send_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(False)
    
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