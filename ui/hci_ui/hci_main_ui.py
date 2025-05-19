from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QMdiArea, QMdiSubWindow,
    QSplitter, QMainWindow, QGroupBox, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
import importlib
import os
import sys
from pathlib import Path

# Import the base UI classes
from .hci_base_ui import HciSubWindow, HciBaseUI

class HciCommandSelector(QWidget):
    """Widget for selecting HCI commands from a hierarchical structure"""
    
    command_selected = pyqtSignal(str, str)  # Signal emitted when a command is selected (category, command)
    
    def __init__(self):
        super().__init__()
        self.categories = []
        self.commands = {}
        self.init_ui()
        self.load_commands()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Categories list
        categories_group = QGroupBox("Command Categories")
        categories_layout = QVBoxLayout()
        self.categories_list = QListWidget()
        self.categories_list.currentItemChanged.connect(self.on_category_selected)
        categories_layout.addWidget(self.categories_list)
        categories_group.setLayout(categories_layout)
        
        # Commands list
        commands_group = QGroupBox("Available Commands")
        commands_layout = QVBoxLayout()
        self.commands_list = QListWidget()
        self.commands_list.currentItemChanged.connect(self.on_command_selected)
        commands_layout.addWidget(self.commands_list)
        commands_group.setLayout(commands_layout)
        
        # Add lists to layout
        main_layout.addWidget(categories_group)
        main_layout.addWidget(commands_group)
        
    def load_commands(self):
        """Load available HCI command categories and commands"""
        # Simulated command structure - in a real application, this would be loaded dynamically
        self.categories = ['link_control', 'link_policy', 'controller', 'info_params', 'status_params', 'testing']
        
        # Populate categories
        self.categories_list.clear()
        for category in self.categories:
            self.categories_list.addItem(category)
            
        # Simulated commands for each category
        self.commands = {
            'link_control': ['inquiry', 'create_connection', 'disconnect', 'accept_connection', 'reject_connection', 'change_connection_packet_type', 'remote_name_request'],
            'link_policy': ['hold_mode', 'sniff_mode', 'exit_sniff_mode', 'qos_setup', 'role_discovery', 'switch_role', 'read_link_policy_settings'],
            'controller': ['set_event_mask', 'reset', 'set_event_filter', 'write_local_name', 'read_local_name', 'read_class_of_device', 'write_class_of_device'],
            'info_params': ['read_local_version', 'read_local_supported_features', 'read_bd_addr', 'read_rssi', 'read_buffer_size'],
            'status_params': ['read_failed_contact_counter', 'reset_failed_contact_counter', 'get_link_quality', 'read_encryption_key_size'],
            'testing': ['read_loopback_mode', 'write_loopback_mode', 'enable_device_under_test_mode']
        }
    
    def on_category_selected(self, current, previous):
        """Handle selection of a command category"""
        if current is None:
            return
            
        # Load commands for the selected category
        category = current.text()
        self.commands_list.clear()
        for command in self.commands.get(category, []):
            self.commands_list.addItem(command)
    
    def on_command_selected(self, current, previous):
        """Handle selection of a specific command"""
        if current is None or self.categories_list.currentItem() is None:
            return
            
        category = self.categories_list.currentItem().text()
        command = current.text()
        self.command_selected.emit(category, command)


class HciCommandManager:
    """Manager class for HCI commands and their UIs"""
    
    def __init__(self, mdi_area):
        self.mdi_area = mdi_area
        self.open_windows = {}  # Keep track of open windows
        
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


class HciMainUI(QWidget):
    """Main UI for HCI command selection and management"""
    
    _instance = None
    
    @classmethod
    def create_instance(cls, main_window : QMainWindow):
        """Create or get the instance of the HCI Main UI"""
        if cls._instance is None:
            cls._instance = cls(main_window)
        return cls._instance
    
    def __init__(self, main_window : QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.sub_window = None
        self.init_ui()
        self.show_window()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Command selector
        self.command_selector = HciCommandSelector()
        self.command_selector.command_selected.connect(self.on_command_selected)
        main_layout.addWidget(self.command_selector)
        
        # Create the command manager
        self.command_manager = HciCommandManager(self.main_window.mdi_area)
        
    def on_command_selected(self, category, command):
        """Handle selection of a command"""
        self.command_manager.open_command_ui(category, command)
        
    def show_window(self):
        """Show the HCI Main UI in a subwindow"""
        # Create a subwindow
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWidget(self)
        self.sub_window.setWindowTitle("HCI Command Center")
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose)
        self.sub_window.setWindowIconText("HCI Commands")
        
        # Add the subwindow to the MDI area
        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        
        # Connect close event
        self.sub_window.destroyed.connect(self.on_subwindow_closed)
        
    def on_subwindow_closed(self):
        """Handle subwindow closed event"""
        self.__class__._instance = None