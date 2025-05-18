"""
LE (Low Energy) events package

This package provides implementations for BLE HCI events.
"""

from .le_events import (
    # Event classes
    LeConnectionCompleteEvent,
    LeAdvertisingReportEvent,
    LeConnectionUpdateCompleteEvent,
    LeReadRemoteFeaturesCompleteEvent,
    
    # Helper functions
    le_connection_complete,
    le_advertising_report,
    le_connection_update_complete,
    le_read_remote_features_complete,
)

# Re-export everything to make public API cleaner
__all__ = [
    # Event classes
    'LeConnectionCompleteEvent',
    'LeAdvertisingReportEvent',
    'LeConnectionUpdateCompleteEvent',
    'LeReadRemoteFeaturesCompleteEvent',
    
    # Helper functions
    'le_connection_complete',
    'le_advertising_report',
    'le_connection_update_complete',
    'le_read_remote_features_complete',
]