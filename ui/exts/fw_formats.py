"""
Firmware image formats and vendor download profiles.

Firmware download is not standardised: every silicon vendor invented its own
opcodes and its own container. What they have in common is the shape -- a
sequence of vendor HCI commands, each of which must complete before the next is
sent -- so this module turns each container into a common `FwCommand` list and
lets the screen drive them all the same way.

Formats parsed here:

* **.hcd** (Broadcom / Cypress) -- a bare sequence of HCI commands with no
  framing at all: opcode, length, parameters, repeated to end of file. Usually
  Download_Minidriver, then a run of Write_RAM, then Launch_RAM.
* **.bts** (TI CC256x service packs) -- a 32-byte header then typed actions,
  which is richer: as well as commands it carries delays and *baud rate
  changes*, and a parser that ignores those will desynchronise partway through.
* **Text HCI script** -- one hex command per line, for hand-written sequences.
* **Raw binary** -- a ROM or NVM image, chunked into vendor write commands
  against a base address.

The vendor profiles below describe the write/launch opcodes for the families
whose protocols are publicly documented. Anything else is served by
`GENERIC_PROFILE`, where the opcodes are set by hand -- which is honest about
the fact that this tool cannot know a proprietary loader it has never seen.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class FwCommand:
    """
    One step of a download sequence.

    Most steps are a command to send, but `.bts` files also carry delays and
    baud changes, so a step may instead be one of those -- hence the `kind`.
    """

    kind: str = "command"          # command | delay | baud | remark
    opcode: int = 0
    payload: bytes = b''
    delay_ms: int = 0
    baudrate: int = 0
    flow_control: bool = False
    text: str = ""

    def to_bytes(self) -> bytes:
        """The H4 command packet for this step."""
        if self.kind != "command":
            return b''
        if len(self.payload) > 0xFF:
            raise ValueError(f"command 0x{self.opcode:04X} has "
                             f"{len(self.payload)} parameter bytes; the HCI "
                             "length field is one byte")
        return struct.pack("<BHB", 0x01, self.opcode,
                           len(self.payload)) + self.payload

    def describe(self) -> str:
        if self.kind == "delay":
            return f"delay {self.delay_ms} ms"
        if self.kind == "baud":
            return (f"switch to {self.baudrate} baud"
                    f"{' with RTS/CTS' if self.flow_control else ''}")
        if self.kind == "remark":
            return f"# {self.text}"
        return (f"0x{self.opcode:04X}  {len(self.payload)} bytes"
                + (f"  {self.text}" if self.text else ""))


@dataclass
class FwImage:
    """A parsed firmware file, ready to download."""

    name: str = ""
    format: str = ""
    commands: List[FwCommand] = field(default_factory=list)
    source_size: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def command_count(self) -> int:
        return sum(1 for c in self.commands if c.kind == "command")

    @property
    def payload_bytes(self) -> int:
        return sum(len(c.payload) for c in self.commands if c.kind == "command")

    def summary(self) -> str:
        parts = [f"{self.format}", f"{self.command_count} commands",
                 f"{self.payload_bytes} payload bytes",
                 f"{self.source_size} bytes on disk"]
        extras = [c for c in self.commands if c.kind in ("delay", "baud")]
        if extras:
            parts.append(f"{len(extras)} timing/baud steps")
        return ", ".join(parts)


# ------------------------------------------------------------------- parsers

def parse_hcd(data: bytes, name: str = "") -> FwImage:
    """
    Broadcom / Cypress `.hcd`: back-to-back HCI commands, no framing.

    A truncated final record is reported rather than silently dropped -- a
    half-written patch file will brick a download in a way that is very hard to
    diagnose from the controller's side.
    """
    commands: List[FwCommand] = []
    offset = 0
    while offset + 3 <= len(data):
        opcode, length = struct.unpack_from("<HB", data, offset)
        offset += 3
        if offset + length > len(data):
            raise ValueError(
                f"truncated .hcd: command 0x{opcode:04X} at offset "
                f"{offset - 3} claims {length} bytes but only "
                f"{len(data) - offset} remain")
        payload = data[offset:offset + length]
        offset += length
        commands.append(FwCommand(opcode=opcode, payload=payload,
                                  text=_hcd_hint(opcode, payload)))

    if offset != len(data):
        raise ValueError(f"trailing {len(data) - offset} bytes after the last "
                         "complete command")
    if not commands:
        raise ValueError("no commands found -- is this really a .hcd file?")

    image = FwImage(name=name, format="Broadcom/Cypress HCD",
                    commands=commands, source_size=len(data))
    if commands[0].opcode != 0xFC2E:
        image.notes.append(
            "does not start with Download_Minidriver (0xFC2E); most .hcd "
            "patches do, and the controller may reject the writes without it")
    if not any(c.opcode == 0xFC4E for c in commands):
        image.notes.append(
            "contains no Launch_RAM (0xFC4E); the patch will be written but "
            "never started")
    return image


def _hcd_hint(opcode: int, payload: bytes) -> str:
    """Name the well-known Broadcom loader opcodes, with their target address."""
    if opcode == 0xFC2E:
        return "Download_Minidriver"
    if opcode == 0xFC4C and len(payload) >= 4:
        return f"Write_RAM @ 0x{struct.unpack_from('<I', payload, 0)[0]:08X}"
    if opcode == 0xFC4E and len(payload) >= 4:
        return f"Launch_RAM @ 0x{struct.unpack_from('<I', payload, 0)[0]:08X}"
    if opcode == 0xFC4F and len(payload) >= 4:
        return f"Read_RAM @ 0x{struct.unpack_from('<I', payload, 0)[0]:08X}"
    if opcode == 0x0C03:
        return "HCI Reset"
    return ""


#: `.bts` action identifiers.
BTS_ACTION_SEND_COMMAND = 1
BTS_ACTION_WAIT_EVENT = 2
BTS_ACTION_SERIAL_PORT_PARAMETERS = 3
BTS_ACTION_DELAY = 6
BTS_ACTION_RUN_SCRIPT = 7
BTS_ACTION_REMARKS = 10


def parse_bts(data: bytes, name: str = "") -> FwImage:
    """
    TI CC256x `.bts` service pack.

    32-byte header ("BTSB" + version + reserved), then typed actions. The baud
    and delay actions are kept: a service pack that switches the UART to 3 Mbaud
    halfway through is normal, and dropping that step leaves the rest of the
    download talking at the wrong rate.
    """
    if len(data) < 32 or data[:4] != b"BTSB":
        raise ValueError("not a .bts file: expected the 'BTSB' magic")

    version = struct.unpack_from("<I", data, 4)[0]
    commands: List[FwCommand] = []
    offset = 32

    while offset + 4 <= len(data):
        action, size = struct.unpack_from("<HH", data, offset)
        offset += 4
        if offset + size > len(data):
            raise ValueError(f"truncated .bts: action {action} at offset "
                             f"{offset - 4} claims {size} bytes")
        body = data[offset:offset + size]
        offset += size

        if action == BTS_ACTION_SEND_COMMAND:
            # The action body is a full H4 command packet, type byte included.
            if len(body) < 4 or body[0] != 0x01:
                raise ValueError(f"malformed Send Command action at offset "
                                 f"{offset - size - 4}")
            opcode, length = struct.unpack_from("<HB", body, 1)
            payload = body[4:4 + length]
            commands.append(FwCommand(opcode=opcode, payload=payload))

        elif action == BTS_ACTION_DELAY and size >= 4:
            commands.append(FwCommand(
                kind="delay",
                delay_ms=struct.unpack_from("<I", body, 0)[0]))

        elif action == BTS_ACTION_SERIAL_PORT_PARAMETERS and size >= 4:
            baud = struct.unpack_from("<I", body, 0)[0]
            flow = bool(struct.unpack_from("<I", body, 4)[0]) if size >= 8 else False
            commands.append(FwCommand(kind="baud", baudrate=baud,
                                      flow_control=flow))

        elif action == BTS_ACTION_REMARKS:
            commands.append(FwCommand(
                kind="remark",
                text=body.split(b"\x00", 1)[0].decode("ascii", "replace")))

        # Wait Event and Run Script are skipped deliberately: this downloader
        # already waits for each command's completion, and nested scripts would
        # need the containing directory, which a single-file picker does not
        # give us.

    if not any(c.kind == "command" for c in commands):
        raise ValueError("no Send Command actions found in the .bts file")

    image = FwImage(name=name, format=f"TI BTS (version {version})",
                    commands=commands, source_size=len(data))
    baud_steps = [c for c in commands if c.kind == "baud"]
    if baud_steps:
        image.notes.append(
            f"changes the UART baud {len(baud_steps)} time(s) -- the transport "
            "is reconfigured mid-download, so do not touch the port while it runs")
    return image


def parse_hci_script(text: str, name: str = "") -> FwImage:
    """
    A text script: one hex HCI command per line.

    Accepts an optional `01` H4 type byte, `#` or `//` comments, and any
    separator. Written for hand-made bring-up sequences.
    """
    commands: List[FwCommand] = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = re.split(r"#|//", line, maxsplit=1)[0].strip()
        if not line:
            continue
        clean = re.sub(r"[^0-9A-Fa-f]", "", line)
        if len(clean) % 2:
            raise ValueError(f"line {number}: odd number of hex digits")
        raw = bytes.fromhex(clean)
        if raw and raw[0] == 0x01:
            raw = raw[1:]
        if len(raw) < 3:
            raise ValueError(f"line {number}: a command needs at least an "
                             "opcode and a length byte")
        opcode, length = struct.unpack_from("<HB", raw, 0)
        payload = raw[3:3 + length]
        if len(payload) != length:
            raise ValueError(f"line {number}: length byte says {length} but "
                             f"{len(payload)} parameter bytes follow")
        commands.append(FwCommand(opcode=opcode, payload=payload))

    if not commands:
        raise ValueError("the script contains no commands")
    return FwImage(name=name, format="HCI script", commands=commands,
                   source_size=len(text))


# --------------------------------------------------------------- raw images

def chunk_image(data: bytes, base_address: int, opcode: int,
                chunk_size: int = 240, address_bytes: int = 4,
                little_endian: bool = True) -> List[FwCommand]:
    """
    Split a raw binary into vendor write commands.

    Each command is `address || chunk`. The chunk size is capped so the address
    field plus the payload still fits the one-byte HCI length -- exceeding it is
    the usual reason a hand-rolled loader works for small images and fails for
    large ones.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    max_chunk = 0xFF - address_bytes
    if chunk_size > max_chunk:
        raise ValueError(f"chunk_size {chunk_size} leaves no room for the "
                         f"{address_bytes}-byte address in a 255-byte command; "
                         f"use {max_chunk} or less")

    order = "little" if little_endian else "big"
    commands = []
    for offset in range(0, len(data), chunk_size):
        chunk = data[offset:offset + chunk_size]
        address = base_address + offset
        commands.append(FwCommand(
            opcode=opcode,
            payload=address.to_bytes(address_bytes, order) + chunk,
            text=f"@ 0x{address:0{address_bytes * 2}X}"))
    return commands


