"""
Event windows for extended advertising, periodic advertising and Channel
Sounding.

Same split as the legacy LE windows: anything that arrives in a flood
(extended reports, periodic reports, CS subevent results) aggregates into one
live table; the one-shot completions share a small event-log window each, so a
sync/terminate sequence reads as a sequence instead of scattering windows.
"""

from __future__ import annotations

import time

from PyQt5.QtWidgets import QLabel

from hci.evt.evt_codes import HciEventCode, LeMetaEventSubCode
from hci.evt.le.ext_events import phy_name

from .. import register_event_ui
from ..evt_baseui import AggregatingEvtUI, HCIEvtUI, addr_str


def _now() -> str:
    return time.strftime("%H:%M:%S")


def _addr_kind(address_type) -> str:
    return "random" if address_type in (0x01, 0x03) else "public"


@register_event_ui
class LeExtendedAdvertisingReportUI(AggregatingEvtUI):
    """Live extended scan results: one row per advertiser, updated in place."""

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.EXTENDED_ADVERTISING_REPORT),
    )
    WINDOW_KEY = "le_ext_adv_reports"
    NAME = "LE Extended Advertising Reports"
    AUTO_POPUP = True

    COLUMNS = ("Address", "Name", "RSSI", "Type", "SID", "PHY (pri/sec)",
               "Periodic", "TX Pwr", "Data")
    STRETCH_COLUMN = 1

    def rows_for(self, event):
        rows = []
        for report in event.params.get('reports', ()):
            adv = report.get('adv_data')
            interval = report.get('periodic_adv_interval') or 0
            rows.append((
                report.get('address_str') or addr_str(report.get('address')),
                getattr(adv, 'local_name', None) or "",
                "" if report.get('rssi') is None else f"{report['rssi']} dBm",
                report.get('event_type_str', ""),
                str(report.get('adv_sid', "")),
                f"{phy_name(report.get('primary_phy'))}/"
                f"{phy_name(report.get('secondary_phy'))}",
                f"{interval * 1.25:.1f} ms" if interval else "-",
                "-" if report.get('tx_power') is None else f"{report['tx_power']} dBm",
                bytes(report.get('data') or b'').hex(' '),
            ))
        return tuple(rows)


@register_event_ui
class LePeriodicAdvertisingUI(AggregatingEvtUI):
    """
    Periodic advertising: sync lifecycle plus the report stream.

    Rows are keyed by sync handle, so an established sync gets one row that then
    updates with each report rather than growing without bound.
    """

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT,
         LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_ESTABLISHED),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.PERIODIC_ADVERTISING_REPORT),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_LOST),
    )
    WINDOW_KEY = "le_periodic_adv"
    NAME = "LE Periodic Advertising"
    AUTO_POPUP = True

    COLUMNS = ("Sync", "State", "Advertiser", "SID", "PHY", "Interval",
               "RSSI", "Last data")
    STRETCH_COLUMN = 7

    def rows_for(self, event):
        params = event.params
        sub = getattr(event, 'SUB_EVENT_CODE', None)
        handle = params.get('sync_handle', 0)
        key = f"0x{handle:04X}"

        if sub == LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_ESTABLISHED:
            status = params.get('status', 0xFF)
            interval = params.get('periodic_adv_interval') or 0
            return ((
                key,
                "synced" if status == 0x00 else f"failed 0x{status:02X}",
                params.get('advertiser_address_str', ""),
                str(params.get('adv_sid', "")),
                phy_name(params.get('advertiser_phy')),
                f"{interval * 1.25:.1f} ms" if interval else "-",
                "", "",
            ),)

        if sub == LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_LOST:
            # Keep the row so the advertiser stays visible after the loss;
            # only the state and the live columns change.
            return ((key, "lost", "", "", "", "", "", ""),)

        adv = params.get('adv_data')
        rssi = params.get('rssi')
        return ((
            key,
            "receiving",
            "", "", "", "",
            "" if rssi is None else f"{rssi} dBm",
            getattr(adv, 'summary', lambda: "")() or
            bytes(params.get('data') or b'').hex(' '),
        ),)

    def _upsert(self, cells) -> None:
        # A report carries no advertiser/SID/PHY -- blanking those columns on
        # every report would erase what the sync-established row put there.
        key = cells[self.KEY_COLUMN]
        existing = self._rows.get(key)
        if existing is not None:
            for column, text in enumerate(cells):
                item = self.table.item(existing, column)
                if not text and item is not None and item.text():
                    cells[column] = item.text()
        super()._upsert(cells)


