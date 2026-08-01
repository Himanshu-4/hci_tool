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
from ...hci_util import bd_addr_str_to_bytes

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

class HoldMode(HciCmdBasePacket):
    """Hold Mode Command"""
    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.HOLD_MODE)
    NAME = "Hold_Mode"

    def __init__(self,
                 connection_handle: int,
                 hold_mode_max_interval: int = 0x0080,
                 hold_mode_min_interval: int = 0x0040):
        """
        Initialize Hold Mode Command

        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            hold_mode_max_interval: Maximum hold interval (N * 0.625 ms)
            hold_mode_min_interval: Minimum hold interval (N * 0.625 ms)
        """
        super().__init__(
            connection_handle=connection_handle,
            hold_mode_max_interval=hold_mode_max_interval,
            hold_mode_min_interval=hold_mode_min_interval
        )

    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Validate connection handle
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")

        for key in ('hold_mode_max_interval', 'hold_mode_min_interval'):
            if not (0x0002 <= self.params[key] <= 0xFFFE):
                raise ValueError(f"Invalid {key}: {self.params[key]}, must be between 0x0002 and 0xFFFE")

        if self.params['hold_mode_min_interval'] > self.params['hold_mode_max_interval']:
            raise ValueError("hold_mode_min_interval must not exceed hold_mode_max_interval")

    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Connection_Handle(2) Hold_Mode_Max_Interval(2) Hold_Mode_Min_Interval(2)
        return struct.pack("<HHH",
                           self.params['connection_handle'],
                           self.params['hold_mode_max_interval'],
                           self.params['hold_mode_min_interval'])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'HoldMode':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 6:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 6 bytes")
        handle, max_interval, min_interval = struct.unpack("<HHH", data[:6])
        return cls(connection_handle=handle,
                   hold_mode_max_interval=max_interval,
                   hold_mode_min_interval=min_interval)

class QosSetup(HciCmdBasePacket):
    """QoS Setup Command"""

    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.QOS_SETUP)
    NAME = "QoS_Setup"

    class ServiceType(IntEnum):
        NO_TRAFFIC = 0x00
        BEST_EFFORT = 0x01
        GUARANTEED = 0x02

    # "Don't care" for latency and delay variation.
    NO_CONSTRAINT = 0xFFFFFFFF

    def __init__(self,
                 connection_handle: int,
                 flags: int = 0x00,
                 service_type: int = ServiceType.BEST_EFFORT,
                 token_rate: int = 0x00000000,
                 peak_bandwidth: int = 0x00000000,
                 latency: int = NO_CONSTRAINT,
                 delay_variation: int = NO_CONSTRAINT):
        """
        Initialize QoS Setup Command

        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            flags: Reserved, must be 0
            service_type: No traffic / best effort / guaranteed
            token_rate: Token rate in bytes per second
            peak_bandwidth: Peak bandwidth in bytes per second
            latency: Acceptable latency in microseconds
            delay_variation: Acceptable delay variation in microseconds
        """
        super().__init__(
            connection_handle=connection_handle,
            flags=flags,
            service_type=service_type,
            token_rate=token_rate,
            peak_bandwidth=peak_bandwidth,
            latency=latency,
            delay_variation=delay_variation
        )

    def _validate_params(self) -> None:
        """Validate command parameters"""
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")

        if not (0x00 <= self.params['flags'] <= 0xFF):
            raise ValueError(f"Invalid flags: {self.params['flags']}, must be between 0x00 and 0xFF")

        if self.params['service_type'] not in (0x00, 0x01, 0x02):
            raise ValueError(f"Invalid service_type: {self.params['service_type']}, must be 0x00, 0x01 or 0x02")

        for key in ('token_rate', 'peak_bandwidth', 'latency', 'delay_variation'):
            if not (0 <= self.params[key] <= 0xFFFFFFFF):
                raise ValueError(f"Invalid {key}: {self.params[key]}, must fit in 32 bits")

    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        # Handle(2) Flags(1) Service_Type(1) Token_Rate(4) Peak_Bandwidth(4)
        # Latency(4) Delay_Variation(4)
        return struct.pack("<HBBLLLL",
                           self.params['connection_handle'],
                           self.params['flags'],
                           self.params['service_type'],
                           self.params['token_rate'],
                           self.params['peak_bandwidth'],
                           self.params['latency'],
                           self.params['delay_variation'])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'QosSetup':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 20:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 20 bytes")
        (handle, flags, service_type, token_rate,
         peak_bandwidth, latency, delay_variation) = struct.unpack("<HBBLLLL", data[:20])
        return cls(connection_handle=handle, flags=flags, service_type=service_type,
                   token_rate=token_rate, peak_bandwidth=peak_bandwidth,
                   latency=latency, delay_variation=delay_variation)