def parse_raw_image(data: bytes, name: str, base_address: int, opcode: int,
                    chunk_size: int = 240, address_bytes: int = 4) -> FwImage:
    """A raw ROM/NVM binary as a sequence of write commands."""
    if not data:
        raise ValueError("the image file is empty")
    commands = chunk_image(data, base_address, opcode, chunk_size, address_bytes)
    return FwImage(name=name, format="Raw image", commands=commands,
                   source_size=len(data))


# ---------------------------------------------------------- vendor profiles

@dataclass
class VendorProfile:
    """
    How one silicon family expects a download to be driven.

    `launch_opcode` of 0 means the profile has no separate launch step -- the
    image starts running when the last write completes.
    """

    name: str
    write_opcode: int = 0x0000
    launch_opcode: int = 0x0000
    prepare_opcode: int = 0x0000
    address_bytes: int = 4
    chunk_size: int = 240
    nvm_read_opcode: int = 0x0000
    nvm_write_opcode: int = 0x0000
    patch_formats: tuple = ("hcd", "bts", "script")
    notes: str = ""

    def prepare_command(self) -> Optional[FwCommand]:
        if not self.prepare_opcode:
            return None
        return FwCommand(opcode=self.prepare_opcode,
                         text=f"prepare loader (0x{self.prepare_opcode:04X})")

    def launch_command(self, address: int) -> Optional[FwCommand]:
        if not self.launch_opcode:
            return None
        return FwCommand(
            opcode=self.launch_opcode,
            payload=address.to_bytes(self.address_bytes, "little"),
            text=f"launch @ 0x{address:08X}")


