from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, 
    QMainWindow, QLabel, QGridLayout, QGroupBox
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import Qt, pyqtSignal

import struct
from ...hci_base_ui import HciEventUI, HciSubWindow


def bd_addr_bytes_to_str(addr_bytes):
    """Convert a BD_ADDR bytes (little-endian) to a string representation"""
    if len(addr_bytes) != 6:
        return "Invalid BD_ADDR"
    
    # Reverse for proper display order (Bluetooth addresses are little-endian)
    addr = list(addr_bytes)
    addr.reverse()
    
    # Format as a string with colons
    return ':'.join('{:02X}'.format(b) for b in addr)


class ConnectionCompleteEventUI(HciEventUI):
    """UI for HCI Connection Complete Event"""
    
    def __init__(self):
        super().__init__("HCI Connection Complete Event")
        
    def add_event_ui(self):
        """Add Connection Complete event specific UI components"""
        super().add_event_ui()
        
        # Initialize parameter labels
        self.status_label = self.add_parameter(0, "Status:", "Unknown")
        self.handle_label = self.add_parameter(1, "Connection Handle:", "Unknown")
        self.bd_addr_label = self.add_parameter(2, "BD_ADDR:", "Unknown")
        self.link_type_label = self.add_parameter(3, "Link Type:", "Unknown")
        self.encryption_label = self.add_parameter(4, "Encryption Enabled:", "Unknown")
        
    def process_event(self, event_data):
        """Process a Connection Complete event"""
        if len(event_data) < 11:
            self.log("Invalid Connection Complete event data length", "red")
            return
        
        # Parse the event data
        status = event_data[0]
        connection_handle = struct.unpack("<H", event_data[1:3])[0]
        bd_addr = event_data[3:9]
        link_type = event_data[9]
        encryption_enabled = event_data[10]
        
        # Update the UI
        self.status_label.setText("0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        self.handle_label.setText("0x{:04X}".format(connection_handle))
        self.bd_addr_label.setText(bd_addr_bytes_to_str(bd_addr))
        
        link_type_str = "Unknown"
        if link_type == 0:
            link_type_str = "SCO"
        elif link_type == 1:
            link_type_str = "ACL"
        self.link_type_label.setText("{} (0x{:02X})".format(link_type_str, link_type))
        
        self.encryption_label.setText("{}".format(
            "Enabled" if encryption_enabled == 1 else "Disabled"))
        
        # Log the event
        self.log("Connection Complete event received:")
        self.log("  Status: 0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        self.log("  Connection Handle: 0x{:04X}".format(connection_handle))
        self.log("  BD_ADDR: {}".format(bd_addr_bytes_to_str(bd_addr)))
        self.log("  Link Type: {}".format(link_type_str))
        self.log("  Encryption Enabled: {}".format(
            "Enabled" if encryption_enabled == 1 else "Disabled"))


class ConnectionRequestEventUI(HciEventUI):
    """UI for HCI Connection Request Event"""
    
    def __init__(self):
        super().__init__("HCI Connection Request Event")
        
    def add_event_ui(self):
        """Add Connection Request event specific UI components"""
        super().add_event_ui()
        
        # Initialize parameter labels
        self.bd_addr_label = self.add_parameter(0, "BD_ADDR:", "Unknown")
        self.class_of_device_label = self.add_parameter(1, "Class of Device:", "Unknown")
        self.link_type_label = self.add_parameter(2, "Link Type:", "Unknown")
        
    def process_event(self, event_data):
        """Process a Connection Request event"""
        if len(event_data) < 10:
            self.log("Invalid Connection Request event data length", "red")
            return
        
        # Parse the event data
        bd_addr = event_data[0:6]
        class_of_device = struct.unpack("<L", event_data[6:9] + b'\x00')[0]
        link_type = event_data[9]
        
        # Update the UI
        self.bd_addr_label.setText(bd_addr_bytes_to_str(bd_addr))
        self.class_of_device_label.setText("0x{:06X}".format(class_of_device))
        
        link_type_str = "Unknown"
        if link_type == 0:
            link_type_str = "SCO"
        elif link_type == 1:
            link_type_str = "ACL"
        self.link_type_label.setText("{} (0x{:02X})".format(link_type_str, link_type))
        
        # Log the event
        self.log("Connection Request event received:")
        self.log("  BD_ADDR: {}".format(bd_addr_bytes_to_str(bd_addr)))
        self.log("  Class of Device: 0x{:06X}".format(class_of_device))
        self.log("  Link Type: {}".format(link_type_str))


class DisconnectionCompleteEventUI(HciEventUI):
    """UI for HCI Disconnection Complete Event"""
    
    def __init__(self):
        super().__init__("HCI Disconnection Complete Event")
        
    def add_event_ui(self):
        """Add Disconnection Complete event specific UI components"""
        super().add_event_ui()
        
        # Initialize parameter labels
        self.status_label = self.add_parameter(0, "Status:", "Unknown")
        self.handle_label = self.add_parameter(1, "Connection Handle:", "Unknown")
        self.reason_label = self.add_parameter(2, "Reason:", "Unknown")
        
    def process_event(self, event_data):
        """Process a Disconnection Complete event"""
        if len(event_data) < 4:
            self.log("Invalid Disconnection Complete event data length", "red")
            return
        
        # Parse the event data
        status = event_data[0]
        connection_handle = struct.unpack("<H", event_data[1:3])[0]
        reason = event_data[3]
        
        # Update the UI
        self.status_label.setText("0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        self.handle_label.setText("0x{:04X}".format(connection_handle))
        
        reason_str = "Unknown"
        reason_descriptions = {
            0x05: "Authentication Failure",
            0x13: "Remote User Terminated Connection",
            0x14: "Remote Device Terminated Connection due to Low Resources",
            0x15: "Remote Device Terminated Connection due to Power Off",
            0x16: "Connection Terminated by Local Host",
            0x1A: "Unsupported Remote Feature",
            0x3B: "Unacceptable Connection Parameters"
        }
        
        if reason in reason_descriptions:
            reason_str = reason_descriptions[reason]
        
        self.reason_label.setText("0x{:02X} ({})".format(reason, reason_str))
        
        # Log the event
        self.log("Disconnection Complete event received:")
        self.log("  Status: 0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        self.log("  Connection Handle: 0x{:04X}".format(connection_handle))
        self.log("  Reason: 0x{:02X} ({})".format(reason, reason_str))


class RemoteNameRequestCompleteEventUI(HciEventUI):
    """UI for HCI Remote Name Request Complete Event"""
    
    def __init__(self):
        super().__init__("HCI Remote Name Request Complete Event")
        
    def add_event_ui(self):
        """Add Remote Name Request Complete event specific UI components"""
        super().add_event_ui()
        
        # Initialize parameter labels
        self.status_label = self.add_parameter(0, "Status:", "Unknown")
        self.bd_addr_label = self.add_parameter(1, "BD_ADDR:", "Unknown")
        self.remote_name_label = self.add_parameter(2, "Remote Name:", "Unknown")
        
    def process_event(self, event_data):
        """Process a Remote Name Request Complete event"""
        if len(event_data) < 7:
            self.log("Invalid Remote Name Request Complete event data length", "red")
            return
        
        # Parse the event data
        status = event_data[0]
        bd_addr = event_data[1:7]
        
        # Remote name is a null-terminated string (max 248 bytes)
        remote_name = ""
        if len(event_data) > 7:
            # Find the null terminator
            null_pos = event_data.find(0, 7)
            if null_pos != -1:
                remote_name = event_data[7:null_pos].decode('utf-8', errors='replace')
            else:
                remote_name = event_data[7:].decode('utf-8', errors='replace')
        
        # Update the UI
        self.status_label.setText("0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        self.bd_addr_label.setText(bd_addr_bytes_to_str(bd_addr))
        self.remote_name_label.setText(remote_name)
        
        # Log the event
        self.log("Remote Name Request Complete event received:")
        self.log("  Status: 0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        self.log("  BD_ADDR: {}".format(bd_addr_bytes_to_str(bd_addr)))
        self.log("  Remote Name: {}".format(remote_name))


class InquiryCompleteEventUI(HciEventUI):
    """UI for HCI Inquiry Complete Event"""
    
    def __init__(self):
        super().__init__("HCI Inquiry Complete Event")
        
    def add_event_ui(self):
        """Add Inquiry Complete event specific UI components"""
        super().add_event_ui()
        
        # Initialize parameter labels
        self.status_label = self.add_parameter(0, "Status:", "Unknown")
        
    def process_event(self, event_data):
        """Process an Inquiry Complete event"""
        if len(event_data) < 1:
            self.log("Invalid Inquiry Complete event data length", "red")
            return
        
        # Parse the event data
        status = event_data[0]
        
        # Update the UI
        self.status_label.setText("0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))
        
        # Log the event
        self.log("Inquiry Complete event received:")
        self.log("  Status: 0x{:02X} ({})".format(
            status, "Success" if status == 0 else "Error"))


class InquiryResultEventUI(HciEventUI):
    """UI for HCI Inquiry Result Event"""
    
    def __init__(self):
        super().__init__("HCI Inquiry Result Event")
        
    def add_event_ui(self):
        """Add Inquiry Result event specific UI components"""
        super().add_event_ui()
        
        # Create a group for the inquiry results
        self.results_group = QGroupBox("Inquiry Results")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        self.content_layout.addWidget(self.results_group)
        
    def process_event(self, event_data):
        """Process an Inquiry Result event"""
        if len(event_data) < 1:
            self.log("Invalid Inquiry Result event data length", "red")
            return
        
        # Parse the event data
        num_responses = event_data[0]
        
        # Check if the data length is consistent with the number of responses
        expected_length = 1 + (num_responses * 14)  # 1 byte for num_responses + 14 bytes per response
        if len(event_data) < expected_length:
            self.log("Invalid Inquiry Result event data length for {} responses".format(num_responses), "red")
            return
        
        # Clear previous results
        for i in reversed(range(self.results_layout.count())):
            self.results_layout.itemAt(i).widget().deleteLater()
        
        # Log the event
        self.log("Inquiry Result event received with {} device(s)".format(num_responses))
        
        # Process each response
        for i in range(num_responses):
            # Extract data for this response
            offset = 1 + (i * 14)
            bd_addr = event_data[offset:offset+6]
            page_scan_repetition_mode = event_data[offset+6]
            reserved = event_data[offset+7:offset+9]
            class_of_device = struct.unpack("<L", event_data[offset+9:offset+12] + b'\x00')[0]
            clock_offset = struct.unpack("<H", event_data[offset+12:offset+14])[0]
            
            # Create a widget for this result
            result_widget = QGroupBox("Device {}".format(i+1))
            result_layout = QGridLayout()
            
            # Add the device information
            result_layout.addWidget(QLabel("BD_ADDR:"), 0, 0)
            result_layout.addWidget(QLabel(bd_addr_bytes_to_str(bd_addr)), 0, 1)
            
            result_layout.addWidget(QLabel("Page Scan Repetition Mode:"), 1, 0)
            mode_str = "Unknown"
            if page_scan_repetition_mode == 0:
                mode_str = "R0"
            elif page_scan_repetition_mode == 1:
                mode_str = "R1"
            elif page_scan_repetition_mode == 2:
                mode_str = "R2"
            result_layout.addWidget(QLabel("{} (0x{:02X})".format(mode_str, page_scan_repetition_mode)), 1, 1)
            
            result_layout.addWidget(QLabel("Class of Device:"), 2, 0)
            result_layout.addWidget(QLabel("0x{:06X}".format(class_of_device)), 2, 1)
            
            result_layout.addWidget(QLabel("Clock Offset:"), 3, 0)
            result_layout.addWidget(QLabel("0x{:04X}".format(clock_offset)), 3, 1)
            
            result_widget.setLayout(result_layout)
            self.results_layout.addWidget(result_widget)
            
            # Log this result
            self.log("  Device {}:".format(i+1))
            self.log("    BD_ADDR: {}".format(bd_addr_bytes_to_str(bd_addr)))
            self.log("    Page Scan Repetition Mode: {}".format(mode_str))
            self.log("    Class of Device: 0x{:06X}".format(class_of_device))
            self.log("    Clock Offset: 0x{:04X}".format(clock_offset))


class InquiryResultWithRSSIEventUI(HciEventUI):
    """UI for HCI Inquiry Result with RSSI Event"""
    
    def __init__(self):
        super().__init__("HCI Inquiry Result with RSSI Event")
        
    def add_event_ui(self):
        """Add Inquiry Result with RSSI event specific UI components"""
        super().add_event_ui()
        
        # Create a group for the inquiry results
        self.results_group = QGroupBox("Inquiry Results with RSSI")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        self.content_layout.addWidget(self.results_group)
        
    def process_event(self, event_data):
        """Process an Inquiry Result with RSSI event"""
        if len(event_data) < 1:
            self.log("Invalid Inquiry Result with RSSI event data length", "red")
            return
        
        # Parse the event data
        num_responses = event_data[0]
        
        # Check if the data length is consistent with the number of responses
        expected_length = 1 + (num_responses * 15)  # 1 byte for num_responses + 15 bytes per response
        if len(event_data) < expected_length:
            self.log("Invalid Inquiry Result with RSSI event data length for {} responses".format(num_responses), "red")
            return
        
        # Clear previous results
        for i in reversed(range(self.results_layout.count())):
            self.results_layout.itemAt(i).widget().deleteLater()
        
        # Log the event
        self.log("Inquiry Result with RSSI event received with {} device(s)".format(num_responses))
        
        # Process each response
        for i in range(num_responses):
            # Extract data for this response
            offset = 1 + (i * 15)
            bd_addr = event_data[offset:offset+6]
            page_scan_repetition_mode = event_data[offset+6]
            reserved = event_data[offset+7]
            class_of_device = struct.unpack("<L", event_data[offset+8:offset+11] + b'\x00')[0]
            clock_offset = struct.unpack("<H", event_data[offset+11:offset+13])[0]
            rssi = struct.unpack("<b", bytes([event_data[offset+13]]))[0]  # signed byte
            
            # Create a widget for this result
            result_widget = QGroupBox("Device {}".format(i+1))
            result_layout = QGridLayout()
            
            # Add the device information
            result_layout.addWidget(QLabel("BD_ADDR:"), 0, 0)
            result_layout.addWidget(QLabel(bd_addr_bytes_to_str(bd_addr)), 0, 1)
            
            result_layout.addWidget(QLabel("Page Scan Repetition Mode:"), 1, 0)
            mode_str = "Unknown"
            if page_scan_repetition_mode == 0:
                mode_str = "R0"
            elif page_scan_repetition_mode == 1:
                mode_str = "R1"
            elif page_scan_repetition_mode == 2:
                mode_str = "R2"
            result_layout.addWidget(QLabel("{} (0x{:02X})".format(mode_str, page_scan_repetition_mode)), 1, 1)
            
            result_layout.addWidget(QLabel("Class of Device:"), 2, 0)
            result_layout.addWidget(QLabel("0x{:06X}".format(class_of_device)), 2, 1)
            
            result_layout.addWidget(QLabel("Clock Offset:"), 3, 0)
            result_layout.addWidget(QLabel("0x{:04X}".format(clock_offset)), 3, 1)
            
            result_layout.addWidget(QLabel("RSSI:"), 4, 0)
            result_layout.addWidget(QLabel("{} dBm".format(rssi)), 4, 1)
            
            result_widget.setLayout(result_layout)
            self.results_layout.addWidget(result_widget)
            
            # Log this result
            self.log("  Device {}:".format(i+1))
            self.log("    BD_ADDR: {}".format(bd_addr_bytes_to_str(bd_addr)))
            self.log("    Page Scan Repetition Mode: {}".format(mode_str))
            self.log("    Class of Device: 0x{:06X}".format(class_of_device))
            self.log("    Clock Offset: 0x{:04X}".format(clock_offset))
            self.log("    RSSI: {} dBm".format(rssi))


class HCIEventManager:
    """Manager class for HCI events and their UIs"""
    
    def __init__(self, mdi_area):
        self.mdi_area = mdi_area
        self.open_windows = {}  # Keep track of open windows by event code
        
        # Define mapping of event codes to UI classes
        self.event_ui_map = {
            0x03: ConnectionCompleteEventUI,
            0x04: ConnectionRequestEventUI,
            0x05: DisconnectionCompleteEventUI,
            0x07: RemoteNameRequestCompleteEventUI,
            0x01: InquiryCompleteEventUI,
            0x02: InquiryResultEventUI,
            0x22: InquiryResultWithRSSIEventUI
        }
        
    def process_event(self, event_code, event_data):
        """Process an HCI event and open or update the appropriate UI"""
        if event_code in self.event_ui_map:
            # Check if there's already an open window for this event
            if event_code in self.open_windows:
                # Update the existing window
                self.open_windows[event_code].widget().process_event(event_data)
                # Bring the window to the front
                self.open_windows[event_code].raise_()
                self.open_windows[event_code].activateWindow()
            else:
                # Create a new window for this event
                event_ui_class = self.event_ui_map[event_code]
                event_ui = event_ui_class()
                
                # Create a subwindow for the event UI
                sub_window = HCISubWindow(event_ui, event_ui.title)
                sub_window.closed.connect(lambda title: self.on_window_closed(event_code))
                
                # Add the subwindow to the MDI area
                self.mdi_area.addSubWindow(sub_window)
                sub_window.show()
                
                # Process the event data
                event_ui.process_event(event_data)
                
                # Store the window reference
                self.open_windows[event_code] = sub_window
        else:
            print(f"No UI handler for event code 0x{event_code:02X}")
    
    def on_window_closed(self, event_code):
        """Handle closing of an event window"""
        if event_code in self.open_windows:
            del self.open_windows[event_code]