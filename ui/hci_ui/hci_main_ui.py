"""Main UI for HCI command selection and management"""  

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QMdiArea, QMdiSubWindow,
    QSplitter, QMainWindow, QGroupBox, QPushButton,
    QCheckBox, QComboBox, QLineEdit, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import importlib
import os
import sys
from pathlib import Path
import uuid  # For generating unique IDs for windows

from typing import Optional
from collections import namedtuple
from enum import IntEnum

from hci.cmd.cmd_opcodes import  (
    OGF, InformationOCF, LinkControlOCF, LinkPolicyOCF,
    ControllerBasebandOCF,  StatusOCF, TestingOCF, LEControllerOCF,
    VendorSpecificOCF)


Bluetooth_cmd = namedtuple('Bluetooth_cmd', ['cmd', 'cmd_type', 'cmd_desc'])

class cmd_type(IntEnum):
    """Command types for Bluetooth commands"""
    #expand all the values in OGF
    LINK_CONTROL = OGF.LINK_CONTROL
    LINK_POLICY = OGF.LINK_POLICY
    CONTROLLER_BASEBAND = OGF.CONTROLLER_BASEBAND
    INFORMATION = OGF.INFORMATION_PARAMS
    STATUS = OGF.STATUS_PARAMS
    TESTING = OGF.TESTING
    LE = OGF.LE_CONTROLLER
    VENDOR_SPECIFIC = OGF.VENDOR_SPECIFIC
    # Add more command types as needed
    def __repr__(self):
        """String representation of command types"""
        return {
            self.LINK_CONTROL: "Link Control",
            self.LINK_POLICY: "Link Policy",
            self.CONTROLLER_BASEBAND: "Controller & Baseband",
            self.INFORMATION: "Informational",
            self.STATUS: "Status",
            self.TESTING: "Testing",
            self.LE: "LE",
            self.VENDOR_SPECIFIC: 'vendor_specific'
        }.get(self, "Unknown")
    
    def __str__(self):
        """String representation of command types"""
        return {
            self.LINK_CONTROL: "Link Control",
            self.LINK_POLICY: "Link Policy",
            self.CONTROLLER_BASEBAND: "Controller & Baseband",
            self.INFORMATION: "Informational ",
            self.STATUS: "Status",
            self.TESTING: "Testing",
            self.LE: "LE",
            self.VENDOR_SPECIFIC: 'vendor_specific'
        }.get(self, "Unknown")    
        
class commands:
    #link control commands list 
    LINK_CONTROL_COMMANDS = [cmd.name for cmd in LinkControlOCF]
    #link policy commands list
    LINK_POLICY_COMMANDS = [ cmd.name for cmd in LinkPolicyOCF ]
    #controller baseband commands list
    CONTROLLER_BASEBAND_COMMANDS = [ cmd.name for cmd in ControllerBasebandOCF ]
    #information commands list
    INFORMATION_COMMANDS = [ cmd.name for cmd in InformationOCF ]
    #status commands list
    STATUS_COMMANDS = [ cmd.name for cmd in StatusOCF ]
    #testing commands list
    TESTING_COMMANDS = [ cmd.name for cmd in TestingOCF ]
    #le controller commands list
    LE_CONTROLLER_COMMANDS = [ cmd.name for cmd in LEControllerOCF ]
    #vendor specific commands list
    VENDOR_SPECIFIC_COMMANDS = [ cmd.name for cmd in VendorSpecificOCF ]
    # Add more command types as needed


# Import the base UI classes
from .hci_base_ui import HciSubWindow, HciBaseUI

