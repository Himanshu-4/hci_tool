"""
HCI Packet Base Module

This module defines the base HCI packet structure and common packet types.
"""

from abc import ABC, abstractmethod
from enum import IntEnum, unique
from typing import Dict, Any, Optional, ClassVar, Type, Union

@unique
class HciPacketType(IntEnum):
    """HCI Packet Types"""
    COMMAND = 0x01
    ACL_DATA = 0x02
    SYNCHRONOUS_DATA = 0x03
    EVENT = 0x04
    ISO_DATA = 0x05

#MARK: HCIpacket
class HciPacket(ABC):
    """Base class for all HCI packet types"""
    
    # Class variables to be defined by subclasses
    PACKET_TYPE: ClassVar[HciPacketType]
    
    def __init__(self, **kwargs):
        """Initialize a HCI packet with parameters"""
        self.params = kwargs
    
    @abstractmethod
    def _validate_params(self) -> None:
        """Validate packet parameters"""
        pass
    
    @abstractmethod
    def to_bytes(self) -> bytes:
        """Convert packet to bytes"""
        pass
    
    @classmethod
    @abstractmethod
    def from_bytes(cls, data: bytes) -> 'HciPacket':
        """Create a packet from bytes"""
        pass
    
    @abstractmethod
    def __str__(self) -> str:
        """String representation of the packet"""
        pass

#MARK: HciCommandPacket
class HciCommandPacket(HciPacket):
    """Base class for HCI Command packets"""
    PACKET_TYPE = HciPacketType.COMMAND
    
    # Additional class variables
    OPCODE: ClassVar[int]  # Command opcode
    NAME: ClassVar[str]    # Command name
    PARAMS: Optional[bytes]# Command parameters
    
    def __init__(self, **kwargs):
        """
        Initialize HCI Command packet
        
        Args:
            opcode: Command opcode (2 bytes)
            params: Command parameters
        """
        super().__init__(**kwargs)

        
    @abstractmethod
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # This method should be implemented by subclasses to validate specific command parameters
        pass
    
#MARK: HciEventPacket
class HciEventPacket(HciPacket):
    """Base class for HCI Event packets"""
    PACKET_TYPE = HciPacketType.EVENT
    
    # Additional class variables
    EVENT_CODE: ClassVar[int]  # Event code
    SUB_EVENT_CODE: ClassVar[int]  # Sub-event code (if applicable)
    NAME: ClassVar[str]        # Event name
  
    def __init__(self, **kwargs):
        """
        Initialize HCI Event packet
        
        Args:
            event_code: Event code (1 byte)
            sub_event_code: Sub-event code (if applicable, 1 byte)
            params: Event parameters
        """
        super().__init__(**kwargs)

    @abstractmethod
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # This method should be implemented by subclasses to validate specific event parameters
        pass

