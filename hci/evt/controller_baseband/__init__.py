"""
Controller events package.

This package provides implementations for Controller and Baseband HCI events.
"""

from .controller_baseband_events import (
    # Event classes
    FlushOccurredEvent,
    DataBufferOverflowEvent,
    MaxSlotsChangeEvent,
    QosViolationEvent,
    NumberOfCompletedPacketsEvent,
    PageScanRepetitionModeChangeEvent,
    
    # Helper functions
    flush_occurred,
    data_buffer_overflow,
    max_slots_change,
    qos_violation,
    number_of_completed_packets,
    page_scan_repetition_mode_change,
)

# Re-export everything to make public API cleaner
__all__ = [
    # Event classes
    'FlushOccurredEvent',
    'DataBufferOverflowEvent',
    'MaxSlotsChangeEvent',
    'QosViolationEvent',
    'NumberOfCompletedPacketsEvent',
    'PageScanRepetitionModeChangeEvent',
    
    # Helper functions
    'flush_occurred',
    'data_buffer_overflow',
    'max_slots_change',
    'qos_violation',
    'number_of_completed_packets',
    'page_scan_repetition_mode_change',
]
