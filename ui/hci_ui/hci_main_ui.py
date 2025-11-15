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

from typing import Optional

from transports.transport import Transport, TransportEvent

# Import the base UI classes
from .cmd_factory import HCICommandFactory
from .evt_factory import HCIEventFactory

from .cmds.cmd_baseui import HCICmdUI

from hci.cmd.cmd_opcodes import cmd_type, commands_list



#MARK: HCiCmdSlctr
class HciCommandSelector(QWidget):
    """Widget for selecting HCI commands from a hierarchical structure"""
    
    command_selected = pyqtSignal(str, str)  # Signal emitted when a command is selected (category, command)
    transport_state_changed = pyqtSignal(bool)  # Signal emitted when transport state changes
    
    def __init__(self, baudrate):
        super().__init__()
        self.categories = []
        self.commands = {}
        # filtered commands and results for navigation
        self.filtered_commands = {}
        self.filtered_results = []  # Store filtered results for navigation
        self.current_match_index = -1  # Track current match index
        
        # flag to track if the instance is destroyed
        self._is_destroyed = False  
        # initialize the UI
        self.init_ui(baudrate)
        # load the commands
        self.load_commands()

    def __del__(self):
        """Destructor to ensure all command windows are closed"""
        if not self._is_destroyed:
            self.cleanup()
    
    def cleanup(self):
        """Explicit cleanup method"""
        if self._is_destroyed:
            return
        self._is_destroyed = True
        # Qt elements are automatically deleted when the parent is deleted
        # so we don't need to do anything here
        pass

    def init_ui(self,baudrate):
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
        self.enable_checkbox = QCheckBox("Enable Device")
        self.enable_checkbox.setChecked(True)
        control_layout.addWidget(self.enable_checkbox)
        
        control_layout.addStretch(1)
        
        # Baudrate display
        self.baudrate_label = QLabel(f"Baudrate: {baudrate or  "No Baudrate"}")
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
        # filter commands when text is changed
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
        """Handle keyboard events for regex search navigation"""
        if event.type() == event.KeyPress:
            if source == self.search_box:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    # Execute selected command
                    if self.commands_list.currentItem():
                        self._on_command_cliked(self.commands_list.currentItem())
                    return True
                elif event.key() == Qt.Key_Down:
                    # Move focus to command list and select first item
                    if self.commands_list.count() > 0:
                        self.commands_list.setFocus()
                        self.commands_list.setCurrentRow(0)
                        self.commands_list.scrollToItem(self.commands_list.item(0))
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
                elif event.key() == Qt.Key_Up:
                    # Move up in the list
                    current_row = self.commands_list.currentRow()
                    if current_row > 0:
                        self.commands_list.setCurrentRow(current_row - 1)
                        self.commands_list.scrollToItem(self.commands_list.currentItem())
                    else:
                        # If at top, move focus to search box
                        self.search_box.setFocus()
                    return True
                elif event.key() == Qt.Key_Down:
                    # Move down in the list
                    current_row = self.commands_list.currentRow()
                    if current_row < self.commands_list.count() - 1:
                        self.commands_list.setCurrentRow(current_row + 1)
                        self.commands_list.scrollToItem(self.commands_list.currentItem())
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
            str(cmd): index for index, cmd in enumerate[cmd_type](cmd_type)
        }
            
        # Commands for each category
        self.commands = {
            str(cmd_type.LINK_CONTROL) : commands_list.LINK_CONTROL,
            str(cmd_type.LINK_POLICY) : commands_list.LINK_POLICY,
            str(cmd_type.CONTROLLER_BASEBAND) : commands_list.CONTROLLER_BASEBAND,
            str(cmd_type.INFORMATION) : commands_list.INFORMATION,
            str(cmd_type.STATUS) : commands_list.STATUS,
            str(cmd_type.TESTING) : commands_list.TESTING,
            str(cmd_type.LE) : commands_list.LE,
            str(cmd_type.VENDOR_SPECIFIC) : commands_list.VENDOR_SPECIFIC,
        }
        
        # Initialize filtered commands to match all commands
        self.filtered_commands = dict[str, list[str]](self.commands)
        
        # Populate the command type combo box
        self._on_category_selected(self.command_type_combo.currentText())

    def _on_device_connected(self, *args, **kwargs):
        """Update UI based on transport connection state"""
        # update the enable checkbox
        self.enable_checkbox.setChecked(True)
        self.commands_list.setEnabled(True)
        self.command_type_combo.setEnabled(True)
        self.search_box.setEnabled(True)
        
    def _on_device_disconnected(self, *args, **kwargs):
        """Update UI based on transport connection state"""
        # update the enable checkbox
        self.enable_checkbox.setChecked(False)
        self.commands_list.setEnabled(False)
        self.command_type_combo.setEnabled(False)
        self.search_box.setEnabled(False)
        
    def filter_commands(self):
        """Filter commands by type and search text"""
        search_text = self.search_box.text().lower()
        
        # Get the selected command type
        selected_type_index = self.command_type_combo.currentIndex()
        selected_category = self.command_type_combo.currentText()

        # Initialize empty filtered commands
        self.filtered_commands = {}
        self.filtered_results = []  # Clear previous results
        self.current_match_index = -1  # Reset match index
        
        # Only filter within the selected category
        if selected_category in self.commands:
            # Filter commands by search text
            if search_text:
                filtered_cmds = [
                    cmd for cmd in self.commands[selected_category]
                    if search_text in cmd.lower()
                ]
                self.filtered_commands[selected_category] = filtered_cmds
                # Add to flat list of results for navigation
                for cmd in filtered_cmds:
                    self.filtered_results.append({'category': selected_category, 'command': cmd})
            else:
                self.filtered_commands[selected_category] = list[str](self.commands[selected_category])
        
        # Update the commands list
        self.commands_list.clear()
        if selected_category in self.filtered_commands:
            for cmd in self.filtered_commands[selected_category]:
                self.commands_list.addItem(cmd)
        
        # Select first match if there are results
        if self.filtered_results:
            self.current_match_index = 0
            self.commands_list.setCurrentRow(0)
            self.commands_list.scrollToItem(self.commands_list.item(0))
    
    def _on_category_selected(self, current : Optional[str] = None ):
        """Handle selection of a command category"""
        if current is None:
            return 
        
        current_category = self.command_type_combo.currentText()
        # Load commands for the selected category
        self.commands_list.clear()
        for command in self.commands.get(current_category, []):
            self.commands_list.addItem(command)
        # select the first command
        if self.commands_list.count() > 0:
            self.commands_list.setCurrentRow(0)
            self.commands_list.scrollToItem(self.commands_list.item(0))
    
    def _on_command_cliked(self, current : Optional[QListWidgetItem] = None):
        """Handle selection of a specific command"""
        if current is None or self.commands_list.currentItem() is None:
            return
            
        # category = self.categories_list.currentItem().text()
        command = current.text()
        self.command_selected.emit( self.command_type_combo.currentText(),command)
    


