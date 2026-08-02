"""
BR/EDR page and scan configuration commands.

    0x0C16  Write_Connection_Accept_Timeout
    0x0C18  Write_Page_Timeout
    0x0C1C  Write_Page_Scan_Activity
    0x0C1E  Write_Inquiry_Scan_Activity
    0x0C43  Write_Inquiry_Scan_Type
    0x0C47  Write_Page_Scan_Type

These decide how findable and how connectable a BR/EDR device is, and how long
it keeps trying before giving up. `Write_Scan_Enable` (0x0C1A, in `poc_cmds`)
turns the two scans on; the commands here set how often and for how long each
one actually listens.

All the timing parameters are in 0.625 ms slots. The two that matter most:

* **Page timeout** is how long a paging attempt runs before Connection Complete
  comes back with Page Timeout (0x04). The default 0x2000 is 5.12 s.
* **Scan interval/window** is a duty cycle. A window equal to the interval means
  continuous scanning -- fastest to be found, worst for power and for any other
  radio activity sharing the antenna.
"""

from __future__ import annotations

import struct
from enum import IntEnum, unique
from typing import Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import ControllerBasebandOCF, OGF, create_opcode


@unique
class ScanType(IntEnum):
    """Scan type for the inquiry/page scan type commands."""

    STANDARD = 0x00     # mandatory, R1 timing
    INTERLACED = 0x01   # optional; roughly halves the time to be discovered


#: Handy activity presets, as (interval, window) in 0.625 ms slots.
SCAN_ACTIVITY_DEFAULT = (0x0800, 0x0012)      # 1.28 s / 11.25 ms -- the spec default
SCAN_ACTIVITY_FAST = (0x0200, 0x0100)         # 320 ms / 160 ms -- 50% duty cycle
SCAN_ACTIVITY_CONTINUOUS = (0x0012, 0x0012)   # window == interval


class _SlotTimeoutCommand(HciCmdBasePacket):
    """Shared body for the two commands that are a single 16-bit slot count."""

    PARAM_NAME = "timeout"
    MIN_VALUE = 0x0001
    MAX_VALUE = 0xFFFF

    def __init__(self, timeout: int = 0x2000):
        super().__init__(**{self.PARAM_NAME: timeout})

    def _validate_params(self) -> None:
        value = self.params[self.PARAM_NAME]
        if not (self.MIN_VALUE <= value <= self.MAX_VALUE):
            raise ValueError(
                f"{self.PARAM_NAME} 0x{value:04X} out of range "
                f"(0x{self.MIN_VALUE:04X}..0x{self.MAX_VALUE:04X})")

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params[self.PARAM_NAME])

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])

    def __str__(self) -> str:
        value = self.params[self.PARAM_NAME]
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"(0x{value:04X} = {value * 0.625:.2f} ms)")


class WriteConnectionAcceptTimeout(_SlotTimeoutCommand):
    """
    Write Connection Accept Timeout Command (0x0C16).

    How long the controller waits for the host to answer a Connection Request
    before rejecting it itself. Default 0x1FA0 (5 s).
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_CONNECTION_ACCEPT_TIMEOUT)
    NAME = "Write_Connection_Accept_Timeout"

    PARAM_NAME = "conn_accept_timeout"
    MIN_VALUE = 0x0001
    MAX_VALUE = 0xB540

    def __init__(self, conn_accept_timeout: int = 0x1FA0):
        super().__init__(conn_accept_timeout)


class WritePageTimeout(_SlotTimeoutCommand):
    """
    Write Page Timeout Command (0x0C18).

    How long a paging attempt runs before it fails. Default 0x2000 (5.12 s);
    0x0000 is not allowed, which is why the range starts at 1.
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_PAGE_TIMEOUT)
    NAME = "Write_Page_Timeout"

    PARAM_NAME = "page_timeout"

    def __init__(self, page_timeout: int = 0x2000):
        super().__init__(page_timeout)


