"""
HCI Command Module initialization

This module provides functionality for creating and parsing HCI commands.
"""

from typing import Dict, Type, Optional, Any, Union

from .cmd_baseui import HCICmdUI


# Command registry - maps opcodes to command classes
_cmd_ui_registry : Dict[int, Type[HCICmdUI]] = {}

# Forward imports for easier access
# These will be populated during initialization
# link_policy = None
# link_controller = None
# status = None
# le_cmds = None
# controller_baseband = None
# information = None
# testing = None
# vs_specific = None

def register_command_ui(cmd_class: Type[HCICmdUI]) -> None:
    """
        Register a command class with its opcode
        Args: cmd_class: Command class to register
    """
    # print(f"Registering command {cmd_class.__name__} with opcode 0x{cmd_class.OPCODE:04X} in file {cmd_class.__module__}")
    if not hasattr(cmd_class, 'OPCODE'):
        raise ValueError(f"Command class {cmd_class.__name__} has no OPCODE defined")
    
    opcode = cmd_class.OPCODE
    # print(f"Registering command {cmd_class.__name__} with opcode 0x{opcode:04X} in file {cmd_class.__module__}\r\n caller {__file__}")
    if opcode in _cmd_ui_registry:
        raise ValueError(f"Command with opcode 0x{opcode:04X} already registered as {_cmd_ui_registry[opcode].__name__}")
    
    _cmd_ui_registry[opcode] = cmd_class

def get_cmd_ui_class(opcode: int) -> Optional[Type[HCICmdUI]]:
    """Get command class from opcode"""
    return _cmd_ui_registry.get(opcode)

# def cmd_from_bytes(data: bytes) -> Optional[HciCommandUI]:
#     """
#     Parse HCI command from complete command bytes
    
#     Args:
#         data: Complete command bytes including header
        
#     Returns:
#         Parsed command object or None if parsing failed
#     """
#     if len(data) < 3:  # Need at least opcode (2 bytes) and length (1 byte)
#         return None
    
#     opcode, length = struct.unpack("<HB", data[:3])
#     cmd_class = get_command_class(opcode)
    
#     if cmd_class is None:
#         ogf = (opcode >> 10) & 0x3F
#         ocf = opcode & 0x03FF
#         print(f"Unknown command with opcode 0x{opcode:04X} (OGF=0x{ogf:02X}, OCF=0x{ocf:04X})")
#         return None
    
#     return cmd_class.from_bytes(data[3:])

from . import link_policy
from . import link_control
from . import status
from . import le
from . import controller_baseband
from . import information
from . import testing
from . import vendor_specific
        

__all__ = [
    'register_command_ui',
    'get_cmd_ui_class',
    'link_policy',
    'link_control',
    'status',
    'le',
    'controller_baseband',
    'information',
    'testing',
    'vendor_specific',
]