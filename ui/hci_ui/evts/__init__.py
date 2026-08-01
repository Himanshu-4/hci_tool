"""
Event UI registry.

Maps `(event_code, sub_event_code)` to the window class that displays it.
`sub_event_code` is None for everything except LE meta events, where the
sub-code is what actually identifies the event.

A class may claim several keys -- `InquiryResultsUI` handles the three inquiry
result event codes -- and several classes may share a `WINDOW_KEY`, in which
case the factory keeps one window for all of them.
"""

from typing import Dict, List, Optional, Tuple, Type

from .evt_baseui import AggregatingEvtUI, GenericEventUI, HCIEvtUI

EvtKey = Tuple[int, Optional[int]]

_evt_ui_registry: Dict[EvtKey, Type[HCIEvtUI]] = {}


def _keys_of(evt_ui_class: Type[HCIEvtUI]) -> List[EvtKey]:
    """The keys a class claims, falling back to its EVENT_CODE/SUB_EVENT_CODE."""
    keys = list(getattr(evt_ui_class, 'EVENT_KEYS', ()) or ())
    if keys:
        return [(int(code), None if sub is None else int(sub)) for code, sub in keys]

    event_code = getattr(evt_ui_class, 'EVENT_CODE', None)
    if event_code is None:
        raise ValueError(
            f"Event UI {evt_ui_class.__name__} declares neither EVENT_KEYS nor EVENT_CODE")
    sub = getattr(evt_ui_class, 'SUB_EVENT_CODE', None)
    return [(int(event_code), None if sub is None else int(sub))]


def register_event_ui(evt_ui_class: Type[HCIEvtUI]) -> Type[HCIEvtUI]:
    """Register an event UI class for every key it claims."""
    for key in _keys_of(evt_ui_class):
        existing = _evt_ui_registry.get(key)
        if existing is not None and existing is not evt_ui_class:
            raise ValueError(
                f"Event key {key} already registered as {existing.__name__}")
        _evt_ui_registry[key] = evt_ui_class
    return evt_ui_class


def get_event_ui_class(event_code: int,
                       sub_evt_code: Optional[int] = None) -> Optional[Type[HCIEvtUI]]:
    """
    Look up the window class for an event.

    An LE meta event falls back to the generic 0x3E entry when its specific
    sub-event has no window of its own.
    """
    if sub_evt_code is not None:
        found = _evt_ui_registry.get((event_code, int(sub_evt_code)))
        if found is not None:
            return found
    return _evt_ui_registry.get((event_code, None))


def get_event_ui_class_for(event) -> Optional[Type[HCIEvtUI]]:
    """Look up the window class for a parsed event object."""
    event_code = getattr(event, 'EVENT_CODE', None)
    if event_code is None:
        return None
    return get_event_ui_class(int(event_code), getattr(event, 'SUB_EVENT_CODE', None))


def get_all_event_ui_classes() -> List[Type[HCIEvtUI]]:
    """Every registered class, once each."""
    seen: List[Type[HCIEvtUI]] = []
    for cls in _evt_ui_registry.values():
        if cls not in seen:
            seen.append(cls)
    return seen


def get_event_ui_class_by_name(name: str) -> Optional[Type[HCIEvtUI]]:
    """Get an event UI class by its human-readable name."""
    for cls in get_all_event_ui_classes():
        if cls.NAME == name:
            return cls
    return None


def window_key_of(evt_ui_class: Type[HCIEvtUI], key: EvtKey) -> str:
    """The identity the factory uses to decide whether to reuse a window."""
    return evt_ui_class.WINDOW_KEY or f"{evt_ui_class.__name__}"


# Importing these registers their classes.
from . import link_control      # noqa: E402
from . import le                # noqa: E402


__all__ = [
    'register_event_ui',
    'get_event_ui_class',
    'get_event_ui_class_for',
    'get_all_event_ui_classes',
    'get_event_ui_class_by_name',
    'window_key_of',
    'HCIEvtUI',
    'GenericEventUI',
    'AggregatingEvtUI',
]
