"""
HCI Base UI Module

This module provides base classes for HCI command and event UI elements.
It defines common functionality for all HCI UI components.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QFormLayout, QGroupBox, QDialog, QDialogButtonBox,
    QFrame, QScrollArea
)
from PyQt5.QtGui import QTextCursor, QIntValidator, QFont, QCloseEvent
from PyQt5.QtCore import Qt, pyqtSignal, QObject

import importlib
import inspect
import sys

# Import HCI library 
import hci
import hci.cmd as hci_cmd
import hci.evt as hci_evt

class HciBaseUI(QWidget):
    """Base class for HCI UI components"""
    
    def __init__(self, title="HCI Component", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the basic UI layout"""
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Header label
        self.header_label = QLabel(self.title)
        self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.header_label)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)
    
    def log(self, message):
        """Log a message to the log area"""
        self.log_area.append(message)
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.ensureCursorVisible()

class HciCommandUI(HciBaseUI):
    """Base class for HCI command UI components"""
    
    command_sent = pyqtSignal(bytes)
    
    def __init__(self, title="HCI Command", command_class=None, parent=None):
        self.command_class = command_class
        super().__init__(title, parent)
        
    def setup_ui(self):
        """Set up the UI for command input"""
        super().setup_ui()
        
        # Command parameters area
        self.params_group = QGroupBox("Command Parameters")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        self.layout.addWidget(self.params_group)
        
        # Add parameters if a command class is provided
        if self.command_class:
            self.add_command_parameters()
        
        # Add send button
        self.send_button = QPushButton("Send Command")
        self.send_button.clicked.connect(self.send_command)
        self.layout.addWidget(self.send_button)
    
    def add_command_parameters(self):
        """Add parameter input fields based on the command class"""
        # This is a placeholder - subclasses should implement this
        pass
    
    def get_parameter_values(self):
        """Get values from input fields"""
        # This is a placeholder - subclasses should implement this
        return {}
    
    def send_command(self):
        """Create and send the command"""
        try:
            params = self.get_parameter_values()
            if self.command_class:
                # Create the command instance
                command = self.command_class(**params)
                # Serialize the command
                command_bytes = command.to_bytes()
                # Add packet type for transport layer
                full_bytes = bytes([hci.HciPacketType.COMMAND]) + command_bytes
                # Log the command
                self.log(f"Sending command: {command_bytes.hex()}")
                # Emit the signal with the command bytes
                self.command_sent.emit(full_bytes)
                return full_bytes
            else:
                self.log("Error: No command class specified")
                return None
        except Exception as e:
            self.log(f"Error creating command: {str(e)}")
            return None

class HciEventUI(HciBaseUI):
    """Base class for HCI event UI components"""
    
    def __init__(self, title="HCI Event", event_instance=None, parent=None):
        self.event_instance = event_instance
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Set up the UI for event display"""
        super().setup_ui()
        
        # Event details area
        self.details_group = QGroupBox("Event Details")
        self.details_layout = QFormLayout()
        self.details_group.setLayout(self.details_layout)
        self.layout.addWidget(self.details_group)
        
        # Display event details if an event instance is provided
        if self.event_instance:
            self.display_event_details()
    
    def display_event_details(self):
        """Display the event details"""
        # This is a placeholder - subclasses should implement this
        pass
    
    def process_event(self, event_bytes):
        """Process an event and update the UI"""
        try:
            # Parse the event
            event = hci_evt.hci_evt_parse_from_bytes(event_bytes)
            if event:
                self.event_instance = event
                self.display_event_details()
                return True
            else:
                self.log("Error: Could not parse event")
                return False
        except Exception as e:
            self.log(f"Error processing event: {str(e)}")
            return False

class HciCommandListUI(HciBaseUI):
    """UI for listing and selecting HCI commands within a command type"""
    
    command_selected = pyqtSignal(object)  # Signal for when a command is selected
    
    def __init__(self, title="HCI Commands", command_module=None, parent=None):
        self.command_module = command_module
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Set up the UI for command listing"""
        super().setup_ui()
        
        # Command list
        self.command_list = QListWidget()
        self.command_list.itemClicked.connect(self.on_command_selected)
        self.layout.addWidget(self.command_list)
        
        # Populate command list if a module is provided
        if self.command_module:
            self.populate_command_list()
    
    def populate_command_list(self):
        """Populate the command list from the module"""
        try:
            # Clear the list
            self.command_list.clear()
            
            # Get command classes and functions from the module
            for name, obj in inspect.getmembers(self.command_module):
                # Filter to only include command classes and functions
                if (inspect.isclass(obj) and issubclass(obj, hci.cmd.HciCmdBasePacket) and obj != hci.cmd.HciCmdBasePacket) or \
                   (inspect.isfunction(obj) and name.startswith('_') == False):
                    # Add to list
                    item = QListWidgetItem(name)
                    # Store the actual object as user data
                    item.setData(Qt.UserRole, obj)
                    self.command_list.addItem(item)
        except Exception as e:
            self.log(f"Error populating command list: {str(e)}")
    
    def on_command_selected(self, item):
        """Handle command selection"""
        try:
            # Get the command class or function
            command = item.data(Qt.UserRole)
            if command:
                # Log the selection
                self.log(f"Selected command: {item.text()}")
                # Emit the signal with the command
                self.command_selected.emit(command)
        except Exception as e:
            self.log(f"Error selecting command: {str(e)}")