#: Broadcom / Cypress: Download_Minidriver, Write_RAM, Launch_RAM.
BROADCOM_PROFILE = VendorProfile(
    name="Broadcom / Cypress",
    write_opcode=0xFC4C, launch_opcode=0xFC4E, prepare_opcode=0xFC2E,
    address_bytes=4, chunk_size=240,
    patch_formats=("hcd", "script"),
    notes="Download_Minidriver first, then Write_RAM chunks, then Launch_RAM. "
          "The controller usually needs a settling delay after the minidriver.")

#: TI CC256x: the service pack is a script, so there is no separate write opcode.
TI_PROFILE = VendorProfile(
    name="TI CC256x",
    write_opcode=0x0000, launch_opcode=0x0000,
    patch_formats=("bts", "script"),
    notes="Service packs are .bts scripts that carry their own commands, "
          "delays and baud changes; there is nothing to configure here.")

#: Anything else: the opcodes are entered by hand.
GENERIC_PROFILE = VendorProfile(
    name="Generic / custom",
    write_opcode=0xFC4C, launch_opcode=0xFC4E,
    patch_formats=("hcd", "bts", "script"),
    notes="Set the write and launch opcodes to match the controller's loader. "
          "This tool cannot know a proprietary protocol it has not been told.")

PROFILES: Dict[str, VendorProfile] = {
    profile.name: profile
    for profile in (BROADCOM_PROFILE, TI_PROFILE, GENERIC_PROFILE)
}


