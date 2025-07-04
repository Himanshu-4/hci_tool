"""
HCI Command Parser module

This module provides the main functions for parsing HCI commands from bytes.
"""

import struct
from typing import Dict, Type, Optional, Any, Union, Tuple, List

from .cmd_base_packet import HciCmdBasePacket

# Importing the registry from __init__
from . import get_command_class

def parse_command_header(data: bytes) -> Tuple[int, int, bytes]:
    """
    Parse HCI command header (opcode and parameter length)

    Args:
        data: Complete command bytes
        
    Returns:
        Tuple of (opcode, parameter length, parameter bytes)
    """
    if len(data) < 4:  # Need at least opcode (2 bytes) and length (1 byte)
        raise ValueError(f"Invalid data length: {len(data)}, expected at least 4 bytes")
    
    packet_id, opcode, length = struct.unpack("<BHB", data[:4])
    
    if packet_id != HciCmdBasePacket.PACKET_TYPE:
        raise ValueError(f"Invalid packet ID: {packet_id}, expected {HciCmdBasePacket.PACKET_TYPE}")
    
    return opcode, length, data[4:4+length]

def hci_cmd_parse_from_bytes(data: bytes) -> Optional[HciCmdBasePacket]:
    """
    Parse HCI command from complete command bytes
    
    Args:
        data: Complete command bytes including header
        
    Returns:
        Parsed command object or None if parsing failed
    """
    if len(data) < 3:  # Need at least opcode (2 bytes) and length (1 byte)
        raise ValueError(f"Invalid data length: {len(data or b'')}, expected at least 3 bytes")
    
    opcode, length, param_bytes = parse_command_header(data)
    cmd_class =  get_command_class(opcode)
    if cmd_class is None:
        return HciCmdBasePacket(opcode=opcode, params={})
    
    if cmd_class is None:
        ogf = (opcode >> 10) & 0x3F
        ocf = opcode & 0x03FF
        print(f"Unknown command with opcode 0x{opcode:04X} (OGF=0x{ogf:02X}, OCF=0x{ocf:04X})")
        return None
    return cmd_class.from_bytes(param_bytes)

def hci_cmd_serialize(cmd: HciCmdBasePacket) -> bytes:
    """
    Serialize HCI command to bytes
    
    Args:
        cmd: HCI command object
        
    Returns:
        Serialized command bytes
    """
    return cmd.to_bytes()

# Export public functions
__all__ = [
    'parse_command_header',
    'hci_cmd_parse_from_bytes',
    'hci_cmd_serialize',
]