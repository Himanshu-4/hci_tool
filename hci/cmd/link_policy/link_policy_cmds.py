"""
Link Policy HCI Commands

This module provides classes for Link Policy HCI commands.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import HciOpcode, create_opcode, OGF, LinkPolicyOCF
from .. import register_command

class SniffMode(HciCmdBasePacket):
    """Sniff Mode Command"""
    
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.SNIFF_MODE)
    NAME = "Sniff_Mode"
    
    def __init__(self, 
                 connection_handle: int,
                 sniff_max_interval: int,
                 sniff_min_interval: int,
                 sniff_attempt: int,
                 sniff_timeout: int):
        """
        Initialize Sniff Mode Command
        
        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            sniff_max_interval: Maximum interval between consecutive sniff periods
                               Range: 0x0002 to 0xFFFE; Time = N * 0.625 ms
            sniff_min_interval: Minimum interval between consecutive sniff periods
                               Range: 0x0002 to 0xFFFE; Time = N * 0.625 ms
            sniff_attempt: Number of attempts for receiving a packet
                         Range: 0x0001 to 0x7FFF; Time = N * 1.25 ms
            sniff_timeout: The amount of time before the sniff attempt is terminated
                         Range: 0x0000 to 0x7FFF; Time = N * 1.25 ms
        """
        super().__init__(
            connection_handle=connection_handle,
            sniff_max_interval=sniff_max_interval,
            sniff_min_interval=sniff_min_interval,
            sniff_attempt=sniff_attempt,
            sniff_timeout=sniff_timeout
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate sniff intervals
        if not (0x0002 <= self.params['sniff_max_interval'] <= 0xFFFE):
            raise ValueError(f"Invalid sniff_max_interval: {self.params['sniff_max_interval']}, must be between 0x0002 and 0xFFFE")
            
        if not (0x0002 <= self.params['sniff_min_interval'] <= 0xFFFE):
            raise ValueError(f"Invalid sniff_min_interval: {self.params['sniff_min_interval']}, must be between 0x0002 and 0xFFFE")
            
        if self.params['sniff_min_interval'] > self.params['sniff_max_interval']:
            raise ValueError(f"sniff_min_interval ({self.params['sniff_min_interval']}) must not be greater than sniff_max_interval ({self.params['sniff_max_interval']})")
        
        # Validate sniff attempt
        if not (0x0001 <= self.params['sniff_attempt'] <= 0x7FFF):
            raise ValueError(f"Invalid sniff_attempt: {self.params['sniff_attempt']}, must be between 0x0001 and 0x7FFF")
        
        # Validate sniff timeout
        if not (0x0000 <= self.params['sniff_timeout'] <= 0x7FFF):
            raise ValueError(f"Invalid sniff_timeout: {self.params['sniff_timeout']}, must be between 0x0000 and 0x7FFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<HHHHH",
                          self.params['connection_handle'],
                          self.params['sniff_max_interval'],
                          self.params['sniff_min_interval'],
                          self.params['sniff_attempt'],
                          self.params['sniff_timeout'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'SniffMode':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 10:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 10 bytes")
        
        connection_handle, sniff_max_interval, sniff_min_interval, sniff_attempt, sniff_timeout = struct.unpack("<HHHHH", data[:10])
        
        return cls(
            connection_handle=connection_handle,
            sniff_max_interval=sniff_max_interval,
            sniff_min_interval=sniff_min_interval,
            sniff_attempt=sniff_attempt,
            sniff_timeout=sniff_timeout
        )

class ExitSniffMode(HciCmdBasePacket):
    """Exit Sniff Mode Command"""
    
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.EXIT_SNIFF_MODE)
    NAME = "Exit_Sniff_Mode"
    
    def __init__(self, connection_handle: int):
        """
        Initialize Exit Sniff Mode Command
        
        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
        """
        super().__init__(
            connection_handle=connection_handle
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<H", self.params['connection_handle'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ExitSniffMode':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        
        connection_handle = struct.unpack("<H", data[:2])[0]
        
        return cls(
            connection_handle=connection_handle
        )

# Function wrappers for easier access
def sniff_mode(connection_handle: int,
              sniff_max_interval: int,
              sniff_min_interval: int,
              sniff_attempt: int,
              sniff_timeout: int) -> SniffMode:
    """Create Sniff Mode Command"""
    return SniffMode(
        connection_handle=connection_handle,
        sniff_max_interval=sniff_max_interval,
        sniff_min_interval=sniff_min_interval,
        sniff_attempt=sniff_attempt,
        sniff_timeout=sniff_timeout
    )

def exit_sniff_mode(connection_handle: int) -> ExitSniffMode:
    """Create Exit Sniff Mode Command"""
    return ExitSniffMode(connection_handle=connection_handle)

# Register all command classes
register_command(SniffMode)
register_command(ExitSniffMode)

# Export public functions and classes
__all__ = [
    'sniff_mode',
    'exit_sniff_mode',
    'SniffMode',
    'ExitSniffMode',
]