"""
LE (Low Energy) events module

This module provides implementations for LE HCI events.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode, LeMetaEventSubCode
from ..event_types import LEEventType
from ..error_codes import StatusCode
from .. import register_event

class LeConnectionCompleteEvent(HciEvtBasePacket):
    """LE Connection Complete Event"""
    
    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CONNECTION_COMPLETE
    NAME = "LE_Connection_Complete"
    
    # Role values
    class Role(IntEnum):
        MASTER = 0x00
        SLAVE = 0x01
    
    def __init__(self, 
                 status: Union[int, StatusCode],
                 connection_handle: int,
                 role: Union[int, 'LeConnectionCompleteEvent.Role'],
                 peer_address_type: int,
                 peer_address: bytes,
                 conn_interval: int,
                 conn_latency: int,
                 supervision_timeout: int,
                 master_clock_accuracy: int):
        """
        Initialize LE Connection Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            role: Role (0x00 = Master, 0x01 = Slave)
            peer_address_type: Peer address type
            peer_address: Peer address (6 bytes)
            conn_interval: Connection interval
            conn_latency: Connection latency
            supervision_timeout: Supervision timeout
            master_clock_accuracy: Master clock accuracy
        """
        # Convert enum values to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        if isinstance(role, self.Role):
            role = role.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            role=role,
            peer_address_type=peer_address_type,
            peer_address=peer_address,
            conn_interval=conn_interval,
            conn_latency=conn_latency,
            supervision_timeout=supervision_timeout,
            master_clock_accuracy=master_clock_accuracy
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate role
        if self.params['role'] not in (0x00, 0x01):
            raise ValueError(f"Invalid role: {self.params['role']}, must be 0x00 (Master) or 0x01 (Slave)")
        
        # Validate peer address type
        if not (0 <= self.params['peer_address_type'] <= 3):
            raise ValueError(f"Invalid peer_address_type: {self.params['peer_address_type']}, must be between 0 and 3")
        
        # Validate peer address
        if len(self.params['peer_address']) != 6:
            raise ValueError(f"Invalid peer_address length: {len(self.params['peer_address'])}, must be 6 bytes")
        
        # Validate connection interval
        if not (0x0006 <= self.params['conn_interval'] <= 0x0C80):
            raise ValueError(f"Invalid conn_interval: {self.params['conn_interval']}, must be between 0x0006 and 0x0C80")
        
        # Validate connection latency
        if not (0x0000 <= self.params['conn_latency'] <= 0x01F3):
            raise ValueError(f"Invalid conn_latency: {self.params['conn_latency']}, must be between 0x0000 and 0x01F3")
        
        # Validate supervision timeout
        if not (0x000A <= self.params['supervision_timeout'] <= 0x0C80):
            raise ValueError(f"Invalid supervision_timeout: {self.params['supervision_timeout']}, must be between 0x000A and 0x0C80")
        
        # Validate master clock accuracy
        if not (0 <= self.params['master_clock_accuracy'] <= 7):
            raise ValueError(f"Invalid master_clock_accuracy: {self.params['master_clock_accuracy']}, must be between 0 and 7")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<BBHBB",
                           self.params['subevent_code'],
                           self.params['status'],
                           self.params['connection_handle'],
                           self.params['role'],
                           self.params['peer_address_type'])
        
        # Add peer address (reversed for little-endian)
        result += bytes(reversed(self.params['peer_address']))
        
        # Add remaining parameters
        result += struct.pack("<HHHB",
                            self.params['conn_interval'],
                            self.params['conn_latency'],
                            self.params['supervision_timeout'],
                            self.params['master_clock_accuracy'])
        
        return result
    
    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int)-> 'LeConnectionCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 19:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 19 bytes")
        
        # Parse parameters
        subevent_code, status, connection_handle, role, peer_address_type = struct.unpack("<BBHBB", data[:6])
        
        # Extract peer address (6 bytes, reversed for little-endian)
        peer_address = bytes(reversed(data[6:12]))
        
        # Parse remaining parameters
        conn_interval, conn_latency, supervision_timeout, master_clock_accuracy = struct.unpack("<HHHB", data[12:19])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            role=role,
            peer_address_type=peer_address_type,
            peer_address=peer_address,
            conn_interval=conn_interval,
            conn_latency=conn_latency,
            supervision_timeout=supervision_timeout,
            master_clock_accuracy=master_clock_accuracy
        )

class LeAdvertisingReportEvent(HciEvtBasePacket):
    """LE Advertising Report Event"""
    
    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.ADVERTISING_REPORT
    NAME = "LE_Advertising_Report"
    
    # Event type values
    class EventType(IntEnum):
        ADV_IND = 0x00           # Connectable undirected advertising
        ADV_DIRECT_IND = 0x01    # Connectable directed advertising
        ADV_SCAN_IND = 0x02      # Scannable undirected advertising
        ADV_NONCONN_IND = 0x03   # Non-connectable undirected advertising
        SCAN_RSP = 0x04          # Scan response
    
    def __init__(self, 
                 num_reports: int,
                 event_type: Union[int, 'LeAdvertisingReportEvent.EventType'],
                 address_type: int,
                 address: bytes,
                 data_length: int,
                 data: bytes,
                 rssi: int):
        """
        Initialize LE Advertising Report Event
        
        Args:
            num_reports: Number of reports in this event
            event_type: Type of advertising report
            address_type: Address type
            address: Advertiser address (6 bytes)
            data_length: Length of advertising data
            data: Advertising data
            rssi: RSSI value (signed byte, 127 = not available)
        """
        # Convert enum value to integer if needed
        if isinstance(event_type, self.EventType):
            event_type = event_type.value
            
        super().__init__(
            num_reports=num_reports,
            event_type=event_type,
            address_type=address_type,
            address=address,
            data_length=data_length,
            data=data,
            rssi=rssi
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate number of reports
        if not (1 <= self.params['num_reports'] <= 0xFF):
            raise ValueError(f"Invalid num_reports: {self.params['num_reports']}, must be between 1 and 0xFF")
        
        # Validate event type
        if not (0 <= self.params['event_type'] <= 4):
            raise ValueError(f"Invalid event_type: {self.params['event_type']}, must be between 0 and 4")
        
        # Validate address type
        if not (0 <= self.params['address_type'] <= 3):
            raise ValueError(f"Invalid address_type: {self.params['address_type']}, must be between 0 and 3")
        
        # Validate address
        if len(self.params['address']) != 6:
            raise ValueError(f"Invalid address length: {len(self.params['address'])}, must be 6 bytes")
        
        # Validate data length
        if not (0 <= self.params['data_length'] <= 31):
            raise ValueError(f"Invalid data_length: {self.params['data_length']}, must be between 0 and 31")
        
        # Validate data
        if len(self.params['data']) != self.params['data_length']:
            raise ValueError(f"Data length mismatch: data_length is {self.params['data_length']}, but data is {len(self.params['data'])} bytes")
        
        # Validate RSSI
        if not (-127 <= self.params['rssi'] <= 127):
            raise ValueError(f"Invalid rssi: {self.params['rssi']}, must be between -127 and 127")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<BBB",
                           self.params['subevent_code'],
                           self.params['num_reports'],
                           self.params['event_type'])
        
        # Add address type
        result += struct.pack("<B", self.params['address_type'])
        
        # Add address (reversed for little-endian)
        result += bytes(reversed(self.params['address']))
        
        # Add data length and data
        result += struct.pack("<B", self.params['data_length'])
        result += self.params['data']
        
        # Add RSSI
        result += struct.pack("<b", self.params['rssi'])
        
        return result
    
    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int) -> 'LeAdvertisingReportEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 12:  # Need at least basic parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 12 bytes")
        # Parse beginning parameters
        subevent_code, num_reports, event_type, address_type = struct.unpack("<BBBB", data[:4])
        
        # Extract address (6 bytes, reversed for little-endian)
        address = bytes(reversed(data[4:10]))
        
        # Get data length
        data_length = data[10]
        
        # Make sure we have enough bytes for the data and RSSI
        if len(data) < 12 + data_length:
            raise ValueError(f"Invalid data length: need {12 + data_length} bytes, got {len(data)}")
        
        # Extract advertising data
        adv_data = data[11:11+data_length]
        
        # Extract RSSI
        rssi = struct.unpack("<b", data[11+data_length:12+data_length])[0]
        
        return cls(
            num_reports=num_reports,
            event_type=event_type,
            address_type=address_type,
            address=address,
            data_length=data_length,
            data=adv_data,
            rssi=rssi
        )

class LeConnectionUpdateCompleteEvent(HciEvtBasePacket):
    """LE Connection Update Complete Event"""
    
    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CONNECTION_UPDATE_COMPLETE
    NAME = "LE_Connection_Update_Complete"
    
    def __init__(self, 
                 status: Union[int, StatusCode],
                 connection_handle: int,
                 conn_interval: int,
                 conn_latency: int,
                 supervision_timeout: int):
        """
        Initialize LE Connection Update Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            conn_interval: Connection interval
            conn_latency: Connection latency
            supervision_timeout: Supervision timeout
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            conn_interval=conn_interval,
            conn_latency=conn_latency,
            supervision_timeout=supervision_timeout
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate connection interval
        if not (0x0006 <= self.params['conn_interval'] <= 0x0C80):
            raise ValueError(f"Invalid conn_interval: {self.params['conn_interval']}, must be between 0x0006 and 0x0C80")
        
        # Validate connection latency
        if not (0x0000 <= self.params['conn_latency'] <= 0x01F3):
            raise ValueError(f"Invalid conn_latency: {self.params['conn_latency']}, must be between 0x0000 and 0x01F3")
        
        # Validate supervision timeout
        if not (0x000A <= self.params['supervision_timeout'] <= 0x0C80):
            raise ValueError(f"Invalid supervision_timeout: {self.params['supervision_timeout']}, must be between 0x000A and 0x0C80")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BBHHH",
                          self.params['subevent_code'],
                          self.params['status'],
                          self.params['connection_handle'],
                          self.params['conn_interval'],
                          self.params['conn_latency'],
                          self.params['supervision_timeout'])
    
    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int) -> 'LeConnectionUpdateCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 9:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 9 bytes")
        subevent_code, status, connection_handle, conn_interval, conn_latency, supervision_timeout = struct.unpack("<BBHHH", data[:9])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            conn_interval=conn_interval,
            conn_latency=conn_latency,
            supervision_timeout=supervision_timeout
        )

