from struct import pack, unpack
from enum import IntEnum

from ..hci_packet import HciPacket
from .opcode import OpCode


class CommandPacket(HciPacket):
    OFFSET_DATA_LENGTH = 0x03
    OpCode = OpCode

    class Ogf(IntEnum):
        LINK_CONTROL = 1
        LINK_POLICY = 2
        CONTROLLER_AND_BASEBAND = 3
        INFORMATIONAL_PARAMETERS = 4
        STATUS_PARAMETERS = 5
        TESTING = 6
        LE_CONTROLLER = 8
        VENDOR_SPECIFIC = 63

    def __init__(self, opcode, parameters=b''):
        super().__init__(
            HciPacket.PacketType.COMMAND,
            CommandPacket._params_to_binary(opcode, parameters)
        )

    @staticmethod
    def _params_to_binary(opcode, parameters):
        fmt = '<HB%ds' % len(parameters)
        return pack(fmt, opcode, len(parameters), parameters)

    @property
    def opcode(self):
        OFFSET, SIZE_OCTETS = 1, 2
        data = self._get_data(OFFSET, SIZE_OCTETS)
        return unpack('<H', data)[0]

    @property
    def ogf(self):
        return (self.opcode >> 10)

    @property
    def ocf(self):
        return self.opcode & 0x3FF

    @property
    def parameter_total_length(self):
        OFFSET, SIZE_OCTETS = 3, 1
        data = self._get_data(OFFSET, SIZE_OCTETS)
        return unpack('<B', data)[0]

    def __str__(self):
        return super().__str__() + '\n' + '\n'.join([
            'OpCode: {} ({})',
            '  OGF: {} ({})',
            '  OCF: {} ({})',
            'Data Length: {} ({})',
        ]).format(
            hex(self.opcode),
            OpCode(self.opcode).name,
            hex(self.ogf),
            CommandPacket.Ogf(self.ogf).name,
            hex(self.ocf),
            int(self.ocf),
            hex(self.parameter_total_length),
            int(self.parameter_total_length),
        )
        
        
"""
Base packet structure for HCI commands
"""
from abc import ABC, abstractmethod
from typing import Type, Dict, Any, ClassVar, Optional, Tuple
import struct

class HciCmdBasePacket(ABC):
    """Base class for all HCI command packets"""
    
    # Class variables to be defined by subclasses
    OPCODE: ClassVar[int]  # The command opcode (2 bytes)
    NAME: ClassVar[str]    # Human-readable name of the command
    
    def __init__(self, **kwargs):
        """Initialize command with parameters"""
        self.params = kwargs
        self._validate_params()
    
    @abstractmethod
    def _validate_params(self) -> None:
        """Validate command parameters, raise ValueError if invalid"""
        pass
    
    @abstractmethod
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        pass
    
    @classmethod
    @abstractmethod
    def from_bytes(cls, data: bytes) -> 'HciCmdBasePacket':
        """Create a command object from bytes"""
        pass
    
    def to_bytes(self) -> bytes:
        """Convert command to bytes, including header"""
        param_bytes = self._serialize_params()
        length = len(param_bytes)
        
        # HCI Command packet format:
        # - 2 bytes: Opcode (OGF:6 bits, OCF:10 bits)
        # - 1 byte: Parameter Total Length
        # - N bytes: Parameters
        header = struct.pack("<HB", self.OPCODE, length)
        return header + param_bytes
    
    def __str__(self) -> str:
        """String representation of the command"""
        return f"{self.NAME} (0x{self.OPCODE:04X}): {self.params}"
    
    @staticmethod
    def get_opcode_bytes(opcode: int) -> Tuple[int, int]:
        """Split opcode into OGF and OCF values"""
        ogf = (opcode >> 10) & 0x3F  # 6 bits for OGF
        ocf = opcode & 0x03FF        # 10 bits for OCF
        return ogf, ocf
    
    @staticmethod
    def create_opcode(ogf: int, ocf: int) -> int:
        """Create opcode from OGF and OCF values"""
        return ((ogf & 0x3F) << 10) | (ocf & 0x03FF)