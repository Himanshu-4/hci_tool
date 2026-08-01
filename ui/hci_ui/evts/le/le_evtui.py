"""
Event windows for LE meta events.

Advertising reports are the reason `AggregatingEvtUI` exists: an active scan
produces tens of reports per second for the same handful of devices, and one
window per report would be unusable. They all land in a single live table.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel

from hci.evt.evt_codes import HciEventCode, LeMetaEventSubCode

from ..evt_baseui import AggregatingEvtUI, GenericEventUI, HCIEvtUI, addr_str
from .. import register_event_ui


_ADV_TYPES = {
    0x00: "ADV_IND",
    0x01: "ADV_DIRECT_IND",
    0x02: "ADV_SCAN_IND",
    0x03: "ADV_NONCONN_IND",
    0x04: "SCAN_RSP",
}


def _addr_kind(address_type) -> str:
    return "random" if address_type in (0x01, 0x03) else "public"


def _status_text(status: int) -> str:
    return "Success" if status == 0x00 else f"Error 0x{status:02X}"


@register_event_ui
class LeAdvertisingReportUI(AggregatingEvtUI):
    """Live scan results: one row per advertiser, updated in place."""

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.ADVERTISING_REPORT),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.DIRECTED_ADVERTISING_REPORT),
    )
    WINDOW_KEY = "le_adv_reports"
    NAME = "LE Advertising Reports"
    AUTO_POPUP = True

    COLUMNS = ("Address", "Name", "RSSI", "Type", "Addr Type", "Data")
    STRETCH_COLUMN = 1

    def rows_for(self, event):
        rows = []
        for report in event.params.get('reports', ()):
            adv = report.get('adv_data')
            name = getattr(adv, 'local_name', None) or ""
            payload = report.get('data') or b''
            rows.append((
                report.get('address_str') or addr_str(report.get('address')),
                name,
                f"{report['rssi']} dBm" if report.get('rssi') is not None else "",
                _ADV_TYPES.get(report.get('event_type'), f"0x{report.get('event_type', 0):02X}"),
                _addr_kind(report.get('address_type')),
                bytes(payload).hex(' '),
            ))
        return tuple(rows)


@register_event_ui
class LeConnectionCompleteUI(HCIEvtUI):
    """An LE link came up (or the attempt failed)."""

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CONNECTION_COMPLETE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.ENHANCED_CONNECTION_COMPLETE),
    )
    WINDOW_KEY = "le_connection_complete"
    NAME = "LE Connection Complete"
    AUTO_POPUP = True

    def build_content(self):
        self.status_label = QLabel("-")
        self.handle_label = QLabel("-")
        self.peer_label = QLabel("-")
        self.role_label = QLabel("-")
        self.interval_label = QLabel("-")
        self.timeout_label = QLabel("-")
        self.form_layout.addRow("Status:", self.status_label)
        self.form_layout.addRow("Connection Handle:", self.handle_label)
        self.form_layout.addRow("Peer:", self.peer_label)
        self.form_layout.addRow("Role:", self.role_label)
        self.form_layout.addRow("Interval:", self.interval_label)
        self.form_layout.addRow("Supervision Timeout:", self.timeout_label)

    def render(self, event):
        params = event.params
        status = params.get('status', 0xFF)
        self.status_label.setText(_status_text(status))
        self.status_label.setStyleSheet(
            "color: #2e7d32;" if status == 0 else "color: #c62828;")

        handle = params.get('connection_handle')
        self.handle_label.setText("-" if handle is None else f"0x{handle:04X}")

        peer = params.get('peer_address_str') or addr_str(params.get('peer_address'))
        self.peer_label.setText(
            f"{peer} ({_addr_kind(params.get('peer_address_type'))})")

        self.role_label.setText(
            "central" if params.get('role') == 0 else "peripheral")

        interval = params.get('conn_interval')
        self.interval_label.setText(
            "-" if interval is None else f"{interval * 1.25:.2f} ms")

        timeout = params.get('supervision_timeout')
        self.timeout_label.setText(
            "-" if timeout is None else f"{timeout * 10} ms")


@register_event_ui
class LeMetaEventUI(GenericEventUI):
    """
    Fallback for LE meta events without a window of their own.

    Registered on (0x3E, None), which `get_event_ui_class` falls back to, so a
    PHY update or data length change is still inspectable rather than invisible.
    """

    EVENT_KEYS = ((HciEventCode.LE_META_EVENT, None),)
    WINDOW_KEY = "le_meta_other"
    NAME = "LE Meta Event"
    AUTO_POPUP = False


__all__ = [
    "LeAdvertisingReportUI",
    "LeConnectionCompleteUI",
    "LeMetaEventUI",
]
