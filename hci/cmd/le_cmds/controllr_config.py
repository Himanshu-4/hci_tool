"""
Low Energy (LE) HCI Commands

This module provides classes for Low Energy HCI commands.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import HciOpcode, create_opcode, OGF, LEControllerOCF
from .. import register_command

# LE Advertising Types
class AdvertisingType(IntEnum):
    ADV_IND = 0x00                  # Connectable and scannable undirected advertising
    ADV_DIRECT_IND = 0x01           # Connectable directed advertising
    ADV_SCAN_IND = 0x02             # Scannable undirected advertising
    ADV_NONCONN_IND = 0x03          # Non-connectable undirected advertising
    ADV_DIRECT_IND_LOW_DUTY = 0x04  # Connectable directed advertising (low duty cycle)

# LE Address Types
class AddressType(IntEnum):
    PUBLIC = 0x00
    RANDOM = 0x01
    PUBLIC_IDENTITY = 0x02
    RANDOM_IDENTITY = 0x03

class LeSetAdvParams(HciCmdBasePacket):
    """LE Set Advertising Parameters Command"""
    
    OPCODE = HciOpcode.LE_SET_ADVERTISING_PARAMETERS
    NAME = "LE_Set_Advertising_Parameters"
    
    def __init__(self, 
                 adv_interval_min: int = 0x0800,      # Default: 1.28s (0x0800 * 0.625ms)
                 adv_interval_max: int = 0x0800,      # Default: 1.28s (0x0800 * 0.625ms)
                 adv_type: Union[int, AdvertisingType] = AdvertisingType.ADV_IND,
                 own_addr_type: Union[int, AddressType] = AddressType.PUBLIC,
                 peer_addr_type: Union[int, AddressType] = AddressType.PUBLIC,
                 peer_addr: bytes = b'\x00\x00\x00\x00\x00\x00',
                 adv_channel_map: int = 0x07,         # All channels (ch 37, 38, 39)
                 adv_filter_policy: int = 0x00):      # Process all devices
        """
        Initialize LE Set Advertising Parameters Command
        
        Args:
            adv_interval_min: Minimum advertising interval (0x0020 to 0x4000, default: 0x0800)
                             Time = interval * 0.625 ms
            adv_interval_max: Maximum advertising interval (0x0020 to 0x4000, default: 0x0800)
                             Time = interval * 0.625 ms
            adv_type: Advertising type (see AdvertisingType enum)
            own_addr_type: Own address type (see AddressType enum)
            peer_addr_type: Peer address type for directed advertising (see AddressType enum)
            peer_addr: Peer address for directed advertising (6 bytes)
            adv_channel_map: Advertising channel map (bit 0: ch 37, bit 1: ch 38, bit 2: ch 39)
            adv_filter_policy: Advertising filter policy
        """
        # Convert enum values to integers if needed
        if isinstance(adv_type, AdvertisingType):
            adv_type = adv_type.value
        if isinstance(own_addr_type, AddressType):
            own_addr_type = own_addr_type.value
        if isinstance(peer_addr_type, AddressType):
            peer_addr_type = peer_addr_type.value
            
        super().__init__(
            adv_interval_min=adv_interval_min,
            adv_interval_max=adv_interval_max,
            adv_type=adv_type,
            own_addr_type=own_addr_type,
            peer_addr_type=peer_addr_type,
            peer_addr=peer_addr,
            adv_channel_map=adv_channel_map,
            adv_filter_policy=adv_filter_policy
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate advertising intervals
        if not (0x0020 <= self.params['adv_interval_min'] <= 0x4000):
            raise ValueError(f"Invalid adv_interval_min: {self.params['adv_interval_min']}, must be between 0x0020 and 0x4000")
        
        if not (0x0020 <= self.params['adv_interval_max'] <= 0x4000):
            raise ValueError(f"Invalid adv_interval_max: {self.params['adv_interval_max']}, must be between 0x0020 and 0x4000")
            
        if self.params['adv_interval_min'] > self.params['adv_interval_max']:
            raise ValueError(f"adv_interval_min ({self.params['adv_interval_min']}) must not be greater than adv_interval_max ({self.params['adv_interval_max']})")
        
        # Validate advertising type
        if not (0 <= self.params['adv_type'] <= 4):
            raise ValueError(f"Invalid adv_type: {self.params['adv_type']}, must be between 0 and 4")
        
        # Validate address types
        if not (0 <= self.params['own_addr_type'] <= 3):
            raise ValueError(f"Invalid own_addr_type: {self.params['own_addr_type']}, must be between 0 and 3")
            
        if not (0 <= self.params['peer_addr_type'] <= 3):
            raise ValueError(f"Invalid peer_addr_type: {self.params['peer_addr_type']}, must be between 0 and 3")
        
        # Validate peer address
        if len(self.params['peer_addr']) != 6:
            raise ValueError(f"Invalid peer_addr length: {len(self.params['peer_addr'])}, must be 6 bytes")
        
        # Validate advertising channel map
        if not (0x01 <= self.params['adv_channel_map'] <= 0x07):
            raise ValueError(f"Invalid adv_channel_map: {self.params['adv_channel_map']}, must be between 0x01 and 0x07")
        
        # Validate advertising filter policy
        if not (0 <= self.params['adv_filter_policy'] <= 3):
            raise ValueError(f"Invalid adv_filter_policy: {self.params['adv_filter_policy']}, must be between 0 and 3")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<HHBBBB6sBB",
                        self.params['adv_interval_min'],
                        self.params['adv_interval_max'],
                        self.params['adv_type'],
                        self.params['own_addr_type'],
                        self.params['peer_addr_type'],
                        *reversed(self.params['peer_addr']),  # Reverse for little-endian
                        self.params['adv_channel_map'],
                        self.params['adv_filter_policy'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LeSetAdvParams':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 15:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 15 bytes")
        
        adv_interval_min, adv_interval_max, adv_type, own_addr_type, peer_addr_type, \
        peer_addr_5, peer_addr_4, peer_addr_3, peer_addr_2, peer_addr_1, peer_addr_0, \
        adv_channel_map, adv_filter_policy = struct.unpack("<HHBBBBBBBBBBB", data[:15])
        
        peer_addr = bytes([peer_addr_0, peer_addr_1, peer_addr_2, peer_addr_3, peer_addr_4, peer_addr_5])
        
        return cls(
            adv_interval_min=adv_interval_min,
            adv_interval_max=adv_interval_max,
            adv_type=adv_type,
            own_addr_type=own_addr_type,
            peer_addr_type=peer_addr_type,
            peer_addr=peer_addr,
            adv_channel_map=adv_channel_map,
            adv_filter_policy=adv_filter_policy
        )

class LeSetAdvData(HciCmdBasePacket):
    """LE Set Advertising Data Command"""
    
    OPCODE = HciOpcode.LE_SET_ADVERTISING_DATA
    NAME = "LE_Set_Advertising_Data"
    
    def __init__(self, data: Union[bytes, List[int]] = b'', data_length: Optional[int] = None):
        """
        Initialize LE Set Advertising Data Command
        
        Args:
            data: Advertising data (0-31 bytes)
            data_length: Length of advertising data (if None, calculated from data)
        """
        # Convert list to bytes if needed
        if isinstance(data, list):
            data = bytes(data)
            
        # Calculate data length if not provided
        if data_length is None:
            data_length = len(data)
            
        super().__init__(data_length=data_length, data=data)
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate data length
        if not (0 <= self.params['data_length'] <= 31):
            raise ValueError(f"Invalid data_length: {self.params['data_length']}, must be between 0 and 31")
        
        # Validate data
        if len(self.params['data']) > 31:
            raise ValueError(f"Invalid data length: {len(self.params['data'])}, must be at most 31 bytes")
            
        if self.params['data_length'] != len(self.params['data']):
            raise ValueError(f"data_length ({self.params['data_length']}) does not match actual data length ({len(self.params['data'])})")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Pad data to 31 bytes
        data = self.params['data'] + b'\x00' * (31 - len(self.params['data']))
        return struct.pack("<B31s", self.params['data_length'], data)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LeSetAdvData':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 32:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 32 bytes")
        
        data_length = data[0]
        adv_data = data[1:data_length+1]
        
        return cls(data=adv_data, data_length=data_length)

class LeSetScanParameters(HciCmdBasePacket):
    """LE Set Scan Parameters Command"""
    
    OPCODE = HciOpcode.LE_SET_SCAN_PARAMETERS
    NAME = "LE_Set_Scan_Parameters"
    
    def __init__(self,
                 scan_type: int = 0x01,            # Active scanning (0x00: passive, 0x01: active)
                 scan_interval: int = 0x0010,      # Scan interval (0x0004 to 0x4000, default: 10ms)
                 scan_window: int = 0x0010,        # Scan window (0x0004 to 0x4000, default: 10ms)
                 own_addr_type: Union[int, AddressType] = AddressType.PUBLIC,
                 scanning_filter_policy: int = 0x00):  # Accept all advertisements
        """
        Initialize LE Set Scan Parameters Command
        
        Args:
            scan_type: 0x00 (passive scanning) or 0x01 (active scanning)
            scan_interval: Time between scan cycles (N * 0.625 ms)
            scan_window: Duration of scan cycle (N * 0.625 ms)
            own_addr_type: Type of address used in scan requests
            scanning_filter_policy: Scanning filter policy
        """
        # Convert enum values to integers if needed
        if isinstance(own_addr_type, AddressType):
            own_addr_type = own_addr_type.value
            
        super().__init__(
            scan_type=scan_type,
            scan_interval=scan_interval,
            scan_window=scan_window,
            own_addr_type=own_addr_type,
            scanning_filter_policy=scanning_filter_policy
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate scan type
        if self.params['scan_type'] not in (0x00, 0x01):
            raise ValueError(f"Invalid scan_type: {self.params['scan_type']}, must be 0x00 or 0x01")
        
        # Validate scan interval and window
        if not (0x0004 <= self.params['scan_interval'] <= 0x4000):
            raise ValueError(f"Invalid scan_interval: {self.params['scan_interval']}, must be between 0x0004 and 0x4000")
            
        if not (0x0004 <= self.params['scan_window'] <= 0x4000):
            raise ValueError(f"Invalid scan_window: {self.params['scan_window']}, must be between 0x0004 and 0x4000")
        
        if self.params['scan_window'] > self.params['scan_interval']:
            raise ValueError(f"scan_window ({self.params['scan_window']}) must not be greater than scan_interval ({self.params['scan_interval']})")
        
        # Validate own address type
        if not (0 <= self.params['own_addr_type'] <= 3):
            raise ValueError(f"Invalid own_addr_type: {self.params['own_addr_type']}, must be between 0 and 3")
        
        # Validate scanning filter policy
        if not (0 <= self.params['scanning_filter_policy'] <= 3):
            raise ValueError(f"Invalid scanning_filter_policy: {self.params['scanning_filter_policy']}, must be between 0 and 3")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BHHBB",
                           self.params['scan_type'],
                           self.params['scan_interval'],
                           self.params['scan_window'],
                           self.params['own_addr_type'],
                           self.params['scanning_filter_policy'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LeSetScanParameters':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 7 bytes")
        
        scan_type, scan_interval, scan_window, own_addr_type, scanning_filter_policy = struct.unpack("<BHHBB", data[:7])
        
        return cls(
            scan_type=scan_type,
            scan_interval=scan_interval,
            scan_window=scan_window,
            own_addr_type=own_addr_type,
            scanning_filter_policy=scanning_filter_policy
        )

class LeSetScanEnable(HciCmdBasePacket):
    """LE Set Scan Enable Command"""
    
    OPCODE = HciOpcode.LE_SET_SCAN_ENABLE
    NAME = "LE_Set_Scan_Enable"
    
    def __init__(self, scan_enable: bool = False, filter_duplicates: bool = False):
        """
        Initialize LE Set Scan Enable Command
        
        Args:
            scan_enable: Enable (True) or disable (False) scanning
            filter_duplicates: Filter out duplicate advertisements
        """
        super().__init__(
            scan_enable=1 if scan_enable else 0,
            filter_duplicates=1 if filter_duplicates else 0
        )
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate scan enable
        if self.params['scan_enable'] not in (0, 1):
            raise ValueError(f"Invalid scan_enable: {self.params['scan_enable']}, must be 0 or 1")
        
        # Validate filter duplicates
        if self.params['filter_duplicates'] not in (0, 1):
            raise ValueError(f"Invalid filter_duplicates: {self.params['filter_duplicates']}, must be 0 or 1")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<BB",
                          self.params['scan_enable'],
                          self.params['filter_duplicates'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LeSetScanEnable':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        
        scan_enable, filter_duplicates = struct.unpack("<BB", data[:2])
        
        return cls(
            scan_enable=(scan_enable == 1),
            filter_duplicates=(filter_duplicates == 1)
        )

# Function wrappers for easier access
def le_set_adv_params(**kwargs) -> LeSetAdvParams:
    """Create LE Set Advertising Parameters Command"""
    return LeSetAdvParams(**kwargs)

def le_set_adv_data(**kwargs) -> LeSetAdvData:
    """Create LE Set Advertising Data Command"""
    return LeSetAdvData(**kwargs)

def le_set_scan_parameters(**kwargs) -> LeSetScanParameters:
    """Create LE Set Scan Parameters Command"""
    return LeSetScanParameters(**kwargs)

def le_set_scan_enable(**kwargs) -> LeSetScanEnable:
    """Create LE Set Scan Enable Command"""
    return LeSetScanEnable(**kwargs)

# Register all command classes
register_command(LeSetAdvParams)
register_command(LeSetAdvData)
register_command(LeSetScanParameters)
register_command(LeSetScanEnable)

# Export public functions and classes
__all__ = [
    'le_set_adv_params',
    'le_set_adv_data',
    'le_set_scan_parameters',
    'le_set_scan_enable',
    'LeSetAdvParams',
    'LeSetAdvData',
    'LeSetScanParameters',
    'LeSetScanEnable',
    'AdvertisingType',
    'AddressType',
]