class HciCommandSelector(QWidget):
    """Widget for selecting HCI commands from a hierarchical structure"""
    

    
    command_selected = pyqtSignal(str, str)  # Signal emitted when a command is selected (category, command)
    
    def __init__(self):
        super().__init__()
        self.categories = []
        self.commands = {}
        self.filtered_commands = {}
        self.init_ui()
        self.load_commands()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Categories list
        categories_layout = QVBoxLayout()
        
        # Enable checkbox and baudrate display
        control_layout = QHBoxLayout()
        
        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable Commands")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        control_layout.addWidget(self.enable_checkbox)
        
        control_layout.addStretch(1)
        
        # Baudrate display
        self.baudrate_label = QLabel("Baudrate: 115200")
        self.baudrate_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.baudrate_label)
        
        categories_layout.addLayout(control_layout)
        
        # Add a separator
        # line = QFrame()
        # line.setFrameShape(QFrame.HLine)
        # line.setFrameShadow(QFrame.Sunken)
        # categories_layout.addWidget(line)
        
        
        # Command type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Command Type:"))
        
        self.command_type_combo = QComboBox()
        for cmd in cmd_type:
            self.command_type_combo.addItem(str(cmd))
        self.command_type_combo.currentIndexChanged.connect(self.on_category_selected)
        type_layout.addWidget(self.command_type_combo)
        
        categories_layout.addLayout(type_layout)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Find Command:"))
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search commands...")
        self.search_box.textChanged.connect(self.filter_commands)
        search_layout.addWidget(self.search_box)
        
        categories_layout.addLayout(search_layout)
        
        
        # Commands list
        commands_layout = QVBoxLayout()
        self.commands_list = QListWidget()
        self.commands_list.currentItemChanged.connect(self.on_command_selected)
        commands_layout.addWidget(self.commands_list)
        
        # Add lists to layout
        main_layout.addLayout(categories_layout)
        main_layout.addLayout(commands_layout)
        
        
    def load_commands(self):
        """Load available HCI command categories and commands"""
        # Command categories - in a real application, this would be loaded dynamically
        self.categories = [ str(cmd) for cmd in cmd_type ]
        # Map category names to command type combo box indexes
        self.category_to_index = {
            str(cmd): index for index, cmd in enumerate(cmd_type)
        }
            
        # Commands for each category
        self.commands = {
            str(cmd_type.LINK_CONTROL) : commands.LINK_CONTROL_COMMANDS,
            str(cmd_type.LINK_POLICY) : commands.LINK_POLICY_COMMANDS,
            str(cmd_type.CONTROLLER_BASEBAND) : commands.CONTROLLER_BASEBAND_COMMANDS,
            str(cmd_type.INFORMATION) : commands.INFORMATION_COMMANDS,
            str(cmd_type.STATUS) : commands.STATUS_COMMANDS,
            str(cmd_type.TESTING) : commands.TESTING_COMMANDS,
            str(cmd_type.LE) : commands.LE_CONTROLLER_COMMANDS,
            str(cmd_type.VENDOR_SPECIFIC) : commands.VENDOR_SPECIFIC_COMMANDS
        }
        
        # Initialize filtered commands to match all commands
        self.filtered_commands = dict(self.commands)
        
        # Populate the command type combo box
        self.on_category_selected(self.command_type_combo.currentText())
    
    def on_enable_changed(self, state):
        """Handle enable checkbox state change"""
        is_enabled = (state == Qt.Checked)
        self.commands_list.setEnabled(is_enabled)
        self.command_type_combo.setEnabled(is_enabled)
        self.search_box.setEnabled(is_enabled)
        
    def filter_commands(self):
        """Filter commands by type and search text"""
        search_text = self.search_box.text().lower()
        
        # Get the selected command type
        selected_type_index = self.command_type_combo.currentIndex()
        
        # Initialize empty filtered commands
        self.filtered_commands = {}
        
        # Filter by command type
        if selected_type_index == 0:  # All Commands
            # Include all categories
            categories_to_include = self.categories
        else:
            # Include only the selected category
            for category, index in self.category_to_index.items():
                if index == selected_type_index:
                    categories_to_include = [category]
                    break
            else:
                categories_to_include = []
        
        # Apply category filter
        for category in categories_to_include:
            # Filter commands by search text
            if search_text:
                self.filtered_commands[category] = [
                    cmd for cmd in self.commands.get(category, [])
                    if search_text in cmd.lower()
                ]
            else:
                self.filtered_commands[category] = list(self.commands.get(category, []))
        
        # Update the categories list
        for category in categories_to_include:
            if category in self.filtered_commands and self.filtered_commands[category]:
                self.commands_list.addItem(category)
        
        # If a category is selected, update the commands list
        # if self.commands_list.currentItem():
        #     self.on_category_selected(self.commands_list.currentItem(), None)
    
    def on_category_selected(self, current : None ):
        """Handle selection of a command category"""
        if current is None:
            return
            
        # Load commands for the selected category
        self.commands_list.clear()
        for command in self.commands.get(self.command_type_combo.currentText(), []):
            self.commands_list.addItem(command)
    
    def on_command_selected(self, current, previous : None):
        """Handle selection of a specific command"""
        if current is None or self.commands_list.currentItem() is None:
            return
            
        # category = self.categories_list.currentItem().text()
        command = current.text()
        self.command_selected.emit( self.command_type_combo.currentText(),command)
    
    def set_baudrate(self, baudrate):
        """Update the displayed baudrate"""
        self.baudrate_label.setText(f"Baudrate: {baudrate}")


