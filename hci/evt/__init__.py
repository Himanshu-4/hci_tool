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

# Event registry - maps event codes to event classes
_evt_registry: Dict[int, Type[HciEvtBasePacket]] = {}

def register_event(evt_class: Type[HciEvtBasePacket]) -> None:
    """Register an event class with its event code"""
    if not hasattr(evt_class, 'EVENT_CODE'):
        raise ValueError(f"Event class {evt_class.__name__} has no EVENT_CODE defined")
    
    event_code = evt_class.EVENT_CODE
    # print(f"Registering event {evt_class.__name__} with opcode 0x{event_code:04X} in file {evt_class.__module__}\r\n caller {__file__}")
    if event_code in _evt_registry:
        raise ValueError(f"Event with code 0x{event_code:02X} already registered as {_evt_registry[event_code].__name__} with name {__file__}")
    
    _evt_registry[event_code] = evt_class

def get_event_class(event_code: int) -> Optional[Type[HciEvtBasePacket]]:
    """Get event class from event code"""
    return _evt_registry.get(event_code)

def evt_from_bytes(data: bytes) -> Optional[HciEvtBasePacket]:
    """
    Parse HCI event from complete event bytes
    
    Args:
        data: Complete event bytes including header
        
    Returns:
        Parsed event object or None if parsing failed
    """
    if len(data) < 2:  # Need at least event code (1 byte) and length (1 byte)
        return None
    
    event_code, length = struct.unpack("<BB", data[:2])
    evt_class = get_event_class(event_code)
    
    if evt_class is None:
        print(f"Unknown event with code 0x{event_code:02X}")
        return None
    
    try:
        return evt_class.from_bytes(data[2:])
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
# from . import status
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
