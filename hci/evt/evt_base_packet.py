"""
Base packet structure for HCI events.

Every hook here is **concrete**. That is deliberate: an event class that is
registered but abstract is worse than one that is missing, because the dispatcher
finds it and then raises `TypeError` at construction time -- on the receive
thread, mid-session. Subclasses override what they care about (`__str__`,
`_validate_params`, `_serialize_params`, `from_bytes`) and inherit sane defaults
for the rest.
"""

from __future__ import annotations

import struct
from typing import Any, ClassVar, Dict, Optional

from ..hci_packet import HciEventPacket


class HciEvtBasePacket(HciEventPacket):
    """Base class for all HCI event packets."""

    # Class variables filled in by subclasses.
    OPCODE: ClassVar[int]           # for Command Complete flavours
    EVENT_CODE: ClassVar[int]       # event code (1 byte)
    SUB_EVENT_CODE: Optional[int] = None   # LE meta sub-event code, if any
    NAME: ClassVar[str] = "Unknown_Event"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Allow per-instance overrides for generically-constructed events.
        if self.params.get('opcode'):
            self.OPCODE = self.params.get('opcode')
        if self.params.get('event_code'):
            self.EVENT_CODE = self.params.get('event_code')
        if self.params.get('sub_event_code'):
            self.SUB_EVENT_CODE = self.params.get('sub_event_code')
        if self.params.get('name'):
            self.NAME = self.params.get('name')
        self._validate_params()

    # ------------------------------------------------------------ overridable

    def _validate_params(self) -> None:
        """
        Validate parameters. Default: accept anything.

        Events come *from* the controller -- rejecting a slightly odd one is
        rarely more useful than surfacing it, so validation is opt-in.
        """

    def _serialize_params(self) -> bytes:
        """Serialize parameters. Default: no payload."""
        return b''

    def __str__(self) -> str:
        """
        Readable one-liner. Subclasses usually override with a decoded form;
        this default keeps every event printable without any extra work.
        """
        name = getattr(self.__class__, 'NAME', None) or 'Unknown_Event'
        code = getattr(self, 'EVENT_CODE', None)
        head = f"{name} (0x{code:02X})" if isinstance(code, int) else name

        sub = getattr(self, 'SUB_EVENT_CODE', None)
        if isinstance(sub, int):
            head += f"[sub=0x{sub:02X}]"

        if not self.params:
            return head
        return f"{head}: " + ", ".join(
            f"{k}={self._fmt(v)}" for k, v in self.params.items() if v is not None
        )

    @staticmethod
    def _fmt(value: Any) -> str:
        if isinstance(value, (bytes, bytearray)):
            return value.hex(' ') if value else "''"
        if isinstance(value, int) and not isinstance(value, bool):
            return f"0x{value:02X}" if 0 <= value <= 0xFF else str(value)
        return str(value)

    # ---------------------------------------------------------------- codecs

    def to_bytes(self) -> bytes:
        """Serialize to an event packet (without the H4 type byte)."""
        param_bytes = self._serialize_params() or b''
        return struct.pack("<BB", int(self.EVENT_CODE), len(param_bytes)) + param_bytes

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        """
        Build an event from its parameter bytes (header already stripped).

        Default behaviour dispatches to `from_bytes_sub_event` when the subclass
        defines one -- that is the convention the LE meta events use, and wiring
        it here means they do not each need a `from_bytes` shim.
        """
        sub_handler = getattr(cls, 'from_bytes_sub_event', None)
        if sub_handler is not None:
            if sub_event_code is None and data:
                sub_event_code = data[0]
            return sub_handler(data, sub_event_code)

        # Nothing more specific available: keep the payload so the caller can
        # still log and inspect it.
        return cls(raw_params=bytes(data))

    # ------------------------------------------------------------ convenience

    @property
    def status(self) -> Optional[int]:
        """Status byte, when the event carries one."""
        value = self.params.get('status')
        return value if isinstance(value, int) else None

    @property
    def is_success(self) -> bool:
        return self.status == 0x00

    @property
    def event_name(self) -> str:
        return getattr(self.__class__, 'NAME', 'Unknown_Event')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.event_name,
            'event_code': getattr(self, 'EVENT_CODE', None),
            'sub_event_code': getattr(self, 'SUB_EVENT_CODE', None),
            'params': dict(self.params),
        }


__all__ = ['HciEvtBasePacket']
