"""
Information HCI Commands

This module provides classes for Information HCI commands.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import HciOpcode, create_opcode, OGF, InformationOCF
from .. import register_command

class ReadBdAddr(HciCmdBasePacket):
    """Read BD_ADDR Command"""
    
    OPCODE = HciOpcode.READ_BD_ADDR
    NAME = "Read_BD_ADDR"
    
    def __init__(self):
        """Initialize Read BD_ADDR Command (no parameters)"""
        super().__init__()
    
    def _validate_params(self) -> None:
        """Validate command parameters (none for Read BD_ADDR)"""
        pass
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes (no parameters)"""
        return b''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadBdAddr':
        """Create command from parameter bytes (excluding header)"""
        return cls()

class ReadLocalVersionInformation(HciCmdBasePacket):
    """Read Local Version Information Command"""
    
    OPCODE = HciOpcode.READ_LOCAL_VERSION_INFORMATION
    NAME = "Read_Local_Version_Information"
    
    def __init__(self):
        """Initialize Read Local Version Information Command (no parameters)"""
        super().__init__()
    
    def _validate_params(self) -> None:
        """Validate command parameters (none for Read Local Version Information)"""
        pass
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes (no parameters)"""
        return b''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadLocalVersionInformation':
        """Create command from parameter bytes (excluding header)"""
        return cls()

class ReadLocalSupportedCommands(HciCmdBasePacket):
    """Read Local Supported Commands Command"""
    
    OPCODE = create_opcode(OGF.INFORMATION_PARAMS, InformationOCF.READ_LOCAL_SUPPORTED_COMMANDS)
    NAME = "Read_Local_Supported_Commands"
    
    def __init__(self):
        """Initialize Read Local Supported Commands Command (no parameters)"""
        super().__init__()
    
    def _validate_params(self) -> None:
        """Validate command parameters (none for Read Local Supported Commands)"""
        pass
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes (no parameters)"""
        return b''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadLocalSupportedCommands':
        """Create command from parameter bytes (excluding header)"""
        return cls()

# Function wrappers for easier access
def read_bd_addr() -> ReadBdAddr:
    """Create Read BD_ADDR Command"""
    return ReadBdAddr()

def read_local_version_information() -> ReadLocalVersionInformation:
    """Create Read Local Version Information Command"""
    return ReadLocalVersionInformation()

def read_local_supported_commands() -> ReadLocalSupportedCommands:
    """Create Read Local Supported Commands Command"""
    return ReadLocalSupportedCommands()

# Register all command classes
register_command(ReadBdAddr)
register_command(ReadLocalVersionInformation)
register_command(ReadLocalSupportedCommands)

# Export public functions and classes
__all__ = [
    'read_bd_addr',
    'read_local_version_information',
    'read_local_supported_commands',
    'ReadBdAddr',
    'ReadLocalVersionInformation',
    'ReadLocalSupportedCommands',
]