"""
Base packet structure for HCI events
"""
from abc import abstractmethod
from typing import Type, Dict, Any, ClassVar, Optional, Tuple
import struct

from ..hci_packet import HciEventPacket

class HciEvtBasePacket(HciEventPacket):
    """Base class for all HCI event packets"""
    
    # Class variables to be defined by subclasses
    EVENT_CODE: ClassVar[int]  # The event code (1 byte)
    SUB_EVENT_CODE: Optional[int] = None  # Sub-event code (if applicable, 1 byte)
    NAME: ClassVar[str]        # Human-readable name of the event
    
    def __init__(self, **kwargs):
        """Initialize event with parameters"""
        super().__init__(**kwargs)
    
    def to_bytes(self) -> bytes:
        """Convert event to bytes, including header"""
        param_bytes = self._serialize_params()
        length = len(param_bytes)
        
        # HCI Event packet format:
        # - 1 byte: HCI Packet Type (not included here, added by transport layer)
        # - 1 byte: Event Code
        # - 1 byte: Parameter Total Length
        # - N bytes: Parameters
        header = struct.pack("<BB", self.EVENT_CODE, length)
        return header + param_bytes
    
    @abstractmethod
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        pass
    
    @classmethod
    @abstractmethod
    def from_bytes(cls, data: bytes, sub_event_code : Optional[int] = None) -> 'HciEvtBasePacket':
        """Create event from parameter bytes (excluding header)"""
        pass
    
    @classmethod
    @abstractmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int) -> 'HciEvtBasePacket':
        """Create event from parameter bytes for sub-event"""
        """
        This method is used for events that have a sub-event code.
        It allows the creation of an event instance from raw bytes,
        including the sub-event code.
        """
        pass