@register_event_ui
class LeAdvertisingSetEventsUI(AggregatingEvtUI):
    """Advertising-set lifecycle: terminations, scan requests, scan timeouts."""

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.ADVERTISING_SET_TERMINATED),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.SCAN_REQUEST_RECEIVED),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.SCAN_TIMEOUT),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CHANNEL_SELECTION_ALGORITHM),
    )
    WINDOW_KEY = "le_adv_set_events"
    NAME = "LE Advertising Set Events"
    AUTO_POPUP = True

    # Keyed by time so every occurrence is a new row: these are one-off
    # notifications, and collapsing them would hide a repeat.
    COLUMNS = ("Time", "Event", "Detail")
    STRETCH_COLUMN = 2

    def rows_for(self, event):
        params = event.params
        sub = getattr(event, 'SUB_EVENT_CODE', None)
        stamp = f"{_now()}.{self.event_count:04d}"

        if sub == LeMetaEventSubCode.ADVERTISING_SET_TERMINATED:
            status = params.get('status', 0xFF)
            if status == 0x00:
                detail = (f"set {params.get('adv_handle')} -> connection "
                          f"0x{params.get('connection_handle', 0):04X}")
            else:
                detail = (f"set {params.get('adv_handle')} stopped "
                          f"(0x{status:02X}) after "
                          f"{params.get('num_completed_ext_adv_events')} events")
            return ((stamp, "Set Terminated", detail),)

        if sub == LeMetaEventSubCode.SCAN_REQUEST_RECEIVED:
            return ((stamp, "Scan Request",
                     f"set {params.get('adv_handle')} scanned by "
                     f"{params.get('scanner_address_str', '')} "
                     f"({_addr_kind(params.get('scanner_address_type'))})"),)

        if sub == LeMetaEventSubCode.SCAN_TIMEOUT:
            return ((stamp, "Scan Timeout", "extended scan duration elapsed"),)

        return ((stamp, "Channel Selection",
                 f"handle 0x{params.get('connection_handle', 0):04X} uses "
                 f"algorithm #{params.get('channel_selection_algorithm', 0) + 1}"),)


