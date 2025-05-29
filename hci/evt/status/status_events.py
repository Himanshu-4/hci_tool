"""
Status events module

This module provides implementations for Status HCI events.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ...cmd.cmd_opcodes import StatusOCF,OGF,create_opcode

from ..base_events import CommandCompleteEvent
from ..evt_codes import HciEventCode
from ..event_types import StatusEventType
from ..error_codes import StatusCode, get_status_description
from .. import register_event

class ReadRssiCompleteEvent(CommandCompleteEvent):
    """Read RSSI Complete Event"""
    OPCODE = create_opcode(OGF.STATUS_PARAMS, StatusOCF.READ_RSSI) 
    NAME = "Read_RSSI_Complete"
    
    def __init__(self, num_hci_command_packets: int, opcode: int, status: Union[int, StatusCode],connection_handle: int, rssi: int):
        """
        Initialize Read RSSI Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            rssi: RSSI value (signed byte, -127 to +20, 127 for invalid)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        # For Command Complete events, we need to construct the return parameters
        # The return parameters for Read RSSI are:
        # - Status (1 byte)
        # - Connection_Handle (2 bytes)
        # - RSSI (1 byte, signed)
        
        super().__init__(
            num_hci_command_packets=num_hci_command_packets,  # Always set to 1
            opcode=self.OPCODE,      # Read RSSI opcode (OGF=0x05, OCF=0x05)
            status=status,
            # Store the actual parameters for easier access
            connection_handle=connection_handle,
            rssi=rssi
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate num_hci_command_packets
        if not (0 <= self.params['num_hci_command_packets'] <= 0xFF):
            raise ValueError(f"Invalid num_hci_command_packets: {self.params['num_hci_command_packets']}, must be between 0 and 0xFF")
        
        # Validate command opcode
        if not (0 <= self.params['opcode'] <= 0xFFFF):
            raise ValueError(f"Invalid command_opcode: {self.params['command_opcode']}, must be between 0 and 0xFFFF")
        
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate RSSI
        if not (-127 <= self.params['rssi'] <= 127):
            raise ValueError(f"Invalid rssi: {self.params['rssi']}, must be between -127 and 127")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return super()._serialize_params() + struct.pack("<HB",
            self.params['connection_handle'],
            self.params['rssi']
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadRssiCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 7:  # Num_HCI_Command_Packets(1) + Command_Opcode(2) + Status(1) + Connection_Handle(2) + RSSI(1)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 6 bytes")
        num_hci_command_packets, opcode, status, rem_data = cls.get_basic_event_data(data)
        # Parse the Read RSSI return parameters
        connection_handle, rssi = struct.unpack("<Hb", rem_data)
        
        return cls(
            num_hci_command_packets=num_hci_command_packets,
            opcode=opcode,
            status=status,
            connection_handle=connection_handle,
            rssi=rssi
        )

    def __str__(self) -> str:
        """ string representation of the event packet"""
        return super().__str__() + f"connection_handle=0x{self.params['connection_handle']:04X}, " \
               f"rssi={self.params['rssi']} (0x{self.params['rssi']:02X})"

class ReadLinkQualityCompleteEvent(CommandCompleteEvent):
    """Read Link Quality Complete Event"""
    OPCODE = create_opcode(OGF.STATUS_PARAMS, StatusOCF.READ_LINK_QUALITY)
    EVENT_CODE = HciEventCode.COMMAND_COMPLETE  # This is a Command Complete event
    NAME = "Read_Link_Quality_Complete"
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int, link_quality: int):
        """
        Initialize Read Link Quality Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            link_quality: Link quality (0-255, higher values mean better quality)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        # For Command Complete events, we need to construct the return parameters
        # The return parameters for Read Link Quality are:
        # - Status (1 byte)
        # - Connection_Handle (2 bytes)
        # - Link_Quality (1 byte)
        return_parameters = struct.pack("<BHB", status, connection_handle, link_quality)
        
        super().__init__(
            num_hci_command_packets=1,  # Always set to 1
            command_opcode=0x1403,      # Read Link Quality opcode (OGF=0x05, OCF=0x03)
            return_parameters=return_parameters,
            # Store the actual parameters for easier access
            status=status,
            connection_handle=connection_handle,
            link_quality=link_quality
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate num_hci_command_packets
        if not (0 <= self.params['num_hci_command_packets'] <= 0xFF):
            raise ValueError(f"Invalid num_hci_command_packets: {self.params['num_hci_command_packets']}, must be between 0 and 0xFF")
        
        # Validate command opcode
        if not (0 <= self.params['command_opcode'] <= 0xFFFF):
            raise ValueError(f"Invalid command_opcode: {self.params['command_opcode']}, must be between 0 and 0xFFFF")
        
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate link quality
        if not (0 <= self.params['link_quality'] <= 0xFF):
            raise ValueError(f"Invalid link_quality: {self.params['link_quality']}, must be between 0 and 0xFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Command Complete event format:
        # - 1 byte: Number of HCI Command Packets
        # - 2 bytes: Command Opcode
        # - N bytes: Return Parameters
        return struct.pack("<BH", 
                         self.params['num_hci_command_packets'],
                         self.params['command_opcode']) + self.params['return_parameters']
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadLinkQualityCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 7:  # Num_HCI_Command_Packets(1) + Command_Opcode(2) + Status(1) + Connection_Handle(2) + Link_Quality(1)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 7 bytes")
        
        # Parse the Command Complete event parameters
        num_cmd_pkts, cmd_opcode = struct.unpack("<BH", data[:3])
        
        # Check if this is a Read Link Quality command
        if cmd_opcode != 0x1403:  # Read Link Quality opcode
            raise ValueError(f"Invalid command opcode: 0x{cmd_opcode:04X}, expected 0x1403 (Read Link Quality)")
        
        # Parse the Read Link Quality return parameters
        status, connection_handle, link_quality = struct.unpack("<BHB", data[3:7])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            link_quality=link_quality
        )

class ReadAFHChannelMapCompleteEvent(CommandCompleteEvent):
    """Read AFH Channel Map Complete Event"""
    OPCODE = create_opcode(OGF.STATUS_PARAMS, StatusOCF.READ_AFH_CHANNEL_MAP)
    EVENT_CODE = HciEventCode.COMMAND_COMPLETE  # This is a Command Complete event
    NAME = "Read_AFH_Channel_Map_Complete"
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int, 
                 afh_mode: int, afh_channel_map: bytes):
        """
        Initialize Read AFH Channel Map Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            afh_mode: AFH mode (0 = disabled, 1 = enabled)
            afh_channel_map: AFH channel map (10 bytes)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        # For Command Complete events, we need to construct the return parameters
        # The return parameters for Read AFH Channel Map are:
        # - Status (1 byte)
        # - Connection_Handle (2 bytes)
        # - AFH_Mode (1 byte)
        # - AFH_Channel_Map (10 bytes)
        return_parameters = struct.pack("<BHB", status, connection_handle, afh_mode) + afh_channel_map
        
        super().__init__(
            num_hci_command_packets=1,  # Always set to 1
            command_opcode=0x1406,      # Read AFH Channel Map opcode (OGF=0x05, OCF=0x06)
            return_parameters=return_parameters,
            # Store the actual parameters for easier access
            status=status,
            connection_handle=connection_handle,
            afh_mode=afh_mode,
            afh_channel_map=afh_channel_map
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate num_hci_command_packets
        if not (0 <= self.params['num_hci_command_packets'] <= 0xFF):
            raise ValueError(f"Invalid num_hci_command_packets: {self.params['num_hci_command_packets']}, must be between 0 and 0xFF")
        
        # Validate command opcode
        if not (0 <= self.params['command_opcode'] <= 0xFFFF):
            raise ValueError(f"Invalid command_opcode: {self.params['command_opcode']}, must be between 0 and 0xFFFF")
        
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate AFH mode
        if self.params['afh_mode'] not in (0, 1):
            raise ValueError(f"Invalid afh_mode: {self.params['afh_mode']}, must be 0 or 1")
        
        # Validate AFH channel map
        if len(self.params['afh_channel_map']) != 10:
            raise ValueError(f"Invalid afh_channel_map length: {len(self.params['afh_channel_map'])}, must be 10 bytes")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Command Complete event format:
        # - 1 byte: Number of HCI Command Packets
        # - 2 bytes: Command Opcode
        # - N bytes: Return Parameters
        return struct.pack("<BH", 
                         self.params['num_hci_command_packets'],
                         self.params['command_opcode']) + self.params['return_parameters']
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadAFHChannelMapCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 16:  # Num_HCI_Command_Packets(1) + Command_Opcode(2) + Status(1) + Connection_Handle(2) + AFH_Mode(1) + AFH_Channel_Map(10)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 16 bytes")
        
        # Parse the Command Complete event parameters
        num_cmd_pkts, cmd_opcode = struct.unpack("<BH", data[:3])
        
        # Check if this is a Read AFH Channel Map command
        if cmd_opcode != 0x1406:  # Read AFH Channel Map opcode
            raise ValueError(f"Invalid command opcode: 0x{cmd_opcode:04X}, expected 0x1406 (Read AFH Channel Map)")
        
        # Parse the Read AFH Channel Map return parameters
        status, connection_handle, afh_mode = struct.unpack("<BHB", data[3:7])
        afh_channel_map = data[7:17]
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            afh_mode=afh_mode,
            afh_channel_map=afh_channel_map
        )

class ReadClockCompleteEvent(CommandCompleteEvent):
    """Read Clock Complete Event"""
    OPCODE = create_opcode(OGF.STATUS_PARAMS, StatusOCF.READ_CLOCK)
    EVENT_CODE = HciEventCode.COMMAND_COMPLETE  # This is a Command Complete event
    NAME = "Read_Clock_Complete"
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int, 
                 clock: int, accuracy: int):
        """
        Initialize Read Clock Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle (0xFFFF for local device)
            clock: Clock value (4 bytes)
            accuracy: Clock accuracy (2 bytes, microseconds)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        # For Command Complete events, we need to construct the return parameters
        # The return parameters for Read Clock are:
        # - Status (1 byte)
        # - Connection_Handle (2 bytes)
        # - Clock (4 bytes)
        # - Accuracy (2 bytes)
        return_parameters = struct.pack("<BHIH", status, connection_handle, clock, accuracy)
        
        super().__init__(
            num_hci_command_packets=1,  # Always set to 1
            command_opcode=0x1407,      # Read Clock opcode (OGF=0x05, OCF=0x07)
            return_parameters=return_parameters,
            # Store the actual parameters for easier access
            status=status,
            connection_handle=connection_handle,
            clock=clock,
            accuracy=accuracy
        ) 
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate num_hci_command_packets
        if not (0 <= self.params['num_hci_command_packets'] <= 0xFF):
            raise ValueError(f"Invalid num_hci_command_packets: {self.params['num_hci_command_packets']}, must be between 0 and 0xFF")
        
        # Validate command opcode
        if not (0 <= self.params['command_opcode'] <= 0xFFFF):
            raise ValueError(f"Invalid command_opcode: {self.params['command_opcode']}, must be between 0 and 0xFFFF")
        
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0xFFFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0xFFFF")
        
        # Validate clock
        if not (0 <= self.params['clock'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid clock: {self.params['clock']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate accuracy
        if not (0 <= self.params['accuracy'] <= 0xFFFF):
            raise ValueError(f"Invalid accuracy: {self.params['accuracy']}, must be between 0 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Command Complete event format:
        # - 1 byte: Number of HCI Command Packets
        # - 2 bytes: Command Opcode
        # - N bytes: Return Parameters
        return struct.pack("<BH", 
                         self.params['num_hci_command_packets'],
                         self.params['command_opcode']) + self.params['return_parameters']
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadClockCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 12:  # Num_HCI_Command_Packets(1) + Command_Opcode(2) + Status(1) + Connection_Handle(2) + Clock(4) + Accuracy(2)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 12 bytes")
        
        # Parse the Command Complete event parameters
        num_cmd_pkts, cmd_opcode = struct.unpack("<BH", data[:3])
        
        # Check if this is a Read Clock command
        if cmd_opcode != cls.OPCODE:  # Read Clock opcode
            raise ValueError(f"Invalid command opcode: 0x{cmd_opcode:04X}, expected 0x1407 (Read Clock)")
        
        # Parse the Read Clock return parameters
        status, connection_handle, clock, accuracy = struct.unpack("<BHIH", data[3:12])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            clock=clock,
            accuracy=accuracy
        )
        


# Register all event classes
register_event(ReadRssiCompleteEvent)
register_event(ReadLinkQualityCompleteEvent)
register_event(ReadAFHChannelMapCompleteEvent)
register_event(ReadClockCompleteEvent)


# Function wrappers for easier access
def read_rssi_complete(status: Union[int, StatusCode], connection_handle: int, 
                     rssi: int) -> ReadRssiCompleteEvent:
    """Create Read RSSI Complete Event"""
    return ReadRssiCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        rssi=rssi
    )

def read_link_quality_complete(status: Union[int, StatusCode], connection_handle: int,
                             link_quality: int) -> ReadLinkQualityCompleteEvent:
    """Create Read Link Quality Complete Event"""
    return ReadLinkQualityCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        link_quality=link_quality
    )

def read_afh_channel_map_complete(status: Union[int, StatusCode], connection_handle: int,
                                afh_mode: int, afh_channel_map: bytes) -> ReadAFHChannelMapCompleteEvent:
    """Create Read AFH Channel Map Complete Event"""
    return ReadAFHChannelMapCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        afh_mode=afh_mode,
        afh_channel_map=afh_channel_map
    )

def read_clock_complete(status: Union[int, StatusCode], connection_handle: int,
                      clock: int, accuracy: int) -> ReadClockCompleteEvent:
    """Create Read Clock Complete Event"""
    return ReadClockCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        clock=clock,
        accuracy=accuracy
    )

# Export public functions and classes
__all__ = [
    'read_rssi_complete',
    'read_link_quality_complete',
    'read_afh_channel_map_complete',
    'read_clock_complete',
    'CommandStatusEvent',
    'ReadRssiCompleteEvent',
    'ReadLinkQualityCompleteEvent',
    'ReadAFHChannelMapCompleteEvent',
    'ReadClockCompleteEvent',
]