"""
Transport package.

Layered, event-driven transport for HCI:

    Transport            named facade the UI holds
      └─ TransportInterface   UART | VIRTUAL | USB | SDIO
           ├─ IoReactor       interrupt-style I/O engine (no polling)
           └─ H4Framer        byte stream -> whole HCI packets

The receive path is push-based. Subscribe to `TransportEvent.READ` to get one
complete H4 packet per callback; callbacks run on the I/O thread, so use
`transports.qt_bridge.QtTransportBridge` when the consumer is a Qt widget.

Example::

    from transports import Transport, TransportEvent

    transport = Transport.get_instance("dongle")
    transport.select_interface("UART")
    transport.configure({"port": "/dev/tty.usbserial-1", "baudrate": 115200,
                         "rtscts": True})
    transport.add_callback(TransportEvent.READ, lambda pkt: print(pkt.hex()))
    transport.connect()
    transport.write(bytes.fromhex("01030c00"))   # HCI_Reset
"""

from .base_lib import (
    ConfigurationError,
    ConnectionError,
    TransportError,
    TransportEvent,
    TransportInterface,
    TransportState,
)
from .h4 import H4Framer, H4Packet, H4PacketType
from .reactor import BlockingReactor, IoReactor, ReactorError, SelectorReactor
from .SDIO.sdio import SDIOTransport
from .transport import Transport
from .UART.uart import COMMON_BAUDRATES, UARTConfig, UARTTransport
from .USB.usb import USBTransport
from .virtual import VirtualControllerTransport, VirtualDevice

__version__ = "2.0.0"

__all__ = [
    "Transport",
    "TransportInterface",
    "TransportState",
    "TransportEvent",
    "TransportError",
    "ConfigurationError",
    "ConnectionError",
    "UARTTransport",
    "UARTConfig",
    "COMMON_BAUDRATES",
    "SDIOTransport",
    "USBTransport",
    "VirtualControllerTransport",
    "VirtualDevice",
    "H4Framer",
    "H4Packet",
    "H4PacketType",
    "IoReactor",
    "SelectorReactor",
    "BlockingReactor",
    "ReactorError",
]
