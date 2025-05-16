"""
Link Controller HCI Commands

This module provides classes for Link Controller HCI commands.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import HciOpcode, create_opcode, OGF, LinkControlOCF
from .. import register_command

class Inquiry(HciCmdBasePacket):
    """Inquiry Command"""
    
    OPCODE = HciOpcode.INQUIRY
    NAME = "Inquiry"
    
    # Inquiry access codes
    IAC_GIAC = b'\x33\x8B\x9E'  # General Inquiry Access Code
    IAC_LIAC = b'\x00\x8B\x9E'  # Limited Inquiry Access Code
    
    def __init__(self, 
                 lap: bytes = IAC_GIAC,  # Inquiry access code
                 inquiry_length: int = 0x30,  # Inquiry length (N * 1.28s)
                 num_responses: int = 0x00):  # Unlimited responses
        """
        Initialize Inquiry Command
        
        Args:
            lap: Inquiry access code (3 bytes)
            inquiry_length: Maximum inquiry length (N * 1.28s)
            num_responses: Maximum number of responses (0 = unlimited)
        """
        super().__init__(
            lap=lap,
            inquiry_length=inquiry_length,
            num_responses=num_responses
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate LAP
        if len(self.params['lap']) != 3:
            raise ValueError(f"Invalid lap length: {len(self.params['lap'])}, must be 3 bytes")
        
        # Validate inquiry length
        if not (0x01 <= self.params['inquiry_length'] <= 0x30):
            raise ValueError(f"Invalid inquiry_length: {self.params['inquiry_length']}, must be between 0x01 and 0x30")
        
        # Validate number of responses
        if not (0x00 <= self.params['num_responses'] <= 0xFF):
            raise ValueError(f"Invalid num_responses: {self.params['num_responses']}, must be between 0x00 and 0xFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<3sBB",
                          self.params['lap'],
                          self.params['inquiry_length'],
                          self.params['num_responses'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Inquiry':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 5:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 5 bytes")
        
        lap = data[:3]
        inquiry_length, num_responses = struct.unpack("<BB", data[3:5])
        
        return cls(
            lap=lap,
            inquiry_length=inquiry_length,
            num_responses=num_responses
        )

class InquiryCancel(HciCmdBasePacket):
    """Inquiry Cancel Command"""
    
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.INQUIRY_CANCEL)
    NAME = "Inquiry_Cancel"
    
    def __init__(self):
        """Initialize Inquiry Cancel Command (no parameters)"""
        super().__init__()
    
    def _validate_params(self) -> None:
        """Validate command parameters (none for Inquiry Cancel)"""
        pass
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes (no parameters)"""
        return b''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'InquiryCancel':
        """Create command from parameter bytes (excluding header)"""
        return cls()

class Disconnect(HciCmdBasePacket):
    """Disconnect Command"""
    
    OPCODE = HciOpcode.DISCONNECT
    NAME = "Disconnect"
    
    # Disconnect reason codes
    class Reason(IntEnum):
        AUTHENTICATION_FAILURE = 0x05
        REMOTE_USER_TERMINATED = 0x13
        REMOTE_LOW_RESOURCES = 0x14
        REMOTE_POWER_OFF = 0x15
        UNSUPPORTED_REMOTE_FEATURE = 0x1A
        PAIRING_WITH_UNIT_KEY_NOT_SUPPORTED = 0x29
        UNACCEPTABLE_CONNECTION_PARAMETERS = 0x3B
    
    def __init__(self, 
                 connection_handle: int,
                 reason: Union[int, 'Disconnect.Reason'] = Reason.REMOTE_USER_TERMINATED):
        """
        Initialize Disconnect Command
        
        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            reason: Reason for disconnection
        """
        # Convert enum value to integer if needed
        if isinstance(reason, self.Reason):
            reason = reason.value
            
        super().__init__(
            connection_handle=connection_handle,
            reason=reason
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate reason
        if not (0x01 <= self.params['reason'] <= 0xFF):
            raise ValueError(f"Invalid reason: {self.params['reason']}, must be between 0x01 and 0xFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<HB",
                          self.params['connection_handle'],
                          self.params['reason'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Disconnect':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 3 bytes")
        
        connection_handle, reason = struct.unpack("<HB", data[:3])
        
        return cls(
            connection_handle=connection_handle,
            reason=reason
        )

# Function wrappers for easier access
def inquiry(lap: bytes = Inquiry.IAC_GIAC,
           inquiry_length: int = 0x30,
           num_responses: int = 0x00) -> Inquiry:
    """Create Inquiry Command"""
    return Inquiry(
        lap=lap,
        inquiry_length=inquiry_length,
        num_responses=num_responses
    )

def inquiry_cancel() -> InquiryCancel:
    """Create Inquiry Cancel Command"""
    return InquiryCancel()

def disconnect(connection_handle: int,
              reason: Union[int, Disconnect.Reason] = Disconnect.Reason.REMOTE_USER_TERMINATED) -> Disconnect:
    """Create Disconnect Command"""
    return Disconnect(
        connection_handle=connection_handle,
        reason=reason
    )

# Register all command classes
register_command(Inquiry)
register_command(InquiryCancel)
register_command(Disconnect)

# Export public functions and classes
__all__ = [
    'inquiry',
    'inquiry_cancel',
    'disconnect',
    'Inquiry',
    'InquiryCancel',
    'Disconnect',
]