class HciCommandTypeListUI(HciBaseUI):
    """UI for listing and selecting HCI command types (modules)"""
    
    command_type_selected = pyqtSignal(object)  # Signal for when a command type is selected
    
    def __init__(self, title="HCI Command Types", parent=None):
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Set up the UI for command type listing"""
        super().setup_ui()
        
        # Command type list
        self.type_list = QListWidget()
        self.type_list.itemClicked.connect(self.on_command_type_selected)
        self.layout.addWidget(self.type_list)
        
        # Populate command type list
        self.populate_command_types()
    
    def populate_command_types(self):
        """Populate the command type list from hci.cmd"""
        try:
            # Clear the list
            self.type_list.clear()
            
            # Define the command types
            command_types = [
                ("Link Control", hci_cmd.link_controller),
                ("Link Policy", hci_cmd.link_policy),
                ("Controller & Baseband", hci_cmd.controller_baseband),
                ("Information Parameters", hci_cmd.information),
                ("Status Parameters", hci_cmd.status),
                ("LE Commands", hci_cmd.le_cmds),
                ("Testing", hci_cmd.testing)
            ]
            
            # Add to list
            for name, module in command_types:
                item = QListWidgetItem(name)
                # Store the module as user data
                item.setData(Qt.UserRole, module)
                self.type_list.addItem(item)
        except Exception as e:
            self.log(f"Error populating command types: {str(e)}")
    
    def on_command_type_selected(self, item):
        """Handle command type selection"""
        try:
            # Get the module
            module = item.data(Qt.UserRole)
            if module:
                # Log the selection
                self.log(f"Selected command type: {item.text()}")
                # Emit the signal with the module
                self.command_type_selected.emit(module)
        except Exception as e:
            self.log(f"Error selecting command type: {str(e)}")

class HciEventTypeListUI(HciBaseUI):
    """UI for listing and selecting HCI event types (modules)"""
    
    event_type_selected = pyqtSignal(object)  # Signal for when an event type is selected
    
    def __init__(self, title="HCI Event Types", parent=None):
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Set up the UI for event type listing"""
        super().setup_ui()
        
        # Event type list
        self.type_list = QListWidget()
        self.type_list.itemClicked.connect(self.on_event_type_selected)
        self.layout.addWidget(self.type_list)
        
        # Populate event type list
        self.populate_event_types()
    
    def populate_event_types(self):
        """Populate the event type list from hci.evt"""
        try:
            # Clear the list
            self.type_list.clear()
            
            # Define the event types
            event_types = [
                ("Common Events", hci_evt.common_events),
                ("Link Control Events", hci_evt.link_control_events),
                ("Link Policy Events", hci_evt.link_policy_events),
                ("Controller & Baseband Events", hci_evt.controller_baseband_events),
                ("Information Events", hci_evt.information_events),
                ("Status Events", hci_evt.status_events),
                ("LE Events", hci_evt.le_events),
                ("Testing Events", hci_evt.testing_events)
            ]
            
            # Add to list
            for name, module in event_types:
                item = QListWidgetItem(name)
                # Store the module as user data
                item.setData(Qt.UserRole, module)
                self.type_list.addItem(item)
        except Exception as e:
            self.log(f"Error populating event types: {str(e)}")
    
    def on_event_type_selected(self, item):
        """Handle event type selection"""
        try:
            # Get the module
            module = item.data(Qt.UserRole)
            if module:
                # Log the selection
                self.log(f"Selected event type: {item.text()}")
                # Emit the signal with the module
                self.event_type_selected.emit(module)
        except Exception as e:
            self.log(f"Error selecting event type: {str(e)}")

