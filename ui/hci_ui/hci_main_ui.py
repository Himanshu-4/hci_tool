"""Main UI for HCI command selection and management"""  

import traceback
import re 

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

from typing import Optional
from collections import namedtuple
from enum import IntEnum

from hci.cmd.cmd_opcodes import  (
    OGF, InformationOCF, LinkControlOCF, LinkPolicyOCF,
    ControllerBasebandOCF,  StatusOCF, TestingOCF, LEControllerOCF,
    VendorSpecificOCF
    )

from transports.transport import Transport

# Import the base UI classes
from .cmd_factory import HCICommandFactory
from .evt_factory import HCIEventFactory

from hci.cmd.cmd_opcodes import create_opcode, OPCODE_TO_NAME
from .cmds.cmd_baseui import HCICmdUI
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
            self.INFORMATION: "Informational ",
            self.STATUS: "Status",
            self.TESTING: "Testing",
            self.LE: "LE",
            self.VENDOR_SPECIFIC: 'vendor_specific'
        }
    
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
        self._is_destroyed = False  # Flag to track if the instance is destroyed
        self.init_ui()
        self.load_commands()

    def init_ui(self):
        """Initialize the UI components"""
        if self._is_destroyed:
            return
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
        self.search_box.setClearButtonEnabled(True)  # Enable clear button
        self.search_box.installEventFilter(self)  # Install event filter for keyboard handling
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
    
    def eventFilter(self, source, event):
        """Handle keyboard events for regex search navigation"""
        if event.type() == event.KeyPress:
            if source == self.search_box:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    # Navigate to next match or execute command
                    self._handle_enter_navigation()
                    return True
                elif event.key() == Qt.Key_Down:
                    # Move focus to command list
                    if self.commands_list.count() > 0:
                        self.commands_list.setFocus()
                        self.commands_list.setCurrentRow(0)
                    return True
                elif event.key() == Qt.Key_Escape:
                    # Clear search
                    self.search_box.clear()
                    return True
                    
            elif source == self.commands_list:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    # Execute selected command
                    current_item = self.commands_list.currentItem()
                    if current_item:
                        self._on_command_cliked(current_item)
                    return True
                elif event.key() == Qt.Key_Escape:
                    # Return focus to search box
                    self.search_box.setFocus()
                    return True
        # Call the base class event filter for other events       
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
    
    def _handle_enter_navigation(self):
        """Handle Enter key in search box - navigate through matches"""
        # if not self.filtered_results:
        #     return
            
        # if len(self.filtered_results) == 1:
        #     # Only one match - execute it directly
        #     command = self.filtered_results[0]['command']
        #     self._execute_selected_command(command)
        # else:
        #     # Multiple matches - navigate through them
        #     self.current_match_index = (self.current_match_index + 1) % len(self.filtered_results)
            
        #     # Find the item in the list and select it
        #     target_command = self.filtered_results[self.current_match_index]['command']
        #     for i in range(self.commands_list.count()):
        #         item = self.commands_list.item(i)
        #         if item.text() == target_command:
        #             self.commands_list.setCurrentRow(i)
        #             self.commands_list.scrollToItem(item)
        #             break
            
        #     # Update status to show navigation
        #     current = self.current_match_index + 1
        #     total = len(self.filtered_results)
        #     print(f"Navigating to match {current}/{total}: {target_command}")
        self.commands_list.setCurrentRow(5)  # Reset to first item
        print("Enter key pressed in search box - navigating through matches")    
        
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


"""Manager class for HCI commands and their UIs"""

