"""
Transport Package

This package provides a unified interface for different transport protocols
including UART, SDIO, and USB communications.

Main Classes:
- Transport: Main transport manager class
- TransportInterface: Abstract base class for all transport implementations
- UARTTransport: UART communication implementation
- SDIOTransport: SDIO communication implementation (placeholder)
- USBTransport: USB communication implementation (placeholder)

Usage Example:
    from transport import Transport
    
    # Create transport instance
    transport = Transport()
    
    # Select UART interface
    transport.select_interface('UART')
    
    # Configure UART parameters
    config = {
        'port': 'COM3',
        'baudrate': 115200,
        'timeout': 1
    }
    transport.configure(config)
    
    # Connect
    if transport.connect():
        # Send data
        transport.write(b'Hello World')
        
        # Read data
        data = transport.read()
        
        # Disconnect
        transport.disconnect()
"""

from .transport import Transport
from .base_lib import TransportInterface, ConnectionStatus, TransportError, ConfigurationError, ConnectionError
from .UART.uart import UARTTransport
from .SDIO.sdio import SDIOTransport  
from .USB.usb import USBTransport

__version__ = "1.0.0"
__author__ = "Transport Module"

__all__ = [
    'Transport',
    'TransportInterface', 
    'ConnectionStatus',
    'TransportError',
    'ConfigurationError', 
    'ConnectionError',
    'UARTTransport',
    'SDIOTransport',
    'USBTransport'
]