class HciCommandSubWindow(QMdiSubWindow):
    """MDI Subwindow for HCI command UI"""
    
    def __init__(self, widget, main_window, title="HCI Command"):
        super().__init__()
        self.setWidget(widget)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        self.resize(400, 300)
        self.main_window = main_window
        
        # Add to MDI area
        if hasattr(main_window, 'mdi_area'):
            main_window.mdi_area.addSubWindow(self)
            self.show()

class HciEventSubWindow(QMdiSubWindow):
    """MDI Subwindow for HCI event UI"""
    
    def __init__(self, widget, main_window, title="HCI Event"):
        super().__init__()
        self.setWidget(widget)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        self.resize(400, 300)
        self.main_window = main_window
        
        # Add to MDI area
        if hasattr(main_window, 'mdi_area'):
            main_window.mdi_area.addSubWindow(self)
            self.show()

class HciSubWindow(QMdiSubWindow):
    """
    A customized MDI subwindow for the HCI tool.
    
    This class provides a standardized container for HCI UI components, with consistent
    window behavior, styling, and lifecycle management.
    """
    
    # Signal emitted when the window is closed
    closed = pyqtSignal(str)  # Emits the window title
    
    def __init__(self, widget=None, window_title="", parent=None):
        """
        Initialize the HCI SubWindow.
        
        Args:
            widget: The main widget to display in the subwindow
            window_title: The title for the window
            parent: The parent widget
        """
        super().__init__(parent)
        
        # Save the title for reference
        self.window_title = window_title
        
        # Set window properties
        self.setWindowTitle(window_title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        
        # Configure the layout if a widget is provided
        if widget:
            self.setWidget(widget)
        
        # Default size
        self.resize(600, 400)
    
    def closeEvent(self, event):
        """
        Handle the window close event.
        
        Args:
            event: The close event
        """
        # Emit the closed signal with the window title
        self.closed.emit(self.window_title)
        
        # Call the parent class closeEvent
        super().closeEvent(event)
    
    def maximize(self):
        """
        Maximize the subwindow.
        """
        self.setWindowState(Qt.WindowMaximized)
    
    def restore(self):
        """
        Restore the window to its normal state.
        """
        self.setWindowState(Qt.WindowNoState)
    
    def center_in_parent(self):
        """
        Center the window within its parent MDI area.
        """
        if self.parentWidget():
            parent_rect = self.parentWidget().rect()
            self_rect = self.rect()
            
            x = (parent_rect.width() - self_rect.width()) // 2
            y = (parent_rect.height() - self_rect.height()) // 2
            
            self.move(x, y)

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









# added later +++++++++++++++ temp purpose z
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QFrame, QGroupBox, QDateTimeEdit
)
from PyQt5.QtGui import QTextCursor, QIntValidator, QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime

class HciBaseUI(QWidget):
    """Base class for all HCI UI components"""
    
    def __init__(self, title="HCI Base"):
        super().__init__()
        self.title = title
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # Header section
        self.header_layout = QHBoxLayout()
        self.header_label = QLabel(self.title)
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.header_layout.addWidget(self.header_label)
        self.header_layout.addStretch(1)
        self.main_layout.addLayout(self.header_layout)
        
        # Add a separator line
        self.add_separator()
        
        # Content area - to be overridden by child classes
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)
        
        # Log area
        self.log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        self.log_group.setLayout(log_layout)
        self.main_layout.addWidget(self.log_group)
        
        # Set style
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid silver;
                border-radius: 6px;
                margin-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        
    def add_separator(self):
        """Add a horizontal separator line"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(line)
        
    def log(self, message, color=None):
        """Log a message to the log area with optional color"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        self.log_area.moveCursor(QTextCursor.End)
        if color:
            self.log_area.insertHtml(f'<span style="color:{color};">[{timestamp}] {message}</span><br>')
        else:
            self.log_area.insertHtml(f'[{timestamp}] {message}<br>')
        self.log_area.moveCursor(QTextCursor.End)
        
    def create_bytearray_from_inputs(self):
        """Create a bytearray from UI inputs - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement this method")
        
    def send_command(self):
        """Send the command to the HCI transport layer"""
        try:
            cmd_bytes = self.create_bytearray_from_inputs()
            self.log(f"Sending command: {cmd_bytes.hex()}", "blue")
            # Here you would send the bytearray to your HCI transport
            # Example: transport.send(cmd_bytes)
        except Exception as e:
            self.log(f"Error sending command: {str(e)}", "red")


class HciSubWindow(QMdiSubWindow):
    """Base class for HCI subwindows"""
    
    closed = pyqtSignal(str)  # Signal emitted when window is closed with window title
    
    def __init__(self, widget, title="HCI Window"):
        super().__init__()
        self.setWidget(widget)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowIconText(title)
        
    def closeEvent(self, event):
        """Handle the close event"""
        self.closed.emit(self.windowTitle())
        super().closeEvent(event)


class HciCommandUI(HciBaseUI):
    """Base class for HCI command UI components"""
    
    def __init__(self, title="HCI Command"):
        super().__init__(title)
        self.add_command_ui()
        
    def add_command_ui(self):
        """Add command-specific UI components"""
        # Command parameters group
        self.params_group = QGroupBox("Command Parameters")
        self.params_layout = QGridLayout()
        self.params_group.setLayout(self.params_layout)
        self.content_layout.addWidget(self.params_group)
        
        # Send button
        self.send_button_layout = QHBoxLayout()
        self.send_button = QPushButton("Send Command")
        self.send_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px;")
        self.send_button.clicked.connect(self.send_command)
        self.send_button_layout.addStretch(1)
        self.send_button_layout.addWidget(self.send_button)
        self.content_layout.addLayout(self.send_button_layout)
        
    def add_parameter(self, row, name, widget):
        """Add a parameter to the command UI"""
        label = QLabel(name)
        self.params_layout.addWidget(label, row, 0)
        self.params_layout.addWidget(widget, row, 1)
        return widget


class HciEventUI(HciBaseUI):
    """Base class for HCI event UI components"""
    
    def __init__(self, title="HCI Event"):
        super().__init__(title)
        self.add_event_ui()
        
    def add_event_ui(self):
        """Add event-specific UI components"""
        # Event parameters group
        self.params_group = QGroupBox("Event Parameters")
        self.params_layout = QGridLayout()
        self.params_group.setLayout(self.params_layout)
        self.content_layout.addWidget(self.params_group)
        
    def add_parameter(self, row, name, value):
        """Add a parameter to the event UI"""
        name_label = QLabel(name)
        value_label = QLabel(str(value))
        value_label.setStyleSheet("font-weight: bold;")
        self.params_layout.addWidget(name_label, row, 0)
        self.params_layout.addWidget(value_label, row, 1)
        return value_label
        
    def process_event(self, event_data):
        """Process an incoming HCI event"""
        # To be implemented by subclasses
        pass


class HciEventHandler:
    """Base class for HCI event handlers"""
    
    def __init__(self, mdi_area):
        """Initialize the event handler"""
        self.mdi_area = mdi_area
        self.event_windows = {}  # Map event codes to open windows
        
    def process_event(self, event_code, event_data):
        """Process an HCI event and route it to the appropriate UI"""
        # To be implemented by subclasses
        pass
    
    def register_event_ui(self, event_code, event_ui_class):
        """Register an event UI class for a specific event code"""
        if not hasattr(self, 'event_ui_map'):
            self.event_ui_map = {}
        self.event_ui_map[event_code] = event_ui_class