# -------------------------------------------------------------- NVM helpers

def nvm_write_command(opcode: int, item_id: int, data: bytes,
                      id_bytes: int = 2, with_length: bool = True) -> FwCommand:
    """
    A vendor NV write: item id, optional length, then the value.

    `id_bytes` and `with_length` are settings rather than constants because
    vendors disagree: TI's NV items are a 2-byte id plus a length byte, while
    several others use a 1-byte id and infer the length from the command.
    """
    if len(data) > 0xFF - id_bytes - (1 if with_length else 0):
        raise ValueError(f"NV value is {len(data)} bytes; too long for a single "
                         "command with this id/length layout")
    payload = item_id.to_bytes(id_bytes, "little")
    if with_length:
        payload += bytes([len(data)])
    return FwCommand(opcode=opcode, payload=payload + bytes(data),
                     text=f"NV write item 0x{item_id:04X}, {len(data)} bytes")


def nvm_read_command(opcode: int, item_id: int, length: int = 0,
                     id_bytes: int = 2, with_length: bool = True) -> FwCommand:
    """A vendor NV read: item id, and the length to read when the vendor wants it."""
    payload = item_id.to_bytes(id_bytes, "little")
    if with_length:
        payload += bytes([length & 0xFF])
    return FwCommand(opcode=opcode, payload=payload,
                     text=f"NV read item 0x{item_id:04X}")


def detect_format(name: str, data: bytes) -> str:
    """Guess a file's format from its magic, falling back to the extension."""
    if data[:4] == b"BTSB":
        return "bts"
    lowered = name.lower()
    if lowered.endswith(".hcd"):
        return "hcd"
    if lowered.endswith(".bts"):
        return "bts"
    if lowered.endswith((".txt", ".script", ".hci")):
        return "script"
    if lowered.endswith((".bin", ".rom", ".img", ".nvm")):
        return "raw"
    # A .hcd has no magic, so fall back to shape: a plausible first record.
    if len(data) >= 3:
        _, length = struct.unpack_from("<HB", data, 0)
        if 3 + length <= len(data):
            return "hcd"
    return "raw"


__all__ = [
    "FwCommand", "FwImage", "VendorProfile",
    "parse_hcd", "parse_bts", "parse_hci_script", "parse_raw_image",
    "chunk_image", "nvm_read_command", "nvm_write_command", "detect_format",
    "BROADCOM_PROFILE", "TI_PROFILE", "GENERIC_PROFILE", "PROFILES",
]
