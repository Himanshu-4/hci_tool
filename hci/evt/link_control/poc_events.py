"""
Additional Link Control / LE events required by the connection flows.

`Disconnection_Complete` in particular was missing entirely -- without it a
disconnect is never observed and the connection table never clears.

Kept in a separate module from `link_control_events.py` so the existing file
stays as-is; both are imported by the package `__init__`.
"""

from __future__ import annotations

import struct
from typing import List, Optional, Tuple, Union

from .. import register_event
from ..error_codes import StatusCode, get_status_description
from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode


def _addr_str(addr_le: bytes) -> str:
    """Wire-order (little-endian) BD_ADDR bytes -> 'AA:BB:CC:DD:EE:FF'."""
    return ":".join(f"{b:02X}" for b in reversed(addr_le))


class DisconnectionCompleteEvent(HciEvtBasePacket):
    """Disconnection Complete Event (0x05)."""

    EVENT_CODE = HciEventCode.DISCONNECTION_COMPLETE
    NAME = "Disconnection_Complete"

    def __init__(self, status: Union[int, StatusCode], connection_handle: int,
                 reason: Union[int, StatusCode]):
        if isinstance(status, StatusCode):
            status = status.value
        if isinstance(reason, StatusCode):
            reason = reason.value
        super().__init__(status=status, connection_handle=connection_handle,
                         reason=reason)

    def _validate_params(self) -> None:
        handle = self.params['connection_handle']
        if not (0x0000 <= handle <= 0x0EFF):
            raise ValueError(f"Invalid connection_handle: 0x{handle:04X}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<BHB", self.params['status'],
                           self.params['connection_handle'], self.params['reason'])

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4 bytes")
        status, handle, reason = struct.unpack("<BHB", data[:4])
        return cls(status=status, connection_handle=handle, reason=reason)

    def __str__(self) -> str:
        return (f"Disconnection_Complete: Handle=0x{self.params['connection_handle']:04X}, "
                f"Status={get_status_description(self.params['status'])} "
                f"(0x{self.params['status']:02X}), "
                f"Reason={get_status_description(self.params['reason'])} "
                f"(0x{self.params['reason']:02X})")


class InquiryResultWithRssiEvent(HciEvtBasePacket):
    """Inquiry Result with RSSI Event (0x22)."""

    EVENT_CODE = HciEventCode.INQUIRY_RESULT_WITH_RSSI
    NAME = "Inquiry_Result_with_RSSI"

    def __init__(self, responses: List[dict]):
        super().__init__(num_responses=len(responses), responses=responses)

    def _serialize_params(self) -> bytes:
        out = bytearray([len(self.params['responses'])])
        for r in self.params['responses']:
            out += r['bd_addr']
            out += bytes([r['page_scan_repetition_mode'], 0x00])
            out += r['class_of_device'].to_bytes(3, 'little')
            out += struct.pack("<Hb", r['clock_offset'], r['rssi'])
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        if len(data) < 1:
            raise ValueError("Inquiry_Result_with_RSSI: empty payload")
        num = data[0]
        stride = 14  # addr(6) psrm(1) rsvd(1) cod(3) clkoff(2) rssi(1)
        responses = []
        for i in range(num):
            off = 1 + i * stride
            if off + stride > len(data):
                break
            addr = bytes(data[off:off + 6])
            psrm = data[off + 6]
            cod = int.from_bytes(data[off + 8:off + 11], 'little')
            clk, rssi = struct.unpack_from("<Hb", data, off + 11)
            responses.append({
                'bd_addr': addr,
                'bd_addr_str': _addr_str(addr),
                'page_scan_repetition_mode': psrm,
                'class_of_device': cod,
                'clock_offset': clk,
                'rssi': rssi,
            })
        return cls(responses)

    def __str__(self) -> str:
        parts = [f"{r['bd_addr_str']} RSSI={r['rssi']}dBm CoD=0x{r['class_of_device']:06X}"
                 for r in self.params['responses']]
        return f"Inquiry_Result_with_RSSI [{len(parts)}]: " + "; ".join(parts)