#MARK: HciAclDatapacket
class HciAclDataPacket(HciPacket):
    """Base class for HCI ACL Data packets"""
    PACKET_TYPE = HciPacketType.ACL_DATA
    
    def __init__(self, connection_handle: int, pb_flag: int, bc_flag: int, data: bytes):
        """
        Initialize HCI ACL Data packet
        
        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            pb_flag: Packet Boundary flag (0-3)
            bc_flag: Broadcast flag (0-3)
            data: ACL data payload
        """
        super().__init__(
            connection_handle=connection_handle,
            pb_flag=pb_flag,
            bc_flag=bc_flag,
            data=data
        )
    
    def _validate_params(self) -> None:
        """Validate ACL packet parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate PB flag
        if not (0 <= self.params['pb_flag'] <= 3):
            raise ValueError(f"Invalid pb_flag: {self.params['pb_flag']}, must be between 0 and 3")
        
        # Validate BC flag
        if not (0 <= self.params['bc_flag'] <= 3):
            raise ValueError(f"Invalid bc_flag: {self.params['bc_flag']}, must be between 0 and 3")
        
        # Validate data length
        if len(self.params['data']) > 0xFFFF:
            raise ValueError(f"Invalid data length: {len(self.params['data'])}, must be at most 0xFFFF bytes")
    
    def to_bytes(self) -> bytes:
        """Convert ACL packet to bytes"""
        # Packet format:
        # - 1 byte: HCI Packet Type
        # - 2 bytes: Connection Handle (12 bits) + PB Flag (2 bits) + BC Flag (2 bits)
        # - 2 bytes: Data Length
        # - N bytes: Data
        
        # Create handle with flags
        handle_with_flags = (self.params['connection_handle'] & 0x0FFF) | \
                           ((self.params['pb_flag'] & 0x03) << 12) | \
                           ((self.params['bc_flag'] & 0x03) << 14)
        
        # Create packet
        result = bytearray([self.PACKET_TYPE])
        result.extend(handle_with_flags.to_bytes(2, byteorder='little'))
        result.extend(len(self.params['data']).to_bytes(2, byteorder='little'))
        result.extend(self.params['data'])
        
        return bytes(result)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'HciAclDataPacket':
        """Create ACL packet from bytes"""
        if len(data) < 5:  # Need at least 5 bytes (header + length)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 5 bytes")
        
        # Verify packet type
        if data[0] != cls.PACKET_TYPE:
            raise ValueError(f"Invalid packet type: {data[0]}, expected {cls.PACKET_TYPE}")
        
        # Extract handle and flags
        handle_with_flags = int.from_bytes(data[1:3], byteorder='little')
        connection_handle = handle_with_flags & 0x0FFF
        pb_flag = (handle_with_flags >> 12) & 0x03
        bc_flag = (handle_with_flags >> 14) & 0x03
        
        # Extract data length
        data_length = int.from_bytes(data[3:5], byteorder='little')
        
        # Extract data
        if len(data) < 5 + data_length:
            raise ValueError(f"Invalid data length: expected {data_length} bytes, got {len(data) - 5}")
        
        acl_data = data[5:5+data_length]
        
        return cls(
            connection_handle=connection_handle,
            pb_flag=pb_flag,
            bc_flag=bc_flag,
            data=acl_data
        )

#MARK: HciScoPacket
class HciSynchronousDataPacket(HciPacket):
    """Base class for HCI Synchronous Data packets"""
    PACKET_TYPE = HciPacketType.SYNCHRONOUS_DATA
    
    def __init__(self, connection_handle: int, packet_status_flag: int, data: bytes):
        """
        Initialize HCI Synchronous Data packet
        
        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            packet_status_flag: Packet Status Flag (0-3)
            data: Synchronous data payload
        """
        super().__init__(
            connection_handle=connection_handle,
            packet_status_flag=packet_status_flag,
            data=data
        )
    
    def _validate_params(self) -> None:
        """Validate Synchronous packet parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate packet status flag
        if not (0 <= self.params['packet_status_flag'] <= 3):
            raise ValueError(f"Invalid packet_status_flag: {self.params['packet_status_flag']}, must be between 0 and 3")
        
        # Validate data length
        if len(self.params['data']) > 0xFF:
            raise ValueError(f"Invalid data length: {len(self.params['data'])}, must be at most 0xFF bytes")
    
    def to_bytes(self) -> bytes:
        """Convert Synchronous packet to bytes"""
        # Packet format:
        # - 1 byte: HCI Packet Type
        # - 2 bytes: Connection Handle (12 bits) + Reserved (2 bits) + Packet Status Flag (2 bits)
        # - 1 byte: Data Length
        # - N bytes: Data
        
        # Create handle with flags
        handle_with_flags = (self.params['connection_handle'] & 0x0FFF) | \
                           ((self.params['packet_status_flag'] & 0x03) << 14)
        
        # Create packet
        result = bytearray([self.PACKET_TYPE])
        result.extend(handle_with_flags.to_bytes(2, byteorder='little'))
        result.append(len(self.params['data']))
        result.extend(self.params['data'])
        
        return bytes(result)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'HciSynchronousDataPacket':
        """Create Synchronous packet from bytes"""
        if len(data) < 4:  # Need at least 4 bytes (header + length)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 4 bytes")
        
        # Verify packet type
        if data[0] != cls.PACKET_TYPE:
            raise ValueError(f"Invalid packet type: {data[0]}, expected {cls.PACKET_TYPE}")
        
        # Extract handle and flags
        handle_with_flags = int.from_bytes(data[1:3], byteorder='little')
        connection_handle = handle_with_flags & 0x0FFF
        packet_status_flag = (handle_with_flags >> 14) & 0x03
        
        # Extract data length
        data_length = data[3]
        
        # Extract data
        if len(data) < 4 + data_length:
            raise ValueError(f"Invalid data length: expected {data_length} bytes, got {len(data) - 4}")
        
        sync_data = data[4:4+data_length]
        
        return cls(
            connection_handle=connection_handle,
            packet_status_flag=packet_status_flag,
            data=sync_data
        )



#MARK: Utils

def parse_hci_packet(data: bytes) -> Optional[HciPacket]:
    """
    Parse HCI packet from bytes
    
    Args:
        data: Packet bytes including packet type
        
    Returns:
        Parsed HCI packet or None if parsing failed
    """
    if not data:
        return None
    
    # Check packet type
    packet_type = data[0]
    
    if packet_type == HciPacketType.COMMAND:
        # Import here to avoid circular imports
        from .cmd import hci_cmd_parse_from_bytes
        return hci_cmd_parse_from_bytes(data[1:])
    
    elif packet_type == HciPacketType.ACL_DATA:
        return HciAclDataPacket.from_bytes(data)
    
    elif packet_type == HciPacketType.SYNCHRONOUS_DATA:
        return HciSynchronousDataPacket.from_bytes(data)
    
    elif packet_type == HciPacketType.EVENT:
        # Event parsing - would be implemented in an event module
        # Similar to command parsing
        # from .evt import hci_evt_parse_from_bytes
        # return hci_evt_parse_from_bytes(data[1:])
        # For now, return None
        return None
    
    elif packet_type == HciPacketType.ISO_DATA:
        # ISO data parsing - not implemented yet
        return None
    
    else:
        # Unknown packet type
        return None

__all__ = [
    'HciPacketType',
    'HciPacket',
    'HciCommandPacket',
    'HciEventPacket',
    'HciAclDataPacket',
    'HciSynchronousDataPacket',
    'parse_hci_packet',
]