"""Main UI for HCI command selection and management"""  

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QListWidget, QListWidgetItem, QMdiArea, QMdiSubWindow,
    QSplitter, QMainWindow, QGroupBox, QPushButton,
    QCheckBox, QComboBox, QLineEdit, QFrame
)

from PyQt5.QtWidgets import (
    QKeyEventTransition, 
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
    VendorSpecificOCF
    )

from hci.cmd.cmd_opcodes import OPCODE_TO_NAME

from hci.cmd.cmd_base_packet import HciCmdBasePacket
from hci.cmd.cmd_opcodes import HciOpcode, create_opcode


# Import the base UI classes
from .hci_base_ui import  HciCommandUI
from .hci_sub_window import HciSubWindow

from .cmds import get_cmd_ui_class


# import the transport library
from transports import Transport as transport


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
        self.command_type_combo.currentIndexChanged.connect(self._on_category_selected)
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
        # call this on_command_selected when a command is clicked by mouse or Enter key
        self.commands_list.itemDoubleClicked.connect(self._on_command_cliked)   # Double-click
        # Install event filter for keyboard handling
        self.commands_list.installEventFilter(self)
        # self.commands_list.currentItemChanged.connect(self.on_command_selected)
        commands_layout.addWidget(self.commands_list)
        
        # Add lists to layout
        main_layout.addLayout(categories_layout)
        main_layout.addLayout(commands_layout)
        
        
    def eventFilter(self, source, event):
        # print(f"eventFilter: {source}, {event}")
        if source == self.commands_list and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                current_item = self.commands_list.currentItem()
                if current_item:
                    self._on_command_cliked(current_item)
                return True  # Event handled
        return super().eventFilter(source, event)
    
    
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
        self._on_category_selected(self.command_type_combo.currentText())
    
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
        #     self._on_category_selected(self.commands_list.currentItem(), None)
    
    def _on_category_selected(self, current : None ):
        """Handle selection of a command category"""
        if current is None:
            return
            
        # Load commands for the selected category
        self.commands_list.clear()
        for command in self.commands.get(self.command_type_combo.currentText(), []):
            self.commands_list.addItem(command)
    
    def _on_command_cliked(self, current):
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
        # Keep track of open windows by command
        self.open_windows : dict[int, HciSubWindow] = {}
        
    def open_command_ui(self, category : str, command : str):
        """Open a UI for the specified HCI command"""
        
        try:
            cmd_opcode = None
            category = category.replace("&", "").replace(" ", "_").replace("__", "_").upper()
            cmd = command.replace(" ", "_").upper()
            opcode_name_to_srch = f"{category}_{cmd}"
            # Get the class name from the opcode name values 
            for opcode, name in OPCODE_TO_NAME.items():
                if name == opcode_name_to_srch:
                    cmd_opcode = opcode
                    break
                
            # cmd_opcode = create_opcode(getattr(cmd_type, category), getattr(cmd_type, command))
            print(f"cmd_opcode: {cmd_opcode}, srching for {opcode_name_to_srch}")
            
            # Check if the class exists in the module
            if get_cmd_ui_class(cmd_opcode):
                # Check if there's already an open window for this command
                if cmd_opcode in self.open_windows:
                    # Activate the existing window
                    self.open_windows[cmd_opcode].raise_()
                    self.open_windows[cmd_opcode].activateWindow()
                else:
                    # Create a new instance of the command UI
                    command_ui_class = get_cmd_ui_class(cmd_opcode)
                    command_ui = command_ui_class()
                    
                    # Create a subwindow for the command UI
                    sub_window = HciSubWindow(command_ui, f"{category} - {command}")
                    sub_window.closed.connect(lambda : self.on_window_closed(cmd_opcode))
                    
                    # Add the subwindow to the MDI area
                    self.mdi_area.addSubWindow(sub_window)
                    sub_window.show()
                    
                    # Store the window reference
                    self.open_windows[cmd_opcode] = sub_window
            else:
                # If the command doesn't need a UI, try to execute it directly
                self.execute_simple_command(category, command)
                
        except Exception as e:
            print(f"Error opening command UI: {str(e)}")
    
    def execute_simple_command(self, category : str, command : str):
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
    
    def __init__(self, main_window : QMainWindow, name : Optional[str] , transport = None):
        """Initialize the HCI Main UI"""
        super().__init__()
        self.main_window = main_window
        self.sub_window = None
        self.transport = transport
        self.name = name if name else "HCI Command Center"
        self.window_id = str(uuid.uuid4())  # Generate a unique ID for this window
        self._destroy_window_handler = None
        self.init_ui()
        self.show_window()
        
        # Add this instance to the list of open instances
        HciMainUI.open_instances.append(self)
        
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
        self.command_manager = HciCommandManager(self.main_window.mdi_area, self)
        
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
        self.sub_window = QMdiSubWindow()
        self.sub_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sub_window.setWindowTitle(self.name)
        self.sub_window.setWindowIconText("HCI commands")  # Set window icon text
        self.sub_window.setWidget(self)

        self.sub_window.setWindowFlags(Qt.Window)  # Set window flags to make it a top-level window
        self.sub_window.setWindowModality(Qt.ApplicationModal)  # Set window modality to application modal
        # sizing the subwindow
        self.sub_window.resize(300, 700)
        self.sub_window.setMinimumSize(200, 400)  # Set minimum size
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)  # Enable deletion on close
        # Connect close event
        self.sub_window.destroyed.connect(self.on_subwindow_closed)
        # self.sub_window.destroyed.connect(lambda : (setattr(self, 'sub_window', None), self._on_subwindow_closed()))
        # show the subwindow in the main window's MDI area
        self.sub_window.raise_()  # Bring the subwindow to the front
        self.sub_window.activateWindow()  # Activate the subwindow
        self.sub_window.setFocus()  # Set focus to the subwindow
        
        
    def on_command_selected(self, category : str, command :  str):
        """Handle selection of a command"""
        self.command_manager.open_command_ui(category, command)
        
    def show_window(self):
        """Show the HCI Main UI in a subwindow"""    
        # Add the subwindow to the MDI area
        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        
    def on_subwindow_closed(self):
        """Handle subwindow closed event - clean up resources"""
        # Close all command windows opened by this instance
        if hasattr(self, 'command_manager'):
            self.command_manager.close_all_windows()
        
        # Remove this instance from the list of open instances
        if self in HciMainUI.open_instances:
            HciMainUI.open_instances.remove(self)
        
        if self._destroy_window_handler:
            self._destroy_window_handler()
        # Clean up
        self.deleteLater()
        
    def register_destroy(self, handler : callable):
        """Register a handler to be called when the window is destroyed"""
        self._destroy_window_handler = handler
        
    # def closeEvent(self, event): --- should not implement this otherwise subwindow not call on_subwindow_closed
    #     """Handle close event for the main window"""
    #     # Close all command windows opened by this instance
    #     if hasattr(self, 'command_manager'):
    #         self.command_manager.close_all_windows()
        
    #     # Remove this instance from the list of open instances
    #     if self in HciMainUI.open_instances:
    #         HciMainUI.open_instances.remove(self)
        
    #     # Clean up
    #     self.deleteLater()
        
    #     # Call the base class close event
    #     super().closeEvent(event)
    #     # Close the subwindow
    #     if self.sub_window:
    #         self.sub_window.close()
    ########################################################
    ##== Class Methods for Instance Management ===##
    ########################################################
    @classmethod
    def create_instance(cls, main_window):
        """Create a new instance of HciMainUI"""
        return cls(main_window)
    
    @classmethod
    def get_open_instances(cls):
        """Get a list of all open HCI Command Center windows"""
        return cls.open_instances
    
    @classmethod
    def delete_instance(cls, window_name_or_transport :  str | transport):
        """Delete an instance of HciMainUI by window name or transport"""
        for instance in cls.open_instances:
            if isinstance(window_name_or_transport, str):
                if instance.name == window_name_or_transport:
                    instance.sub_window.close()
                    break
            elif isinstance(window_name_or_transport, transport):
                # Check if the transport matches
                if instance.transport == window_name_or_transport:
                    instance.sub_window.close()
                    break
    @classmethod
    def close_all_instances(cls):
        """Close all open HCI Command Center windows"""
        # Make a copy to avoid list modification during iteration
        instances = list(cls.open_instances)
        for instance in instances:
            if instance.sub_window:
                instance.sub_window.close()





