"""
HCI Event Module initialization

This module provides functionality for creating and parsing HCI events.
"""

from typing import Dict, Type, Optional, Any, Union
import struct


# Import event base packet and codes
from .evt_base_packet import HciEvtBasePacket
from .generic import GenericEventPacket, MalformedEventPacket
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
   

def get_cmd_complete_event_class(opcode: int) -> Optional[Type[HciEvtBasePacket]]:
    """Get the Command Complete flavour registered for an opcode, if any."""
    return _cmd_complete_evt_registery.get(opcode)

def get_event_class(event_code: int, sub_evnt_code : Optional[int] = None, opcode : Optional[int] = None) -> Optional[Type[HciEvtBasePacket]]:
    """
    Resolve an event class.

    Command Complete falls back to the generic `CommandCompleteEvent` when no
    per-opcode class is registered -- there are hundreds of opcodes and only a
    handful will ever get bespoke decoders, so the common case must still parse.
    """
    if sub_evnt_code is not None:
        return _sub_evt_registry.get(sub_evnt_code)

    if event_code == HciEventCode.COMMAND_COMPLETE:
        if opcode is not None:
            specific = get_cmd_complete_event_class(opcode)
            if specific is not None:
                return specific
        return _evt_registry.get(HciEventCode.COMMAND_COMPLETE)

    return _evt_registry.get(event_code)


def evt_from_bytes(data: bytes) -> Optional[HciEvtBasePacket]:
    """
    Parse a complete HCI event packet (H4 type byte included).

    **This function never raises.** It runs on the receive path, where an
    exception would kill the link for the rest of the session. Anything it cannot
    decode comes back as a `GenericEventPacket` or `MalformedEventPacket` so the
    caller can log it and move on.

    Args:
        data: complete event bytes, starting with the 0x04 packet indicator

    Returns:
        A parsed event, or None if `data` is too short to be an event at all.
    """
    if data is None or len(data) < 3:
        return None

    packet_id, event_code, param_len = data[0], data[1], data[2]

    if packet_id != HciEvtBasePacket.PACKET_TYPE:
        return MalformedEventPacket(data, f"bad packet indicator 0x{packet_id:02X}")

    params = data[3:]
    if len(params) != param_len:
        return MalformedEventPacket(
            data, f"length mismatch: header says {param_len}, got {len(params)}"
        )

    sub_event_code: Optional[int] = None
    opcode: Optional[int] = None

    if event_code == HciEventCode.LE_META_EVENT and params:
        sub_event_code = params[0]
    elif event_code == HciEventCode.COMMAND_COMPLETE and len(params) >= 3:
        opcode = struct.unpack_from("<H", params, 1)[0]

    evt_class = get_event_class(event_code, sub_evnt_code=sub_event_code, opcode=opcode)

    if evt_class is None:
        return GenericEventPacket(event_code, params, sub_event_code)

    try:
        return evt_class.from_bytes(params)
    except Exception as exc:
        # A decoder bug or an unexpected vendor layout: degrade to a hex dump
        # rather than taking down the receive path.
        print(f"[hci.evt] {evt_class.__name__} failed to parse "
              f"0x{event_code:02X}: {exc!r}")
        return GenericEventPacket(event_code, params, sub_event_code)


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
    print(f"[HCI event] Initing module")
   
# Initialize modules
_initialize_modules()

from . import link_control
from . import link_policy
from . import controller_baseband
from . import testing
from . import status
from . import le
from . import vs_specific
from . import base_events

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
    'base_events',
]
