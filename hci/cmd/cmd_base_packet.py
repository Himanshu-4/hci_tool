"""
Base packet structure for HCI commands
"""
from abc import abstractmethod
from typing import Type, Dict, Any, ClassVar, Optional, Tuple
import struct

from ..hci_packet import HciCommandPacket

class HciCmdBasePacket(HciCommandPacket):
    """Base class for all HCI command packets"""
    
    # Class variables to be defined by subclasses
    OPCODE: ClassVar[int]  # The command opcode (2 bytes)
    NAME: ClassVar[str]    # Human-readable name of the command
    
    def __init__(self, **kwargs):
        """Initialize command with parameters"""
        super().__init__(**kwargs)
    
    def to_bytes(self) -> bytes:
        """Convert command to bytes, including header"""
        param_bytes = self.PARAMS +  self._serialize_params()
        length = len(param_bytes)
        
        # HCI Command packet format:
        # - 1 byte: HCI Packet Type
        # - 2 bytes: Opcode (OGF:6 bits, OCF:10 bits)
        # - 1 byte: Parameter Total Length
        # - N bytes: Parameters
        header = struct.pack("<BHB",self.PACKET_TYPE, self.OPCODE, length)
        return header + param_bytes
    
    @abstractmethod
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        pass
    
    @staticmethod
    def get_opcode_bytes(opcode: int) -> Tuple[int, int]:
        """Split opcode into OGF and OCF values"""
        ogf = (opcode >> 10) & 0x3F  # 6 bits for OGF
        ocf = opcode & 0x03FF        # 10 bits for OCF
        return ogf, ocf
    
    @staticmethod
    def create_cmd_packet(ogf: int, ocf: int, params: bytes, name : Optional[str]) -> 'HciCmdBasePacket':
        """Create command packet from OGF, OCF, and parameters"""
        opcode = HciCmdBasePacket.create_opcode(ogf, ocf)
        return HciCmdBasePacket(opcode=opcode, params=params, name=name)
    
    @staticmethod
    def create_opcode(ogf: int, ocf: int) -> int:
        """Create opcode from OGF and OCF values"""
        return ((ogf & 0x3F) << 10) | (ocf & 0x03FF)