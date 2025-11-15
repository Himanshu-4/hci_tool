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
    OPCODE: ClassVar[int]  # The command opcode for the successful event or completion (2 bytes)
    EVENT_CODE: ClassVar[int]  # The event code (1 byte)
    SUB_EVENT_CODE: Optional[int] = None  # Sub-event code (if applicable, 1 byte)
    NAME: ClassVar[str]        # Human-readable name of the event
    
    def __init__(self, **kwargs):
        """Initialize event with parameters"""
        super().__init__(**kwargs)
        if self.params.get('opcode'):
            self.OPCODE =  self.params.get('opcode')
        if self.params.get('event_code'):
            self.EVENT_CODE =  self.params.get('event_code')
        if self.params.get('sub_event_code'):
            self.SUB_EVENT_CODE =  self.params.get('sub_event_code')
        if self.params.get('name'):
            self.NAME =  self.params.get('name')
        # validate the parameters
        self._validate_params()
        
    @abstractmethod
    def _validate_params(self) -> None:
        # call the derived class to validate the parameters
        """Validate event packet parameters"""
        pass # This can be overridden by subclasses to validate specific parameters
    
    def to_bytes(self) -> bytes:
        """Convert event to bytes, including header"""
        param_bytes = self._serialize_params()
        length = len(param_bytes)
        
        # HCI Event packet format:
        # - 1 byte: HCI Packet Type (not included here, added by layer)
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
    def from_bytes(cls, data: bytes) -> 'HciEvtBasePacket':
        """Create event from parameter bytes (excluding header)"""
        pass