class HciCommandManager:
    """Manager class for HCI commands and their UIs"""
    
    def __init__(self, title, parent_window : QMainWindow , transport: Transport):
        self.parent_window = parent_window
        self._is_destroyed = False  # Flag to track if the instance is destroyed
        # Keep track of open windows by command
        self._cmd_factory = HCICommandFactory(title, parent_window, transport)
        self._evt_factory = HCIEventFactory(title, parent_window, transport)
    
    def __del__(self):
        """Destructor to ensure all command windows are closed"""
        if not self._is_destroyed:
            self.cleanup()
    
    def cleanup(self):
        """Explicit cleanup method"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        
        if hasattr(self, '_cmd_factory') and self._cmd_factory:
            self._cmd_factory.cleanup()
            self._cmd_factory = None
        if hasattr(self, '_evt_factory') and self._evt_factory:
            self._evt_factory.cleanup()
            self._evt_factory = None
    
    def __repr__(self):
        return f"<HciCommandManager parent={self.parent_window}, cmd_factory={self._cmd_factory}, evt_factory={self._evt_factory}>"
    def __str__(self):
        return f"HciCommandManager(parent={self.parent_window}, cmd_factory={self._cmd_factory}, evt_factory={self._evt_factory})"
    def __len__(self):
        """Return the number of command windows currently managed"""
        return len(self._cmd_factory) if self._cmd_factory else 0
    def __contains__(self, cmd_opcode: int) -> bool:
        """Check if a command window with the given opcode exists"""
        return cmd_opcode in self._cmd_factory if self._cmd_factory else False
    def __getitem__(self, cmd_opcode: int) -> Optional[HCICmdUI]:
        """Get a command window by its opcode"""
        return self._cmd_factory[cmd_opcode] if self._cmd_factory else None
    
    
    def open_command_ui(self, category : str, command : str):
        """Open a UI for the specified HCI command"""
        if self._is_destroyed or (self._cmd_factory is None) :
            return
        
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
            if cmd_opcode is None:
                raise ValueError(f"Command {opcode_name_to_srch} not found in OPCODE_TO_NAME mapping")
            
            
            # cmd_opcode = create_opcode(getattr(cmd_type, category), getattr(cmd_type, command))
            print(f"cmd_opcode: {cmd_opcode}, srching for {opcode_name_to_srch}")
            
            cmd_window = self._cmd_factory.create_command_window(cmd_opcode)
            if  cmd_window == None:
                # If the command doesn't need a UI, try to execute it directly
                self.execute_simple_command(cmd_opcode)
                
        except Exception as e:
            print(f"Error opening command UI: {e} ")
            # also point where the error happened
            traceback.print_exc()
    
    def execute_simple_command(self, cmd_opcode : int):
        """Execute a simple command that doesn't need a UI"""
        # Try to find a function for this command
        self._cmd_factory.execute_command(cmd_opcode)
    
    def close_all_windows(self):
        """Close all command windows"""
        self.cleanup()
        
    # create a mouse event handler when clicked it will raise all the command windows
    def raise_all_command_windows(self):
        """Raise all command windows to the front"""
        self._cmd_factory.raise_all_command_windows()
        

