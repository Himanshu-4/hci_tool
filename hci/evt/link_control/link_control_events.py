"""
Link Control events module

This module provides implementations for Link Control HCI events.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode
from ..event_types import LinkControlEventType
from ..error_codes import StatusCode
from .. import register_event

class InquiryCompleteEvent(HciEvtBasePacket):
    """Inquiry Complete Event"""
    
    EVENT_CODE = HciEventCode.INQUIRY_COMPLETE
    NAME = "Inquiry_Complete"
    
    def __init__(self, status: Union[int, StatusCode]):
        """
        Initialize Inquiry Complete Event
        
        Args:
            status: Command status (0x00 = success)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        super().__init__(status=status)
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<B", self.params['status'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'InquiryCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 1:  # Need status (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 1 byte")
        
        status = data[0]
        
        return cls(status=status)

class InquiryResultEvent(HciEvtBasePacket):
    """Inquiry Result Event"""
    
    EVENT_CODE = HciEventCode.INQUIRY_RESULT
    NAME = "Inquiry_Result"
    
    def __init__(self, num_responses: int, bd_addrs: List[bytes], page_scan_repetition_modes: List[int],
                class_of_devices: List[bytes], clock_offsets: List[int]):
        """
        Initialize Inquiry Result Event
        
        Args:
            num_responses: Number of responses
            bd_addrs: List of Bluetooth device addresses (6 bytes each)
            page_scan_repetition_modes: List of page scan repetition modes
            class_of_devices: List of class of device values (3 bytes each)
            clock_offsets: List of clock offset values
        """
        super().__init__(
            num_responses=num_responses,
            bd_addrs=bd_addrs,
            page_scan_repetition_modes=page_scan_repetition_modes,
            class_of_devices=class_of_devices,
            clock_offsets=clock_offsets
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate number of responses
        if not (1 <= self.params['num_responses'] <= 0xFF):
            raise ValueError(f"Invalid num_responses: {self.params['num_responses']}, must be between 1 and 0xFF")
        
        # Validate BD_ADDRs
        if len(self.params['bd_addrs']) != self.params['num_responses']:
            raise ValueError(f"Number of BD_ADDRs ({len(self.params['bd_addrs'])}) does not match num_responses ({self.params['num_responses']})")
        
        for i, addr in enumerate(self.params['bd_addrs']):
            if len(addr) != 6:
                raise ValueError(f"Invalid BD_ADDR length at index {i}: {len(addr)}, must be 6 bytes")
        
        # Validate page scan repetition modes
        if len(self.params['page_scan_repetition_modes']) != self.params['num_responses']:
            raise ValueError(f"Number of page scan repetition modes ({len(self.params['page_scan_repetition_modes'])}) does not match num_responses ({self.params['num_responses']})")
        
        for i, mode in enumerate(self.params['page_scan_repetition_modes']):
            if not (0 <= mode <= 2):
                raise ValueError(f"Invalid page scan repetition mode at index {i}: {mode}, must be between 0 and 2")
        
        # Validate class of devices
        if len(self.params['class_of_devices']) != self.params['num_responses']:
            raise ValueError(f"Number of class of devices ({len(self.params['class_of_devices'])}) does not match num_responses ({self.params['num_responses']})")
        
        for i, cod in enumerate(self.params['class_of_devices']):
            if len(cod) != 3:
                raise ValueError(f"Invalid class of device length at index {i}: {len(cod)}, must be 3 bytes")
        
        # Validate clock offsets
        if len(self.params['clock_offsets']) != self.params['num_responses']:
            raise ValueError(f"Number of clock offsets ({len(self.params['clock_offsets'])}) does not match num_responses ({self.params['num_responses']})")
        
        for i, offset in enumerate(self.params['clock_offsets']):
            if not (0 <= offset <= 0xFFFF):
                raise ValueError(f"Invalid clock offset at index {i}: {offset}, must be between 0 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<B", self.params['num_responses'])
        
        for i in range(self.params['num_responses']):
            # Add BD_ADDR (reversed for little-endian)
            result += bytes(reversed(self.params['bd_addrs'][i]))
            
            # Add page scan repetition mode
            result += struct.pack("<B", self.params['page_scan_repetition_modes'][i])
            
            # Reserved bytes (2 bytes)
            result += b'\x00\x00'
            
            # Add class of device
            result += self.params['class_of_devices'][i]
            
            # Add clock offset
            result += struct.pack("<H", self.params['clock_offsets'][i])
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'InquiryResultEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 1:  # Need at least num_responses (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 1 byte")
        
        num_responses = data[0]
        
        # Each response requires 14 bytes
        if len(data) < 1 + (num_responses * 14):
            raise ValueError(f"Invalid data length: {len(data)}, expected {1 + (num_responses * 14)} bytes for {num_responses} responses")
        
        bd_addrs = []
        page_scan_repetition_modes = []
        class_of_devices = []
        clock_offsets = []
        
        for i in range(num_responses):
            # Parse BD_ADDR (6 bytes, reversed for little-endian)
            offset = 1 + (i * 14)
            bd_addr = bytes(reversed(data[offset:offset+6]))
            bd_addrs.append(bd_addr)
            
            # Parse page scan repetition mode (1 byte)
            page_scan_repetition_mode = data[offset+6]
            page_scan_repetition_modes.append(page_scan_repetition_mode)
            
            # Skip reserved bytes (2 bytes)
            
            # Parse class of device (3 bytes)
            class_of_device = data[offset+9:offset+12]
            class_of_devices.append(class_of_device)
            
            # Parse clock offset (2 bytes)
            clock_offset = struct.unpack("<H", data[offset+12:offset+14])[0]
            clock_offsets.append(clock_offset)
        
        return cls(
            num_responses=num_responses,
            bd_addrs=bd_addrs,
            page_scan_repetition_modes=page_scan_repetition_modes,
            class_of_devices=class_of_devices,
            clock_offsets=clock_offsets
        )

class ConnectionCompleteEvent(HciEvtBasePacket):
    """Connection Complete Event"""
    
    EVENT_CODE = HciEventCode.CONNECTION_COMPLETE
    NAME = "Connection_Complete"
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int, bd_addr: bytes, 
                link_type: int, encryption_enabled: bool):
        """
        Initialize Connection Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            bd_addr: Bluetooth device address (6 bytes)
            link_type: Link type (0x00 = SCO, 0x01 = ACL)
            encryption_enabled: True if encryption is enabled
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            bd_addr=bd_addr,
            link_type=link_type,
            encryption_enabled=1 if encryption_enabled else 0
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate BD_ADDR
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid BD_ADDR length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        # Validate link type
        if self.params['link_type'] not in (0x00, 0x01):
            raise ValueError(f"Invalid link_type: {self.params['link_type']}, must be 0x00 (SCO) or 0x01 (ACL)")
        
        # Validate encryption enabled
        if self.params['encryption_enabled'] not in (0, 1):
            raise ValueError(f"Invalid encryption_enabled: {self.params['encryption_enabled']}, must be 0 or 1")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<BH", 
                            self.params['status'],
                            self.params['connection_handle'])
        
        # Add BD_ADDR (reversed for little-endian)
        result += bytes(reversed(self.params['bd_addr']))
        
        # Add link type and encryption enabled
        result += struct.pack("<BB",
                             self.params['link_type'],
                             self.params['encryption_enabled'])
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ConnectionCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 11:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 11 bytes")
        
        status, connection_handle = struct.unpack("<BH", data[:3])
        
        # Extract BD_ADDR (6 bytes, reversed for little-endian)
        bd_addr = bytes(reversed(data[3:9]))
        
        link_type, encryption_enabled = struct.unpack("<BB", data[9:11])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            bd_addr=bd_addr,
            link_type=link_type,
            encryption_enabled=(encryption_enabled == 1)
        )

class ConnectionRequestEvent(HciEvtBasePacket):
    """Connection Request Event"""
    
    EVENT_CODE = HciEventCode.CONNECTION_REQUEST
    NAME = "Connection_Request"
    
    def __init__(self, bd_addr: bytes, class_of_device: bytes, link_type: int):
        """
        Initialize Connection Request Event
        
        Args:
            bd_addr: Bluetooth device address (6 bytes)
            class_of_device: Class of device (3 bytes)
            link_type: Link type (0x00 = SCO, 0x01 = ACL, 0x02 = eSCO)
        """
        super().__init__(
            bd_addr=bd_addr,
            class_of_device=class_of_device,
            link_type=link_type
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate BD_ADDR
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid BD_ADDR length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        # Validate class of device
        if len(self.params['class_of_device']) != 3:
            raise ValueError(f"Invalid class_of_device length: {len(self.params['class_of_device'])}, must be 3 bytes")
        
        # Validate link type
        if self.params['link_type'] not in (0x00, 0x01, 0x02):
            raise ValueError(f"Invalid link_type: {self.params['link_type']}, must be 0x00 (SCO), 0x01 (ACL), or 0x02 (eSCO)")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Add BD_ADDR (reversed for little-endian)
        result = bytes(reversed(self.params['bd_addr']))
        
        # Add class of device and link type
        result += self.params['class_of_device']
        result += struct.pack("<B", self.params['link_type'])
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ConnectionRequestEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 10:  # Need BD_ADDR (6 bytes), class of device (3 bytes), and link type (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 10 bytes")
        
        # Extract BD_ADDR (6 bytes, reversed for little-endian)
        bd_addr = bytes(reversed(data[0:6]))
        
        # Extract class of device (3 bytes)
        class_of_device = data[6:9]
        
        # Extract link type (1 byte)
        link_type = data[9]
        
        return cls(
            bd_addr=bd_addr,
            class_of_device=class_of_device,
            link_type=link_type
        )

class RemoteNameRequestCompleteEvent(HciEvtBasePacket):
    """Remote Name Request Complete Event"""
    
    EVENT_CODE = HciEventCode.REMOTE_NAME_REQUEST_COMPLETE
    NAME = "Remote_Name_Request_Complete"
    
    def __init__(self, status: Union[int, StatusCode], bd_addr: bytes, remote_name: str):
        """
        Initialize Remote Name Request Complete Event
        
        Args:
            status: Command status (0x00 = success)
            bd_addr: Bluetooth device address (6 bytes)
            remote_name: Remote device name (up to 248 bytes)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        # Convert string to bytes if needed
        if isinstance(remote_name, str):
            remote_name = remote_name.encode('utf-8')
            
        super().__init__(
            status=status,
            bd_addr=bd_addr,
            remote_name=remote_name
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate BD_ADDR
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid BD_ADDR length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        # Validate remote name
        if len(self.params['remote_name']) > 248:
            raise ValueError(f"Invalid remote_name length: {len(self.params['remote_name'])}, must be at most 248 bytes")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<B", self.params['status'])
        
        # Add BD_ADDR (reversed for little-endian)
        result += bytes(reversed(self.params['bd_addr']))
        
        # Add remote name (pad to 248 bytes)
        remote_name_padded = self.params['remote_name'] + b'\x00' * (248 - len(self.params['remote_name']))
        result += remote_name_padded
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'RemoteNameRequestCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 255:  # Need status (1 byte), BD_ADDR (6 bytes), and remote name (248 bytes)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 255 bytes")
        
        status = data[0]
        
        # Extract BD_ADDR (6 bytes, reversed for little-endian)
        bd_addr = bytes(reversed(data[1:7]))
        
        # Extract remote name (248 bytes) and strip trailing nulls
        remote_name = data[7:255].rstrip(b'\x00')
        
        return cls(
            status=status,
            bd_addr=bd_addr,
            remote_name=remote_name
        )

class ReadRemoteVersionInformationCompleteEvent(HciEvtBasePacket):
    """Read Remote Version Information Complete Event"""
    
    EVENT_CODE = HciEventCode.READ_REMOTE_VERSION_INFORMATION_COMPLETE
    NAME = "Read_Remote_Version_Information_Complete"
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int, 
                version: int, manufacturer_name: int, subversion: int):
        """
        Initialize Read Remote Version Information Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            version: LMP/PAL version
            manufacturer_name: Manufacturer name
            subversion: LMP/PAL subversion
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            version=version,
            manufacturer_name=manufacturer_name,
            subversion=subversion
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate version
        if not (0 <= self.params['version'] <= 0xFF):
            raise ValueError(f"Invalid version: {self.params['version']}, must be between 0 and 0xFF")
        
        # Validate manufacturer name
        if not (0 <= self.params['manufacturer_name'] <= 0xFFFF):
            raise ValueError(f"Invalid manufacturer_name: {self.params['manufacturer_name']}, must be between 0 and 0xFFFF")
        
        # Validate subversion
        if not (0 <= self.params['subversion'] <= 0xFFFF):
            raise ValueError(f"Invalid subversion: {self.params['subversion']}, must be between 0 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BHBHH",
                          self.params['status'],
                          self.params['connection_handle'],
                          self.params['version'],
                          self.params['manufacturer_name'],
                          self.params['subversion'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadRemoteVersionInformationCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 8:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 8 bytes")
        
        status, connection_handle, version, manufacturer_name, subversion = struct.unpack("<BHBHH", data[:8])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            version=version,
            manufacturer_name=manufacturer_name,
            subversion=subversion
        )

# Register all event classes
register_event(InquiryCompleteEvent)
register_event(InquiryResultEvent)
register_event(ConnectionCompleteEvent)
register_event(ConnectionRequestEvent)
register_event(RemoteNameRequestCompleteEvent)
register_event(ReadRemoteVersionInformationCompleteEvent)

# Function wrappers for easier access
def inquiry_complete(status: Union[int, StatusCode]) -> InquiryCompleteEvent:
    """Create Inquiry Complete Event"""
    return InquiryCompleteEvent(status=status)

def inquiry_result(num_responses: int, bd_addrs: List[bytes], page_scan_repetition_modes: List[int],
                 class_of_devices: List[bytes], clock_offsets: List[int]) -> InquiryResultEvent:
    """Create Inquiry Result Event"""
    return InquiryResultEvent(
        num_responses=num_responses,
        bd_addrs=bd_addrs,
        page_scan_repetition_modes=page_scan_repetition_modes,
        class_of_devices=class_of_devices,
        clock_offsets=clock_offsets
    )

def connection_complete(status: Union[int, StatusCode], connection_handle: int, bd_addr: bytes,
                      link_type: int, encryption_enabled: bool) -> ConnectionCompleteEvent:
    """Create Connection Complete Event"""
    return ConnectionCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        bd_addr=bd_addr,
        link_type=link_type,
        encryption_enabled=encryption_enabled
    )

def connection_request(bd_addr: bytes, class_of_device: bytes, link_type: int) -> ConnectionRequestEvent:
    """Create Connection Request Event"""
    return ConnectionRequestEvent(
        bd_addr=bd_addr,
        class_of_device=class_of_device,
        link_type=link_type
    )

def remote_name_request_complete(status: Union[int, StatusCode], bd_addr: bytes, 
                               remote_name: str) -> RemoteNameRequestCompleteEvent:
    """Create Remote Name Request Complete Event"""
    return RemoteNameRequestCompleteEvent(
        status=status,
        bd_addr=bd_addr,
        remote_name=remote_name
    )

def read_remote_version_information_complete(status: Union[int, StatusCode], connection_handle: int,
                                          version: int, manufacturer_name: int, 
                                          subversion: int) -> ReadRemoteVersionInformationCompleteEvent:
    """Create Read Remote Version Information Complete Event"""
    return ReadRemoteVersionInformationCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        version=version,
        manufacturer_name=manufacturer_name,
        subversion=subversion
    )

# Export public functions and classes
__all__ = [
    'inquiry_complete',
    'inquiry_result',
    'connection_complete',
    'connection_request',
    'remote_name_request_complete',
    'read_remote_version_information_complete',
    'InquiryCompleteEvent',
    'InquiryResultEvent',
    'ConnectionCompleteEvent',
    'ConnectionRequestEvent',
    'RemoteNameRequestCompleteEvent',
    'ReadRemoteVersionInformationCompleteEvent',
]