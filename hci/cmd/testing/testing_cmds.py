"""
Testing HCI Commands

This module provides classes for Testing HCI commands.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import HciOpcode, create_opcode, OGF, TestingOCF
from .. import register_command

class ReadLoopbackMode(HciCmdBasePacket):
    """Read Loopback Mode Command"""
    
    OPCODE = create_opcode(OGF.TESTING, TestingOCF.READ_LOOPBACK_MODE)
    NAME = "Read_Loopback_Mode"
    
    def __init__(self):
        """Initialize Read Loopback Mode Command (no parameters)"""
        super().__init__()
    
    def _validate_params(self) -> None:
        """Validate command parameters (none for Read Loopback Mode)"""
        pass
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes (no parameters)"""
        return b''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadLoopbackMode':
        """Create command from parameter bytes (excluding header)"""
        return cls()

class WriteLoopbackMode(HciCmdBasePacket):
    """Write Loopback Mode Command"""
    
    OPCODE = create_opcode(OGF.TESTING, TestingOCF.WRITE_LOOPBACK_MODE)
    NAME = "Write_Loopback_Mode"
    
    # Loopback modes
    class Mode(IntEnum):
        NO_LOOPBACK = 0x00
        LOCAL_LOOPBACK = 0x01
        REMOTE_LOOPBACK = 0x02
    
    def __init__(self, loopback_mode: Union[int, 'WriteLoopbackMode.Mode']):
        """
        Initialize Write Loopback Mode Command
        
        Args:
            loopback_mode: Loopback mode (0x00: no loopback, 0x01: local loopback, 0x02: remote loopback)
        """
        # Convert enum value to integer if needed
        if isinstance(loopback_mode, self.Mode):
            loopback_mode = loopback_mode.value
            
        super().__init__(
            loopback_mode=loopback_mode
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate loopback mode
        if not (0x00 <= self.params['loopback_mode'] <= 0x02):
            raise ValueError(f"Invalid loopback_mode: {self.params['loopback_mode']}, must be between 0x00 and 0x02")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<B", self.params['loopback_mode'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'WriteLoopbackMode':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 1:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 1 byte")
        
        loopback_mode = data[0]
        
        return cls(
            loopback_mode=loopback_mode
        )

# Function wrappers for easier access
def read_loopback_mode() -> ReadLoopbackMode:
    """Create Read Loopback Mode Command"""
    return ReadLoopbackMode()

def write_loopback_mode(loopback_mode: Union[int, WriteLoopbackMode.Mode]) -> WriteLoopbackMode:
    """Create Write Loopback Mode Command"""
    return WriteLoopbackMode(loopback_mode=loopback_mode)

# Register all command classes
register_command(ReadLoopbackMode)
register_command(WriteLoopbackMode)

# Export public functions and classes
__all__ = [
    'read_loopback_mode',
    'write_loopback_mode',
    'ReadLoopbackMode',
    'WriteLoopbackMode',
]