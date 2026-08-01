"""
Fallback event packets.

The receive path must never raise. A controller will emit vendor-specific
events, events from a spec version newer than this tool, and -- during a baud
change or a firmware reset -- outright garbage. If parsing those throws, the
exception propagates onto the I/O thread and the link dies for the rest of the
session.

So anything the registry cannot place becomes a `GenericEventPacket`: fully
constructed, printable as a hex dump, and carrying the raw bytes for whoever
wants to dig further.
"""

from __future__ import annotations

import struct
from typing import Optional

from .evt_base_packet import HciEvtBasePacket
from .evt_codes import HCI_EVENT_CODE_TO_NAME, LE_META_EVENT_SUBCODE_TO_NAME


class GenericEventPacket(HciEvtBasePacket):
    """An event we recognise structurally but have no dedicated class for."""

    NAME = "Unknown_Event"

    def __init__(
        self,
        event_code: int,
        params: bytes = b'',
        sub_event_code: Optional[int] = None,
        name: Optional[str] = None,
    ):
        resolved = name or HCI_EVENT_CODE_TO_NAME.get(event_code)
        if resolved is None:
            resolved = ("Vendor_Specific_Event" if event_code == 0xFF
                        else f"Unknown_Event_0x{event_code:02X}")
        elif sub_event_code is not None:
            sub_name = LE_META_EVENT_SUBCODE_TO_NAME.get(sub_event_code)
            resolved = sub_name or f"{resolved}_0x{sub_event_code:02X}"

        super().__init__(
            event_code=event_code,
            sub_event_code=sub_event_code,
            name=resolved,
            raw_params=bytes(params),
        )
        # `params` on the base is the kwargs dict, so keep the payload separately.
        self.EVENT_CODE = event_code
        self.SUB_EVENT_CODE = sub_event_code
        self.NAME = resolved

    @property
    def raw_params(self) -> bytes:
        return self.params.get('raw_params', b'')

    def _serialize_params(self) -> bytes:
        return self.raw_params

    def __str__(self) -> str:
        head = f"{self.NAME} (0x{self.EVENT_CODE:02X}"
        if self.SUB_EVENT_CODE is not None:
            head += f", sub=0x{self.SUB_EVENT_CODE:02X}"
        head += ")"
        payload = self.raw_params
        if not payload:
            return head
        return f"{head}: [{len(payload)}] {payload.hex(' ')}"

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        if not data:
            raise ValueError("empty event data")
        return cls(event_code=data[0], params=bytes(data[1:]),
                   sub_event_code=sub_event_code)


class MalformedEventPacket(GenericEventPacket):
    """
    An event whose declared length did not match the bytes present.

    Kept distinct from `GenericEventPacket` so the UI can flag it: an unknown
    event is normal, a malformed one usually means a framing or baud problem.
    """

    NAME = "Malformed_Event"

    def __init__(self, raw: bytes, reason: str):
        event_code = raw[1] if len(raw) > 1 else 0xFF
        super().__init__(event_code=event_code, params=bytes(raw),
                         name="Malformed_Event")
        self.params['reason'] = reason

    @property
    def reason(self) -> str:
        return self.params.get('reason', '')

    def __str__(self) -> str:
        return (f"Malformed_Event ({self.reason}): "
                f"[{len(self.raw_params)}] {self.raw_params.hex(' ')}")


__all__ = ["GenericEventPacket", "MalformedEventPacket"]
