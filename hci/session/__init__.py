"""
HCI session layer.

Sits between the transport (bytes) and the application (intent). Owns command
flow control, command/event correlation, connection state, and the high-level
procedures for advertising, scanning and connecting.

Typical use::

    from transports import Transport, TransportEvent
    from hci.session import HciSession, procedures

    transport = Transport.get_instance("dongle")
    transport.select_interface("UART")
    transport.configure({"port": "/dev/tty.usbserial-1", "baudrate": 115200})
    transport.connect()

    session = HciSession(transport)
    procedures.initialize_controller(session)
    devices = procedures.scan_le(session, duration=5.0)
    info = procedures.connect_le(session, devices[0].address)
    procedures.disconnect(session, info.handle)
"""

from . import procedures
from .connection import (
    ConnectionInfo,
    ConnectionTable,
    LinkType,
    Role,
    addr_from_str,
    addr_to_str,
)
from .procedures import (
    DeviceRegistry,
    DiscoveredDevice,
    connect_bredr,
    connect_le,
    disconnect,
    disconnect_all,
    initialize_controller,
    inquiry,
    run_in_thread,
    scan_le,
    start_advertising,
    stop_advertising,
)
from .session import (
    EVT_ADV_REPORT,
    EVT_COMMAND_SENT,
    EVT_CONNECTION_DOWN,
    EVT_CONNECTION_UP,
    EVT_ERROR,
    EVT_EVENT,
    EVT_INQUIRY_COMPLETE,
    EVT_INQUIRY_RESULT,
    EVT_PACKET,
    EVT_STATE,
    CmdToken,
    CommandError,
    HciSession,
)

__all__ = [
    "HciSession",
    "CmdToken",
    "CommandError",
    "ConnectionInfo",
    "ConnectionTable",
    "LinkType",
    "Role",
    "addr_to_str",
    "addr_from_str",
    "DiscoveredDevice",
    "DeviceRegistry",
    "procedures",
    "initialize_controller",
    "start_advertising",
    "stop_advertising",
    "scan_le",
    "connect_le",
    "inquiry",
    "connect_bredr",
    "disconnect",
    "disconnect_all",
    "run_in_thread",
    "EVT_PACKET",
    "EVT_EVENT",
    "EVT_COMMAND_SENT",
    "EVT_ADV_REPORT",
    "EVT_INQUIRY_RESULT",
    "EVT_INQUIRY_COMPLETE",
    "EVT_CONNECTION_UP",
    "EVT_CONNECTION_DOWN",
    "EVT_STATE",
    "EVT_ERROR",
]
