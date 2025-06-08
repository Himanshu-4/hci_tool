"""
HCI Module initialization 

This is the main package entry point for the HCI library.
"""

# Import base HCI packet module
from .hci_packet import *
from .hci_util import *

# Import submodules to make them available
from . import cmd
from . import evt


__all__ = [
    'cmd',
    'evt',
    'HciPacketType',
    'HciPacket',
    'HciCommandPacket',
    'HciEventPacket',
    'HciAclDataPacket',
    'HciSynchronousDataPacket',
    'parse_hci_packet',
]