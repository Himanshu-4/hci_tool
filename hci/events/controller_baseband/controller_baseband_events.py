"""
Controller and Baseband events module

This module provides implementations for Controller and Baseband HCI events.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..hci_packet import HciEventPacket
from .evt_base_packet import HciEvtBasePacket
from .evt_codes import HciEventCode
from .event_types import ControllerBasebandEventType
from .error_codes import StatusCode
from .. import register_event

class FlushOccurredEvent(HciEvtBasePacket):
    """Flush Occurred Event"""
    
    EVENT_CODE = HciEventCode.FLUSH_OCCURRED
    NAME = "Flush_Occurred"
    
    def __init__(self, connection_handle: int):
        """
        Initialize Flush Occurred Event
        
        Args:
            connection_handle: Connection handle
        """
        super().__init__(connection_handle=connection_handle)
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<H", self.params['connection_handle'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'FlushOccurredEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 2:  # Need connection handle (2 bytes)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        
        connection_handle = struct.unpack("<H", data[:2])[0]
        
        return cls(connection_handle=connection_handle)

class DataBufferOverflowEvent(HciEvtBasePacket):
    """Data Buffer Overflow Event"""
    
    EVENT_CODE = HciEventCode.DATA_BUFFER_OVERFLOW
    NAME = "Data_Buffer_Overflow"
    
    # Link type values
    class LinkType(IntEnum):
        SYNCHRONOUS = 0x00
        ACL = 0x01
    
    def __init__(self, link_type: Union[int, 'DataBufferOverflowEvent.LinkType']):
        """
        Initialize Data Buffer Overflow Event
        
        Args:
            link_type: Link type (0x00 = Synchronous Buffer, 0x01 = ACL Buffer)
        """
        # Convert enum value to integer if needed
        if isinstance(link_type, self.LinkType):
            link_type = link_type.value
            
        super().__init__(link_type=link_type)
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate link type
        if self.params['link_type'] not in (0x00, 0x01):
            raise ValueError(f"Invalid link_type: {self.params['link_type']}, must be 0x00 (Synchronous) or 0x01 (ACL)")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<B", self.params['link_type'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'DataBufferOverflowEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 1:  # Need link type (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 1 byte")
        
        link_type = data[0]
        
        return cls(link_type=link_type)

class MaxSlotsChangeEvent(HciEvtBasePacket):
    """Max Slots Change Event"""
    
    EVENT_CODE = HciEventCode.MAX_SLOTS_CHANGE
    NAME = "Max_Slots_Change"
    
    def __init__(self, connection_handle: int, lmp_max_slots: int):
        """
        Initialize Max Slots Change Event
        
        Args:
            connection_handle: Connection handle
            lmp_max_slots: LMP Max Slots
        """
        super().__init__(
            connection_handle=connection_handle,
            lmp_max_slots=lmp_max_slots
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate LMP max slots
        if not (0 <= self.params['lmp_max_slots'] <= 0xFF):
            raise ValueError(f"Invalid lmp_max_slots: {self.params['lmp_max_slots']}, must be between 0 and 0xFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<HB",
                          self.params['connection_handle'],
                          self.params['lmp_max_slots'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'MaxSlotsChangeEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 3:  # Need connection handle (2 bytes) and LMP max slots (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 3 bytes")
        
        connection_handle, lmp_max_slots = struct.unpack("<HB", data[:3])
        
        return cls(
            connection_handle=connection_handle,
            lmp_max_slots=lmp_max_slots
        )

class QosViolationEvent(HciEvtBasePacket):
    """QoS Violation Event"""
    
    EVENT_CODE = HciEventCode.QOS_VIOLATION
    NAME = "QoS_Violation"
    
    def __init__(self, connection_handle: int):
        """
        Initialize QoS Violation Event
        
        Args:
            connection_handle: Connection handle
        """
        super().__init__(connection_handle=connection_handle)
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<H", self.params['connection_handle'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'QosViolationEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 2:  # Need connection handle (2 bytes)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        
        connection_handle = struct.unpack("<H", data[:2])[0]
        
        return cls(connection_handle=connection_handle)

class NumberOfCompletedPacketsEvent(HciEvtBasePacket):
    """Number Of Completed Packets Event"""
    
    EVENT_CODE = HciEventCode.NUMBER_OF_COMPLETED_PACKETS
    NAME = "Number_Of_Completed_Packets"
    
    def __init__(self, num_handles: int, connection_handles: List[int], num_completed_packets: List[int]):
        """
        Initialize Number Of Completed Packets Event
        
        Args:
            num_handles: Number of handles
            connection_handles: List of connection handles
            num_completed_packets: List of completed packet counts for each handle
        """
        super().__init__(
            num_handles=num_handles,
            connection_handles=connection_handles,
            num_completed_packets=num_completed_packets
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate number of handles
        if not (1 <= self.params['num_handles'] <= 0xFF):
            raise ValueError(f"Invalid num_handles: {self.params['num_handles']}, must be between 1 and 0xFF")
        
        # Validate connection handles list
        if len(self.params['connection_handles']) != self.params['num_handles']:
            raise ValueError(f"Number of connection handles ({len(self.params['connection_handles'])}) does not match num_handles ({self.params['num_handles']})")
        
        for i, handle in enumerate(self.params['connection_handles']):
            if not (0x0000 <= handle <= 0x0EFF):
                raise ValueError(f"Invalid connection_handle at index {i}: {handle}, must be between 0x0000 and 0x0EFF")
        
        # Validate completed packets list
        if len(self.params['num_completed_packets']) != self.params['num_handles']:
            raise ValueError(f"Number of completed packets counts ({len(self.params['num_completed_packets'])}) does not match num_handles ({self.params['num_handles']})")
        
        for i, count in enumerate(self.params['num_completed_packets']):
            if not (0 <= count <= 0xFFFF):
                raise ValueError(f"Invalid num_completed_packets at index {i}: {count}, must be between 0 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<B", self.params['num_handles'])
        
        # Add connection handles
        for handle in self.params['connection_handles']:
            result += struct.pack("<H", handle)
        
        # Add completed packets counts
        for count in self.params['num_completed_packets']:
            result += struct.pack("<H", count)
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'NumberOfCompletedPacketsEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 1:  # Need at least num_handles (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 1 byte")
        
        num_handles = data[0]
        
        # Each handle requires 4 bytes (2 for handle, 2 for count)
        if len(data) < 1 + (num_handles * 4):
            raise ValueError(f"Invalid data length: {len(data)}, expected {1 + (num_handles * 4)} bytes for {num_handles} handles")
        
        connection_handles = []
        num_completed_packets = []
        
        # Extract connection handles
        for i in range(num_handles):
            offset = 1 + (i * 2)
            handle = struct.unpack("<H", data[offset:offset+2])[0]
            connection_handles.append(handle)
        
        # Extract completed packets counts
        for i in range(num_handles):
            offset = 1 + (num_handles * 2) + (i * 2)
            count = struct.unpack("<H", data[offset:offset+2])[0]
            num_completed_packets.append(count)
        
        return cls(
            num_handles=num_handles,
            connection_handles=connection_handles,
            num_completed_packets=num_completed_packets
        )

class PageScanRepetitionModeChangeEvent(HciEvtBasePacket):
    """Page Scan Repetition Mode Change Event"""
    
    EVENT_CODE = HciEventCode.PAGE_SCAN_REPETITION_MODE_CHANGE
    NAME = "Page_Scan_Repetition_Mode_Change"
    
    # Page scan repetition modes
    class Mode(IntEnum):
        R0 = 0x00
        R1 = 0x01
        R2 = 0x02
    
    def __init__(self, bd_addr: bytes, page_scan_repetition_mode: Union[int, 'PageScanRepetitionModeChangeEvent.Mode']):
        """
        Initialize Page Scan Repetition Mode Change Event
        
        Args:
            bd_addr: Bluetooth device address (6 bytes)
            page_scan_repetition_mode: New page scan repetition mode
        """
        # Convert enum value to integer if needed
        if isinstance(page_scan_repetition_mode, self.Mode):
            page_scan_repetition_mode = page_scan_repetition_mode.value
            
        super().__init__(
            bd_addr=bd_addr,
            page_scan_repetition_mode=page_scan_repetition_mode
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate BD_ADDR
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid BD_ADDR length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        # Validate page scan repetition mode
        if not (0 <= self.params['page_scan_repetition_mode'] <= 2):
            raise ValueError(f"Invalid page_scan_repetition_mode: {self.params['page_scan_repetition_mode']}, must be between 0 and 2")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Add BD_ADDR (reversed for little-endian)
        result = bytes(reversed(self.params['bd_addr']))
        
        # Add page scan repetition mode
        result += struct.pack("<B", self.params['page_scan_repetition_mode'])
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'PageScanRepetitionModeChangeEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 7:  # Need BD_ADDR (6 bytes) and page scan repetition mode (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 7 bytes")
        
        # Extract BD_ADDR (6 bytes, reversed for little-endian)
        bd_addr = bytes(reversed(data[0:6]))
        
        page_scan_repetition_mode = data[6]
        
        return cls(
            bd_addr=bd_addr,
            page_scan_repetition_mode=page_scan_repetition_mode
        )

# Register all event classes
register_event(FlushOccurredEvent)
register_event(DataBufferOverflowEvent)
register_event(MaxSlotsChangeEvent)
register_event(QosViolationEvent)
register_event(NumberOfCompletedPacketsEvent)
register_event(PageScanRepetitionModeChangeEvent)

# Function wrappers for easier access
def flush_occurred(connection_handle: int) -> FlushOccurredEvent:
    """Create Flush Occurred Event"""
    return FlushOccurredEvent(connection_handle=connection_handle)

def data_buffer_overflow(link_type: Union[int, DataBufferOverflowEvent.LinkType]) -> DataBufferOverflowEvent:
    """Create Data Buffer Overflow Event"""
    return DataBufferOverflowEvent(link_type=link_type)

def max_slots_change(connection_handle: int, lmp_max_slots: int) -> MaxSlotsChangeEvent:
    """Create Max Slots Change Event"""
    return MaxSlotsChangeEvent(
        connection_handle=connection_handle,
        lmp_max_slots=lmp_max_slots
    )

def qos_violation(connection_handle: int) -> QosViolationEvent:
    """Create QoS Violation Event"""
    return QosViolationEvent(connection_handle=connection_handle)

def number_of_completed_packets(num_handles: int, connection_handles: List[int], 
                              num_completed_packets: List[int]) -> NumberOfCompletedPacketsEvent:
    """Create Number Of Completed Packets Event"""
    return NumberOfCompletedPacketsEvent(
        num_handles=num_handles,
        connection_handles=connection_handles,
        num_completed_packets=num_completed_packets
    )

def page_scan_repetition_mode_change(bd_addr: bytes, 
                                  page_scan_repetition_mode: Union[int, PageScanRepetitionModeChangeEvent.Mode]) -> PageScanRepetitionModeChangeEvent:
    """Create Page Scan Repetition Mode Change Event"""
    return PageScanRepetitionModeChangeEvent(
        bd_addr=bd_addr,
        page_scan_repetition_mode=page_scan_repetition_mode
    )

# Export public functions and classes
__all__ = [
    'flush_occurred',
    'data_buffer_overflow',
    'max_slots_change',
    'qos_violation',
    'number_of_completed_packets',
    'page_scan_repetition_mode_change',
    'FlushOccurredEvent',
    'DataBufferOverflowEvent',
    'MaxSlotsChangeEvent',
    'QosViolationEvent',
    'NumberOfCompletedPacketsEvent',
    'PageScanRepetitionModeChangeEvent',
]