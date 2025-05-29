"""
HCI Event Module initialization

This module provides functionality for creating and parsing HCI events.
"""

from typing import Dict, Type, Optional, Any, Union
import struct


# Import event base packet and codes
from .evt_base_packet import HciEvtBasePacket
from .evt_codes import HciEventCode, LeMetaEventSubCode
from .error_codes import StatusCode, get_status_description
from .event_types import (
    EventCategory, 
    LinkControlEventType, 
    LinkPolicyEventType, 
    ControllerBasebandEventType,
    InformationEventType,
    TestingEventType,
    LEEventType
)


# define the list of event codes that also have sub-events
# This is used to filter out events that are not LE Meta Events
_sub_evt_codes = [HciEventCode.LE_META_EVENT]

_cmd_complete_evt_registery: Dict[int, Type[HciEvtBasePacket]] = {}
# Event registry - maps event codes to event classes
_evt_registry: Dict[int, Type[HciEvtBasePacket]] = {}
_sub_evt_registry: Dict[int, Type[HciEvtBasePacket]] = {}

def register_event(evt_class: Type[HciEvtBasePacket]) -> None:
    """Register an event class with its event code"""
    if not hasattr(evt_class, 'EVENT_CODE'):
        raise ValueError(f"Event class {evt_class.__class__.__name__} has no EVENT_CODE defined")
    
    event_code = evt_class.EVENT_CODE
    sub_event_code = evt_class.SUB_EVENT_CODE
    
    # Check if the event code is a main event or a sub-event
    if not isinstance(event_code, int) or event_code < 0 or event_code > 0xFF:
        raise ValueError(f"Invalid event code: {event_code}, must be an integer between 0 and 255 (0x00 to 0xFF)")
    
    # register the command complete event if it has an opcode
    if hasattr(evt_class, 'OPCODE') and event_code == HciEventCode.COMMAND_COMPLETE:
        opcode = evt_class.OPCODE
        if opcode in _cmd_complete_evt_registery:
            raise ValueError(f"Command complete event with opcode 0x{opcode:04X} already registered as {_cmd_complete_evt_registery[opcode].__class__.__name__} with name {__file__}")
        _cmd_complete_evt_registery[opcode] = evt_class
        return
        
    if event_code not in  _sub_evt_codes and sub_event_code is None:
        if event_code in _evt_registry:
            raise ValueError(f"Event with code 0x{event_code:02X} already registered as {_evt_registry[event_code].__class__.__name__} with name {__file__}")
        # Register as main event
        _evt_registry[event_code] = evt_class
    else :
        if sub_event_code is None:
            raise ValueError(f"Event class {evt_class.__name__} has no SUB_EVENT_CODE defined")
        if sub_event_code in _sub_evt_registry:
            raise ValueError(f"Sub-event with code 0x{sub_event_code:02X} already registered as {_sub_evt_registry[sub_event_code].__class__.__name__} with name {__file__}")
        # Register as sub-event
        _sub_evt_registry[sub_event_code] = evt_class
   

def get_cmd_complete_event_class(opcode: int) -> Optional[HciEvtBasePacket]:
    """Get command complete event class from opcode"""
    return _cmd_complete_evt_registery.get(opcode)

def get_event_class(event_code: int, sub_evnt_code : Optional[int] = None, opcode : Optional[int] = None) -> Optional[HciEvtBasePacket]:
    """Get event class from event code"""
    if sub_evnt_code is not None:
        return _sub_evt_registry.get(sub_evnt_code)
    
    if opcode is not None and event_code == HciEventCode.COMMAND_COMPLETE:
        # If an opcode is provided, check the command complete event registry
        return get_cmd_complete_event_class(opcode)
    # If no sub-event code or opcode, check the main event registry
    return _evt_registry.get(event_code)


