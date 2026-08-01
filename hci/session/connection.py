"""
Connection bookkeeping.

Tracks which handles are live, what they connect to, and over which transport.
The session owns one of these and updates it from Connection Complete,
LE Connection Complete and Disconnection Complete.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, List, Optional


@unique
class LinkType(str, Enum):
    BR_EDR = "BR/EDR"
    LE = "LE"


@unique
class Role(str, Enum):
    CENTRAL = "central"       # master / initiator
    PERIPHERAL = "peripheral"  # slave / advertiser

    @classmethod
    def from_hci(cls, value: int) -> "Role":
        return cls.CENTRAL if value == 0x00 else cls.PERIPHERAL


def addr_to_str(addr: bytes, wire_order: bool = False) -> str:
    """
    Format a BD_ADDR.

    `wire_order=True` means the bytes are still little-endian as they came off
    the wire and need reversing for display.
    """
    data = bytes(reversed(addr)) if wire_order else bytes(addr)
    return ":".join(f"{b:02X}" for b in data)


def addr_from_str(text: str) -> bytes:
    """'AA:BB:CC:DD:EE:FF' -> wire-order (little-endian) bytes."""
    parts = text.replace("-", ":").split(":")
    if len(parts) != 6:
        raise ValueError(f"Invalid BD_ADDR: {text!r}, expected XX:XX:XX:XX:XX:XX")
    return bytes(int(p, 16) for p in reversed(parts))


@dataclass
class ConnectionInfo:
    """One live ACL connection."""

    handle: int
    bd_addr: str                      # display form, "AA:BB:..."
    link_type: LinkType
    role: Role = Role.CENTRAL
    address_type: int = 0x00          # LE only: 0 public, 1 random
    encrypted: bool = False
    name: Optional[str] = None
    conn_interval: Optional[int] = None      # LE, 1.25 ms units
    conn_latency: Optional[int] = None
    supervision_timeout: Optional[int] = None  # LE, 10 ms units
    established_at: float = field(default_factory=time.monotonic)

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.established_at

    @property
    def interval_ms(self) -> Optional[float]:
        return None if self.conn_interval is None else self.conn_interval * 1.25

    @property
    def timeout_ms(self) -> Optional[int]:
        return None if self.supervision_timeout is None else self.supervision_timeout * 10

    def __str__(self) -> str:
        text = (f"handle=0x{self.handle:04X} {self.bd_addr} "
                f"{self.link_type.value} {self.role.value}")
        if self.name:
            text += f" '{self.name}'"
        if self.interval_ms is not None:
            text += f" interval={self.interval_ms:.2f}ms"
        if self.encrypted:
            text += " [encrypted]"
        return text


class ConnectionTable:
    """Thread-safe map of handle -> ConnectionInfo."""

    def __init__(self):
        self._lock = threading.RLock()
        self._by_handle: Dict[int, ConnectionInfo] = {}

    def add(self, info: ConnectionInfo) -> ConnectionInfo:
        with self._lock:
            self._by_handle[info.handle] = info
            return info

    def remove(self, handle: int) -> Optional[ConnectionInfo]:
        with self._lock:
            return self._by_handle.pop(handle, None)

    def get(self, handle: int) -> Optional[ConnectionInfo]:
        with self._lock:
            return self._by_handle.get(handle)

    def by_address(self, bd_addr: str) -> Optional[ConnectionInfo]:
        target = bd_addr.upper()
        with self._lock:
            for info in self._by_handle.values():
                if info.bd_addr.upper() == target:
                    return info
        return None

    def all(self) -> List[ConnectionInfo]:
        with self._lock:
            return list(self._by_handle.values())

    def handles(self) -> List[int]:
        with self._lock:
            return list(self._by_handle)

    def of_type(self, link_type: LinkType) -> List[ConnectionInfo]:
        with self._lock:
            return [c for c in self._by_handle.values() if c.link_type is link_type]

    def clear(self) -> None:
        with self._lock:
            self._by_handle.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_handle)

    def __contains__(self, handle: int) -> bool:
        with self._lock:
            return handle in self._by_handle

    def __iter__(self):
        return iter(self.all())

    def __str__(self) -> str:
        conns = self.all()
        if not conns:
            return "no connections"
        return "; ".join(str(c) for c in conns)


__all__ = [
    "ConnectionInfo",
    "ConnectionTable",
    "LinkType",
    "Role",
    "addr_to_str",
    "addr_from_str",
]
