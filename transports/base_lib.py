"""
Transport layer core types.

Defines the contract every sub-transport (UART, USB, SDIO, virtual) implements,
plus the state/event vocabulary shared with the layers above.

Callback threading contract
---------------------------
Callbacks registered with `add_callback` fire on the transport's **I/O thread**,
not the UI thread. Handlers must be short and must not touch Qt widgets. Use
`transports.qt_bridge.QtTransportBridge` to marshal onto the Qt main thread.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, StrEnum, unique
from typing import Any, Callable, Dict, List, Optional


@unique
class TransportState(StrEnum):
    """Lifecycle state of a transport interface."""

    INITIATING = "initiating"
    DISCONNECTED = "disconnected"
    DISCONNECTING = "disconnecting"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    IDLE = "idle"
    ERROR = "error"


@unique
class TransportEvent(Enum):
    """
    Events a transport emits to its subscribers.

    READ carries one **complete, framed HCI packet** (type byte included), not a
    raw driver chunk. Subscribers can parse it directly. RAW_RX / RAW_TX carry
    unframed bytes and exist for hex tracing only.
    """

    READ = 0            # (packet: bytes) one complete H4 packet
    WRITE = 1           # (data: bytes) a packet handed to the driver
    CONNECT = 2         # (transport)
    DISCONNECT = 3      # (transport)
    ERROR = 4           # (exception)
    FLOW_CONTROL_UPDATE = 5
    RAW_RX = 6          # (chunk: bytes) unframed bytes off the wire
    RAW_TX = 7          # (chunk: bytes) unframed bytes onto the wire
    STATE_CHANGED = 8   # (old: TransportState, new: TransportState)


class TransportError(Exception):
    """Base class for transport failures."""


class ConfigurationError(TransportError):
    """Invalid or incomplete configuration."""


class ConnectionError(TransportError):  # noqa: A001 - kept: imported by name elsewhere
    """Could not open, or lost, the underlying link."""


class TransportInterface(ABC):
    """
    Abstract base for all transport implementations.

    Concrete subclasses implement `configure`, `connect`, `disconnect`, `write`
    and `read`; everything else (callbacks, state transitions, statistics) is
    provided here so the sub-transports stay small.
    """

    def __init__(self):
        self._status = TransportState.DISCONNECTED
        self.config: Any = None

        self.callbacks: Dict[TransportEvent, List[Callable]] = {
            event: [] for event in TransportEvent
        }

        self._stats = {
            "packets_rx": 0,
            "packets_tx": 0,
            "bytes_rx": 0,
            "bytes_tx": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------ lifecycle

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """Validate and store configuration. Raises ConfigurationError."""

    @abstractmethod
    def connect(self) -> bool:
        """Open the link and start the receive engine."""

    @abstractmethod
    def disconnect(self) -> bool:
        """Stop the receive engine and close the link. Must be idempotent."""

    @abstractmethod
    def write(self, data: bytes) -> bool:
        """Queue one complete HCI packet for transmission."""

    @abstractmethod
    def read(self, size: int = -1) -> Optional[bytes]:
        """
        Legacy pull-style read.

        The transport is push-based: subscribe to `TransportEvent.READ`.
        Implementations may return None.
        """

    # ------------------------------------------------------------- callbacks

    def add_callback(self, event_type: TransportEvent, callback: Callable) -> None:
        if event_type not in self.callbacks:
            raise ValueError(f"Invalid event type: {event_type}")
        if callback not in self.callbacks[event_type]:
            self.callbacks[event_type].append(callback)

    def remove_callback(self, event_type: TransportEvent, callback: Callable) -> None:
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def clear_callbacks(self, event_type: Optional[TransportEvent] = None) -> None:
        if event_type is None:
            for handlers in self.callbacks.values():
                handlers.clear()
        elif event_type in self.callbacks:
            self.callbacks[event_type].clear()

    def _trigger_callbacks(self, event_type: TransportEvent, *args, **kwargs) -> None:
        """
        Fan out to subscribers.

        Iterates a copy: a handler is allowed to unsubscribe itself. One failing
        handler must never stop the others or kill the I/O thread.
        """
        for callback in list(self.callbacks.get(event_type, ())):
            try:
                callback(*args, **kwargs)
            except Exception as exc:
                self._stats["errors"] += 1
                print(f"[transport] callback error on {event_type.name}: {exc!r}")

    # ----------------------------------------------------------------- state

    @property
    def status(self) -> TransportState:
        return self._status

    @status.setter
    def status(self, value: TransportState) -> None:
        self._set_status(value)

    def _set_status(self, value: TransportState) -> None:
        if value == self._status:
            return
        old, self._status = self._status, value
        self._trigger_callbacks(TransportEvent.STATE_CHANGED, old, value)

    def is_connected(self) -> bool:
        """Method, not property -- `Transport` forwards to it as a call."""
        return self._status == TransportState.CONNECTED

    def get_config(self) -> Dict[str, Any]:
        if self.config is None:
            return {}
        if isinstance(self.config, dict):
            return dict(self.config)
        return dict(vars(self.config))

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


__all__ = [
    "TransportState",
    "TransportEvent",
    "TransportInterface",
    "TransportError",
    "ConfigurationError",
    "ConnectionError",
]