class HciMainUI(QWidget):
    """Main UI for HCI command selection and management"""
    
    # Static list to track all open windows
    open_instances : list['HciMainUI'] =  []
    
    @classmethod
    def create_instance(cls, main_window, title: Optional[str] = "HCI Command Center", transport: Optional[Transport] = None) -> 'HciMainUI':
        """Create a new instance of HciMainUI"""
        # Check if an instance with the same transport already exists
        for instance in cls.open_instances:
            if instance.transport == transport:
                # If an instance with the same transport exists, bring it to the front
                try:
                    instance.sub_window.raise_()
                    instance.sub_window.activateWindow()
                    return instance
                except (RuntimeError, AttributeError):
                    # Instance exists but window is deleted, remove from list
                    cls.open_instances.remove(instance)
                    break
        
        # Create a new instance if no existing one matches
        new_instance = cls(main_window, title=title, transport=transport)
        return new_instance
    
    def get_instance(cls, window_name_or_transport: str | transport) -> Optional['HciMainUI']:
        """Get an instance of HciMainUI by window name or transport"""
        for instance in list(cls.open_instances):  # Create a copy to avoid modification during iteration
            try:
                if isinstance(window_name_or_transport, str):
                    if instance.title == window_name_or_transport:
                        return instance
                elif isinstance(window_name_or_transport, transport):
                    # Check if the transport matches
                    if instance.transport == window_name_or_transport:
                        return instance
            except (RuntimeError, AttributeError):
                # Instance is no longer valid, remove it
                cls.open_instances.remove(instance)
        return None
    
    @classmethod
    def get_open_instances(cls)  -> list['HciMainUI']:
        """Get a list of all open HCI Command Center windows"""
        # Filter out invalid instances
        valid_instances = []
        for instance in cls.open_instances:
            try:
                # Try to access a property to check if the instance is still valid
                _ = instance.title
                valid_instances.append(instance)
            except (RuntimeError, AttributeError):
                # Instance is no longer valid, skip it
                pass
        cls.open_instances = valid_instances
        return cls.open_instances
    
    @classmethod
    def delete_instance(cls, window_name_or_transport :  str | transport) -> None:
        """Delete an instance of HciMainUI by window name or transport"""
        for instance in list(cls.open_instances):  # Create a copy to avoid modification during iteration
            try:
                if isinstance(window_name_or_transport, str):
                    if instance.title == window_name_or_transport:
                        instance.cleanup()
                        break
                elif isinstance(window_name_or_transport, transport):
                    # Check if the transport matches
                    if instance.transport == window_name_or_transport:
                        instance.cleanup()
                        break
            except (RuntimeError, AttributeError):
                # Instance is no longer valid, remove it
                if instance in cls.open_instances:
                    cls.open_instances.remove(instance)
                    
    @classmethod
    def close_all_instances(cls):
        """Close all open HCI Command Center windows"""
        # Make a copy to avoid list modification during iteration
        instances = list(cls.open_instances)
        for instance in instances:
            try:
                instance.cleanup()
            except (RuntimeError, AttributeError):
                # Instance is already invalid
                pass
        cls.open_instances.clear()
                
    @classmethod
    def close_instance(cls, instance: 'HciMainUI') -> None:
        """Close a specific instance of HciMainUI"""
        if instance in cls.open_instances:
            try:
                instance.cleanup()
            except (RuntimeError, AttributeError):
                # Instance is already invalid
                pass
            if instance in cls.open_instances:
                cls.open_instances.remove(instance)

    ############################################################
    ##== Initialization and UI Setup ===##
    #############################################################
    def __init__(self, main_window : QMainWindow, *, title : Optional[str] = "HCI Command Center" , transport : Transport):
        """Initialize the HCI Main UI"""
        super().__init__()
        self.main_window = main_window
        self.sub_window = None
        self.transport = transport
        self.title = title
        self._destroy_window_handler = None
        self._is_destroyed = False  # Flag to track if the instance is destroyed
        self.command_manager = None  # Command manager instance
        self.command_selector = None  # Command selector widget
        self.init_ui()
        self.show_window()
        
        # Add this instance to the list of open instances
        HciMainUI.open_instances.append(self)
        
            
    def __del__(self):
        """Destructor to clean up resources"""
        if not self._is_destroyed:
            self.cleanup()

    def cleanup(self):
        """Explicit cleanup method"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        
        # Close the subwindow safely
        if hasattr(self, 'sub_window') and self.sub_window:
            try:
                self.sub_window.close()
            except RuntimeError:
                # Window already deleted by Qt
                pass
            self.sub_window = None
            
        # Remove this instance from the list of open instances
        if self in HciMainUI.open_instances:
            HciMainUI.open_instances.remove(self)
            
        # Clean up command manager
        if hasattr(self, 'command_manager') and self.command_manager:
            self.command_manager.cleanup()
            self.command_manager = None
            
        # Call destroy handler if set
        if self._destroy_window_handler:
            try:
                self._destroy_window_handler()
            except Exception:
                pass  # Ignore errors in handler
            
            
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
             # Command selector
        self.command_selector = HciCommandSelector()
        self.command_selector.command_selected.connect(self.on_command_selected)
        # command selector will set the widget properly
        main_layout.addWidget(self.command_selector)
        
        # Create the command manager
        self.command_manager = HciCommandManager(self.title , self, self.transport)
        # Add a separator
        # line = QFrame()
        # line.setFrameShape(QFrame.HLine)
        # line.setFrameShadow(QFrame.Sunken)
        # main_layout.addWidget(line)
        self.sub_window = QMdiSubWindow()
        self.sub_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sub_window.setWindowTitle(self.title)
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
        if self._is_destroyed:
            return
            
        # Mark as destroyed first to prevent recursive calls
        self._is_destroyed = True
        
        # Close all command windows opened by this instance
        if hasattr(self, 'command_manager') and self.command_manager:
            self.command_manager.cleanup()
        
        # Remove this instance from the list of open instances
        if self in HciMainUI.open_instances:
            HciMainUI.open_instances.remove(self)
        
        if self._destroy_window_handler:
            try:
                self._destroy_window_handler()
            except Exception:
                pass  # Ignore errors in handler
                
        # Clean up
        try:
            self.deleteLater()
        except RuntimeError:
            pass  # Already deleted
        
    def register_destroy(self, handler : callable):
        """Register a handler to be called when the window is destroyed"""
        self._destroy_window_handler = handler
        
    ########################################################
    
    def mousePressEvent(self, event):
        """Handle mouse press events - raise all command windows when clicked"""
        if self._is_destroyed:
            return
            
        # Call the base class implementation first
        try:
            super().mousePressEvent(event)
        except RuntimeError:
            return
        
        # Raise all command windows when any mouse button is clicked
        if hasattr(self, 'command_manager') and self.command_manager:
            self.command_manager.raise_all_command_windows()
        
        
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
  

