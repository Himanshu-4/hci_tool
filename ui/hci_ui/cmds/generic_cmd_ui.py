"""
Generic Command UI Module

This module provides generic UI components for HCI commands that don't have
specific UI implementations.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout,
    QFormLayout, QGroupBox, QDialog, QDialogButtonBox,
    QSpinBox, QDoubleSpinBox
)
from PyQt5.QtGui import QTextCursor, QIntValidator, QFont
from PyQt5.QtCore import Qt, pyqtSignal

import inspect
import types
import enum
from typing import get_type_hints, get_origin, get_args, Union, Optional, List

from hci_ui.hci_base_ui import HciCommandUI

class GenericCommandUI(HciCommandUI):
    """Generic UI for HCI commands with automatic parameter input fields"""
    
    def __init__(self, title, command_class, parent=None):
        super().__init__(title, command_class, parent)
        self.param_widgets = {}  # Store references to parameter widgets
    
    def add_command_parameters(self):
        """Add parameter input fields based on the command class __init__ signature"""
        try:
            # Get the __init__ method of the command class
            init_method = self.command_class.__init__
            
            # Get the signature
            sig = inspect.signature(init_method)
            
            # For each parameter (excluding 'self')
            for param_name, param in list(sig.parameters.items())[1:]:
                # Skip 'kwargs' type parameters
                if param.kind == param.VAR_KEYWORD:
                    continue
                
                # Determine type and default value
                param_type = self._get_parameter_type(param)
                default_value = param.default if param.default != param.empty else None
                
                # Create an appropriate widget based on the type
                widget = self._create_widget_for_type(param_name, param_type, default_value)
                
                # Add to layout
                if widget:
                    self.params_layout.addRow(f"{param_name}:", widget)
                    self.param_widgets[param_name] = widget
        except Exception as e:
            self.log(f"Error adding command parameters: {str(e)}")
    
    def _get_parameter_type(self, param):
        """Get the type of a parameter"""
        # Try to get the annotation
        if param.annotation != param.empty:
            return param.annotation
        
        # If no annotation, try to infer from default value
        if param.default != param.empty:
            return type(param.default)
        
        # Default to str if unknown
        return str
    
    def _create_widget_for_type(self, param_name, param_type, default_value):
        """Create an appropriate widget based on the parameter type"""
        # Handle Union types (e.g., Union[int, SomeEnum])
        if get_origin(param_type) is Union:
            # Get the subtypes
            args = get_args(param_type)
            # Use the first type that's not NoneType
            for arg in args:
                if arg is not type(None):  # Not using 'is not None' to avoid confusion
                    param_type = arg
                    break
        
        # Handle Optional types (e.g., Optional[int])
        if get_origin(param_type) is Optional:
            param_type = get_args(param_type)[0]
        
        # Handle bytes or List[int]
        if param_type == bytes or (get_origin(param_type) is list and get_args(param_type)[0] == int):
            # Hex input for bytes
            widget = QLineEdit()
            if default_value:
                widget.setText(default_value.hex())
            else:
                widget.setPlaceholderText("Enter hex bytes (e.g., 01A2B3)")
            return widget
        
        # Handle enums
        elif isinstance(param_type, type) and issubclass(param_type, enum.Enum):
            widget = QComboBox()
            # Add enum values
            for value in param_type:
                widget.addItem(f"{value.name} (0x{value.value:X})", value.value)
            # Set default if provided
            if default_value is not None:
                for i in range(widget.count()):
                    if widget.itemData(i) == default_value:
                        widget.setCurrentIndex(i)
                        break
            return widget
        
        # Handle booleans
        elif param_type == bool:
            widget = QCheckBox()
            if default_value is not None:
                widget.setChecked(default_value)
            return widget
        
        # Handle integers
        elif param_type == int:
            widget = QSpinBox()
            widget.setRange(-0x80000000, 0x7FFFFFFF)  # Full 32-bit range
            if default_value is not None:
                widget.setValue(default_value)
            return widget
        
        # Handle floats
        elif param_type == float:
            widget = QDoubleSpinBox()
            if default_value is not None:
                widget.setValue(default_value)
            return widget
        
        # Default to string input
        else:
            widget = QLineEdit()
            if default_value is not None:
                widget.setText(str(default_value))
            return widget
    
    def get_parameter_values(self):
        """Get parameter values from the input widgets"""
        values = {}
        
        for param_name, widget in self.param_widgets.items():
            try:
                # Get the value based on widget type
                if isinstance(widget, QLineEdit):
                    # Check if this is a hex input for bytes
                    if widget.placeholderText() and "hex" in widget.placeholderText():
                        # Convert hex string to bytes
                        hex_str = widget.text().strip()
                        # Handle empty string
                        if not hex_str:
                            values[param_name] = b''
                        else:
                            # Remove any spaces and '0x' prefixes
                            hex_str = hex_str.replace(' ', '').replace('0x', '')
                            # Add leading zero if odd length
                            if len(hex_str) % 2 != 0:
                                hex_str = '0' + hex_str
                            values[param_name] = bytes.fromhex(hex_str)
                    else:
                        values[param_name] = widget.text()
                
                elif isinstance(widget, QComboBox):
                    # Get the data value (the enum value)
                    values[param_name] = widget.currentData()
                
                elif isinstance(widget, QCheckBox):
                    values[param_name] = widget.isChecked()
                
                elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                    values[param_name] = widget.value()
                
                # Add more types as needed
            
            except Exception as e:
                self.log(f"Error getting value for parameter '{param_name}': {str(e)}")
        
        return values

class GenericFunctionUI(QWidget):
    """Generic UI for HCI command functions"""
    
    function_called = pyqtSignal(object)  # Signal for when the function is called
    
    def __init__(self, title, function, parent=None):
        super().__init__(parent)
        self.title = title
        self.function = function
        self.setup_ui()
        self.param_widgets = {}  # Store references to parameter widgets
    
    def setup_ui(self):
        """Set up the UI"""
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Header
        self.header_label = QLabel(self.title)
        self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.header_label)
        
        # Function parameters
        self.params_group = QGroupBox("Function Parameters")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        self.layout.addWidget(self.params_group)
        
        # Add parameters
        self.add_function_parameters()
        
        # Call button
        self.call_button = QPushButton("Call Function")
        self.call_button.clicked.connect(self.call_function)
        self.layout.addWidget(self.call_button)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)
    
    def log(self, message):
        """Log a message to the log area"""
        self.log_area.append(message)
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.ensureCursorVisible()
    
    def add_function_parameters(self):
        """Add parameter input fields based on the function signature"""
        try:
            # Get the signature
            sig = inspect.signature(self.function)
            
            # For each parameter
            for param_name, param in sig.parameters.items():
                # Skip '*args' and '**kwargs' type parameters
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                
                # Determine type and default value
                param_type = param.annotation if param.annotation != param.empty else str
                default_value = param.default if param.default != param.empty else None
                
                # Create an appropriate widget based on the type
                widget = self._create_widget_for_type(param_name, param_type, default_value)
                
                # Add to layout
                if widget:
                    self.params_layout.addRow(f"{param_name}:", widget)
                    self.param_widgets[param_name] = widget
        except Exception as e:
            self.log(f"Error adding function parameters: {str(e)}")
    
    def _create_widget_for_type(self, param_name, param_type, default_value):
        """Create an appropriate widget based on the parameter type"""
        # Similar to GenericCommandUI._create_widget_for_type
        # Handle Union types
        if get_origin(param_type) is Union:
            args = get_args(param_type)
            for arg in args:
                if arg is not type(None):
                    param_type = arg
                    break
        
        # Handle Optional types
        if get_origin(param_type) is Optional:
            param_type = get_args(param_type)[0]
        
        # Handle bytes or List[int]
        if param_type == bytes or (get_origin(param_type) is list and get_args(param_type)[0] == int):
            widget = QLineEdit()
            if default_value:
                widget.setText(default_value.hex() if isinstance(default_value, bytes) else str(default_value))
            else:
                widget.setPlaceholderText("Enter hex bytes (e.g., 01A2B3)")
            return widget
        
        # Handle enums
        elif isinstance(param_type, type) and issubclass(param_type, enum.Enum):
            widget = QComboBox()
            for value in param_type:
                widget.addItem(f"{value.name} (0x{value.value:X})", value.value)
            if default_value is not None:
                for i in range(widget.count()):
                    if widget.itemData(i) == default_value:
                        widget.setCurrentIndex(i)
                        break
            return widget
        
        # Handle booleans
        elif param_type == bool:
            widget = QCheckBox()
            if default_value is not None:
                widget.setChecked(default_value)
            return widget
        
        # Handle integers
        elif param_type == int:
            widget = QSpinBox()
            widget.setRange(-0x80000000, 0x7FFFFFFF)
            if default_value is not None:
                widget.setValue(default_value)
            return widget
        
        # Handle floats
        elif param_type == float:
            widget = QDoubleSpinBox()
            if default_value is not None:
                widget.setValue(default_value)
            return widget
        
        # Default to string input
        else:
            widget = QLineEdit()
            if default_value is not None:
                widget.setText(str(default_value))
            return widget
    
    def get_parameter_values(self):
        """Get parameter values from the input widgets"""
        values = {}
        
        for param_name, widget in self.param_widgets.items():
            try:
                # Get the value based on widget type
                if isinstance(widget, QLineEdit):
                    # Check if this is a hex input for bytes
                    if widget.placeholderText() and "hex" in widget.placeholderText():
                        # Convert hex string to bytes
                        hex_str = widget.text().strip()
                        # Handle empty string
                        if not hex_str:
                            values[param_name] = b''
                        else:
                            # Remove any spaces and '0x' prefixes
                            hex_str = hex_str.replace(' ', '').replace('0x', '')
                            # Add leading zero if odd length
                            if len(hex_str) % 2 != 0:
                                hex_str = '0' + hex_str
                            values[param_name] = bytes.fromhex(hex_str)
                    else:
                        values[param_name] = widget.text()
                
                elif isinstance(widget, QComboBox):
                    values[param_name] = widget.currentData()
                
                elif isinstance(widget, QCheckBox):
                    values[param_name] = widget.isChecked()
                
                elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                    values[param_name] = widget.value()
                
                # Add more types as needed
            
            except Exception as e:
                self.log(f"Error getting value for parameter '{param_name}': {str(e)}")
        
        return values
    
    def call_function(self):
        """Call the function with the parameters"""
        try:
            # Get parameter values
            params = self.get_parameter_values()
            
            # Call the function
            result = self.function(**params)
            
            # Log the result
            self.log(f"Function called: {self.title}")
            self.log(f"Result: {result}")
            
            # Emit the signal
            self.function_called.emit(result)
            
            return result
        except Exception as e:
            self.log(f"Error calling function: {str(e)}")
            return None