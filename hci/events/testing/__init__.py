"""
Testing events package.

This package provides implementations for Testing HCI events.
"""

from .testing_events import (
    # Event classes
    LoopbackCommandEvent,
    
    # Helper functions
    loopback_command,
)

# Re-export everything to make public API cleaner
__all__ = [
    # Event classes
    'LoopbackCommandEvent',
    
    # Helper functions
    'loopback_command',
]