#MARK: HciMainUI
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
    
    def get_instance(cls, window_name_or_transport: str | Transport) -> Optional['HciMainUI']:
        """Get an instance of HciMainUI by window name or transport"""
        for instance in list[HciMainUI](cls.open_instances):  # Create a copy to avoid modification during iteration
            try:
                if isinstance(window_name_or_transport, str):
                    if instance.title == window_name_or_transport:
                        return instance
                elif isinstance(window_name_or_transport, Transport):
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
    def delete_instance(cls, window_name_or_transport :  str | Transport) -> None:
        """Delete an instance of HciMainUI by window name or transport"""
        for instance in list[HciMainUI](cls.open_instances):  # Create a copy to avoid modification during iteration
            try:
                if isinstance(window_name_or_transport, str):
                    if instance.title == window_name_or_transport:
                        instance._cleanup()
                        break
                elif isinstance(window_name_or_transport, Transport):
                    # Check if the transport matches
                    if instance.transport == window_name_or_transport:
                        instance._cleanup()
                        break
            except (RuntimeError, AttributeError):
                # Instance is no longer valid, remove it
                if instance in cls.open_instances:
                    cls.open_instances.remove(instance)
                    
    @classmethod
    def close_all_instances(cls):
        """Close all open HCI Command Center windows"""
        # Make a copy to avoid list modification during iteration
        instances = list[HciMainUI](cls.open_instances)
        for instance in instances:
            try:
                instance._cleanup()
            except (RuntimeError, AttributeError):
                # Instance is already invalid
                pass
        cls.open_instances.clear()
                
    @classmethod
    def close_instance(cls, instance: 'HciMainUI') -> None:
        """Close a specific instance of HciMainUI"""
        if instance in cls.open_instances:
            try:
                instance._cleanup()
            except (RuntimeError, AttributeError):
                # Instance is already invalid
                pass
            if instance in cls.open_instances:
                cls.open_instances.remove(instance)
                
    
    def __repr__(self):
        return f"<HciCommandManager parent={self.main_window}, cmd_factory={self._cmd_factory}, evt_factory={self._evt_factory}>"
    def __str__(self):
        return f"HciCommandManager(parent={self.main_window}, cmd_factory={self._cmd_factory}, evt_factory={self._evt_factory})"
    def __len__(self):
        """Return the number of command windows currently managed"""
        return len(self._cmd_factory) if self._cmd_factory else 0
    def __contains__(self, cmd_opcode: int) -> bool:
        """Check if a command window with the given opcode exists"""
        return cmd_opcode in self._cmd_factory if self._cmd_factory else False
    def __getitem__(self, cmd_opcode: int) -> Optional[HCICmdUI]:
        """Get a command window by its opcode"""
        return self._cmd_factory[cmd_opcode] if self._cmd_factory else None
    
    ############################################################
    ##== Initialization and UI Setup ===##
    #############################################################
    def __init__(self, main_window : QMainWindow, *, title : Optional[str] = "HCI Command Center" , transport : Transport):
        """Initialize the HCI Main UI"""
        super().__init__()
        self._is_destroyed = False  # Flag to track if the instance is destroyed
        
        self.main_window = main_window
        self.sub_window : QMdiSubWindow = None
        self.title = title
        self._destroy_window_handler : callable = None
        
        # cmd selector window
        self.command_selector : HciCommandSelector = None  # Command selector widget
        # cmd factory and evt factory
        self._cmd_factory : HCICommandFactory = None
        self._evt_factory : HCIEventFactory = None
        # transport instance
        self.transport : Transport = transport
        
        self.init_ui()
        self.show_window()
        
        # Add this instance to the list of open instances
        HciMainUI.open_instances.append(self)
        
            
    def __del__(self):
        """Destructor to clean up resources"""
        if not self._is_destroyed:
            self._cleanup()

    def _cleanup(self):
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
          
        # Call destroy handler if set
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
        self.command_selector = HciCommandSelector(self.transport.transport_instance.get_config["baudrate"])
        self.command_selector.command_selected.connect(lambda category_opcode, command_opcode : self._cmd_factory.execute_command(category=category_opcode, opcode=command_opcode))
        def _on_enable_changed(state) -> None:
            """Handle enable checkbox state change"""
            is_enabled = (state == Qt.Checked)
            if is_enabled:
                self.transport.connect()
            else:
                self.transport.disconnect()
        self.command_selector.enable_checkbox.stateChanged.connect(_on_enable_changed)
        
        # command selector will set the widget properly
        main_layout.addWidget(self.command_selector)
        
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

         # set the window flags to make it a top-level, resizable window
        self.sub_window.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)

        self.sub_window.setWindowFlags(Qt.Window)  # Set window flags to make it a top-level window
        self.sub_window.setWindowModality(Qt.ApplicationModal)  # Set window modality to application modal
        # sizing the subwindow
        self.sub_window.resize(300, 700)
        self.sub_window.setMinimumSize(200, 400)  # Set minimum size
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)  # Enable deletion on close
        
        
        # define the command and event factories
        self._cmd_factory = HCICommandFactory(self.title, self.sub_window, self.transport)
        self._evt_factory = HCIEventFactory(self.title, self.sub_window, self.transport)
        
        # callbacks when transport state changes
        self.transport.add_callback(TransportEvent.CONNECT, self.command_selector._on_device_connected)
        self.transport.add_callback(TransportEvent.DISCONNECT, self.command_selector._on_device_disconnected)
        self.transport.add_callback(TransportEvent.DISCONNECT, lambda _ : (self._cmd_factory.close_all_command_windows(), self._evt_factory.close_all_event_windows()))

        # callback when subwindow is destroyed
        self.sub_window.destroyed.connect(lambda : (setattr(self, 'sub_window', None), self._cleanup()))
        # show the subwindow in the main window's MDI area
        self.sub_window.raise_()  # Bring the subwindow to the front
        self.sub_window.activateWindow()  # Activate the subwindow
        self.sub_window.setFocus()  # Set focus to the subwindow
       
    def show_window(self):
        """Show the HCI Main UI in a subwindow"""    
        # Add the subwindow to the MDI area
        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        
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
        self._cmd_factory.raise_all_windows()
        self._evt_factory.raise_all_windows()
        