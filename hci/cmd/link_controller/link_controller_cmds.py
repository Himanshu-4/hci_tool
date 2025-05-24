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

class CreateConnection(HciCmdBasePacket):
    """Create Connection Command"""
    
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CREATE_CONNECTION)
    NAME = "Create_Connection"
    
    def __init__(self, 
                 bd_addr: bytes,  # Bluetooth Device Address (6 bytes)
                 packet_type: int = 0x0008,  # Default packet type
                 page_scan_repetition_mode: int = 0x00,  # Default mode
                 clock_offset: int = 0x0000,  # Default clock offset
                 allow_role_switch: bool = True):  # Allow role switch
        """
        Initialize Create Connection Command
        
        Args:
            bd_addr: Bluetooth Device Address (6 bytes)
            packet_type: Packet type for the connection
            page_scan_repetition_mode: Page scan repetition mode
            clock_offset: Clock offset for the connection
            allow_role_switch: Allow role switch during connection establishment
        """
        super().__init__(
            bd_addr=bd_addr,
            packet_type=packet_type,
            page_scan_repetition_mode=page_scan_repetition_mode,
            clock_offset=clock_offset,
            allow_role_switch=allow_role_switch
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        if not (0x0001 <= self.params['packet_type'] <= 0xFFFF):
            raise ValueError(f"Invalid packet_type: {self.params['packet_type']}, must be between 0x0001 and 0xFFFF")
        
        if not (0x00 <= self.params['page_scan_repetition_mode'] <= 0x03):
            raise ValueError(f"Invalid page_scan_repetition_mode: {self.params['page_scan_repetition_mode']}, must be between 0x00 and 0x03")
        
        if not (0x0000 <= self.params['clock_offset'] <= 0xFFFF):
            raise ValueError(f"Invalid clock_offset: {self.params['clock_offset']}, must be between 0x0000 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<6sHHB",
                          self.params['bd_addr'],
                          self.params['packet_type'],
                          self.params['page_scan_repetition_mode'],
                          self.params['clock_offset'],
                          1 if self.params['allow_role_switch'] else 0)


class AcceptConnectionRequest(HciCmdBasePacket):
    """Accept Connection Request Command"""
    
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.ACCEPT_CONNECTION_REQUEST)
    NAME = "Accept_Connection_Request"
    
    MASTER_ROLE = 0x00  # Master role
    SLAVE_ROLE = 0x01   # Slave role
    
    def __init__(self, bd_addr: bytes, role: int = 0x00):
        """
        Initialize Accept Connection Request Command
        
        Args:
            bd_addr: Bluetooth Device Address (6 bytes)
            role: Role to assign (0x00 = Master, 0x01 = Slave)
        """
        super().__init__(
            bd_addr=bd_addr,
            role=role
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        if self.params['role'] not in (0x00, 0x01):
            raise ValueError(f"Invalid role: {self.params['role']}, must be 0x00 (Master) or 0x01 (Slave)")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<6sB", self.params['bd_addr'], self.params['role'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'AcceptConnectionRequest':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 7 bytes")
        
        bd_addr = data[:6]
        role = data[6]
        
        return cls(
            bd_addr=bd_addr,
            role=role
        )
        
class RejectConnectionRequest(HciCmdBasePacket):
    """Reject Connection Request Command"""
    
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REJECT_CONNECTION_REQUEST)
    NAME = "Reject_Connection_Request"
    
    def __init__(self, bd_addr: bytes):
        """
        Initialize Reject Connection Request Command
        
        Args:
            bd_addr: Bluetooth Device Address (6 bytes)
        """
        super().__init__(
            bd_addr=bd_addr
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}, must be 6 bytes")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<6s", self.params['bd_addr'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'RejectConnectionRequest':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 6 bytes")
        
        bd_addr = data[:6]
        
        return cls(
            bd_addr=bd_addr
        )
        
  
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

class ChangeConnectionPacketType(HciCmdBasePacket):
    """Change Connection Packet Type Command"""
    
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.CHANGE_CONNECTION_PACKET_TYPE)
    NAME = "Change_Connection_Packet_Type"
    
    def __init__(self, connection_handle: int, packet_type: int):
        """
        Initialize Change Connection Packet Type Command
        
        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            packet_type: New packet type for the connection
        """
        super().__init__(
            connection_handle=connection_handle,
            packet_type=packet_type
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        if not (0x0001 <= self.params['packet_type'] <= 0xFFFF):
            raise ValueError(f"Invalid packet_type: {self.params['packet_type']}, must be between 0x0001 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<HB",
                          self.params['connection_handle'],
                          self.params['packet_type'])
        
    
class RemoteNameRequest(HciCmdBasePacket):
    """Remote Name Request Command"""
    
    OPCODE = create_opcode(OGF.LINK_CONTROL, LinkControlOCF.REMOTE_NAME_REQUEST)
    NAME = "Remote_Name_Request"
    
    def __init__(self, bd_addr: bytes):
        """
        Initialize Remote Name Request Command
        
        Args:
            bd_addr: Bluetooth Device Address (6 bytes)
        """
        super().__init__(
            bd_addr=bd_addr
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}, must be 6 bytes")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<6s", self.params['bd_addr'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'RemoteNameRequest':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 6 bytes")
        
        bd_addr = data[:6]
        
        return cls(
            bd_addr=bd_addr
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
register_command(CreateConnection)
register_command(AcceptConnectionRequest)
register_command(RejectConnectionRequest)
register_command(Disconnect)
register_command(ChangeConnectionPacketType)
register_command(RemoteNameRequest)

# Export public functions and classes
__all__ = [
    'inquiry',
    'inquiry_cancel',
    'disconnect',
    'Inquiry',
    'CreateConnection',
    'AcceptConnectionRequest',
    'RejectConnectionRequest',
    'InquiryCancel',
    'Disconnect',
    'ChangeConnectionPacketType',
    'RemoteNameRequest'
]