class _ScanActivityCommand(HciCmdBasePacket):
    """Shared body for the page/inquiry scan activity commands."""

    INTERVAL_NAME = "scan_interval"
    WINDOW_NAME = "scan_window"

    MIN_INTERVAL = 0x0012      # 11.25 ms
    MAX_INTERVAL = 0x1000      # 2.56 s
    MIN_WINDOW = 0x0011        # 10.625 ms
    MAX_WINDOW = 0x1000

    def __init__(self, scan_interval: int = SCAN_ACTIVITY_DEFAULT[0],
                 scan_window: int = SCAN_ACTIVITY_DEFAULT[1]):
        super().__init__(**{self.INTERVAL_NAME: scan_interval,
                            self.WINDOW_NAME: scan_window})

    def _validate_params(self) -> None:
        interval = self.params[self.INTERVAL_NAME]
        window = self.params[self.WINDOW_NAME]
        if not (self.MIN_INTERVAL <= interval <= self.MAX_INTERVAL):
            raise ValueError(f"{self.INTERVAL_NAME} 0x{interval:04X} out of range "
                             f"(0x{self.MIN_INTERVAL:04X}..0x{self.MAX_INTERVAL:04X})")
        if not (self.MIN_WINDOW <= window <= self.MAX_WINDOW):
            raise ValueError(f"{self.WINDOW_NAME} 0x{window:04X} out of range "
                             f"(0x{self.MIN_WINDOW:04X}..0x{self.MAX_WINDOW:04X})")
        if window > interval:
            raise ValueError(f"{self.WINDOW_NAME} must be <= {self.INTERVAL_NAME}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HH", self.params[self.INTERVAL_NAME],
                           self.params[self.WINDOW_NAME])

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4")
        interval, window = struct.unpack_from("<HH", data, 0)
        return cls(interval, window)

    def __str__(self) -> str:
        interval = self.params[self.INTERVAL_NAME]
        window = self.params[self.WINDOW_NAME]
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"(interval {interval * 0.625:.2f} ms, window {window * 0.625:.2f} ms, "
                f"{window / interval * 100:.0f}% duty)")


class WritePageScanActivity(_ScanActivityCommand):
    """
    Write Page Scan Activity Command (0x0C1C).

    How often and how long the device listens for pages -- that is, how quickly
    it can be connected to. Requires page scan to be enabled in
    `Write_Scan_Enable`.
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_PAGE_SCAN_ACTIVITY)
    NAME = "Write_Page_Scan_Activity"

    INTERVAL_NAME = "page_scan_interval"
    WINDOW_NAME = "page_scan_window"

    def __init__(self, page_scan_interval: int = SCAN_ACTIVITY_DEFAULT[0],
                 page_scan_window: int = SCAN_ACTIVITY_DEFAULT[1]):
        super().__init__(page_scan_interval, page_scan_window)


class WriteInquiryScanActivity(_ScanActivityCommand):
    """
    Write Inquiry Scan Activity Command (0x0C1E).

    The discoverability equivalent of the above: how often and how long the
    device listens for inquiries.
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_INQUIRY_SCAN_ACTIVITY)
    NAME = "Write_Inquiry_Scan_Activity"

    INTERVAL_NAME = "inquiry_scan_interval"
    WINDOW_NAME = "inquiry_scan_window"

    def __init__(self, inquiry_scan_interval: int = SCAN_ACTIVITY_DEFAULT[0],
                 inquiry_scan_window: int = SCAN_ACTIVITY_DEFAULT[1]):
        super().__init__(inquiry_scan_interval, inquiry_scan_window)