@register_event_ui
class LeChannelSoundingUI(AggregatingEvtUI):
    """
    Channel Sounding: setup completions and the measurement stream.

    Subevent results are the volume here -- one row per procedure counter, so a
    running procedure updates a single row while each new procedure appends.
    """

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT,
         LeMetaEventSubCode.CS_READ_REMOTE_SUPPORTED_CAPABILITIES_COMPLETE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_READ_REMOTE_FAE_TABLE_COMPLETE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_SECURITY_ENABLE_COMPLETE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_CONFIG_COMPLETE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_PROCEDURE_ENABLE_COMPLETE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_SUBEVENT_RESULT),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_SUBEVENT_RESULT_CONTINUE),
        (HciEventCode.LE_META_EVENT, LeMetaEventSubCode.CS_TEST_END_COMPLETE),
    )
    WINDOW_KEY = "le_channel_sounding"
    NAME = "LE Channel Sounding"
    AUTO_POPUP = True

    COLUMNS = ("Key", "Stage", "Handle", "Config", "Steps", "Ref Power", "Status")
    STRETCH_COLUMN = 6

    def build_content(self):
        super().build_content()
        self.summary_label = QLabel("no procedure running")
        self.summary_label.setStyleSheet("color: gray;")
        self.content_layout.addWidget(self.summary_label)
        self._steps_seen = 0

    def rows_for(self, event):
        params = event.params
        sub = getattr(event, 'SUB_EVENT_CODE', None)
        handle = params.get('connection_handle')
        handle_str = "-" if handle is None else f"0x{handle:04X}"
        config = params.get('config_id')
        config_str = "-" if config is None else str(config)
        status = params.get('status')

        if sub in (LeMetaEventSubCode.CS_SUBEVENT_RESULT,
                   LeMetaEventSubCode.CS_SUBEVENT_RESULT_CONTINUE):
            steps = getattr(event, 'steps', [])
            self._steps_seen += len(steps)
            counter = params.get('procedure_counter')
            if counter is None:
                # A Continue event does not repeat the procedure counter;
                # attach it to the row the matching result opened.
                counter = self._last_counter
            else:
                self._last_counter = counter
            ref_power = params.get('reference_power_level')
            self.summary_label.setText(
                f"procedure #{counter}: {self._steps_seen} steps, "
                f"{params.get('num_antenna_paths', '?')} antenna path(s)")
            return ((
                f"{handle_str}/{config_str}/proc {counter}",
                "Subevent Result",
                handle_str,
                config_str,
                str(params.get('num_steps_reported', len(steps))),
                "-" if ref_power is None else f"{ref_power} dBm",
                f"procedure {self._done(params.get('procedure_done_status'))}, "
                f"subevent {self._done(params.get('subevent_done_status'))}",
            ),)

        stage = {
            LeMetaEventSubCode.CS_READ_REMOTE_SUPPORTED_CAPABILITIES_COMPLETE:
                "Remote Capabilities",
            LeMetaEventSubCode.CS_READ_REMOTE_FAE_TABLE_COMPLETE: "Remote FAE Table",
            LeMetaEventSubCode.CS_SECURITY_ENABLE_COMPLETE: "Security Enable",
            LeMetaEventSubCode.CS_CONFIG_COMPLETE: "Config",
            LeMetaEventSubCode.CS_PROCEDURE_ENABLE_COMPLETE: "Procedure Enable",
            LeMetaEventSubCode.CS_TEST_END_COMPLETE: "Test End",
        }.get(sub, f"0x{sub:02X}" if sub is not None else "?")

        if status in (None, 0x00):
            detail = "ok"
            if sub == LeMetaEventSubCode.CS_CONFIG_COMPLETE:
                detail = "created" if params.get('action') else "removed"
            elif sub == LeMetaEventSubCode.CS_PROCEDURE_ENABLE_COMPLETE:
                detail = "enabled" if params.get('state') else "disabled"
                self._steps_seen = 0
        else:
            detail = f"failed 0x{status:02X}"

        return ((f"{handle_str}/{config_str}/{stage}", stage, handle_str,
                 config_str, "-", "-", detail),)

    _last_counter = 0

    @staticmethod
    def _done(value) -> str:
        return {0x00: "complete", 0x01: "partial",
                0x0F: "aborted"}.get(value, f"0x{value:02X}" if value is not None else "?")


@register_event_ui
class LePeriodicSyncTransferUI(HCIEvtUI):
    """Periodic advertising sync transfer received -- shown on its own."""

    EVENT_KEYS = (
        (HciEventCode.LE_META_EVENT,
         LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_TRANSFER_RECEIVED),
    )
    WINDOW_KEY = "le_past_received"
    NAME = "LE Periodic Sync Transfer Received"
    AUTO_POPUP = False


__all__ = [
    "LeExtendedAdvertisingReportUI",
    "LePeriodicAdvertisingUI",
    "LeAdvertisingSetEventsUI",
    "LeChannelSoundingUI",
    "LePeriodicSyncTransferUI",
]
