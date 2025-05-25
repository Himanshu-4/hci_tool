from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QGroupBox, QSplitter
)

from typing import Optional

from PyQt5.QtGui import QTextCursor, QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal

from .hci_main_ui import HciMainUI
from transports.transport import Transport


class HCIControlUI:
    """
    Main HCI Control class - integrates command UI and event handling.
    """
    
    def __init__(self, main_window : Optional[QMainWindow],  transport : Transport, title : Optional[str] = "HCIControlUI"): 
        """Initialize the HCI Control with reference to the main window"""
        self.main_window = main_window
        self._is_destroyed = False
        
        # Create the main UI
        self.main_ui = HciMainUI(main_window, title=title, transport=transport)
        # register destroy method        
        self.main_ui.register_destroy(lambda: self._on_main_ui_closed())

    def __del__(self):
        """Destructor to clean up the instance"""
        if not self._is_destroyed:
            self.cleanup()

    def cleanup(self):
        """Explicit cleanup method"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        print("HCIControlUI instance deleted")
        
        if hasattr(self, 'main_ui') and self.main_ui:
            try:
                self.main_ui.cleanup()
            except (RuntimeError, AttributeError):
                # UI already destroyed
                pass
            self.main_ui = None
            
        if hasattr(self, 'event_handler'):
            self.event_handler = None

        
    def _on_main_ui_closed(self):
        """Handle closing of the main UI"""
        if self._is_destroyed:
            return
            
        print("HCIControlUI closed")
        if hasattr(self, '_destroy_window_handler') and self._destroy_window_handler:
            try:
                self._destroy_window_handler()
            except Exception:
                pass  # Ignore errors in handler
                
        self.cleanup()

    
    def register_destroy(self, handler : Optional[callable]):
        """ create a property function that assigned in different methods
        and can be called here above """
        self._destroy_window_handler = handler
        
    def process_hci_event(self, event_data):
        """Process an incoming HCI event packet"""
        if not self._is_destroyed and hasattr(self, 'event_handler') and self.event_handler:
            self.event_handler.process_hci_packet(event_data)
    
    def simulate_event(self, event_code, event_data):
        """Simulate an HCI event for testing purposes"""
        if not self._is_destroyed and hasattr(self, 'event_handler') and self.event_handler:
            self.event_handler.simulate_event(event_code, event_data)


# Class for the HCI Control Window interface
class HCIControlWindow(QWidget):
    """User interface for the HCI Control functionality"""
    
    def __init__(self, main_wind=None):
        """Initialize the HCI Control Window"""
        super().__init__()
        
        self.main_wind = main_wind
        self.init_ui()
    
    def init_ui(self):
        """Set up the UI layout and components"""
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header section
        header_layout = QHBoxLayout()
        header_label = QLabel("HCI Control")
        header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)
        main_layout.addLayout(header_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Command selection
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Add connect button
        connect_button = QPushButton("Connect Device")
        connect_button.clicked.connect(self.open_connect_window)
        left_layout.addWidget(connect_button)
        
        # Add commands button
        commands_button = QPushButton("HCI Commands")
        commands_button.clicked.connect(self.open_hci_command_window)
        left_layout.addWidget(commands_button)
        
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)
        
        # Right panel - Log area
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Add log area
        log_group = QGroupBox("HCI Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # Add event simulation section (for testing)
        sim_group = QGroupBox("Event Simulation")
        sim_layout = QGridLayout()
        
        sim_layout.addWidget(QLabel("Event Code (hex):"), 0, 0)
        self.event_code_input = QLineEdit("03")  # Default: Connection Complete
        sim_layout.addWidget(self.event_code_input, 0, 1)
        
        sim_layout.addWidget(QLabel("Event Data (hex):"), 1, 0)
        self.event_data_input = QLineEdit("00 0001 112233445566 01 00")  # Default data for Connection Complete
        sim_layout.addWidget(self.event_data_input, 1, 1)
        
        simulate_button = QPushButton("Simulate Event")
        simulate_button.clicked.connect(self.simulate_event)
        sim_layout.addWidget(simulate_button, 2, 0, 1, 2)
        
        sim_group.setLayout(sim_layout)
        right_layout.addWidget(sim_group)
        
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        
        # Set initial sizes
        splitter.setSizes([200, 400])
        
        main_layout.addWidget(splitter)
        
        # Set the main layout
        self.setLayout(main_layout)
    
    def open_connect_window(self):
        """Open the Connect Window"""
        if not ConnectWindow.is_instance():
            ConnectWindow(self.main_wind)
    
    def open_hci_command_window(self):
        """Open the HCI Command Window"""
        if HCIControl.is_inited():
            if not HCIControl.is_open():
                # Recreate the window if it's not visible
                HCIControl.create_instance(self.main_wind)
        else:
            # Create a new instance
            HCIControl.create_instance(self.main_wind)
    
    def simulate_event(self):
        """Simulate an HCI event for testing"""
        try:
            # Parse event code from hex
            event_code = int(self.event_code_input.text(), 16)
            
            # Parse event data from hex
            hex_data = self.event_data_input.text().replace(" ", "")
            if len(hex_data) % 2 != 0:
                raise ValueError("Hex data must have an even number of characters")
            
            event_data = bytearray.fromhex(hex_data)
            
            # Log the simulation
            self.log_area.append(f"Simulating HCI event 0x{event_code:02X} with data: {event_data.hex()}")
            
            # If HCI Control is initialized, send the event
            if HCIControl.is_inited():
                hci_control = HCIControl.get_instance()
                hci_control.simulate_event(event_code, event_data)
            else:
                self.log_area.append("Error: HCI Control not initialized. Open the HCI Commands window first.")
        
        except ValueError as e:
            self.log_area.append(f"Error parsing input: {str(e)}")
    
    @staticmethod
    def is_instance():
        """Check if ConnectWindow instance exists"""
        return ConnectWindow._instance is not None
    
    
    
"""
HCI SubWindow Module

This module defines an MDI subwindow class that can be used in the HCI tool UI.
It provides a container for HCI-related UI components and handles window management.
"""
from PyQt5.QtWidgets import QMdiSubWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent

class HciSubWindow(QMdiSubWindow):
    """
    A customized MDI subwindow for the HCI tool.
    
    This class provides a standardized container for HCI UI components, with consistent
    window behavior, styling, and lifecycle management.
    """
    
    # Signal emitted when the window is closed
    closed = pyqtSignal(str)  # Emits the window title
    
    def __init__(self, widget: QWidget = None, window_title: str = "", parent=None):
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
        self.windowIconText(window_title)  # Set window icon text
        
        # Configure the layout if a widget is provided
        if widget:
            self.setWidget(widget)
        
        # Default size
        self.resize(600, 400)
    
    def closeEvent(self, event: QCloseEvent):
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

