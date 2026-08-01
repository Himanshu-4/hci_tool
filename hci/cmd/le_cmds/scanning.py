"""
LE scanning helpers.

The scan commands themselves (`LE_Set_Scan_Parameters` 0x200B and
`LE_Set_Scan_Enable` 0x200C) are defined in `controller_config.py`; this module
re-exports them under scan-oriented names and adds the enums that make call
sites readable.
"""

from __future__ import annotations

from enum import IntEnum, unique

from .controller_config import LeSetScanEnable, LeSetScanParameters


@unique
class ScanType(IntEnum):
    """LE scan type."""

    PASSIVE = 0x00   # listen only; no SCAN_REQ, so no scan responses
    ACTIVE = 0x01    # send SCAN_REQ to collect scan response data


@unique
class ScanFilterPolicy(IntEnum):
    """Which advertisers the controller reports."""

    ACCEPT_ALL = 0x00
    FILTER_ACCEPT_LIST_ONLY = 0x01
    ACCEPT_ALL_PLUS_DIRECTED_RPA = 0x02
    FILTER_ACCEPT_LIST_PLUS_DIRECTED_RPA = 0x03


# Handy interval/window presets, in 0.625 ms units.
SCAN_INTERVAL_FAST = 0x0060   # 60 ms
SCAN_WINDOW_FAST = 0x0030     # 30 ms  (50% duty cycle)
SCAN_INTERVAL_SLOW = 0x0800   # 1.28 s
SCAN_WINDOW_SLOW = 0x0012     # 11.25 ms


def le_set_scan_parameters(scan_type: int = ScanType.ACTIVE,
                           scan_interval: int = SCAN_INTERVAL_FAST,
                           scan_window: int = SCAN_WINDOW_FAST,
                           own_addr_type: int = 0x00,
                           filter_policy: int = ScanFilterPolicy.ACCEPT_ALL
                           ) -> LeSetScanParameters:
    """Build LE_Set_Scan_Parameters. Must be sent while scanning is disabled."""
    return LeSetScanParameters(
        scan_type=int(scan_type),
        scan_interval=scan_interval,
        scan_window=scan_window,
        own_addr_type=own_addr_type,
        scanning_filter_policy=int(filter_policy),
    )


def le_set_scan_enable(enable: bool = True,
                       filter_duplicates: bool = True) -> LeSetScanEnable:
    """
    Build LE_Set_Scan_Enable.

    `filter_duplicates` makes the controller suppress repeat reports from the
    same advertiser, which keeps a scan list readable. Turn it off when you want
    to watch RSSI change over time.
    """
    return LeSetScanEnable(scan_enable=bool(enable),
                           filter_duplicates=bool(filter_duplicates))


__all__ = [
    'ScanType',
    'ScanFilterPolicy',
    'LeSetScanParameters',
    'LeSetScanEnable',
    'le_set_scan_parameters',
    'le_set_scan_enable',
    'SCAN_INTERVAL_FAST',
    'SCAN_WINDOW_FAST',
    'SCAN_INTERVAL_SLOW',
    'SCAN_WINDOW_SLOW',
]
