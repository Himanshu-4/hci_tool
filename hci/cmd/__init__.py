"""
HCI Command Module initialization

This module provides functionality for creating and parsing HCI commands.
"""

from typing import Dict, Type, Optional, Any, Union
import importlib
import pkgutil
import inspect
import struct
import sys

from .cmd_base_packet import HciCmdBasePacket
from .cmd_opcodes import OPCODE_TO_NAME, OGF

# Command registry - maps opcodes to command classes
_cmd_registry: Dict[int, Type[HciCmdBasePacket]] = {}

# Forward imports for easier access
# These will be populated during initialization
link_policy = None
link_controller = None
status = None
le_cmds = None
controller_baseband = None
information = None
testing = None

def register_command(cmd_class: Type[HciCmdBasePacket]) -> None:
    """Register a command class with its opcode"""
    if not hasattr(cmd_class, 'OPCODE'):
        raise ValueError(f"Command class {cmd_class.__name__} has no OPCODE defined")
    
    opcode = cmd_class.OPCODE
    if opcode in _cmd_registry:
        raise ValueError(f"Command with opcode 0x{opcode:04X} already registered as {_cmd_registry[opcode].__name__}")
    
    _cmd_registry[opcode] = cmd_class

def get_command_class(opcode: int) -> Optional[Type[HciCmdBasePacket]]:
    """Get command class from opcode"""
    return _cmd_registry.get(opcode)

def cmd_from_bytes(data: bytes) -> Optional[HciCmdBasePacket]:
    """
    Parse HCI command from complete command bytes
    
    Args:
        data: Complete command bytes including header
        
    Returns:
        Parsed command object or None if parsing failed
    """
    if len(data) < 3:  # Need at least opcode (2 bytes) and length (1 byte)
        return None
    
    opcode, length = struct.unpack("<HB", data[:3])
    cmd_class = get_command_class(opcode)
    
    if cmd_class is None:
        ogf = (opcode >> 10) & 0x3F
        ocf = opcode & 0x03FF
        print(f"Unknown command with opcode 0x{opcode:04X} (OGF=0x{ogf:02X}, OCF=0x{ocf:04X})")
        return None
    
    return cmd_class.from_bytes(data[3:])

def _initialize_modules():
    """Import all submodules to register commands"""
    global link_policy, link_controller, status, le_cmds, controller_baseband, information, testing
    
    try:
        # Import all command modules
        from . import link_policy
        from . import link_controller
        from . import status
        from . import le_cmds 
        from . import controller_baseband
        from . import information
        from . import testing
    except ImportError as e:
        print(f"Warning: Unable to import some command modules: {e}")

# Initialize modules when this package is imported
_initialize_modules()

__all__ = [
    'register_command',
    'get_command_class',
    'cmd_from_bytes',
    'HciCmdBasePacket',
    'link_policy',
    'link_controller',
    'status',
    'le_cmds',
    'controller_baseband',
    'information',
    'testing',
]