class RoleDiscovery(HciCmdBasePacket):
    """Role Discovery Command"""

    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.ROLE_DISCOVERY)
    NAME = "Role_Discovery"

    def __init__(self, connection_handle: int):
        """
        Initialize Role Discovery Command

        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
        """
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        """Validate command parameters"""
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")

    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RoleDiscovery':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        return cls(connection_handle=struct.unpack("<H", data[:2])[0])


class SwitchRole(HciCmdBasePacket):
    """Switch Role Command"""

    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.SWITCH_ROLE)
    NAME = "Switch_Role"

    CENTRAL = 0x00
    PERIPHERAL = 0x01

    def __init__(self, bd_addr: Union[str, bytes], role: int = CENTRAL):
        """
        Initialize Switch Role Command

        Args:
            bd_addr: Bluetooth Device Address of the connected peer
            role: Requested local role (0x00 = central, 0x01 = peripheral)
        """
        super().__init__(
            bd_addr=bd_addr_str_to_bytes(bd_addr),
            role=role
        )

    def _validate_params(self) -> None:
        """Validate command parameters"""
        if len(self.params['bd_addr']) != 6:
            raise ValueError(f"Invalid bd_addr length: {len(self.params['bd_addr'])}, must be 6 bytes")

        if self.params['role'] not in (self.CENTRAL, self.PERIPHERAL):
            raise ValueError(f"Invalid role: {self.params['role']}, must be 0x00 (central) or 0x01 (peripheral)")

    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<6sB", bytes(reversed(self.params['bd_addr'])),
                           self.params['role'])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'SwitchRole':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 7 bytes")
        return cls(bd_addr=bytes(reversed(data[:6])), role=data[6])


class ReadLinkPolicySettings(HciCmdBasePacket):
    """Read Link Policy Settings Command"""

    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.READ_LINK_POLICY_SETTINGS)
    NAME = "Read_Link_Policy_Settings"

    def __init__(self, connection_handle: int):
        """
        Initialize Read Link Policy Settings Command

        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
        """
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        """Validate command parameters"""
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")

    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadLinkPolicySettings':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        return cls(connection_handle=struct.unpack("<H", data[:2])[0])


class WriteLinkPolicySettings(HciCmdBasePacket):
    """Write Link Policy Settings Command"""

    OPCODE = create_opcode(OGF.LINK_POLICY, LinkPolicyOCF.WRITE_LINK_POLICY_SETTINGS)
    NAME = "Write_Link_Policy_Settings"

    # Link policy bits
    DISABLE_ALL = 0x0000
    ENABLE_ROLE_SWITCH = 0x0001
    ENABLE_HOLD_MODE = 0x0002
    ENABLE_SNIFF_MODE = 0x0004
    ENABLE_PARK_STATE = 0x0008

    def __init__(self, connection_handle: int, link_policy_settings: int = DISABLE_ALL):
        """
        Initialize Write Link Policy Settings Command

        Args:
            connection_handle: Connection handle (0x0000-0x0EFF)
            link_policy_settings: Bit mask of the permitted policies
        """
        super().__init__(
            connection_handle=connection_handle,
            link_policy_settings=link_policy_settings
        )

    def _validate_params(self) -> None:
        """Validate command parameters"""
        if not (0x0000 <= self.params['connection_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: {self.params['connection_handle']}, must be between 0x0000 and 0x0EFF")

        if not (0x0000 <= self.params['link_policy_settings'] <= 0x000F):
            raise ValueError(f"Invalid link_policy_settings: {self.params['link_policy_settings']}, must be between 0x0000 and 0x000F")

    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<HH", self.params['connection_handle'],
                           self.params['link_policy_settings'])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'WriteLinkPolicySettings':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 4 bytes")
        handle, settings = struct.unpack("<HH", data[:4])
        return cls(connection_handle=handle, link_policy_settings=settings)


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
register_command(HoldMode)
register_command(QosSetup)
register_command(RoleDiscovery)
register_command(SwitchRole)
register_command(ReadLinkPolicySettings)
register_command(WriteLinkPolicySettings)

# Export public functions and classes
__all__ = [
    'sniff_mode',
    'exit_sniff_mode',
    'SniffMode',
    'ExitSniffMode',
    'HoldMode',
    'QosSetup',
    'RoleDiscovery',
    'SwitchRole',
    'ReadLinkPolicySettings',
    'WriteLinkPolicySettings',
]