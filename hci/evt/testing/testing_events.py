"""
Testing events module

This module provides implementations for Testing HCI events.
"""

import struct
from typing import List, Dict, Any, ClassVar, Optional, Tuple, Union
from enum import IntEnum

from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode
from ..event_types import TestingEventType
from ..error_codes import StatusCode
from .. import register_event

class LoopbackCommandEvent(HciEvtBasePacket):
    """Loopback Command Event"""
    
    EVENT_CODE = HciEventCode.LOOPBACK_COMMAND
    NAME = "Loopback_Command"
    
    def __init__(self, hci_command_packet: bytes):
        """
        Initialize Loopback Command Event
        
        Args:
            hci_command_packet: HCI command packet to be looped back
        """
        super().__init__(hci_command_packet=hci_command_packet)
    
    def _validate_params(self) -> None:
        """Validate event parameters"""
        # Validate HCI command packet
        if len(self.params['hci_command_packet']) < 3:  # Need at least opcode (2 bytes) and length (1 byte)
            raise ValueError(f"Invalid hci_command_packet length: {len(self.params['hci_command_packet'])}, must be at least 3 bytes")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return self.params['hci_command_packet']
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LoopbackCommandEvent':
        """Create event from parameter bytes (excluding header)"""
        if len(data) < 3:  # Need at least opcode (2 bytes) and length (1 byte)
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 3 bytes")
        
        return cls(hci_command_packet=data)

# Register all event classes
register_event(LoopbackCommandEvent)

# Function wrappers for easier access
def loopback_command(hci_command_packet: bytes) -> LoopbackCommandEvent:
    """Create Loopback Command Event"""
    return LoopbackCommandEvent(hci_command_packet=hci_command_packet)

# Export public functions and classes
__all__ = [
    'loopback_command',
    'LoopbackCommandEvent',
]