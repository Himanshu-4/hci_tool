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



class HciCommandUI(HciBaseUI):
    """Base class for HCI command UI components"""
     # Class variables to be defined by subclasses
    OPCODE: ClassVar[int]  # The command opcode (2 bytes)
    NAME: ClassVar[str]    # Human-readable name of the command
    
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