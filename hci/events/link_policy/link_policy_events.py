"""
Link Policy events module

This module provides implementations for Link Policy HCI events.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..hci_packet import HciEventPacket
from .evt_base_packet import HciEvtBasePacket
from .evt_codes import HciEventCode
from .event_types import LinkPolicyEventType
from .error_codes import StatusCode
from .. import register_event

class ModeChangeEvent(HciEvtBasePacket):
    """Mode Change Event"""
    
    EVENT_CODE = HciEventCode.MODE_CHANGE
    NAME = "Mode_Change"
    
    # Current modes
    class Mode(IntEnum):
        ACTIVE = 0x00
        HOLD = 0x01
        SNIFF = 0x02
        PARK = 0x03
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int, 
                current_mode: Union[int, 'ModeChangeEvent.Mode'], interval: int):
        """
        Initialize Mode Change Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            current_mode: Current mode (0x00 = Active Mode, 0x01 = Hold Mode, 
                          0x02 = Sniff Mode, 0x03 = Park Mode)
            interval: Hold, Sniff, or Park interval (depend on current_mode)
        """
        # Convert enum values to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        if isinstance(current_mode, self.Mode):
            current_mode = current_mode.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            current_mode=current_mode,
            interval=interval
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate current mode
        if not (0 <= self.params['current_mode'] <= 3):
            raise ValueError(f"Invalid current_mode: {self.params['current_mode']}, must be between 0 and 3")
        
        # Validate interval (depends on current mode)
        if not (0 <= self.params['interval'] <= 0xFFFF):
            raise ValueError(f"Invalid interval: {self.params['interval']}, must be between 0 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BHBH",
                          self.params['status'],
                          self.params['connection_handle'],
                          self.params['current_mode'],
                          self.params['interval'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ModeChangeEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 6:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 6 bytes")
        
        status, connection_handle, current_mode, interval = struct.unpack("<BHBH", data[:6])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            current_mode=current_mode,
            interval=interval
        )

class RoleChangeEvent(HciEvtBasePacket):
    """Role Change Event"""
    
    EVENT_CODE = HciEventCode.ROLE_CHANGE
    NAME = "Role_Change"
    
    # Current roles
    class Role(IntEnum):
        MASTER = 0x00
        SLAVE = 0x01
    
    def __init__(self, status: Union[int, StatusCode], bd_addr: bytes, 
                new_role: Union[int, 'RoleChangeEvent.Role']):
        """
        Initialize Role Change Event
        
        Args:
            status: Command status (0x00 = success)
            bd_addr: Bluetooth device address (6 bytes)
            new_role: New role (0x00 = Master, 0x01 = Slave)
        """
        # Convert enum values to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        if isinstance(new_role, self.Role):
            new_role = new_role.value
            
        super().__init__(
            status=status,
            bd_addr=bd_addr,
            new_role=new_role
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate BD_ADDR
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid BD_ADDR length: {len(self.params['bd_addr'])}, must be 6 bytes")
        
        # Validate new role
        if self.params['new_role'] not in (0x00, 0x01):
            raise ValueError(f"Invalid new_role: {self.params['new_role']}, must be 0x00 (Master) or 0x01 (Slave)")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        result = struct.pack("<B", self.params['status'])
        
        # Add BD_ADDR (reversed for little-endian)
        result += bytes(reversed(self.params['bd_addr']))
        
        # Add new role
        result += struct.pack("<B", self.params['new_role'])
        
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'RoleChangeEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 8:  # Need status (1 byte), BD_ADDR (6 bytes), and new role (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 8 bytes")
        
        status = data[0]
        
        # Extract BD_ADDR (6 bytes, reversed for little-endian)
        bd_addr = bytes(reversed(data[1:7]))
        
        new_role = data[7]
        
        return cls(
            status=status,
            bd_addr=bd_addr,
            new_role=new_role
        )

class QosSetupCompleteEvent(HciEvtBasePacket):
    """QoS Setup Complete Event"""
    
    EVENT_CODE = HciEventCode.QOS_SETUP_COMPLETE
    NAME = "QoS_Setup_Complete"
    
    # Service type values
    class ServiceType(IntEnum):
        NO_TRAFFIC = 0x00
        BEST_EFFORT = 0x01
        GUARANTEED = 0x02
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int,
                flags: int, service_type: Union[int, 'QosSetupCompleteEvent.ServiceType'],
                token_rate: int, peak_bandwidth: int, latency: int, delay_variation: int):
        """
        Initialize QoS Setup Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            flags: Reserved for future use (0)
            service_type: Type of service (0x00 = No Traffic, 0x01 = Best Effort, 0x02 = Guaranteed)
            token_rate: Token rate (bytes/second)
            peak_bandwidth: Peak bandwidth (bytes/second)
            latency: Maximum latency (microseconds)
            delay_variation: Delay variation (microseconds)
        """
        # Convert enum values to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        if isinstance(service_type, self.ServiceType):
            service_type = service_type.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            flags=flags,
            service_type=service_type,
            token_rate=token_rate,
            peak_bandwidth=peak_bandwidth,
            latency=latency,
            delay_variation=delay_variation
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate flags
        if self.params['flags'] != 0:
            raise ValueError(f"Invalid flags: {self.params['flags']}, must be 0")
        
        # Validate service type
        if not (0 <= self.params['service_type'] <= 2):
            raise ValueError(f"Invalid service_type: {self.params['service_type']}, must be between 0 and 2")
        
        # Validate token rate
        if not (0 <= self.params['token_rate'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid token_rate: {self.params['token_rate']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate peak bandwidth
        if not (0 <= self.params['peak_bandwidth'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid peak_bandwidth: {self.params['peak_bandwidth']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate latency
        if not (0 <= self.params['latency'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid latency: {self.params['latency']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate delay variation
        if not (0 <= self.params['delay_variation'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid delay_variation: {self.params['delay_variation']}, must be between 0 and 0xFFFFFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BHBBIIII",
                          self.params['status'],
                          self.params['connection_handle'],
                          self.params['flags'],
                          self.params['service_type'],
                          self.params['token_rate'],
                          self.params['peak_bandwidth'],
                          self.params['latency'],
                          self.params['delay_variation'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'QosSetupCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 21:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 21 bytes")
        
        status, connection_handle, flags, service_type, token_rate, peak_bandwidth, latency, delay_variation = struct.unpack("<BHBBIIII", data[:21])
        
        return cls(
            status=status,
            connection_handle=connection_handle,
            flags=flags,
            service_type=service_type,
            token_rate=token_rate,
            peak_bandwidth=peak_bandwidth,
            latency=latency,
            delay_variation=delay_variation
        )

class FlowSpecificationCompleteEvent(HciEvtBasePacket):
    """Flow Specification Complete Event"""
    
    EVENT_CODE = HciEventCode.FLOW_SPECIFICATION_COMPLETE
    NAME = "Flow_Specification_Complete"
    
    # Flow direction values
    class FlowDirection(IntEnum):
        OUTGOING = 0x00
        INCOMING = 0x01
    
    # Service type values (same as QoS)
    class ServiceType(IntEnum):
        NO_TRAFFIC = 0x00
        BEST_EFFORT = 0x01
        GUARANTEED = 0x02
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int,
                flags: int, flow_direction: Union[int, 'FlowSpecificationCompleteEvent.FlowDirection'],
                service_type: Union[int, 'FlowSpecificationCompleteEvent.ServiceType'],
                token_rate: int, token_bucket_size: int, peak_bandwidth: int, 
                access_latency: int):
        """
        Initialize Flow Specification Complete Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            flags: Reserved for future use (0)
            flow_direction: Direction of flow (0x00 = Outgoing, 0x01 = Incoming)
            service_type: Type of service (0x00 = No Traffic, 0x01 = Best Effort, 0x02 = Guaranteed)
            token_rate: Token rate (bytes/second)
            token_bucket_size: Token bucket size (bytes)
            peak_bandwidth: Peak bandwidth (bytes/second)
            access_latency: Access latency (microseconds)
        """
        # Convert enum values to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        if isinstance(flow_direction, self.FlowDirection):
            flow_direction = flow_direction.value
            
        if isinstance(service_type, self.ServiceType):
            service_type = service_type.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            flags=flags,
            flow_direction=flow_direction,
            service_type=service_type,
            token_rate=token_rate,
            token_bucket_size=token_bucket_size,
            peak_bandwidth=peak_bandwidth,
            access_latency=access_latency
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate flags
        if self.params['flags'] != 0:
            raise ValueError(f"Invalid flags: {self.params['flags']}, must be 0")
        
        # Validate flow direction
        if self.params['flow_direction'] not in (0x00, 0x01):
            raise ValueError(f"Invalid flow_direction: {self.params['flow_direction']}, must be 0x00 (Outgoing) or 0x01 (Incoming)")
        
        # Validate service type
        if not (0 <= self.params['service_type'] <= 2):
            raise ValueError(f"Invalid service_type: {self.params['service_type']}, must be between 0 and 2")
        
        # Validate token rate
        if not (0 <= self.params['token_rate'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid token_rate: {self.params['token_rate']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate token bucket size
        if not (0 <= self.params['token_bucket_size'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid token_bucket_size: {self.params['token_bucket_size']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate peak bandwidth
        if not (0 <= self.params['peak_bandwidth'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid peak_bandwidth: {self.params['peak_bandwidth']}, must be between 0 and 0xFFFFFFFF")
        
        # Validate access latency
        if not (0 <= self.params['access_latency'] <= 0xFFFFFFFF):
            raise ValueError(f"Invalid access_latency: {self.params['access_latency']}, must be between 0 and 0xFFFFFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BHBBIIII",
                          self.params['status'],
                          self.params['connection_handle'],
                          self.params['flags'],
                          self.params['flow_direction'],
                          self.params['service_type'],
                          self.params['token_rate'],
                          self.params['token_bucket_size'],
                          self.params['peak_bandwidth'],
                          self.params['access_latency'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'FlowSpecificationCompleteEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 22:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 22 bytes")
        
        fields = struct.unpack("<BHBBIIII", data[:22])
        
        return cls(
            status=fields[0],
            connection_handle=fields[1],
            flags=fields[2],
            flow_direction=fields[3],
            service_type=fields[4],
            token_rate=fields[5],
            token_bucket_size=fields[6],
            peak_bandwidth=fields[7],
            access_latency=fields[8]
        )

class SniffSubratingEvent(HciEvtBasePacket):
    """Sniff Subrating Event"""
    
    EVENT_CODE = HciEventCode.SNIFF_SUBRATING
    NAME = "Sniff_Subrating"
    
    def __init__(self, status: Union[int, StatusCode], connection_handle: int,
                maximum_transmit_latency: int, maximum_receive_latency: int,
                minimum_remote_timeout: int, minimum_local_timeout: int):
        """
        Initialize Sniff Subrating Event
        
        Args:
            status: Command status (0x00 = success)
            connection_handle: Connection handle
            maximum_transmit_latency: Maximum transmit latency (slots)
            maximum_receive_latency: Maximum receive latency (slots)
            minimum_remote_timeout: Minimum remote timeout (slots)
            minimum_local_timeout: Minimum local timeout (slots)
        """
        # Convert enum values to integer if needed
        if isinstance(status, StatusCode):
            status = status.value
            
        super().__init__(
            status=status,
            connection_handle=connection_handle,
            maximum_transmit_latency=maximum_transmit_latency,
            maximum_receive_latency=maximum_receive_latency,
            minimum_remote_timeout=minimum_remote_timeout,
            minimum_local_timeout=minimum_local_timeout
        )
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate status
        if not (0 <= self.params['status'] <= 0xFF):
            raise ValueError(f"Invalid status: {self.params['status']}, must be between 0 and 0xFF")
        
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")
        
        # Validate maximum transmit latency
        if not (0 <= self.params['maximum_transmit_latency'] <= 0xFFFF):
            raise ValueError(f"Invalid maximum_transmit_latency: {self.params['maximum_transmit_latency']}, must be between 0 and 0xFFFF")
        
        # Validate maximum receive latency
        if not (0 <= self.params['maximum_receive_latency'] <= 0xFFFF):
            raise ValueError(f"Invalid maximum_receive_latency: {self.params['maximum_receive_latency']}, must be between 0 and 0xFFFF")
        
        # Validate minimum remote timeout
        if not (0 <= self.params['minimum_remote_timeout'] <= 0xFFFF):
            raise ValueError(f"Invalid minimum_remote_timeout: {self.params['minimum_remote_timeout']}, must be between 0 and 0xFFFF")
        
        # Validate minimum local timeout
        if not (0 <= self.params['minimum_local_timeout'] <= 0xFFFF):
            raise ValueError(f"Invalid minimum_local_timeout: {self.params['minimum_local_timeout']}, must be between 0 and 0xFFFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BHHHHH",
                          self.params['status'],
                          self.params['connection_handle'],
                          self.params['maximum_transmit_latency'],
                          self.params['maximum_receive_latency'],
                          self.params['minimum_remote_timeout'],
                          self.params['minimum_local_timeout'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'SniffSubratingEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 11:  # Need all parameters
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 11 bytes")
        
        fields = struct.unpack("<BHHHHH", data[:11])
        
        return cls(
            status=fields[0],
            connection_handle=fields[1],
            maximum_transmit_latency=fields[2],
            maximum_receive_latency=fields[3],
            minimum_remote_timeout=fields[4],
            minimum_local_timeout=fields[5]
        )

# Register all event classes
register_event(ModeChangeEvent)
register_event(RoleChangeEvent)
register_event(QosSetupCompleteEvent)
register_event(FlowSpecificationCompleteEvent)
register_event(SniffSubratingEvent)

# Function wrappers for easier access
def mode_change(status: Union[int, StatusCode], connection_handle: int,
               current_mode: Union[int, ModeChangeEvent.Mode], interval: int) -> ModeChangeEvent:
    """Create Mode Change Event"""
    return ModeChangeEvent(
        status=status,
        connection_handle=connection_handle,
        current_mode=current_mode,
        interval=interval
    )

def role_change(status: Union[int, StatusCode], bd_addr: bytes,
               new_role: Union[int, RoleChangeEvent.Role]) -> RoleChangeEvent:
    """Create Role Change Event"""
    return RoleChangeEvent(
        status=status,
        bd_addr=bd_addr,
        new_role=new_role
    )

def qos_setup_complete(status: Union[int, StatusCode], connection_handle: int,
                      flags: int, service_type: Union[int, QosSetupCompleteEvent.ServiceType],
                      token_rate: int, peak_bandwidth: int, latency: int, 
                      delay_variation: int) -> QosSetupCompleteEvent:
    """Create QoS Setup Complete Event"""
    return QosSetupCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        flags=flags,
        service_type=service_type,
        token_rate=token_rate,
        peak_bandwidth=peak_bandwidth,
        latency=latency,
        delay_variation=delay_variation
    )

def flow_specification_complete(status: Union[int, StatusCode], connection_handle: int,
                               flags: int, flow_direction: Union[int, FlowSpecificationCompleteEvent.FlowDirection],
                               service_type: Union[int, FlowSpecificationCompleteEvent.ServiceType],
                               token_rate: int, token_bucket_size: int, peak_bandwidth: int,
                               access_latency: int) -> FlowSpecificationCompleteEvent:
    """Create Flow Specification Complete Event"""
    return FlowSpecificationCompleteEvent(
        status=status,
        connection_handle=connection_handle,
        flags=flags,
        flow_direction=flow_direction,
        service_type=service_type,
        token_rate=token_rate,
        token_bucket_size=token_bucket_size,
        peak_bandwidth=peak_bandwidth,
        access_latency=access_latency
    )

def sniff_subrating(status: Union[int, StatusCode], connection_handle: int,
                   maximum_transmit_latency: int, maximum_receive_latency: int,
                   minimum_remote_timeout: int, minimum_local_timeout: int) -> SniffSubratingEvent:
    """Create Sniff Subrating Event"""
    return SniffSubratingEvent(
        status=status,
        connection_handle=connection_handle,
        maximum_transmit_latency=maximum_transmit_latency,
        maximum_receive_latency=maximum_receive_latency,
        minimum_remote_timeout=minimum_remote_timeout,
        minimum_local_timeout=minimum_local_timeout
    )

# Export public functions and classes
__all__ = [
    'mode_change',
    'role_change',
    'qos_setup_complete',
    'flow_specification_complete',
    'sniff_subrating',
    'ModeChangeEvent',
    'RoleChangeEvent',
    'QosSetupCompleteEvent',
    'FlowSpecificationCompleteEvent',
    'SniffSubratingEvent',
]