class HciCommandManager:
    """Manager class for HCI commands and their UIs"""
    
    def __init__(self, mdi_area, parent_window=None):
        self.mdi_area = mdi_area
        self.parent_window = parent_window
        self.open_windows = {}  # Keep track of open windows by command
        
    def open_command_ui(self, category, command):
        """Open a UI for the specified HCI command"""
        # Construct the module path
        module_path = f"hci_ui.cmd.{category}.{category}_cmdui"
        
        try:
            # Try to import the module
            module = importlib.import_module(module_path)
            
            # Get the command class
            # Most command classes will follow a naming convention
            class_name = f"{command.title().replace('_', '')}CommandUI"
            
            # Check if the class exists in the module
            if hasattr(module, class_name):
                command_class = getattr(module, class_name)
                
                # Check if there's already an open window for this command
                window_key = f"{category}.{command}"
                if window_key in self.open_windows:
                    # Activate the existing window
                    self.open_windows[window_key].raise_()
                    self.open_windows[window_key].activateWindow()
                else:
                    # Create a new instance of the command UI
                    command_ui = command_class()
                    
                    # Create a subwindow for the command UI
                    sub_window = HciSubWindow(command_ui, f"{category} - {command}")
                    sub_window.closed.connect(lambda title: self.on_window_closed(window_key))
                    
                    # Add the subwindow to the MDI area
                    self.mdi_area.addSubWindow(sub_window)
                    sub_window.show()
                    
                    # Store the window reference
                    self.open_windows[window_key] = sub_window
            else:
                # If the command doesn't need a UI, try to execute it directly
                self.execute_simple_command(category, command, module)
                
        except ImportError:
            print(f"Module {module_path} not found")
        except Exception as e:
            print(f"Error opening command UI: {str(e)}")
    
    def execute_simple_command(self, category, command, module):
        """Execute a simple command that doesn't need a UI"""
        # Try to find a function for this command
        func_name = f"execute_{command}"
        if hasattr(module, func_name):
            func = getattr(module, func_name)
            
            # Execute the function
            try:
                command_bytes = func()
                print(f"Executed simple command {category}.{command}: {command_bytes.hex()}")
                # Here you would send the bytearray to your HCI transport
                # Example: transport.send(cmd_bytes)
            except Exception as e:
                print(f"Error executing command: {str(e)}")
        else:
            print(f"No UI or execution function found for command {category}.{command}")
    
    def on_window_closed(self, window_key):
        """Handle closing of a command window"""
        if window_key in self.open_windows:
            del self.open_windows[window_key]
            
    def close_all_windows(self):
        """Close all command windows"""
        # Make a copy of the keys to avoid dictionary size change during iteration
        window_keys = list(self.open_windows.keys())
        for window_key in window_keys:
            if window_key in self.open_windows:
                self.open_windows[window_key].close()


class HciMainUI(QWidget):
    """Main UI for HCI command selection and management"""
    
    # Static list to track all open windows
    open_instances = []
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.sub_window = None
        self.window_id = str(uuid.uuid4())  # Generate a unique ID for this window
        self.init_ui()
        self.show_window()
        
        # Add this instance to the list of open instances
        HciMainUI.open_instances.append(self)
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Window title with unique ID
        # title_layout = QHBoxLayout()
        # title_label = QLabel(f"HCI Command Center [{self.window_id[:8]}]")
        # title_label.setFont(QFont("Arial", 12, QFont.Bold))
        # title_layout.addWidget(title_label)
        # title_layout.addStretch(1)
        # main_layout.addLayout(title_layout)
        
        # Add a separator
        # line = QFrame()
        # line.setFrameShape(QFrame.HLine)
        # line.setFrameShadow(QFrame.Sunken)
        # main_layout.addWidget(line)
        
        # Command selector
        self.command_selector = HciCommandSelector()
        self.command_selector.command_selected.connect(self.on_command_selected)
        main_layout.addWidget(self.command_selector)
        
        # Create the command manager
        self.command_manager = HciCommandManager(self.main_window.mdi_area, self)
        
    def on_command_selected(self, category, command):
        """Handle selection of a command"""
        self.command_manager.open_command_ui(category, command)
        
    def show_window(self):
        """Show the HCI Main UI in a subwindow"""
        # Create a subwindow
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWidget(self)
        self.sub_window.setWindowTitle(f"HCI Command Center [{self.window_id[:8]}]")
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose)
        self.sub_window.setWindowIconText("HCI Commands")
        
        # Add the subwindow to the MDI area
        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        
        # Connect close event
        self.sub_window.destroyed.connect(self.on_subwindow_closed)
        
    def on_subwindow_closed(self):
        """Handle subwindow closed event - clean up resources"""
        # Close all command windows opened by this instance
        if hasattr(self, 'command_manager'):
            self.command_manager.close_all_windows()
        
        # Remove this instance from the list of open instances
        if self in HciMainUI.open_instances:
            HciMainUI.open_instances.remove(self)
        
        # Clean up
        self.deleteLater()
        
    @classmethod
    def create_instance(cls, main_window):
        """Create a new instance of HciMainUI"""
        return cls(main_window)
    
    @classmethod
    def close_all_instances(cls):
        """Close all open HCI Command Center windows"""
        # Make a copy to avoid list modification during iteration
        instances = list(cls.open_instances)
        for instance in instances:
            if instance.sub_window:
                instance.sub_window.close()

