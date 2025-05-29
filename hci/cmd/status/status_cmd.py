"""
status commands for HCI (Host Controller Interface) in Python
This module provides classes for status-related HCI commands.
"""

import struct
from typing import Optional, Dict, Any, ClassVar

from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import HciOpcode, create_opcode, OGF, StatusOCF
from .. import register_command


class ReadRssi(HciCmdBasePacket):
    """Read RSSI Command"""
    
    OPCODE: ClassVar[int] = create_opcode(OGF.STATUS_PARAMS, StatusOCF.READ_RSSI)
    NAME: ClassVar[str] = "Read_RSSI"
    
    def __init__(self, conn_handle: int):
        """
        Initialize Read RSSI Command
        
        Args:
            conn_handle: Connection handle to read RSSI for
        """
        super().__init__(conn_handle=conn_handle)
    
    def _validate_params(self) -> None:
        """Validate command parameters"""
        if not (0 <= self.params['conn_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid connection handle: {self.params['conn_handle']}, must be between 0 and 0x0EFF")
    
    def _serialize_params(self) -> bytes:
        """Serialize parameters to bytes"""
        return struct.pack("<H", self.params['conn_handle'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ReadRssi':
        """Create command from parameter bytes (excluding header)"""
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 2 bytes")
        
        conn_handle = struct.unpack("<H", data[:2])[0]
        
        return cls(conn_handle=conn_handle)
    
    def __str__(self) -> str:
        """String representation of the command packet"""
        return super().__str__() + f"\r\nConnection Handle: {self.params['conn_handle']:04X}"
    
    
    
    
# Register the commands class
register_command(ReadRssi)