def evt_from_bytes(data: bytes) -> Optional[HciEvtBasePacket]:
    """
    Parse HCI event from complete event bytes
    
    Args:
        data: Complete event bytes including header
        
    Returns:
        Parsed event object or None if parsing failed
    """
    if len(data) < 4:  # Need at least packet ID, event code (1 byte) and length (1 byte)
        return None
    
    # extract the event code and subevent code if present and then get the event class
    evt_class = None
    sub_event_code = None
    # First byte is event code, second byte is length
    # If the event code is LE_META_EVENT, we need to check the sub_event_code
    packetid, event_code, param_len, sub_event_code = struct.unpack("<BBBB", data[:4])
    opcode = None
    #check if the packet ID is valid
    if packetid != HciEvtBasePacket.PACKET_TYPE:
        raise ValueError(f"Invalid packet ID: {packetid}, expected {HciEvtBasePacket.PACKET_TYPE}")
    if param_len != len(data) - 3:  # Length should match the remaining bytes after header
        raise ValueError(f"Invalid parameter length: {param_len}, expected {len(data) - 4}")
    if event_code not in HciEventCode:
        raise ValueError(f"Invalid event code: {event_code}, must be between 0x00 and 0xFF")
    
    sub_event_code = opcode = None
    # Check if the event code is LE_META_EVENT
    if event_code == HciEventCode.LE_META_EVENT:
        # For LE Meta Event, use sub_event_code to determine the specific event class
        if len(data) < 4:
            raise ValueError("LE Meta Event data too short")
        sub_event_code = data[3]  # Sub-event code is the 4th byte
    
    elif event_code == HciEventCode.COMMAND_COMPLETE:
        # For Command Complete Event, we need to extract the opcode
        if len(data) < 7:
            raise ValueError("Command Complete Event data too short")
        # Opcode is the next 2 bytes after the event code and length
        opcode = struct.unpack("<H", data[4:6])[0]

    else:
        sub_event_code = None
    
    # Get the event class based on the event code and sub-event code
    # If the event code is LE_META_EVENT, we need to check the sub_event_code
    evt_class = get_event_class(event_code, sub_evnt_code=sub_event_code, opcode=opcode)
    
    if evt_class is None:
        raise ValueError(f"Unknown event with code 0x{event_code:02X} and sub-event code 0x{sub_event_code:02X} (if applicable)")
    
    try:
        # For regular events, just pass the data excluding the header [packet ID + Evt code + length]
        return evt_class.from_bytes(data[3:])
    except Exception as e:
        print(f"Failed to parse event: {e}")
        return None

def hci_evt_parse_from_bytes(data: bytes) -> Optional[HciEvtBasePacket]:
    """
    Parse HCI event from complete event bytes
    
    Args:
        data: Complete event bytes including header
        
    Returns:
        Parsed event object or None if parsing failed
    """
    return evt_from_bytes(data)


# Initialize event modules when this package is imported
def _initialize_modules():
    """Import all event submodules to register events"""
    print(f"Initializing event modules...")
   
# Initialize modules
_initialize_modules()

from . import link_control
from . import link_policy
from . import controller_baseband
from . import testing
from . import status
from . import le
from . import vs_specific

# Make submodule event functions available at the top level
# This enables usage like: import hci.evt as hci_evt; hci_evt.le.le_set_adv_params(...)
# instead of: from hci.evt.le import le_set_adv_params; le_set_adv_params(...)


# Export public functions and classes
__all__ = [
    'register_event',
    'get_event_class',
    'evt_from_bytes',
    'hci_evt_parse_from_bytes',
    'HciEvtBasePacket',
    'HciEventCode',
    'LeMetaEventSubCode',
    'StatusCode',
    'get_status_description',
    'EventCategory',
    'LinkControlEventType',
    'LinkPolicyEventType',
    'ControllerBasebandEventType',
    'InformationEventType',
    'TestingEventType',
    'LEEventType',
    'link_control',
    'link_policy',
    'controller_baseband',
    'testing',
    'status',
    'le',
    'vs_specific',
]