class ExtendedInquiryResultEvent(HciEvtBasePacket):
    """Extended Inquiry Result Event (0x2F). Always exactly one response."""

    EVENT_CODE = HciEventCode.EXTENDED_INQUIRY_RESULT
    NAME = "Extended_Inquiry_Result"

    def __init__(self, bd_addr: bytes, page_scan_repetition_mode: int,
                 class_of_device: int, clock_offset: int, rssi: int,
                 extended_inquiry_response: bytes):
        super().__init__(
            num_responses=1,
            bd_addr=bd_addr,
            bd_addr_str=_addr_str(bd_addr),
            page_scan_repetition_mode=page_scan_repetition_mode,
            class_of_device=class_of_device,
            clock_offset=clock_offset,
            rssi=rssi,
            extended_inquiry_response=extended_inquiry_response,
        )

    def _serialize_params(self) -> bytes:
        return (bytes([1]) + self.params['bd_addr']
                + bytes([self.params['page_scan_repetition_mode'], 0x00])
                + self.params['class_of_device'].to_bytes(3, 'little')
                + struct.pack("<Hb", self.params['clock_offset'], self.params['rssi'])
                + self.params['extended_inquiry_response'].ljust(240, b"\x00"))

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        if len(data) < 15:
            raise ValueError(f"Extended_Inquiry_Result too short: {len(data)}")
        addr = bytes(data[1:7])
        psrm = data[7]
        cod = int.from_bytes(data[9:12], 'little')
        clk, rssi = struct.unpack_from("<Hb", data, 12)
        return cls(addr, psrm, cod, clk, rssi, bytes(data[15:]))

    def __str__(self) -> str:
        return (f"Extended_Inquiry_Result: {self.params['bd_addr_str']} "
                f"RSSI={self.params['rssi']}dBm "
                f"CoD=0x{self.params['class_of_device']:06X}")


class EncryptionChangeEvent(HciEvtBasePacket):
    """Encryption Change Event (0x08)."""

    EVENT_CODE = HciEventCode.ENCRYPTION_CHANGE
    NAME = "Encryption_Change"

    def __init__(self, status: int, connection_handle: int, encryption_enabled: int):
        super().__init__(status=status, connection_handle=connection_handle,
                         encryption_enabled=encryption_enabled)

    def _serialize_params(self) -> bytes:
        return struct.pack("<BHB", self.params['status'],
                           self.params['connection_handle'],
                           self.params['encryption_enabled'])

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        if len(data) < 4:
            raise ValueError(f"Encryption_Change too short: {len(data)}")
        status, handle, enabled = struct.unpack("<BHB", data[:4])
        return cls(status, handle, enabled)

    def __str__(self) -> str:
        state = {0: "off", 1: "on (E0/AES-CCM)", 2: "on (AES-CCM)"}.get(
            self.params['encryption_enabled'], "unknown")
        return (f"Encryption_Change: Handle=0x{self.params['connection_handle']:04X}, "
                f"Encryption={state}, "
                f"Status={get_status_description(self.params['status'])}")


class HardwareErrorEvent(HciEvtBasePacket):
    """Hardware Error Event (0x10) -- the controller telling you it is unwell."""

    EVENT_CODE = HciEventCode.HARDWARE_ERROR
    NAME = "Hardware_Error"

    def __init__(self, hardware_code: int):
        super().__init__(hardware_code=hardware_code)

    def _serialize_params(self) -> bytes:
        return bytes([self.params['hardware_code']])

    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None):
        if not data:
            raise ValueError("Hardware_Error: empty payload")
        return cls(data[0])

    def __str__(self) -> str:
        return f"Hardware_Error: code=0x{self.params['hardware_code']:02X}"


register_event(DisconnectionCompleteEvent)
register_event(InquiryResultWithRssiEvent)
register_event(ExtendedInquiryResultEvent)
register_event(EncryptionChangeEvent)
register_event(HardwareErrorEvent)


__all__ = [
    'DisconnectionCompleteEvent',
    'InquiryResultWithRssiEvent',
    'ExtendedInquiryResultEvent',
    'EncryptionChangeEvent',
    'HardwareErrorEvent',
]
