"""
Base packet structure for HCI commands
"""
from abc import abstractmethod
from typing import Type, Dict, Any, ClassVar, Optional, Tuple
import struct
import weakref
from .cmd_opcodes import OPCODE_TO_NAME
from ..hci_packet import HciCommandPacket

class HciCmdBasePacket(HciCommandPacket):
    """Base class for all HCI command packets"""
    
    # # Class variables to be defined by subclasses
    OPCODE: ClassVar[int]  # The command opcode (2 bytes)
    NAME: ClassVar[str]    # Human-readable name of the command
    PARAMS : Optional[bytes]  # Default parameters (empty for no parameters)
    
    def __init__(self, **kwargs):
        """Initialize command with parameters"""
        super().__init__(**kwargs)
        if self.params.get('opcode'):
            self.OPCODE =  self.params['opcode']
        if self.params.get('name'):
            self.NAME =  self.params['name']
        if self.params.get('params'):
            self.PARAMS =  self.params['params']
            
        # can call validate params here 
        self._validate_params()
    
    def to_bytes(self) -> bytes:
        """Convert command to bytes, including header"""
        param_bytes = self._serialize_params() or b''

        # Raw parameter blocks handed to `create_cmd_packet` live on the
        # *instance*, so read them from there. Reading the class attribute
        # instead silently dropped them, producing a valid-looking but
        # parameterless packet.
        raw = getattr(self, 'PARAMS', None)
        if raw and not param_bytes:
            param_bytes = bytes(raw)

        opcode = getattr(self, 'OPCODE', None)
        if opcode is None:
            opcode = self.params.get('opcode', 0)
        packet_type = getattr(self.__class__, 'PACKET_TYPE')

        # HCI Command packet format:
        # - 1 byte: HCI Packet Type
        # - 2 bytes: Opcode (OGF:6 bits, OCF:10 bits)
        # - 1 byte: Parameter Total Length
        # - N bytes: Parameters
        if len(param_bytes) > 0xFF:
            raise ValueError(
                f"command parameters are {len(param_bytes)} bytes; "
                "the HCI length field is one byte (max 255)"
            )

        header = struct.pack("<BHB", int(packet_type), int(opcode), len(param_bytes))
        return header + param_bytes
    
    def __str__(self) -> str:
        """String representation of the command packet"""
        # Get name with clear fallback
        name = getattr(self.__class__, 'NAME', None)
        if not name and hasattr(self, 'params') and self.params:
            name = self.params.get('name')
            if not name:
                name = OPCODE_TO_NAME.get(self.params.get('opcode', 0), 'UNKNOWN')
        
        # Get opcode  
        opcode = getattr(self.__class__, 'OPCODE', None)
        if not opcode and hasattr(self, 'params') and self.params:
            opcode = self.params.get('opcode', 0)
        
        # Use opcode lookup as final fallback for name
        if not name and opcode:
            name = OPCODE_TO_NAME.get(opcode, 'UNKNOWN')
        
        # Defaults
        name = name or 'UNKNOWN'
        opcode = opcode or 0
        
        return f"{name} : 0x{opcode:04X}"
        
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes. Default: no parameters."""
        return b''


    def _validate_params(self) -> None:
        """Validate command parameters"""
        # Call the derived class to validate the parameters
        pass
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'HciCmdBasePacket':
        """Create command from parameter bytes (excluding header) only use opcode and params"""
        pass
        
    @staticmethod
    def get_opcode_bytes(opcode: int) -> Tuple[int, int]:
        """Split opcode into OGF and OCF values"""
        ogf = (opcode >> 10) & 0x3F  # 6 bits for OGF
        ocf = opcode & 0x03FF        # 10 bits for OCF
        return ogf, ocf
    
    @staticmethod
    def create_cmd_packet(opcode: int, params: Optional[bytes] = None, name : Optional[str] = None) -> 'HciCmdBasePacket':
        """Create command packet from opcode and parameters"""
        return HciCmdBasePacket(opcode=opcode, params=params, name=name)
    
    @staticmethod
    def create_opcode(ogf: int, ocf: int) -> int:
        """Create opcode from OGF and OCF values"""
        return ((ogf & 0x3F) << 10) | (ocf & 0x03FF)