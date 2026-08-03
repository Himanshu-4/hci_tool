"""
Minimal L2CAP framing over ACL, for the profile test screens.

This tool has no L2CAP state machine: it does not do connection requests,
configuration or channel allocation. What it does have is everything needed to
put a payload on a channel that *already exists* -- build the B-frame, fragment
it across ACL packets, and reassemble the other direction.

That is a deliberate limit, and it is why the HID and A2DP screens ask for a
CID rather than discovering one. The CID comes from whatever established the
channel: a real stack on the other side of the controller, or the vendor L2CAP
commands some controllers expose. Sending on the wrong CID is silently dropped
by the peer, so the screens show which CID they are using.

B-frame layout: length (2, little endian, payload only) + CID (2) + payload.
"""

from __future__ import annotations

import struct
from typing import Dict, Iterator, List, Optional, Tuple

from hci.hci_packet import HciAclDataPacket

#: Well-known PSMs, for reference in the screens.
PSM_SDP = 0x0001
PSM_RFCOMM = 0x0003
PSM_HID_CONTROL = 0x0011
PSM_HID_INTERRUPT = 0x0013
PSM_AVDTP = 0x0019
PSM_AVCTP = 0x0017

#: Fixed CIDs that never need discovering.
CID_SIGNALLING = 0x0001
CID_CONNECTIONLESS = 0x0002
CID_ATT = 0x0004
CID_LE_SIGNALLING = 0x0005
CID_SMP = 0x0006

#: ACL packet boundary flags.
PB_FIRST_NON_FLUSHABLE = 0x00
PB_CONTINUATION = 0x01
PB_FIRST_FLUSHABLE = 0x02


def build_bframe(cid: int, payload: bytes) -> bytes:
    """One L2CAP basic frame."""
    if not (0x0001 <= cid <= 0xFFFF):
        raise ValueError(f"Invalid CID: 0x{cid:04X}")
    if len(payload) > 0xFFFF:
        raise ValueError(f"L2CAP payload is {len(payload)} bytes; the length "
                         "field is 16 bits")
    return struct.pack("<HH", len(payload), cid) + bytes(payload)


def fragment_acl(handle: int, frame: bytes, max_payload: int = 27,
                 flushable: bool = True) -> List[bytes]:
    """
    Split one L2CAP frame across ACL packets.

    `max_payload` is the controller's ACL data length from Read Buffer Size --
    exceeding it gets the write refused, which is the usual reason a large
    frame silently fails while a small one works.
    """
    if max_payload < 1:
        raise ValueError("max_payload must be at least 1")

    first_flag = PB_FIRST_FLUSHABLE if flushable else PB_FIRST_NON_FLUSHABLE
    packets = []
    offset = 0
    while offset < len(frame):
        chunk = frame[offset:offset + max_payload]
        packet = HciAclDataPacket(
            connection_handle=handle,
            pb_flag=first_flag if offset == 0 else PB_CONTINUATION,
            bc_flag=0x00,
            data=chunk)
        packets.append(packet.to_bytes())
        offset += len(chunk)

    if not packets:
        # A zero-length frame is still a frame; the peer needs the header.
        packets.append(HciAclDataPacket(connection_handle=handle,
                                        pb_flag=first_flag, bc_flag=0x00,
                                        data=b'').to_bytes())
    return packets


def acl_packets_for(handle: int, cid: int, payload: bytes,
                    max_payload: int = 27, flushable: bool = True) -> List[bytes]:
    """Build the frame and fragment it, in one call."""
    return fragment_acl(handle, build_bframe(cid, payload), max_payload,
                        flushable)


class L2capReassembler:
    """
    Rebuilds L2CAP frames from received ACL packets.

    One partial buffer per connection handle: a continuation fragment belongs to
    whatever that handle was in the middle of, and interleaving across handles
    is normal when several links are up.
    """

    def __init__(self):
        self._partial: Dict[int, bytearray] = {}

    def feed(self, raw: bytes) -> Iterator[Tuple[int, int, bytes]]:
        """
        Consume one raw ACL packet, yielding (handle, cid, payload) per complete
        frame. Ignores anything that is not ACL.
        """
        if not raw or raw[0] != 0x02 or len(raw) < 5:
            return
        try:
            packet = HciAclDataPacket.from_bytes(raw)
        except ValueError:
            return

        handle = packet.params['connection_handle']
        pb_flag = packet.params['pb_flag']
        data = packet.params['data']

        if pb_flag in (PB_FIRST_NON_FLUSHABLE, PB_FIRST_FLUSHABLE):
            buffer = bytearray(data)
            self._partial[handle] = buffer
        else:
            buffer = self._partial.get(handle)
            if buffer is None:
                # A continuation with no start: the beginning was missed, so
                # there is nothing to attach it to.
                return
            buffer += data

        # A buffer may hold more than one frame once fragments are joined.
        while len(buffer) >= 4:
            length, cid = struct.unpack_from("<HH", buffer, 0)
            if len(buffer) < 4 + length:
                break
            yield handle, cid, bytes(buffer[4:4 + length])
            del buffer[:4 + length]

        if not buffer:
            self._partial.pop(handle, None)

    def reset(self, handle: Optional[int] = None) -> None:
        if handle is None:
            self._partial.clear()
        else:
            self._partial.pop(handle, None)


__all__ = [
    "PSM_SDP", "PSM_RFCOMM", "PSM_HID_CONTROL", "PSM_HID_INTERRUPT",
    "PSM_AVDTP", "PSM_AVCTP",
    "CID_SIGNALLING", "CID_ATT", "CID_LE_SIGNALLING", "CID_SMP",
    "PB_FIRST_NON_FLUSHABLE", "PB_CONTINUATION", "PB_FIRST_FLUSHABLE",
    "build_bframe", "fragment_acl", "acl_packets_for", "L2capReassembler",
]