class LeReadRemoteFeaturesCompleteEvent(HciEvtBasePacket):
    """LE Read Remote Features Complete Event"""
    
    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.READ_REMOTE_FEATURES_COMPLETE
    NAME = "LE_Read_Remote_Features_Complete"
    
    def __init__(self, 
                 status: Union[int, StatusCode],
                 connection_handle: int,
                 le_features: bytes):
        """
        Initialize LE Read Remote Features Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            le_features: LE features (8 bytes)
        """
        # Convert enum value to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            le_features=le_features
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate LE features
        if len(self.params['le_features']) != 8:
            raise ValueError(f"Invalid le_features length: {len(self.params['le_features'])}, must be 8 bytes")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<BBH",
                           self.params['subevent_code'],
                           self.params['status'],
                           self.params['connection_handle'])
        
        # Add LE features
        result += self.params['le_features']
        
        return result
    
    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int) -> 'LeReadRemoteFeaturesCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 12:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 12 bytes")
        
        subevent_code, status, connection_handle = struct.unpack("<BBH", data[:4])
        le_features = data[4:12]
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            le_features=le_features
        )

# Register all event classes
register_event(LeConnectionCompleteEvent)
register_event(LeAdvertisingReportEvent)
register_event(LeConnectionUpdateCompleteEvent)
register_event(LeReadRemoteFeaturesCompleteEvent)