# class HciCommandSelector(QWidget):
#     """Widget for selecting HCI commands from a hierarchical structure"""
    
#     command_selected = pyqtSignal(str, str)  # Signal emitted when a command is selected (category, command)
    
#     def __init__(self):
#         super().__init__()
#         self.categories = []
#         self.commands = {}
#         self.init_ui()
#         self.load_commands()
        
#     def init_ui(self):
#         """Initialize the UI components"""
#         # Main layout
#         main_layout = QVBoxLayout()
#         self.setLayout(main_layout)
        
#         # Categories list
#         categories_group = QGroupBox("Command Categories")
#         categories_layout = QVBoxLayout()
#         self.categories_list = QListWidget()
#         self.categories_list.currentItemChanged.connect(self.on_category_selected)
#         categories_layout.addWidget(self.categories_list)
#         categories_group.setLayout(categories_layout)
        
#         # Commands list
#         commands_group = QGroupBox("Available Commands")
#         commands_layout = QVBoxLayout()
#         self.commands_list = QListWidget()
#         self.commands_list.currentItemChanged.connect(self.on_command_selected)
#         commands_layout.addWidget(self.commands_list)
#         commands_group.setLayout(commands_layout)
        
#         # Add lists to layout
#         main_layout.addWidget(categories_group)
#         main_layout.addWidget(commands_group)
        
#     def load_commands(self):
#         """Load available HCI command categories and commands"""
#         # Simulated command structure - in a real application, this would be loaded dynamically
#         self.categories = ['link_control', 'link_policy', 'controller', 'info_params', 'status_params', 'testing']
        
#         # Populate categories
#         self.categories_list.clear()
#         for category in self.categories:
#             self.categories_list.addItem(category)
            
#         # Simulated commands for each category
#         self.commands = {
#             'link_control': ['inquiry', 'create_connection', 'disconnect', 'accept_connection', 'reject_connection', 'change_connection_packet_type', 'remote_name_request'],
#             'link_policy': ['hold_mode', 'sniff_mode', 'exit_sniff_mode', 'qos_setup', 'role_discovery', 'switch_role', 'read_link_policy_settings'],
#             'controller': ['set_event_mask', 'reset', 'set_event_filter', 'write_local_name', 'read_local_name', 'read_class_of_device', 'write_class_of_device'],
#             'info_params': ['read_local_version', 'read_local_supported_features', 'read_bd_addr', 'read_rssi', 'read_buffer_size'],
#             'status_params': ['read_failed_contact_counter', 'reset_failed_contact_counter', 'get_link_quality', 'read_encryption_key_size'],
#             'testing': ['read_loopback_mode', 'write_loopback_mode', 'enable_device_under_test_mode']
#         }
    
#     def on_category_selected(self, current, previous):
#         """Handle selection of a command category"""
#         if current is None:
#             return
            
#         # Load commands for the selected category
#         category = current.text()
#         self.commands_list.clear()
#         for command in self.commands.get(category, []):
#             self.commands_list.addItem(command)
    
#     def on_command_selected(self, current, previous):
#         """Handle selection of a specific command"""
#         if current is None or self.categories_list.currentItem() is None:
#             return
            
