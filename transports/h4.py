"""
H4 (UART) HCI transport framing.

A pure byte-oriented state machine: no I/O, no threads, no Qt. Feed it whatever
chunks the driver hands you -- one byte, half a header, six packets glued
together -- and it yields complete H4 packets in order.

Keeping this free of I/O is deliberate. Framing is where transport bugs hide,
and a pure function of (state, bytes) is the only version that can be tested
exhaustively without hardware.

Wire format -- one type byte, then a type-specific header carrying the payload
length:

    type  header after type byte              length field
    0x01  opcode(2) + plen(1)                 1 byte
    0x02  handle+flags(2) + dlen(2)           2 bytes LE
    0x03  handle+flags(2) + dlen(1)           1 byte
    0x04  evtcode(1) + plen(1)                1 byte
    0x05  handle+flags(2) + dlen(2)           2 bytes LE (top 2 bits RFU)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import Callable, List, Optional


@unique
class H4PacketType(IntEnum):
    """H4 packet indicator byte."""

    COMMAND = 0x01
    ACL_DATA = 0x02
    SCO_DATA = 0x03
    EVENT = 0x04
    ISO_DATA = 0x05

    @classmethod
    def is_valid(cls, value: int) -> bool:
        return value in _VALID_TYPES


_VALID_TYPES = frozenset(int(t) for t in H4PacketType)

# (header length after the type byte, offset of the length field, width of it)
_HEADER_SPEC = {
    H4PacketType.COMMAND: (3, 2, 1),
    H4PacketType.ACL_DATA: (4, 2, 2),
    H4PacketType.SCO_DATA: (3, 2, 1),
    H4PacketType.EVENT: (2, 1, 1),
    H4PacketType.ISO_DATA: (4, 2, 2),
}

# ISO data length is 12 bits + 2 RFU + 2 flag bits in the upper nibble.
_ISO_LENGTH_MASK = 0x3FFF


@dataclass(frozen=True)
class H4Packet:
    """One complete H4 packet, header and payload included."""

    type: H4PacketType
    payload: bytes  # everything after the type byte, header included

    @property
    def raw(self) -> bytes:
        """The packet as it appeared on the wire, type byte first."""
        return bytes([int(self.type)]) + self.payload

    def __len__(self) -> int:
        return len(self.payload) + 1

    def __str__(self) -> str:
        return f"{self.type.name}[{len(self.payload)}] {self.payload.hex(' ')}"


@dataclass
class FramerStats:
    """Cheap counters -- useful when a link misbehaves in the field."""

    packets: int = 0
    bytes_in: int = 0
    resyncs: int = 0
    discarded_bytes: int = 0
    by_type: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "packets": self.packets,
            "bytes_in": self.bytes_in,
            "resyncs": self.resyncs,
            "discarded_bytes": self.discarded_bytes,
            "by_type": {k.name if isinstance(k, H4PacketType) else k: v
                        for k, v in self.by_type.items()},
        }


class H4Framer:
    """
    Incremental H4 deframer.

    Usage::

        framer = H4Framer(on_error=log.warning)
        for pkt in framer.feed(chunk):
            handle(pkt)

    The framer never raises on bad input. A byte that cannot be a packet type is
    dropped, `stats.resyncs` is bumped, and `on_error` is called if supplied.
    That policy matters: this runs on the I/O thread, and an exception there
    kills the link for the rest of the session. Real controllers emit vendor
    noise, boot banners and truncated packets across a baud-rate change -- the
    framer has to walk through it.
    """

    #: Hard cap on the buffer. A stuck length byte must not grow memory forever.
    MAX_BUFFER = 1 << 16

    def __init__(self, on_error: Optional[Callable[[str], None]] = None):
        self._buf = bytearray()
        self._on_error = on_error
        self.stats = FramerStats()

    # ------------------------------------------------------------------ API

    def feed(self, data: bytes) -> List[H4Packet]:
        """Push received bytes in, get zero or more complete packets out."""
        if not data:
            return []

        self.stats.bytes_in += len(data)
        self._buf.extend(data)

        if len(self._buf) > self.MAX_BUFFER:
            # Should be unreachable with a sane peer; if we get here the stream
            # is garbage. Drop it rather than grow without bound.
            self._error(f"framer buffer overflow ({len(self._buf)} bytes), flushing")
            self.stats.discarded_bytes += len(self._buf)
            self._buf.clear()
            return []

        packets: List[H4Packet] = []
        while True:
            pkt = self._try_parse_one()
            if pkt is None:
                break
            packets.append(pkt)
        return packets

    def reset(self) -> None:
        """Drop any partial packet. Call on (re)connect."""
        self._buf.clear()

    @property
    def pending_bytes(self) -> int:
        """Bytes buffered as part of an incomplete packet."""
        return len(self._buf)

    # -------------------------------------------------------------- internals

    def _try_parse_one(self) -> Optional[H4Packet]:
        if not self._buf:
            return None

        if not self._resync():
            return None

        ptype = H4PacketType(self._buf[0])
        hdr_len, len_off, len_width = _HEADER_SPEC[ptype]

        # +1 for the type byte itself.
        if len(self._buf) < 1 + hdr_len:
            return None  # header not complete yet

        start = 1 + len_off
        payload_len = int.from_bytes(
            self._buf[start:start + len_width], byteorder="little"
        )
        if ptype is H4PacketType.ISO_DATA:
            payload_len &= _ISO_LENGTH_MASK

        total = 1 + hdr_len + payload_len
        if len(self._buf) < total:
            return None  # payload not complete yet

        payload = bytes(self._buf[1:total])
        del self._buf[:total]

        self.stats.packets += 1
        self.stats.by_type[ptype] = self.stats.by_type.get(ptype, 0) + 1
        return H4Packet(type=ptype, payload=payload)

    def _resync(self) -> bool:
        """
        Drop leading bytes until the buffer starts on a plausible type byte.

        Returns False if nothing is left.
        """
        dropped = 0
        while self._buf and not H4PacketType.is_valid(self._buf[0]):
            dropped += 1
            del self._buf[0]

        if dropped:
            self.stats.resyncs += 1
            self.stats.discarded_bytes += dropped
            self._error(f"resync: discarded {dropped} byte(s) of non-H4 data")

        return bool(self._buf)

    def _error(self, msg: str) -> None:
        if self._on_error is not None:
            try:
                self._on_error(msg)
            except Exception:  # never let a logging hook break framing
                pass


__all__ = ["H4PacketType", "H4Packet", "H4Framer", "FramerStats"]