# Function wrappers for easier access
def le_connection_complete(status: Union[int, StatusCode], connection_handle: int,
                         role: Union[int, LeConnectionCompleteEvent.Role], peer_address_type: int,
                         peer_address: bytes, conn_interval: int, conn_latency: int,
                         supervision_timeout: int, master_clock_accuracy: int) -> LeConnectionCompleteEvent:
    """Create LE Connection Complete Event"""
    return LeConnectionCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        role=role,
        peer_address_type=peer_address_type,
        peer_address=peer_address,
        conn_interval=conn_interval,
        conn_latency=conn_latency,
        supervision_timeout=supervision_timeout,
        master_clock_accuracy=master_clock_accuracy
    )

def le_advertising_report(num_reports: int, event_type: Union[int, LeAdvertisingReportEvent.EventType],
                        address_type: int, address: bytes, data_length: int,
                        data: bytes, rssi: int) -> LeAdvertisingReportEvent:
    """Create LE Advertising Report Event"""
    return LeAdvertisingReportEvent(
        num_reports=num_reports,
        event_type=event_type,
        address_type=address_type,
        address=address,
        data_length=data_length,
        data=data,
        rssi=rssi
    )

def le_connection_update_complete(status: Union[int, StatusCode], connection_handle: int,
                                conn_interval: int, conn_latency: int,
                                supervision_timeout: int) -> LeConnectionUpdateCompleteEvent:
    """Create LE Connection Update Complete Event"""
    return LeConnectionUpdateCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        conn_interval=conn_interval,
        conn_latency=conn_latency,
        supervision_timeout=supervision_timeout
    )

def le_read_remote_features_complete(status: Union[int, StatusCode], connection_handle: int,
                                   le_features: bytes) -> LeReadRemoteFeaturesCompleteEvent:
    """Create LE Read Remote Features Complete Event"""
    return LeReadRemoteFeaturesCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        le_features=le_features
    )

# # Export public functions and classes
__all__ = [
    'le_connection_complete',
    'le_advertising_report',
    'le_connection_update_complete',
    'le_read_remote_features_complete',
    'LeConnectionCompleteEvent',
    'LeAdvertisingReportEvent',
    'LeConnectionUpdateCompleteEvent',
    'LeReadRemoteFeaturesCompleteEvent',
]