"""
Transport manager.

A thin facade over the sub-transports (UART, virtual, USB, SDIO). Owns the named
instance registry the UI uses to keep one transport per HCI window, and forwards
the `TransportInterface` surface to whichever sub-transport is selected.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, Union

from .base_lib import (
    TransportError,
    TransportEvent,
    TransportInterface,
    TransportState,
)
from .SDIO.sdio import SDIOTransport
from .UART.uart import UARTTransport
from .USB.usb import USBTransport
from .virtual import VirtualControllerTransport


class Transport:
    """Named handle onto one sub-transport instance."""

    _transport_instances: Dict[str, "Transport"] = {}

    #: Selectable sub-transports, by the name the UI shows.
    AVAILABLE_INTERFACES: Dict[str, Type[TransportInterface]] = {
        "UART": UARTTransport,
        "SDIO": SDIOTransport,
        "USB": USBTransport,
        "VIRTUAL": VirtualControllerTransport,
    }

    # ------------------------------------------------------- instance registry

    @classmethod
    def get_instance(cls, name: str = "DefaultTransport") -> "Transport":
        if name not in cls._transport_instances:
            cls._transport_instances[name] = cls(name)
        return cls._transport_instances[name]

    @classmethod
    def clear_instances(cls) -> None:
        for transport in list(cls._transport_instances.values()):
            try:
                transport.disconnect()
            except Exception:
                pass
        cls._transport_instances.clear()

    @classmethod
    def remove_instance(cls, name: Union[str, "Transport"]) -> None:
        if isinstance(name, Transport):
            name = name.name
        transport = cls._transport_instances.pop(name, None)
        if transport is None:
            raise TransportError(f"Transport instance '{name}' not found.")
        try:
            transport.disconnect()
        except Exception:
            pass

    @classmethod
    def list_instances(cls) -> Dict[str, "Transport"]:
        return dict(cls._transport_instances)

    # ------------------------------------------------------------------ init

    def __init__(self, name: str = "DefaultTransport"):
        self.name = name
        self.interface_type: Optional[str] = None
        self.transport_instance: Optional[TransportInterface] = None
        self.available_interfaces = dict(self.AVAILABLE_INTERFACES)

        # Callbacks registered before an interface exists are replayed onto it
        # when one is selected -- the UI wires handlers up early.
        self._pending_callbacks: List[tuple] = []

    def __repr__(self) -> str:
        return (f"<Transport {self.name!r} interface={self.interface_type} "
                f"state={self.status}>")

    # ------------------------------------------------------------- selection

    def select_interface(self, interface_type: str) -> bool:
        key = interface_type.upper()
        if key not in self.available_interfaces:
            raise TransportError(
                f"Interface '{interface_type}' not available. "
                f"Available: {list(self.available_interfaces)}"
            )

        if self.transport_instance is not None:
            try:
                self.transport_instance.disconnect()
            except Exception:
                pass

        self.transport_instance = self.available_interfaces[key]()
        self.interface_type = key

        for event_type, callback in self._pending_callbacks:
            self.transport_instance.add_callback(event_type, callback)
        return True

    def _require(self) -> TransportInterface:
        if self.transport_instance is None:
            raise TransportError("No interface selected. Call select_interface() first.")
        return self.transport_instance

    # ------------------------------------------------------------- forwarding

    def configure(self, config: Dict[str, Any]) -> bool:
        return self._require().configure(config)

    def connect(self) -> bool:
        return self._require().connect()

    def disconnect(self) -> bool:
        if self.transport_instance is None:
            return True
        return self.transport_instance.disconnect()

    def write(self, data: bytes) -> bool:
        return self._require().write(data)

    def read(self, size: int = -1) -> Optional[bytes]:
        return self._require().read(size)

    def add_callback(self, event_type: TransportEvent, callback: Callable) -> None:
        """Safe to call before `select_interface`; replayed when one is chosen."""
        entry = (event_type, callback)
        if entry not in self._pending_callbacks:
            self._pending_callbacks.append(entry)
        if self.transport_instance is not None:
            self.transport_instance.add_callback(event_type, callback)

    def remove_callback(self, event_type: TransportEvent, callback: Callable) -> None:
        entry = (event_type, callback)
        if entry in self._pending_callbacks:
            self._pending_callbacks.remove(entry)
        if self.transport_instance is not None:
            self.transport_instance.remove_callback(event_type, callback)

    # ------------------------------------------------------------ properties

    @property
    def status(self) -> TransportState:
        if self.transport_instance is None:
            return TransportState.DISCONNECTED
        return self.transport_instance.status

    def is_connected(self) -> bool:
        return self.transport_instance is not None and self.transport_instance.is_connected()

    def get_config(self) -> Dict[str, Any]:
        return {} if self.transport_instance is None else self.transport_instance.get_config()

    def get_interface_type(self) -> Optional[str]:
        return self.interface_type

    def get_available_interfaces(self) -> List[str]:
        return list(self.available_interfaces)

    def get_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "name": self.name,
            "interface_type": self.interface_type,
            "status": self.status.value if self.transport_instance else "not_selected",
        }
        if self.transport_instance is not None:
            stats.update(self.transport_instance.get_stats())
        return stats


def create_uart_transport() -> UARTTransport:
    return UARTTransport()


def create_sdio_transport() -> SDIOTransport:
    return SDIOTransport()


def create_usb_transport() -> USBTransport:
    return USBTransport()


def create_virtual_transport() -> VirtualControllerTransport:
    return VirtualControllerTransport()


__all__ = [
    "Transport",
    "TransportEvent",
    "TransportState",
    "TransportError",
    "create_uart_transport",
    "create_sdio_transport",
    "create_usb_transport",
    "create_virtual_transport",
]