#         category = self.categories_list.currentItem().text()
#         command = current.text()
#         self.command_selected.emit(category, command)


# class HciCommandManager:
#     """Manager class for HCI commands and their UIs"""
    
#     def __init__(self, mdi_area):
#         self.mdi_area = mdi_area
#         self.open_windows = {}  # Keep track of open windows
        
#     def open_command_ui(self, category, command):
#         """Open a UI for the specified HCI command"""
#         # Construct the module path
#         module_path = f"hci_ui.cmd.{category}.{category}_cmdui"
        
#         try:
#             # Try to import the module
#             module = importlib.import_module(module_path)
            
#             # Get the command class
#             # Most command classes will follow a naming convention
#             class_name = f"{command.title().replace('_', '')}CommandUI"
            
#             # Check if the class exists in the module
#             if hasattr(module, class_name):
#                 command_class = getattr(module, class_name)
                
#                 # Check if there's already an open window for this command
#                 window_key = f"{category}.{command}"
#                 if window_key in self.open_windows:
#                     # Activate the existing window
#                     self.open_windows[window_key].raise_()
#                     self.open_windows[window_key].activateWindow()
#                 else:
#                     # Create a new instance of the command UI
#                     command_ui = command_class()
                    
#                     # Create a subwindow for the command UI
#                     sub_window = HciSubWindow(command_ui, f"{category} - {command}")
#                     sub_window.closed.connect(lambda title: self.on_window_closed(window_key))
                    
#                     # Add the subwindow to the MDI area
#                     self.mdi_area.addSubWindow(sub_window)
#                     sub_window.show()
                    
#                     # Store the window reference
#                     self.open_windows[window_key] = sub_window
#             else:
#                 # If the command doesn't need a UI, try to execute it directly
#                 self.execute_simple_command(category, command, module)
                
#         except ImportError:
#             print(f"Module {module_path} not found")
#         except Exception as e:
#             print(f"Error opening command UI: {str(e)}")
    
#     def execute_simple_command(self, category, command, module):
#         """Execute a simple command that doesn't need a UI"""
#         # Try to find a function for this command
#         func_name = f"execute_{command}"
#         if hasattr(module, func_name):
#             func = getattr(module, func_name)
            
#             # Execute the function
#             try:
#                 command_bytes = func()
#                 print(f"Executed simple command {category}.{command}: {command_bytes.hex()}")
#                 # Here you would send the bytearray to your HCI transport
#                 # Example: transport.send(cmd_bytes)
#             except Exception as e:
#                 print(f"Error executing command: {str(e)}")
#         else:
#             print(f"No UI or execution function found for command {category}.{command}")
    
#     def on_window_closed(self, window_key):
#         """Handle closing of a command window"""
#         if window_key in self.open_windows:
#             del self.open_windows[window_key]


# class HciMainUI(QWidget):
#     """Main UI for HCI command selection and management"""
    
#     def __init__(self, main_window : QMainWindow):
#         super().__init__()
#         self.main_window = main_window
#         self.sub_window = None
#         self.init_ui()
#         self.show_window()
        
#     def init_ui(self):
#         """Initialize the UI components"""
#         # Main layout
#         main_layout = QVBoxLayout()
#         self.setLayout(main_layout)
        
#         # Command selector
#         self.command_selector = HciCommandSelector()
#         self.command_selector.command_selected.connect(self.on_command_selected)
#         main_layout.addWidget(self.command_selector)
        
#         # Create the command manager
#         self.command_manager = HciCommandManager(self.main_window.mdi_area)
        
#     def on_command_selected(self, category, command):
#         """Handle selection of a command"""
#         self.command_manager.open_command_ui(category, command)
        
#     def show_window(self):
#         """Show the HCI Main UI in a subwindow"""
#         # Create a subwindow
#         self.sub_window = QMdiSubWindow()
#         self.sub_window.setWidget(self)
#         self.sub_window.setWindowTitle("HCI Command Center")
#         self.sub_window.setAttribute(Qt.WA_DeleteOnClose)
#         self.sub_window.setWindowIconText("HCI Commands")
        
#         # Add the subwindow to the MDI area
#         self.main_window.mdi_area.addSubWindow(self.sub_window)
#         self.sub_window.show()
        
#         # Connect close event
#         self.sub_window.destroyed.connect(self.on_subwindow_closed)
        
#     def on_subwindow_closed(self):
#         """Handle subwindow closed event"""
#         self.__class__._instance = None