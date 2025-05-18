"""
Link Control events package.

This package provides implementations for Link Control HCI events.
"""

from .link_control_events import (
    # Event classes
    InquiryCompleteEvent,
    InquiryResultEvent,
    ConnectionCompleteEvent,
    ConnectionRequestEvent,
    RemoteNameRequestCompleteEvent,
    ReadRemoteVersionInformationCompleteEvent,
    
    # Helper functions
    inquiry_complete,
    inquiry_result,
    connection_complete,
    connection_request,
    remote_name_request_complete,
    read_remote_version_information_complete,
)

# Re-export everything to make public API cleaner
__all__ = [
    # Event classes
    'InquiryCompleteEvent',
    'InquiryResultEvent',
    'ConnectionCompleteEvent',
    'ConnectionRequestEvent',
    'RemoteNameRequestCompleteEvent',
    'ReadRemoteVersionInformationCompleteEvent',
    
    # Helper functions
    'inquiry_complete',
    'inquiry_result',
    'connection_complete',
    'connection_request',
    'remote_name_request_complete',
    'read_remote_version_information_complete',
]
