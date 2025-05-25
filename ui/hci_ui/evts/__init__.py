""" 
    HCI Events UI Module
This module provides generic UI components for HCI events that don't have
specific UI implementations. It allows for easy creation of event UIs by
defining the event code and name, and automatically generates the UI layout
for displaying event parameters.    

"""


from typing import Optional , Dict, Type, Union, List
from .evt_baseui import HCIEvtUI


# Event registry - maps event codes to event classes
_evt_ui_registry: Dict[int, HCIEvtUI] = {}
_sub_evt_ui_registry: Dict[int, HCIEvtUI] = {}

def register_event_ui(evt_class: HCIEvtUI) -> None:
    """
    Register an event class with its event code.
    
    Args:
        evt_class: Event class to register
    """
    print(f"Registering event {evt_class.__name__} with event code 0x{evt_class.EVENT_CODE:02X} in file {evt_class.__module__}")
    
    if not hasattr(evt_class, 'EVENT_CODE'):
        raise ValueError(f"Event class {evt_class.__name__} has no EVENT_CODE defined")
    
    event_code = evt_class.EVENT_CODE
    sub_event_code = evt_class.SUB_EVENT_CODE
    if sub_event_code is not None:
        # Register sub-event
        if sub_event_code in _sub_evt_ui_registry:
            raise ValueError(f"Sub-event with code 0x{sub_event_code:02X} already registered as {_sub_evt_ui_registry[sub_event_code].__name__}")
        _sub_evt_ui_registry[sub_event_code] = evt_class
        return
    
    # Register main event
    if event_code in _evt_ui_registry:
        raise ValueError(f"Event with code 0x{event_code:02X} already registered as {_evt_ui_registry[event_code].__name__}")
    
    _evt_ui_registry[event_code] = evt_class
    
    
def get_event_ui_class(event_code: int, sub_evt_code : Optional[int] = None) -> Optional[Type[HCIEvtUI]]:
    """Get event class from event code."""
    if sub_evt_code is not None:
        return _sub_evt_ui_registry.get(sub_evt_code)
    
    return _evt_ui_registry.get(event_code)


def get_all_event_ui_classes() -> List[Type[HCIEvtUI]]:
    """Get all registered event UI classes."""
    return list(_evt_ui_registry.values()) + list(_sub_evt_ui_registry.values())

def get_event_ui_class_by_name(name: str) -> Optional[Type[HCIEvtUI]]:
    """Get event class by human-readable name."""
    for evt_class in _evt_ui_registry.values():
        if evt_class.NAME == name:
            return evt_class
    for evt_class in _sub_evt_ui_registry.values():
        if evt_class.NAME == name:
            return evt_class
    return None

def evt_from_bytes(data: bytes, sub_event_code: Optional[int] = None) -> Optional[HCIEvtUI]:
    """
    Parse HCI event from complete event bytes.
    
    Args:
        data: Complete event bytes including header
        sub_event_code: Optional sub-event code if applicable
    
    Returns:
        Parsed event object or None if parsing failed
    """
    if len(data) < 2:  # Need at least event code (1 byte) and length (1 byte)
        return None
    
    event_code = data[0]
    
    if sub_event_code is not None:
        evt_class = get_event_ui_class(event_code, sub_event_code)
    else:
        evt_class = get_event_ui_class(event_code)
    if evt_class is None:
        print(f"Unknown event with code 0x{event_code:02X}")
        return None
    try:
        return evt_class.from_bytes(data[1:], sub_event_code)
    except Exception as e:
        print(f"Failed to parse event: {e}")
        return None


from . import link_control


__all__ = [
    'register_event_ui',
    'get_event_ui_class',
    'get_all_event_ui_classes',
    'get_event_ui_class_by_name',
    'evt_from_bytes',
    'link_control',
    'HCIEvtUI',
]