import inspect

class HciMainWindow(QWidget):
    """Main UI for HCI control"""
    
    _instance = None
    
    @classmethod
    def create_instance(cls, main_window):
        if cls._instance is None:
            cls._instance = cls(main_window)
        return cls._instance
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
        
        # Create and show the subwindow
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWidget(self)
        self.sub_window.setWindowTitle("HCI Control")
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose)
        self.sub_window.setWindowFlags(Qt.SubWindow)
        self.sub_window.resize(600, 400)
        
        # Connect the destroyed signal to clean up the instance
        self.sub_window.destroyed.connect(self._on_subwindow_closed)
        
        # Add to MDI area
        if hasattr(main_window, 'mdi_area'):
            main_window.mdi_area.addSubWindow(self.sub_window)
            self.sub_window.show()
    
    def setup_ui(self):
        """Set up the UI"""
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        
        # Left side - Command/Event type selection
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_widget.setLayout(self.left_layout)
        
        # Mode selection (Command/Event)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Commands", "Events"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        self.left_layout.addWidget(self.mode_combo)
        
        # Type list container - will hold either command types or event types
        self.type_container = QWidget()
        self.type_layout = QVBoxLayout()
        self.type_container.setLayout(self.type_layout)
        self.left_layout.addWidget(self.type_container)
        
        # Right side - command/event details
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout()
        self.right_widget.setLayout(self.right_layout)
        
        # Split the layout
        self.layout.addWidget(self.left_widget, 1)
        self.layout.addWidget(self.right_widget, 2)
        
        # Initialize the mode
        self.on_mode_changed(self.mode_combo.currentText())
    
    def on_mode_changed(self, mode):
        """Handle mode selection change"""
        # Clear the type container
        for i in reversed(range(self.type_layout.count())):
            item = self.type_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Create the appropriate type list
        if mode == "Commands":
            self.type_list = HciCommandTypeListUI("Command Types")
            self.type_list.command_type_selected.connect(self.on_command_type_selected)
        else:  # Events
            self.type_list = HciEventTypeListUI("Event Types")
            self.type_list.event_type_selected.connect(self.on_event_type_selected)
        
        # Add to container
        self.type_layout.addWidget(self.type_list)
    
    def on_command_type_selected(self, module):
        """Handle command type selection"""
        # Clear the right side
        for i in reversed(range(self.right_layout.count())):
            item = self.right_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Create command list
        command_list = HciCommandListUI("Commands", module)
        command_list.command_selected.connect(self.on_command_selected)
        self.right_layout.addWidget(command_list)
    
    def on_event_type_selected(self, module):
        """Handle event type selection"""
        # Clear the right side
        for i in reversed(range(self.right_layout.count())):
            item = self.right_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Create event list
        # This part depends on how events are organized
        # For now, we'll just show a message
        label = QLabel("Event display not implemented yet")
        self.right_layout.addWidget(label)
    
    def on_command_selected(self, command):
        """Handle command selection"""
        try:
            # Check if it's a command class or function
            if inspect.isclass(command):
                # Class - create a UI for it
                # Try to find a specific UI class for this command
                command_name = command.__name__
                module_name = command.__module__
                
                # Extract the command type from the module name
                parts = module_name.split('.')
                if len(parts) >= 3:
                    cmd_type = parts[2]  # e.g., "link_controller"
                    
                    # Try to import a specific UI module for this command type
                    try:
                        ui_module = importlib.import_module(f"hci_ui.cmd.{cmd_type}.{cmd_type}_cmdui")
                        
                        # Try to find a specific UI class for this command
                        ui_class_name = f"{command_name}UI"
                        if hasattr(ui_module, ui_class_name):
                            ui_class = getattr(ui_module, ui_class_name)
                            ui_instance = ui_class(command)
                            
                            # Create a subwindow for this command
                            HciCommandSubWindow(ui_instance, self.main_window, command_name)
                            return
                    except ImportError:
                        pass  # No specific UI module found, we'll use the generic one
                
                # No specific UI found, create a generic one
                # Check if the command needs parameters
                if hasattr(command, '__init__'):
                    # Get the parameters from the __init__ method
                    init_sig = inspect.signature(command.__init__)
                    if len(init_sig.parameters) > 1:  # More than just 'self'
                        # Command needs parameters - create a UI
                        from hci_ui.cmd.generic_cmdui import GenericCommandUI
                        ui_instance = GenericCommandUI(command_name, command)
                        HciCommandSubWindow(ui_instance, self.main_window, command_name)
                    else:
                        # Command doesn't need parameters - just create and send it
                        cmd_instance = command()
                        cmd_bytes = cmd_instance.to_bytes()
                        print(f"Sending command (no parameters needed): {cmd_bytes.hex()}")
                        # TODO: Actually send the command
            elif inspect.isfunction(command):
                # Function - call it directly if it doesn't need parameters
                sig = inspect.signature(command)
                if len(sig.parameters) == 0:
                    # Function doesn't need parameters - just call it
                    result = command()
                    print(f"Called function: {command.__name__}, result: {result}")
                else:
                    # Function needs parameters - create a UI
                    from hci_ui.cmd.generic_cmdui import GenericFunctionUI
                    ui_instance = GenericFunctionUI(command.__name__, command)
                    HciCommandSubWindow(ui_instance, self.main_window, command.__name__)
            else:
                print(f"Unknown command type: {type(command)}")
        except Exception as e:
            print(f"Error handling command selection: {str(e)}")
    
    def _on_subwindow_closed(self):
        """Handle subwindow closure"""
        HciMainWindow._instance = None
        self.deleteLater()

