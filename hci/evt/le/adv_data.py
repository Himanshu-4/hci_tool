"""
Advertising Data (AD) structure codec.

The payload of an advertising report is a sequence of length-prefixed AD
structures::

    [len][type][value ...][len][type][value ...] ...

where `len` covers the type byte plus the value. This module turns that into
something a device list can display -- a name, a TX power, service UUIDs -- and
builds it back for `LE_Set_Advertising_Data`.

Assigned-number reference: Bluetooth Core Supplement, Part A.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Sequence, Union


class AdType(IntEnum):
    """Common AD types (Core Supplement, Part A, §1)."""

    FLAGS = 0x01
    INCOMPLETE_16BIT_UUIDS = 0x02
    COMPLETE_16BIT_UUIDS = 0x03
    INCOMPLETE_32BIT_UUIDS = 0x04
    COMPLETE_32BIT_UUIDS = 0x05
    INCOMPLETE_128BIT_UUIDS = 0x06
    COMPLETE_128BIT_UUIDS = 0x07
    SHORTENED_LOCAL_NAME = 0x08
    COMPLETE_LOCAL_NAME = 0x09
    TX_POWER_LEVEL = 0x0A
    CLASS_OF_DEVICE = 0x0D
    DEVICE_ID = 0x10
    SLAVE_CONNECTION_INTERVAL_RANGE = 0x12
    SERVICE_SOLICITATION_16BIT = 0x14
    SERVICE_SOLICITATION_128BIT = 0x15
    SERVICE_DATA_16BIT = 0x16
    PUBLIC_TARGET_ADDRESS = 0x17
    RANDOM_TARGET_ADDRESS = 0x18
    APPEARANCE = 0x19
    ADVERTISING_INTERVAL = 0x1A
    LE_DEVICE_ADDRESS = 0x1B
    LE_ROLE = 0x1C
    SERVICE_DATA_32BIT = 0x20
    SERVICE_DATA_128BIT = 0x21
    URI = 0x24
    LE_SUPPORTED_FEATURES = 0x27
    MANUFACTURER_SPECIFIC_DATA = 0xFF


class AdFlags(IntEnum):
    """Bits of the Flags AD structure."""

    LE_LIMITED_DISCOVERABLE = 0x01
    LE_GENERAL_DISCOVERABLE = 0x02
    BR_EDR_NOT_SUPPORTED = 0x04
    LE_BR_EDR_CONTROLLER = 0x08
    LE_BR_EDR_HOST = 0x10


_FLAG_NAMES = {
    AdFlags.LE_LIMITED_DISCOVERABLE: "LE Limited Discoverable",
    AdFlags.LE_GENERAL_DISCOVERABLE: "LE General Discoverable",
    AdFlags.BR_EDR_NOT_SUPPORTED: "BR/EDR Not Supported",
    AdFlags.LE_BR_EDR_CONTROLLER: "LE+BR/EDR (Controller)",
    AdFlags.LE_BR_EDR_HOST: "LE+BR/EDR (Host)",
}


@dataclass
class AdStructure:
    """One raw AD structure."""

    type: int
    value: bytes

    @property
    def type_name(self) -> str:
        try:
            return AdType(self.type).name
        except ValueError:
            return f"UNKNOWN_0x{self.type:02X}"

    def __str__(self) -> str:
        return f"{self.type_name}={self.value.hex(' ')}"


@dataclass
class AdvertisingData:
    """Decoded view of an advertising payload."""

    structures: List[AdStructure] = field(default_factory=list)
    flags: Optional[int] = None
    local_name: Optional[str] = None
    name_is_complete: bool = False
    tx_power: Optional[int] = None
    appearance: Optional[int] = None
    service_uuids: List[str] = field(default_factory=list)
    service_data: Dict[str, bytes] = field(default_factory=dict)
    manufacturer_id: Optional[int] = None
    manufacturer_data: Optional[bytes] = None
    raw: bytes = b""

    # ------------------------------------------------------------- decoding

    @classmethod
    def parse(cls, data: bytes) -> "AdvertisingData":
        """
        Decode a payload. Never raises.

        Advertising payloads are attacker-controlled and routinely truncated by
        the controller, so a malformed structure just stops the walk -- whatever
        was decoded up to that point is still returned and still useful.
        """
        result = cls(raw=bytes(data))
        i = 0
        n = len(data)

        while i < n:
            length = data[i]
            if length == 0:
                break                      # padding: end of meaningful data
            if i + 1 + length > n:
                break                      # truncated structure
            ad_type = data[i + 1]
            value = bytes(data[i + 2:i + 1 + length])
            result.structures.append(AdStructure(ad_type, value))
            result._absorb(ad_type, value)
            i += 1 + length

        return result

    def _absorb(self, ad_type: int, value: bytes) -> None:
        try:
            if ad_type == AdType.FLAGS and value:
                self.flags = value[0]

            elif ad_type == AdType.COMPLETE_LOCAL_NAME:
                self.local_name = value.decode("utf-8", "replace").rstrip("\x00")
                self.name_is_complete = True

            elif ad_type == AdType.SHORTENED_LOCAL_NAME:
                if not self.name_is_complete:
                    self.local_name = value.decode("utf-8", "replace").rstrip("\x00")

            elif ad_type == AdType.TX_POWER_LEVEL and value:
                self.tx_power = struct.unpack("<b", value[:1])[0]

            elif ad_type == AdType.APPEARANCE and len(value) >= 2:
                self.appearance = struct.unpack("<H", value[:2])[0]

            elif ad_type in (AdType.INCOMPLETE_16BIT_UUIDS, AdType.COMPLETE_16BIT_UUIDS,
                             AdType.SERVICE_SOLICITATION_16BIT):
                for off in range(0, len(value) - 1, 2):
                    uuid = struct.unpack_from("<H", value, off)[0]
                    self.service_uuids.append(f"{uuid:04X}")

            elif ad_type in (AdType.INCOMPLETE_32BIT_UUIDS, AdType.COMPLETE_32BIT_UUIDS):
                for off in range(0, len(value) - 3, 4):
                    uuid = struct.unpack_from("<I", value, off)[0]
                    self.service_uuids.append(f"{uuid:08X}")

            elif ad_type in (AdType.INCOMPLETE_128BIT_UUIDS, AdType.COMPLETE_128BIT_UUIDS,
                             AdType.SERVICE_SOLICITATION_128BIT):
                for off in range(0, len(value) - 15, 16):
                    self.service_uuids.append(_uuid128_str(value[off:off + 16]))

            elif ad_type == AdType.SERVICE_DATA_16BIT and len(value) >= 2:
                uuid = struct.unpack_from("<H", value, 0)[0]
                self.service_data[f"{uuid:04X}"] = value[2:]

            elif ad_type == AdType.SERVICE_DATA_128BIT and len(value) >= 16:
                self.service_data[_uuid128_str(value[:16])] = value[16:]

            elif ad_type == AdType.MANUFACTURER_SPECIFIC_DATA and len(value) >= 2:
                self.manufacturer_id = struct.unpack_from("<H", value, 0)[0]
                self.manufacturer_data = value[2:]
        except Exception:
            # A single malformed structure must not lose the rest of the payload.
            pass

    # ------------------------------------------------------------ reporting

    def flags_text(self) -> str:
        if self.flags is None:
            return ""
        names = [text for bit, text in _FLAG_NAMES.items() if self.flags & bit]
        return ", ".join(names) or f"0x{self.flags:02X}"

    def summary(self) -> str:
        """Short human-readable line for a device list."""
        parts: List[str] = []
        if self.local_name:
            suffix = "" if self.name_is_complete else "…"
            parts.append(f"'{self.local_name}{suffix}'")
        if self.tx_power is not None:
            parts.append(f"TxPwr={self.tx_power}dBm")
        if self.service_uuids:
            shown = ", ".join(self.service_uuids[:3])
            more = f" +{len(self.service_uuids) - 3}" if len(self.service_uuids) > 3 else ""
            parts.append(f"UUIDs=[{shown}{more}]")
        if self.manufacturer_id is not None:
            parts.append(f"MfrID=0x{self.manufacturer_id:04X}")
        if self.flags is not None:
            parts.append(self.flags_text())
        return " ".join(parts) if parts else "(no decodable AD data)"

    def __str__(self) -> str:
        return self.summary()


def _uuid128_str(raw_le: bytes) -> str:
    """128-bit UUID stored little-endian -> canonical dashed string."""
    b = bytes(reversed(raw_le))
    return (f"{b[0:4].hex()}-{b[4:6].hex()}-{b[6:8].hex()}-"
            f"{b[8:10].hex()}-{b[10:16].hex()}").upper()


# ------------------------------------------------------------------ building

class AdvertisingDataBuilder:
    """
    Compose an advertising payload.

    The controller rejects `LE_Set_Advertising_Data` outright if the payload
    exceeds 31 bytes, so the builder enforces that as structures are added --
    failing at `add_name()` is far easier to diagnose than a Command Complete
    with "Invalid HCI Command Parameters" later.
    """

    MAX_PAYLOAD = 31

    def __init__(self, max_payload: int = MAX_PAYLOAD):
        self._structures: List[AdStructure] = []
        self._max = max_payload

    def add(self, ad_type: int, value: bytes) -> "AdvertisingDataBuilder":
        candidate = len(self.build()) + 2 + len(value)
        if candidate > self._max:
            raise ValueError(
                f"AD payload would be {candidate} bytes, limit is {self._max}; "
                f"cannot add {AdType(ad_type).name if ad_type in list(AdType) else hex(ad_type)}"
            )
        self._structures.append(AdStructure(ad_type, bytes(value)))
        return self

    def add_flags(self, flags: int = AdFlags.LE_GENERAL_DISCOVERABLE | AdFlags.BR_EDR_NOT_SUPPORTED):
        return self.add(AdType.FLAGS, bytes([flags]))

    def add_name(self, name: str, complete: bool = True):
        ad_type = AdType.COMPLETE_LOCAL_NAME if complete else AdType.SHORTENED_LOCAL_NAME
        return self.add(ad_type, name.encode("utf-8"))

    def add_tx_power(self, dbm: int):
        return self.add(AdType.TX_POWER_LEVEL, struct.pack("<b", dbm))

    def add_appearance(self, appearance: int):
        return self.add(AdType.APPEARANCE, struct.pack("<H", appearance))

    def add_service_uuids16(self, uuids: Sequence[int], complete: bool = True):
        payload = b"".join(struct.pack("<H", u) for u in uuids)
        ad_type = AdType.COMPLETE_16BIT_UUIDS if complete else AdType.INCOMPLETE_16BIT_UUIDS
        return self.add(ad_type, payload)

    def add_manufacturer_data(self, company_id: int, data: bytes):
        return self.add(AdType.MANUFACTURER_SPECIFIC_DATA,
                        struct.pack("<H", company_id) + bytes(data))

    def build(self) -> bytes:
        out = bytearray()
        for s in self._structures:
            out.append(len(s.value) + 1)
            out.append(s.type)
            out += s.value
        return bytes(out)

    def build_padded(self, size: int = 31) -> bytes:
        """Payload zero-padded to `size` -- the form the HCI command wants."""
        return self.build().ljust(size, b"\x00")

    def __len__(self) -> int:
        return len(self.build())


def parse_adv_data(data: bytes) -> AdvertisingData:
    """Convenience wrapper."""
    return AdvertisingData.parse(data)


__all__ = [
    "AdType",
    "AdFlags",
    "AdStructure",
    "AdvertisingData",
    "AdvertisingDataBuilder",
    "parse_adv_data",
]
