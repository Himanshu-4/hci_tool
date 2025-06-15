"""
HCI Base UI Module

This module provides base classes for HCI command and event UI elements.
It defines common functionality for all HCI UI components.
"""

import traceback
import weakref
import inspect

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QFormLayout, QGroupBox, QDialog, QDialogButtonBox,
    QFrame, QScrollArea, QLayout
)
from PyQt5.QtGui import QTextCursor, QIntValidator, QFont, QCloseEvent
from PyQt5.QtCore import Qt, pyqtSignal, QObject

from transports.transport import Transport


from abc import ABC, abstractmethod
from typing import ClassVar, Type, Optional, Dict, Any, Union, Tuple


# Import HCI library 
import hci.cmd as hci_cmd
import hci.evt as hci_evt

class HciBaseUI(QDialog):
    """Base class for HCI UI components"""
    OPCODE: ClassVar[int]  # The command opcode (2 bytes)
    NAME: ClassVar[str]    # Human-readable name of the command
    #signal emited when the window is closed 
    window_closing = pyqtSignal(object)  # Custom signal for window closing
    
    def __init__(self, title: str, parent=None):
        """Initialize the HCI UI with a title and parent widget"""
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.title = title
        self.invalid_params : str = ""
        self.command_class = None  # Placeholder for command class
        self._main_layout = None
        self.content_layout = None
        self._is_destroyed = False  # Flag to track if the window is destroyed
        self.parent = weakref.ref(parent) if parent else None
         # Make windows stay on top of main window but not system-wide
        if parent:
            self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        # call the setup_ui method to initialize the UI
        self.setup_ui()    
    
    def __del__(self):
        """Destructor to clean up resources"""
        if not self._is_destroyed:
            self.cleanup()
            
    def cleanup(self):
        """Explicit cleanup method"""
        if self._is_destroyed:
            return
        self._is_destroyed = True
        
    def setup_ui(self):
        """Initialize the base UI components"""
        self.setWindowTitle(self.title)
        # self.setWindowModality(Qt.ApplicationModal)  # Make it modal to the parent/high priority window
        # self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        # self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # self.setAttribute(Qt.WA_ShowModal, True)  # Show as modal dialog
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        
        self._main_layout = QVBoxLayout()
        
        # add the cmd title bar to show the command name
        self._title_layout = QHBoxLayout()
        self._title_layout.setContentsMargins(0, 0, 0, 0)
        self._title_layout.setSpacing(5)
        # self._title_layout.setAlignment(Qt.AlignCenter)
        self._title_layout.setSizeConstraint(QLayout.SetFixedSize)
        self._title_layout.setStretch(0, 1)
        
        self._name_label = QLabel()
        self._name_label.setText(self.__class__.NAME)
        self._title_layout.addWidget(self._name_label)
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # create vbox layout to accomodate command or event widgets and params
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        # self.content_layout.setSpacing(5)

        #create a Hboxlayout to hold the command or event error messages in a label
        self._cmd_error_layout = QHBoxLayout()
        self._cmd_error_layout.setContentsMargins(0, 0, 0, 0)
        self._cmd_error_layout.setSpacing(5)
        self._cmd_error_layout.setSizeConstraint(QLayout.SetFixedSize)
        self._cmd_error_layout.setStretch(0, 1)
        
        self._error_label = QLabel()
        self._error_label.setText("dummy error")
        self._cmd_error_layout.addWidget(self._error_label)
        self._error_label.setAlignment(Qt.AlignLeft)
        self._error_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._error_label.setStyleSheet("color: red;")  # Set error label color to red
        self._error_label.setWordWrap(True)  # Enable word wrapping
        self._error_label.setVisible(False)  # Initially hidden
        
        # add a layout for holding the ok and cancel buttons
        self._button_layout = QHBoxLayout()
        self._button_layout.setContentsMargins(0, 0, 0, 0)
        self._button_layout.setSpacing(5)
        self._button_layout.setSizeConstraint(QLayout.SetFixedSize)
        self._button_layout.setStretch(0, 1)
        self._button_layout.setStretch(1, 1)

        # add buttons to the layout
        self.ok_button = QPushButton("Ok")
        self.ok_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.ok_button.clicked.connect(self.on_ok_button_clicked)
        self.ok_button.setDefault(True)  # Set as default button
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.cancel_button.clicked.connect(self.on_cancel_button_clicked)
        self.cancel_button.setDefault(True) # set as default button
        
        self._button_layout.addWidget(self.ok_button)
        self._button_layout.addWidget(self.cancel_button)
        
        
        # Add all components to main layout
        self._main_layout.addLayout(self._title_layout)
        self._main_layout.addLayout(self.content_layout,1)
        self._main_layout.addLayout(self._cmd_error_layout)
        self._main_layout.addLayout(self._button_layout)
        
        self.setLayout(self._main_layout)
    
    
    @abstractmethod
    def on_ok_button_clicked(self):
        """Handle OK button click"""
        pass
    
    @abstractmethod
    def on_cancel_button_clicked(self):
        """Handle Cancel button click"""
        pass
    
    def log(self, message: str):
        """Log a message to the console or UI"""
        # @todo :replace by logger methods 
        # This is a placeholder - subclasses should implement this
        print(message)
        

    def bring_to_front(self):
        """Bring this window to front"""
        self.raise_()
        self.activateWindow()
        self.showNormal()  # In case it was minimized
    
    def get_parent(self):
        """Safely get the parent window"""
        if self.parent is None:
            return None
        parent = self.parent()
        # Check if the parent still exists and hasn't been deleted
        if parent is None:
            return None
        try:
            # Try to access a property to see if the object is still valid
            _ = parent.windowTitle()
            return parent
        except RuntimeError:
            # Object has been deleted by Qt
            return None
        
    def add_to_parent(self):
        """Add this window to the parent's tracking system"""
        if self.parent and hasattr(self.parent, 'register_subwindow'):
            # Determine window type based on class hierarchy
            window_type = 'unknown'
            if 'Cmd' in self.__class__.__name__:
                window_type = 'command'
            elif 'Evt' in self.__class__.__name__:
                window_type = 'event'
                
            self.parent.register_subwindow(self, window_type)
            
    def closeEvent(self, event):
        """Handle window close event"""
        if not self._is_destroyed:
        # Emit signal that window is closing
            self.window_closing.emit(self)
            self.cleanup()  # Clean up resources
        super().closeEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press - bring window to front"""
        if self._is_destroyed:
            return
        try:
            super().mousePressEvent(event)
            if event.button() == Qt.LeftButton:
                self.bring_to_front()
        except RuntimeError:
            pass  # Ignore if the window is already destroyed
            
    def focusInEvent(self, event):
        """Handle focus events"""
        try:
            super().focusInEvent(event)
            parent = self.parent()
            # Update the parent that this window is now active
            if parent and hasattr(parent, 'status_bar'):
                self.parent.status_bar.showMessage(f"Active: {self.windowTitle()}")
        except RuntimeError:
            pass
     #logging function to log messages to the console or UI
    def log_error(self, message: str):
        """Log an error message to the command error label"""
        if self._is_destroyed:
            return
        # log the full traceback to console
        traceback.print_exc()  # Print the full traceback to console.
        try:
            self._error_label.setText(message)
            self._error_label.setVisible(True)
        except RuntimeError:
            # Widget has been destroyed
            pass
        
    def clear_error(self):
        """Clear the command error label"""
        if self._is_destroyed:
            return
        try:
            self._error_label.setText("")
            self._error_label.setVisible(False)
        except RuntimeError:
            # Widget has been destroyed
            pass

##### HCI Command and Event UI Classes
# These classes are specific implementations of the HciBaseUI for commands and events


class HCICmdBaseUI(HciBaseUI):
    """Base class for HCI command UI components"""
    
    # Class variables to be defined by subclasses
    OPCODE: ClassVar[int]  # The command opcode (2 bytes)
    NAME: ClassVar[str]    # Human-readable name of the command
    command_sent = pyqtSignal(bytes)
    
    def __init__(self, title="HCI Command", parent=None, transport : Optional[Transport] = None):
        """Initialize the HCI command UI with a title and parent widget"""
        super().__init__(title, parent) 
        self.transport = transport
        
    def setup_ui(self):
        """Set up the UI for command input"""
        super().setup_ui()
        
    def set_command_class(self, command_class: Type['HCICmdBaseUI']):
        """Set the command class for this UI"""
        self.command_class = command_class
        self._error_label.setText("")
        self._error_label.setVisible(False)
        
        # Set the command opcode
        if hasattr(self.command_class, 'OPCODE'):
            self.OPCODE = self.command_class.OPCODE
        else:
            raise ValueError("Command class does not have an OPCODE defined")
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """Validate the parameters entered in the UI"""
        # This is a placeholder - subclasses should implement this
        pass
        
    def on_ok_button_clicked(self):
        """Handle OK button click - send the command"""
        if self._is_destroyed:
            return
        ret = None
        byte_data = b''
        try:
            if not self.validate_parameters():
                return
            byte_data = self.get_data_bytes()
            if self.transport:
                ret = self.transport.write(byte_data)
            
        except Exception as e:
            self.log(f"Error OK btn: {str(e)}")
            self.log_error(f"Error : {str(e)}")
            return None
        try:
            self.close()
            if ret:
                self.command_sent.emit(byte_data)
        except RuntimeError:
            # Window already destroyed
            pass
    
    def on_cancel_button_clicked(self):
        """Handle Cancel button click - close the window"""
        try:
            self.close()
        except RuntimeError:
            # Window already destroyed
            pass


    @abstractmethod
    def add_command_parameters(self):
        """Add parameter input fields based on the command class"""
        # This is a placeholder - subclasses should implement this
        pass
    
    @abstractmethod
    def get_data_bytes(self) -> Optional[bytes]:
        """Get values from input fields"""
        # This is a placeholder - subclasses should implement this
        pass




class HCIEvtBaseUI(HciBaseUI):
    """Base class for HCI event UI components"""
    
    OPCODE: ClassVar[int]  # The command opcde for the successful event or completion (2 bytes)
    
    EVENT_CODE : ClassVar[int]  # The event code (1 byte)
    SUB_EVENT_CODE: Optional[int] = None  # Sub-event code (if applicable, 1 byte)
    NAME: ClassVar[str]    # Human-readable name of the event
    event_rcvd = pyqtSignal(bytes)
    
    def __init__(self, title="HCI Event",parent = None, event_instance=None):
        self.event_instance = event_instance
        super().__init__(title, parent)
    
    def setup_ui(self):
        """Set up the UI for event display"""
        super().setup_ui()
  
    def on_ok_button_clicked(self):
        """Handle OK button click - close the window"""
        try:
            self.close()
        except RuntimeError:
            # Window already destroyed
            pass
        
    def on_cancel_button_clicked(self):
        """Handle Cancel button click - close the window"""
        try:
            self.close()
        except RuntimeError:
            # Window already destroyed
            pass
        
    @abstractmethod
    def display_event_details(self):
        """Display the details of the event in the UI"""
        # This is a placeholder - subclasses should implement this
        pass
    
    def set_event_instance(self, event_instance):
        """Set the event instance for this UI"""
        if self._is_destroyed:
            return
        self.event_instance = event_instance
        self.display_event_details()
        try:
            self._name_label.setText(self.event_instance.__class__.__name__)
            self._name_label.setText("")
            self._name_label.setVisible(False)
        except (RuntimeError, AttributeError):
            # Widget has been destroyed or event_instance is None
            pass

    
    def process_event(self, event_bytes):
        # @todo have to implement this properly
        """Process an event and update the UI"""
        if self._is_destroyed:
            return False
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