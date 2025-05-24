"""
    HCI Command Factory
    This module provides a factory for creating HCI command windows.
    It manages the creation, positioning, and lifecycle of command windows.
    Each command window is associated with a specific HCI command type.
    The factory ensures that command windows are opened in a consistent manner,
    and provides functionality to close all command windows when needed.
    The command windows are created based on the command type and are positioned
    relative to the main window. The factory also keeps track of all open command
    windows, allowing for easy management and cleanup.
    The command windows are created using the appropriate classes from the
    hci_ui.cmds module, which contains the definitions for each command type.
    The command types include:
    - Controller and Baseband commands
    - Link Control commands
    - LE commands
    - Information commands
    - Status commands
    - Testing commands
    - Vendor-specific commands  
    The command windows are displayed in a cascading manner, with each new window
    offset from the previous one. This provides a clear and organized layout for
    the user to interact with multiple command windows simultaneously.
    The factory also provides a method to close all open command windows, ensuring
    that resources are properly released when the user is done with the HCI commands.
"""

# import all the command classes
from .cmds.link_control import *
from .cmds.link_policy import *
from .cmds.controller_baseband import *
from .cmds.le import *
from .cmds.information import *
from .cmds.status import *
from .cmds.testing import *
from .cmds.vendor_specific import *

from .cmds import get_cmd_ui_class

# Import other command classes as needed

class HCICommandFactory:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.command_windows = {}
        
    def create_command_window(self, cmd_type):
        """Create a command window based on the command type"""
        cmd_window = None
        
        # Controller and Baseband commands
        if cmd_type == "RESET":
            cmd_window = ResetCmd(self.parent)
        elif cmd_type == "SET_EVENT_MASK":
            cmd_window = SetEventMaskCmd(self.parent)
        elif cmd_type == "READ_LOCAL_VERSION":
            cmd_window = ReadLocalVersionCmd(self.parent)
        
        # Link Control commands
        elif cmd_type == "CREATE_CONNECTION":
            cmd_window = CreateConnectionCmd(self.parent)
        elif cmd_type == "DISCONNECT":
            cmd_window = DisconnectCmd(self.parent)
        
        # Add other command types here
        
        if cmd_window:
            # Add to parent's tracking system
            cmd_window.add_to_parent()
            
            # Store in our local tracking
            self.command_windows[cmd_type] = cmd_window
            
            # Position the window relative to main window
            self.position_window(cmd_window)
            
            # Show the window
            cmd_window.show()
            cmd_window.raise_()
            cmd_window.activateWindow()
            
        return cmd_window
    
    def position_window(self, window):
        """Position the window relative to the main window"""
        if self.parent:
            # Get main window geometry
            main_rect = self.parent.geometry()
            
            # Calculate offset position
            offset_x = 50 + (len(self.command_windows) * 30)
            offset_y = 50 + (len(self.command_windows) * 30)
            
            # Set new position
            new_x = main_rect.x() + offset_x
            new_y = main_rect.y() + offset_y
            
            window.move(new_x, new_y)
    
    def close_all_command_windows(self):
        """Close all open command windows"""
        for window in list(self.command_windows.values()):
            try:
                if window:
                    window.close()
            except RuntimeError:
                # Window already destroyed
                pass
        self.command_windows.clear()