class _ScanTypeCommand(HciCmdBasePacket):
    """Shared body for the two scan type commands: one enum byte."""

    PARAM_NAME = "scan_type"

    def __init__(self, scan_type: Union[int, ScanType] = ScanType.STANDARD):
        super().__init__(**{self.PARAM_NAME: int(scan_type)})

    def _validate_params(self) -> None:
        value = self.params[self.PARAM_NAME]
        if value not in (0x00, 0x01):
            raise ValueError(f"Invalid {self.PARAM_NAME}: 0x{value:02X}; expected "
                             "0x00 (standard) or 0x01 (interlaced)")

    def _serialize_params(self) -> bytes:
        return bytes([self.params[self.PARAM_NAME]])

    @classmethod
    def from_bytes(cls, data: bytes):
        if not data:
            raise ValueError(f"{cls.NAME}: empty parameters")
        return cls(data[0])

    def __str__(self) -> str:
        value = self.params[self.PARAM_NAME]
        return (f"{self.NAME} : 0x{self.OPCODE:04X} "
                f"({'interlaced' if value else 'standard'})")


class WritePageScanType(_ScanTypeCommand):
    """
    Write Page Scan Type Command (0x0C47).

    Interlaced page scan roughly halves how long a pager waits before the device
    answers, at the cost of listening more. Optional -- a controller that does
    not support it answers Unsupported Feature.
    """

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_PAGE_SCAN_TYPE)
    NAME = "Write_Page_Scan_Type"

    PARAM_NAME = "page_scan_type"

    def __init__(self, page_scan_type: Union[int, ScanType] = ScanType.STANDARD):
        super().__init__(page_scan_type)


class WriteInquiryScanType(_ScanTypeCommand):
    """Write Inquiry Scan Type Command (0x0C43)."""

    OPCODE = create_opcode(OGF.CONTROLLER_BASEBAND,
                           ControllerBasebandOCF.WRITE_INQUIRY_SCAN_TYPE)
    NAME = "Write_Inquiry_Scan_Type"

    PARAM_NAME = "inquiry_scan_type"

    def __init__(self, inquiry_scan_type: Union[int, ScanType] = ScanType.STANDARD):
        super().__init__(inquiry_scan_type)


# ------------------------------------------------------------ helper builders

def write_connection_accept_timeout(timeout: int = 0x1FA0):
    return WriteConnectionAcceptTimeout(timeout)


def write_page_timeout(timeout: int = 0x2000) -> WritePageTimeout:
    return WritePageTimeout(timeout)


def write_page_scan_activity(interval: int = SCAN_ACTIVITY_DEFAULT[0],
                             window: int = SCAN_ACTIVITY_DEFAULT[1]):
    return WritePageScanActivity(interval, window)


def write_inquiry_scan_activity(interval: int = SCAN_ACTIVITY_DEFAULT[0],
                                window: int = SCAN_ACTIVITY_DEFAULT[1]):
    return WriteInquiryScanActivity(interval, window)


def write_page_scan_type(scan_type: Union[int, ScanType] = ScanType.STANDARD):
    return WritePageScanType(scan_type)


def write_inquiry_scan_type(scan_type: Union[int, ScanType] = ScanType.STANDARD):
    return WriteInquiryScanType(scan_type)


for _cls in (WriteConnectionAcceptTimeout, WritePageTimeout,
             WritePageScanActivity, WriteInquiryScanActivity,
             WritePageScanType, WriteInquiryScanType):
    register_command(_cls)
del _cls


__all__ = [
    'ScanType',
    'SCAN_ACTIVITY_DEFAULT',
    'SCAN_ACTIVITY_FAST',
    'SCAN_ACTIVITY_CONTINUOUS',
    'WriteConnectionAcceptTimeout',
    'WritePageTimeout',
    'WritePageScanActivity',
    'WriteInquiryScanActivity',
    'WritePageScanType',
    'WriteInquiryScanType',
    'write_connection_accept_timeout',
    'write_page_timeout',
    'write_page_scan_activity',
    'write_inquiry_scan_activity',
    'write_page_scan_type',
    'write_inquiry_scan_type',
]
