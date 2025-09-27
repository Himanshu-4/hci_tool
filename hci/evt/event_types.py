"""
Event types for HCI events

This module defines the various event types and categories for HCI events.
"""

from enum import IntEnum, unique

@unique
class EventCategory(IntEnum):
    """HCI Event Categories"""
    LINK_CONTROL = 0x01
    LINK_POLICY = 0x02
    CONTROLLER_BASEBAND = 0x03
    INFORMATION = 0x04
    STATUS = 0x05
    TESTING = 0x06
    LE = 0x07
    VENDOR_SPECIFIC = 0x08

@unique
class LinkControlEventType(IntEnum):
    """Link Control Event Types"""
    INQUIRY_COMPLETE = 0x01
    INQUIRY_RESULT = 0x02
    CONNECTION_COMPLETE = 0x03
    CONNECTION_REQUEST = 0x04
    DISCONNECTION_COMPLETE = 0x05
    AUTHENTICATION_COMPLETE = 0x06
    REMOTE_NAME_REQUEST_COMPLETE = 0x07
    ENCRYPTION_CHANGE = 0x08
    CHANGE_CONNECTION_LINK_KEY_COMPLETE = 0x09
    MASTER_LINK_KEY_COMPLETE = 0x0A
    READ_REMOTE_SUPPORTED_FEATURES_COMPLETE = 0x0B
    READ_REMOTE_VERSION_INFORMATION_COMPLETE = 0x0C

@unique
class LinkPolicyEventType(IntEnum):
    """Link Policy Event Types"""
    MODE_CHANGE = 0x14
    QOS_SETUP_COMPLETE = 0x0D
    ROLE_CHANGE = 0x12
    FLOW_SPECIFICATION_COMPLETE = 0x21
    SNIFF_SUBRATING = 0x2E

@unique
class ControllerBasebandEventType(IntEnum):
    """Controller and Baseband Event Types"""
    FLUSH_OCCURRED = 0x11
    READ_AUTOMATIC_FLUSH_TIMEOUT_COMPLETE = 0x27
    NUMBER_OF_COMPLETED_PACKETS = 0x13
    DATA_BUFFER_OVERFLOW = 0x1A
    MAX_SLOTS_CHANGE = 0x1B
    QOS_VIOLATION = 0x1E
    PAGE_SCAN_REPETITION_MODE_CHANGE = 0x20


class InformationEventType(IntEnum):
    """Information Event Types"""
    HARDWARE_ERROR = 0x10
    FLUSH_OCCURRED = 0x11

@unique
class StatusEventType(IntEnum):
    """Status Event Types"""
    COMMAND_COMPLETE = 0x0E
    COMMAND_STATUS = 0x0F
    HARDWARE_ERROR = 0x10

@unique
class TestingEventType(IntEnum):
    """Testing Event Types"""
    LOOPBACK_COMMAND = 0x19

@unique
class LEEventType(IntEnum):
    """LE Event Types"""
    LE_META_EVENT = 0x3E

@unique
class VendorSpecificEventType(IntEnum):
    """Vendor Specific Event Types"""
    VENDOR_SPECIFIC = 0xFF

# Mapping of event categories to event types
EVENT_CATEGORY_TO_TYPES = {
    EventCategory.LINK_CONTROL: LinkControlEventType,
    EventCategory.LINK_POLICY: LinkPolicyEventType,
    EventCategory.CONTROLLER_BASEBAND: ControllerBasebandEventType,
    EventCategory.INFORMATION: InformationEventType,
    EventCategory.STATUS: StatusEventType,
    EventCategory.TESTING: TestingEventType,
    EventCategory.LE: LEEventType,
    EventCategory.VENDOR_SPECIFIC: VendorSpecificEventType
}

# Mapping of event codes to categories
EVENT_CODE_TO_CATEGORY = {}

# Initialize event code to category mapping
def _initialize_event_categories():
    """Initialize the mapping of event codes to categories"""
    # Link Control Events
    for evt_type in LinkControlEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.LINK_CONTROL
    
    # Link Policy Events
    for evt_type in LinkPolicyEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.LINK_POLICY
    
    # Controller and Baseband Events
    for evt_type in ControllerBasebandEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.CONTROLLER_BASEBAND
    
    # Information Events
    for evt_type in InformationEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.INFORMATION
    
    # Status Events
    for evt_type in StatusEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.STATUS
    
    # Testing Events
    for evt_type in TestingEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.TESTING
    
    # LE Events
    for evt_type in LEEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.LE
    
    # Vendor Specific Events
    for evt_type in VendorSpecificEventType:
        EVENT_CODE_TO_CATEGORY[evt_type] = EventCategory.VENDOR_SPECIFIC

# Initialize the event categories
_initialize_event_categories()

# Export constants
__all__ = [
    'EventCategory',
    'LinkControlEventType',
    'LinkPolicyEventType',
    'ControllerBasebandEventType',
    'InformationEventType',
    'StatusEventType',
    'TestingEventType',
    'LEEventType',
    'VendorSpecificEventType',
    'EVENT_CATEGORY_TO_TYPES',
    'EVENT_CODE_TO_CATEGORY',
]