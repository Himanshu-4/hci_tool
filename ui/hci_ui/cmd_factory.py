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
import traceback
import weakref

from PyQt5.QtWidgets import  (QMdiSubWindow)

# import the hci command for execution
from hci.cmd import get_command_class, split_opcode, OGF

from .cmds import get_cmd_ui_class
from .cmds import HCICmdUI


from transports.transport import Transport
from typing import ClassVar, Optional, Dict, Type


# Import other command classes as needed

class HCICommandFactory:
    def __init__(self, title : str, parent_window : QMdiSubWindow, transport : Transport):
        self.title = title
        self.transport = transport
        self.parent = parent_window
        self._is_destroyed = False
        # create a dictionary to track command windows and structure as {opcode: HCICmdUI}
        self.command_windows : dict[int, HCICmdUI] = {}

    def __del__(self):  
        """Destructor to ensure all command windows are closed"""
        if not self._is_destroyed:
            self.cleanup()
        
    def cleanup(self):
        """Explicit cleanup method to be called before destruction"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        self.close_all_command_windows()
        self.remove_from_parent()
    
    def get_parent(self):
        """Safely get the parent window"""
        # parent = self.parent
        # # Check if the parent still exists and hasn't been deleted
        # if parent is None:
        #     return None
        # try:
        #     # Try to access a property to see if the object is still valid
        #     _ = parent.windowTitle()
        #     return parent
        # except RuntimeError:
        #     # Object has been deleted by Qt
        #     return None
        return self.parent if self.parent and not self._is_destroyed else None
    
    def __repr__(self):
        return f"<HCICommandFactory parent={self.parent}, windows={len(self.command_windows)}>"
    def __str__(self):
        return f"HCICommandFactory(parent={self.parent}, windows={len(self.command_windows)})"
    def __len__(self):
        """Return the number of command windows currently managed"""
        return len(self.command_windows)
    def __contains__(self, cmd_opcode: int) -> bool:
        """Check if a command window with the given opcode exists"""
        return cmd_opcode in self.command_windows
    def __getitem__(self, cmd_opcode: int) -> Optional[HCICmdUI]:
        """Get a command window by its opcode"""
        return self.command_windows.get(cmd_opcode, None)
    
    def create_command_window(self, cmd_opcode : int) -> Optional[HCICmdUI]:
        """Create a command window based on the OGF and OCF values"""
        if self._is_destroyed:
            return None
            
        cmd_window = None
        parent = self.get_parent()
        cmd_type = get_cmd_ui_class(cmd_opcode)
        
        if cmd_type is not None:
            if cmd_opcode in self.command_windows:
            # If the command window already exists, return it
                cmd_window = self.command_windows[cmd_opcode]
                # raise the window to the front
                cmd_window.raise_()
                cmd_window.activateWindow()
                return cmd_window
            
            # Add to parent's tracking system
            cmd_window = cmd_type(self.title, parent, self.transport)
            cmd_window.window_closing.connect( lambda : self.close_command_window(cmd_opcode))
            # Store in our local tracking
            self.command_windows[cmd_opcode] = cmd_window
            
            # Position the window relative to main window
            self.position_window(cmd_window)
            
            # Show the window
            cmd_window.show()
            cmd_window.raise_()
            cmd_window.activateWindow()
            
        return cmd_window
    
    def position_window(self, window : HCICmdUI):
        """Position the window relative to the main window"""
        parent = self.get_parent()
        if parent:
            try:
                # Get main window geometry
                main_rect = parent.geometry()
                
                # Calculate offset position
                offset_x = 50 + (len(self.command_windows) * 30)
                offset_y = 50 + (len(self.command_windows) * 30)
                
                # Set new position
                new_x = main_rect.x() + offset_x
                new_y = main_rect.y() + offset_y
                
                window.move(new_x, new_y)
            except RuntimeError:
                # Parent window has been deleted, skip positioning
                pass
    
    
    def get_command_window_by_opcode(self, cmd_opcode: int) -> Optional[HCICmdUI]:
        """Get a command window by its opcode"""
        return self.command_windows.get(cmd_opcode, None)
    
    def get_command_window_by_name(self, window_name: str) -> Optional[HCICmdUI]:
        """Get a command window by its name"""
        for window in self.command_windows.values():
            try:
                if window.NAME == window_name:
                    return window
            except RuntimeError:
                # Window has been deleted, skip
                continue
        return None
    
    
    def get_command_window_by_type(self, cmd_type: Type[HCICmdUI]) -> Optional[HCICmdUI]:
        """Get a command window by its type"""
        for window in self.command_windows.values():
            if isinstance(window, cmd_type):
                return window
        return None      

    def add_to_parent(self):
        """Add this factory to the parent window's command tracking"""
        parent = self.get_parent()
        if parent and hasattr(parent, 'add_command_factory'):
            try:
                parent.add_command_factory(self)
            except RuntimeError:
                # Parent has been deleted
                pass
            
    def remove_from_parent(self):
        """Remove this factory from the parent window's command tracking"""
        parent = self.get_parent()
        if parent and hasattr(parent, 'remove_command_factory'):
            try:
                parent.remove_command_factory(self)
            except RuntimeError:
                # Parent has been deleted, nothing to do
                pass
    
    def get_command_window(self, cmd_opcode : int) -> Optional[HCICmdUI]:
        """Get a command window by its opcode"""
        return self.command_windows.get(cmd_opcode, None)

    def get_all_command_windows(self) -> list[Optional[HCICmdUI]]:
        """Get all command windows"""
        return list(self.command_windows.values())
    
    def close_command_window(self, cmd_opcode : int):
        """Close a specific command window by its opcode"""
        if cmd_opcode in self.command_windows:
            window = self.command_windows[cmd_opcode]
            try:
                if window.isVisible():
                    # Close the window
                    window.close()
            except RuntimeError:
                # Window already destroyed
                pass
            # del self.command_windows[cmd_opcode] somehow del is not working here
            # Remove from tracking
            self.command_windows.pop(cmd_opcode, None)
    
    def close_all_command_windows(self):
        """Close all open command windows"""
        for cmd_opcode in list(self.command_windows.keys()):
            self.close_command_window(cmd_opcode)
        self.command_windows.clear()
    
    def raise_all_command_windows(self):
        """Raise all command windows to the front"""
        for cmd_opcode, window in list(self.command_windows.items()):
            try:
                if window.isVisible():
                    window.raise_()
                    window.activateWindow()
            except RuntimeError:
                # Window has been deleted, remove from tracking
                del self.command_windows[cmd_opcode]


    def deafualt_base_cmd_executor(self, opcode : int  , command_data: Optional[dict] = None) -> bool:
        """Default command executor for HCI commands
        This method executes a command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        if command_data is None:
            command_data = {}
        
        # execute the command based on the opcode
        # if command is registered command in hci.cmds 
        cmd_class  = get_command_class(opcode)
        if cmd_class is None:
            print(f"Command with opcode {opcode} not found.")
            return False
        
        # Create an instance of the command class
        cmd_instance = cmd_class(**command_data)
        return self.transport.write(cmd_instance.to_bytes())

    def deafult_controller_baseband_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default controller and baseband command executor
        This method executes a controller and baseband command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the controller and baseband command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_link_control_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default link control command executor
        This method executes a link control command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the link control command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_link_policy_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default link policy command executor
        This method executes a link policy command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the link policy command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_le_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default LE command executor
        This method executes a LE command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the LE command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_info_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default information command executor
        This method executes an information command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the information command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_status_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default status command executor
        This method executes a status command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the status command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_testing_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default testing command executor
        This method executes a testing command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the testing command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def default_vendor_cmd_executor(self, opcode: int, command_data: Optional[dict] = None) -> bool:
        """Default vendor command executor
        This method executes a vendor-specific command based on the opcode and command data.
        It retrieves the command class from the hci.cmds module and executes it.
        Args:
            opcode (int): The opcode of the vendor command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        return self.deafualt_base_cmd_executor(opcode, command_data)
    
    def execute_command(self, cmd_opcode: int, command_data: Optional[dict] = None) -> bool:
        """ first fetch the command type and based on that select the executor
        Args:
            cmd_opcode (int): The opcode of the command to execute.
            command_data (Optional[dict]): Additional data for the command.
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        ogf, ocf = split_opcode(cmd_opcode)
        
        #execute the command based on the OGF and OCF values
        if ogf == OGF.CONTROLLER_BASEBAND:
            return self.deafualt_base_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.LINK_CONTROL:
            return self.default_link_control_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.LINK_POLICY:
            return self.default_link_policy_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.LE_CONTROLLER:
            return self.default_le_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.INFORMATION_PARAMS:
            return self.default_info_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.STATUS_PARAMS:
            return self.default_status_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.TESTING:
            return self.default_testing_cmd_executor(cmd_opcode, command_data)
        elif ogf == OGF.VENDOR_SPECIFIC:
            return self.default_vendor_cmd_executor(cmd_opcode, command_data)
        else:
            print(f"Unknown OGF {ogf} for opcode {cmd_opcode}")
            return False
        
        