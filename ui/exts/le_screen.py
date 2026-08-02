"""
LE Control -- one screen for the whole LE surface.

Advertising, scanning, connection and Channel Sounding, each with the legacy and
the extended/periodic form side by side, driven against an open HCI session.

Why a screen rather than the per-command dialogs: a working LE flow is never one
command. Extended advertising alone is "set parameters, set data, enable"; a
periodic train adds two more; Channel Sounding needs six commands in a fixed
order. The dialogs stay available for poking single opcodes -- this is for
getting something on the air.

Like Quick Connect it owns no transport: it attaches to an `HciMainUI` window's
`HciSession`, so connections and command credits are shared with the rest of the
tool.

Threading: `HciSession` fires completions on the transport I/O thread. Nothing
here touches a widget from there -- everything crosses `_result` / `_report` /
`_connections_changed`, which are queued to the Qt thread.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMdiSubWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import hci.cmd.le_cmds as le_cmds
from hci.evt.evt_codes import HciEventCode, LeMetaEventSubCode
from hci.evt.le.adv_data import AdvertisingDataBuilder
from hci.evt.le.ext_events import phy_name
from hci.session.session import (
    EVT_ADV_REPORT,
    EVT_CONNECTION_DOWN,
    EVT_CONNECTION_UP,
    EVT_ERROR,
    EVT_EVENT,
    EVT_STATE,
)
from ui.hci_ui.hci_main_ui import HciMainUI


# --------------------------------------------------------------- small helpers

def _spin(minimum: int, maximum: int, value: int, tip: str = "",
          width: int = 130) -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setMaximumWidth(width)
    if tip:
        box.setToolTip(tip)
    return box


def _combo(items, current=0, width: int = 220) -> QComboBox:
    """`items` is a sequence of (label, data)."""
    box = QComboBox()
    for label, data in items:
        box.addItem(label, data)
    box.setCurrentIndex(current)
    box.setMaximumWidth(width)
    return box


def _addr_types():
    return [(t.name, t.value) for t in le_cmds.AddressType]


def _scrolled(widget: QWidget) -> QScrollArea:
    """Put a panel in a vertical scroll area, keeping its natural width."""
    area = QScrollArea()
    area.setWidget(widget)
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    return area


def _button_row(*buttons) -> QWidget:
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    for button in buttons:
        layout.addWidget(button)
    layout.addStretch(1)
    return holder


def _hex_bytes(text: str, field: str) -> bytes:
    clean = text.strip().replace(" ", "").replace("0x", "").replace(":", "")
    if not clean:
        return b''
    if len(clean) % 2:
        clean = "0" + clean
    try:
        return bytes.fromhex(clean)
    except ValueError:
        raise ValueError(f"{field} is not valid hex: {text!r}")


def _parse_addr(text: str) -> bytes:
    clean = text.replace(":", "").replace("-", "").replace(" ", "").strip()
    if len(clean) != 12:
        raise ValueError(f"address must be 6 bytes (12 hex digits), got {len(clean)}")
    return bytes.fromhex(clean)


class _Panel(QWidget):
    """
    Base for the four feature panels.

    Gives each panel `send()` and `log()` against the host window, so a panel
    never has to know how the session is attached or which thread it is on.
    """

    def __init__(self, host: "LeControlWindow"):
        super().__init__()
        self.host = host
        self.build()

    def build(self) -> None:
        """Subclass hook."""

    def send(self, builder: Callable, label: str) -> None:
        """
        Build and send one command.

        `builder` is a callable so a parameter error (bad address, out-of-range
        interval) is raised here and reported in the log rather than escaping to
        a Qt slot, where it would print a traceback and vanish.
        """
        self.host.send(builder, label)

    def log(self, message: str) -> None:
        self.host.log(message)

    def session_ready(self) -> bool:
        return self.host.session is not None


# ------------------------------------------------------------------ advertising

class AdvertisingPanel(_Panel):
    """Legacy, extended and periodic advertising."""

    def build(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._legacy_tab(), "Legacy")
        tabs.addTab(self._extended_tab(), "Extended")
        tabs.addTab(self._periodic_tab(), "Periodic")
        root.addWidget(tabs)

    # ---- legacy

    def _legacy_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.leg_interval_min = _spin(0x0020, 0x4000, 0x00A0,
                                      "Advertising interval min (N * 0.625 ms)")
        self.leg_interval_max = _spin(0x0020, 0x4000, 0x00F0,
                                      "Advertising interval max (N * 0.625 ms)")
        form.addRow("Interval Min:", self.leg_interval_min)
        form.addRow("Interval Max:", self.leg_interval_max)

        self.leg_adv_type = _combo(
            [(t.name, t.value) for t in le_cmds.AdvertisingType])
        form.addRow("Advertising Type:", self.leg_adv_type)

        self.leg_own_addr = _combo(_addr_types())
        form.addRow("Own Address Type:", self.leg_own_addr)

        self.leg_filter = _combo([
            ("Process all devices", 0x00),
            ("Filter scan requests", 0x01),
            ("Filter connection requests", 0x02),
            ("Filter both", 0x03),
        ])
        form.addRow("Filter Policy:", self.leg_filter)

        self.leg_name = QLineEdit("HCI Tool")
        form.addRow("Local Name:", self.leg_name)

        self.leg_adv_data = QLineEdit()
        self.leg_adv_data.setPlaceholderText(
            "Hex AD structures; blank = flags + the local name above")
        form.addRow("Advertising Data:", self.leg_adv_data)

        self.leg_scan_rsp = QLineEdit()
        self.leg_scan_rsp.setPlaceholderText("Hex scan response data (optional)")
        form.addRow("Scan Response:", self.leg_scan_rsp)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(self._legacy_params)
        data_btn = QPushButton("Set Data")
        data_btn.clicked.connect(self._legacy_data)
        rsp_btn = QPushButton("Set Scan Response")
        rsp_btn.clicked.connect(self._legacy_scan_rsp)
        form.addRow("", _button_row(params_btn, data_btn, rsp_btn))

        start_btn = QPushButton("Start Advertising")
        start_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetAdvertiseEnable(True), "LE Set Advertise Enable"))
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetAdvertiseEnable(False), "LE Set Advertise Disable"))
        all_btn = QPushButton("Params + Data + Start")
        all_btn.setToolTip("Send the three commands in order")
        all_btn.clicked.connect(self._legacy_all)
        form.addRow("", _button_row(start_btn, stop_btn, all_btn))

        return page

    def _adv_payload(self) -> bytes:
        """Hex box if given, otherwise flags + the local name."""
        raw = _hex_bytes(self.leg_adv_data.text(), "advertising data")
        if raw:
            return raw
        return (AdvertisingDataBuilder()
                .add_flags(0x06)                    # general discoverable, LE only
                .add_name(self.leg_name.text() or "HCI Tool")
                .build())

    def _legacy_params(self):
        self.send(lambda: le_cmds.LeSetAdvParams(
            adv_interval_min=self.leg_interval_min.value(),
            adv_interval_max=self.leg_interval_max.value(),
            adv_type=self.leg_adv_type.currentData(),
            own_addr_type=self.leg_own_addr.currentData(),
            adv_filter_policy=self.leg_filter.currentData(),
        ), "LE Set Advertising Parameters")

    def _legacy_data(self):
        self.send(lambda: le_cmds.LeSetAdvData(data=self._adv_payload()),
                  "LE Set Advertising Data")

    def _legacy_scan_rsp(self):
        self.send(lambda: le_cmds.LeSetScanResponseData(
            data=_hex_bytes(self.leg_scan_rsp.text(), "scan response data")),
            "LE Set Scan Response Data")

    def _legacy_all(self):
        self._legacy_params()
        self._legacy_data()
        self.send(lambda: le_cmds.LeSetAdvertiseEnable(True),
                  "LE Set Advertise Enable")

    # ---- extended

    def _extended_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.ext_handle = _spin(0x00, 0xEF, 0x00, "Advertising set handle")
        form.addRow("Advertising Handle:", self.ext_handle)

        self.ext_properties = _combo([
            ("Extended connectable", int(le_cmds.AdvEventProperties.CONNECTABLE)),
            ("Extended scannable", int(le_cmds.AdvEventProperties.SCANNABLE)),
            ("Extended non-conn non-scan", 0x0000),
            ("Extended anonymous", int(le_cmds.AdvEventProperties.ANONYMOUS)),
            ("Legacy ADV_IND", int(le_cmds.LEGACY_ADV_IND)),
            ("Legacy ADV_SCAN_IND", int(le_cmds.LEGACY_ADV_SCAN_IND)),
            ("Legacy ADV_NONCONN_IND", int(le_cmds.LEGACY_ADV_NONCONN_IND)),
        ])
        form.addRow("Event Properties:", self.ext_properties)

        self.ext_interval_min = _spin(0x000020, 0xFFFFFF, 0x0000A0,
                                      "Primary interval min (N * 0.625 ms)")
        self.ext_interval_max = _spin(0x000020, 0xFFFFFF, 0x0000F0,
                                      "Primary interval max (N * 0.625 ms)")
        form.addRow("Primary Interval Min:", self.ext_interval_min)
        form.addRow("Primary Interval Max:", self.ext_interval_max)

        self.ext_primary_phy = _combo(
            [(p.name, p.value) for p in le_cmds.PrimaryPhy])
        form.addRow("Primary PHY:", self.ext_primary_phy)

        self.ext_secondary_phy = _combo(
            [(p.name, p.value) for p in le_cmds.SecondaryPhy])
        form.addRow("Secondary PHY:", self.ext_secondary_phy)

        self.ext_sid = _spin(0x00, 0x0F, 0x00, "Advertising Set ID")
        form.addRow("Advertising SID:", self.ext_sid)

        self.ext_own_addr = _combo(_addr_types())
        form.addRow("Own Address Type:", self.ext_own_addr)

        self.ext_tx_power = _spin(-127, 127, 127, "dBm; 127 = no preference")
        form.addRow("TX Power:", self.ext_tx_power)

        self.ext_name = QLineEdit("HCI Tool Ext")
        form.addRow("Local Name:", self.ext_name)

        self.ext_data = QLineEdit()
        self.ext_data.setPlaceholderText(
            "Hex AD structures; blank = flags + the local name above")
        form.addRow("Advertising Data:", self.ext_data)

        self.ext_duration = _spin(0x0000, 0xFFFF, 0x0000,
                                  "Duration in 10 ms units; 0 = until disabled")
        form.addRow("Enable Duration:", self.ext_duration)

        self.ext_max_events = _spin(0x00, 0xFF, 0x00,
                                    "Stop after N events; 0 = no limit")
        form.addRow("Max Adv Events:", self.ext_max_events)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(self._ext_params)
        data_btn = QPushButton("Set Data")
        data_btn.clicked.connect(self._ext_data)
        rand_btn = QPushButton("Set Set Random Address")
        rand_btn.clicked.connect(self._ext_random_address)
        form.addRow("", _button_row(params_btn, data_btn, rand_btn))

        start_btn = QPushButton("Enable Set")
        start_btn.clicked.connect(lambda: self._ext_enable(True))
        stop_btn = QPushButton("Disable Set")
        stop_btn.clicked.connect(lambda: self._ext_enable(False))
        all_btn = QPushButton("Params + Data + Enable")
        all_btn.clicked.connect(self._ext_all)
        form.addRow("", _button_row(start_btn, stop_btn, all_btn))

        remove_btn = QPushButton("Remove Set")
        remove_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeRemoveAdvertisingSet(self.ext_handle.value()),
            "LE Remove Advertising Set"))
        clear_btn = QPushButton("Clear All Sets")
        clear_btn.clicked.connect(lambda: self.send(
            le_cmds.LeClearAdvertisingSets, "LE Clear Advertising Sets"))
        read_btn = QPushButton("Read Capabilities")
        read_btn.setToolTip("Max advertising data length and number of sets")
        read_btn.clicked.connect(self._ext_read_caps)
        form.addRow("", _button_row(remove_btn, clear_btn, read_btn))

        return page

    def _ext_payload(self) -> bytes:
        raw = _hex_bytes(self.ext_data.text(), "advertising data")
        if raw:
            return raw
        return (AdvertisingDataBuilder()
                .add_flags(0x06)
                .add_name(self.ext_name.text() or "HCI Tool Ext")
                .build())

    def _ext_params(self):
        self.send(lambda: le_cmds.LeSetExtendedAdvertisingParameters(
            adv_handle=self.ext_handle.value(),
            adv_event_properties=self.ext_properties.currentData(),
            primary_adv_interval_min=self.ext_interval_min.value(),
            primary_adv_interval_max=self.ext_interval_max.value(),
            own_address_type=self.ext_own_addr.currentData(),
            adv_tx_power=self.ext_tx_power.value(),
            primary_adv_phy=self.ext_primary_phy.currentData(),
            secondary_adv_phy=self.ext_secondary_phy.currentData(),
            adv_sid=self.ext_sid.value(),
        ), "LE Set Extended Advertising Parameters")

    def _ext_data(self):
        # Long payloads have to be fragmented; the command class knows how.
        payload = self._ext_payload()
        for operation, chunk in le_cmds.LeSetExtendedAdvertisingData.fragments(payload):
            self.send(
                lambda op=operation, data=chunk:
                    le_cmds.LeSetExtendedAdvertisingData(
                        adv_handle=self.ext_handle.value(), data=data,
                        operation=op),
                f"LE Set Extended Advertising Data ({len(chunk)}B)")

    def _ext_random_address(self):
        self.send(lambda: le_cmds.LeSetAdvertisingSetRandomAddress(
            adv_handle=self.ext_handle.value(),
            random_address=bytes([0xC0, 0x00, 0x00, 0x00, 0x00,
                                  self.ext_handle.value() or 0x01]),
        ), "LE Set Advertising Set Random Address")

    def _ext_enable(self, enable: bool):
        self.send(lambda: le_cmds.LeSetExtendedAdvertisingEnable(
            enable=enable,
            sets=[(self.ext_handle.value(), self.ext_duration.value(),
                   self.ext_max_events.value())],
        ), f"LE Set Extended Advertising {'Enable' if enable else 'Disable'}")

    def _ext_all(self):
        self._ext_params()
        self._ext_data()
        self._ext_enable(True)

    def _ext_read_caps(self):
        self.send(le_cmds.LeReadMaximumAdvertisingDataLength,
                  "LE Read Maximum Advertising Data Length")
        self.send(le_cmds.LeReadNumberOfSupportedAdvertisingSets,
                  "LE Read Number Of Supported Advertising Sets")

    # ---- periodic

    def _periodic_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        note = QLabel(
            "Periodic advertising rides on an extended set. Create the set on "
            "the Extended tab first -- non-connectable, non-scannable and "
            "non-anonymous -- then configure and enable it here, and enable the "
            "set itself so the train is actually transmitted.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        form.addRow(note)

        self.per_handle = _spin(0x00, 0xEF, 0x00)
        form.addRow("Advertising Handle:", self.per_handle)

        self.per_interval_min = _spin(0x0006, 0xFFFF, 0x0060,
                                      "Periodic interval min (N * 1.25 ms)")
        self.per_interval_max = _spin(0x0006, 0xFFFF, 0x0080,
                                      "Periodic interval max (N * 1.25 ms)")
        form.addRow("Interval Min:", self.per_interval_min)
        form.addRow("Interval Max:", self.per_interval_max)

        self.per_tx_power = QCheckBox("Include TX power")
        form.addRow("Properties:", self.per_tx_power)

        self.per_data = QLineEdit()
        self.per_data.setPlaceholderText("Hex periodic advertising data")
        form.addRow("Periodic Data:", self.per_data)

        self.per_adi = QCheckBox("Include ADI in AUX_SYNC_IND")
        form.addRow("", self.per_adi)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetPeriodicAdvertisingParameters(
                adv_handle=self.per_handle.value(),
                periodic_adv_interval_min=self.per_interval_min.value(),
                periodic_adv_interval_max=self.per_interval_max.value(),
                periodic_adv_properties=(
                    0x0040 if self.per_tx_power.isChecked() else 0x0000),
            ), "LE Set Periodic Advertising Parameters"))

        data_btn = QPushButton("Set Data")
        data_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetPeriodicAdvertisingData(
                adv_handle=self.per_handle.value(),
                data=_hex_bytes(self.per_data.text(), "periodic data"),
            ), "LE Set Periodic Advertising Data"))
        form.addRow("", _button_row(params_btn, data_btn))

        enable_btn = QPushButton("Enable Periodic")
        enable_btn.clicked.connect(lambda: self._periodic_enable(True))
        disable_btn = QPushButton("Disable Periodic")
        disable_btn.clicked.connect(lambda: self._periodic_enable(False))
        form.addRow("", _button_row(enable_btn, disable_btn))

        return page

    def _periodic_enable(self, enable: bool):
        value = 0x01 if enable else 0x00
        if enable and self.per_adi.isChecked():
            value |= le_cmds.LeSetPeriodicAdvertisingEnable.INCLUDE_ADI
        self.send(lambda: le_cmds.LeSetPeriodicAdvertisingEnable(
            enable=value, adv_handle=self.per_handle.value()),
            f"LE Set Periodic Advertising {'Enable' if enable else 'Disable'}")


# --------------------------------------------------------------------- scanning

class ScanningPanel(_Panel):
    """Legacy scanning, extended scanning and periodic sync, with one result table."""

    def build(self):
        root = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._legacy_tab(), "Legacy")
        tabs.addTab(self._extended_tab(), "Extended")
        tabs.addTab(self._periodic_tab(), "Periodic Sync")
        root.addWidget(tabs)

        results = QGroupBox("Advertising reports")
        results_layout = QVBoxLayout(results)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Address", "Name", "RSSI", "Type", "SID", "PHY", "Data"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        results_layout.addWidget(self.table)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_results)
        use_btn = QPushButton("Copy address to Connection tab")
        use_btn.clicked.connect(self._copy_selection)
        results_layout.addWidget(_button_row(clear_btn, use_btn))
        root.addWidget(results, 1)

        self._rows: Dict[str, int] = {}

    # ---- legacy

    def _legacy_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.leg_scan_type = _combo([("Passive", 0x00), ("Active", 0x01)], 1)
        form.addRow("Scan Type:", self.leg_scan_type)

        self.leg_interval = _spin(0x0004, 0x4000, 0x0060,
                                  "Scan interval (N * 0.625 ms)")
        self.leg_window = _spin(0x0004, 0x4000, 0x0030,
                                "Scan window (N * 0.625 ms)")
        form.addRow("Scan Interval:", self.leg_interval)
        form.addRow("Scan Window:", self.leg_window)

        self.leg_own_addr = _combo(_addr_types())
        form.addRow("Own Address Type:", self.leg_own_addr)

        self.leg_filter_policy = _combo([
            ("Accept all", 0x00),
            ("Filter Accept List only", 0x01),
            ("Accept all + directed RPA", 0x02),
            ("Filter Accept List + directed RPA", 0x03),
        ])
        form.addRow("Filter Policy:", self.leg_filter_policy)

        self.leg_filter_dup = QCheckBox("Filter duplicates")
        self.leg_filter_dup.setChecked(True)
        form.addRow("", self.leg_filter_dup)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetScanParameters(
                scan_type=self.leg_scan_type.currentData(),
                scan_interval=self.leg_interval.value(),
                scan_window=self.leg_window.value(),
                own_addr_type=self.leg_own_addr.currentData(),
                scanning_filter_policy=self.leg_filter_policy.currentData(),
            ), "LE Set Scan Parameters"))

        start_btn = QPushButton("Start Scan")
        start_btn.clicked.connect(self._legacy_start)
        stop_btn = QPushButton("Stop Scan")
        stop_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetScanEnable(scan_enable=False,
                                            filter_duplicates=False),
            "LE Set Scan Disable"))
        form.addRow("", _button_row(params_btn, start_btn, stop_btn))

        return page

    def _legacy_start(self):
        # Parameters cannot be changed while scanning, so send them first and
        # let the session's credit queue order the pair.
        self.send(lambda: le_cmds.LeSetScanParameters(
            scan_type=self.leg_scan_type.currentData(),
            scan_interval=self.leg_interval.value(),
            scan_window=self.leg_window.value(),
            own_addr_type=self.leg_own_addr.currentData(),
            scanning_filter_policy=self.leg_filter_policy.currentData(),
        ), "LE Set Scan Parameters")
        self.send(lambda: le_cmds.LeSetScanEnable(
            scan_enable=True,
            filter_duplicates=self.leg_filter_dup.isChecked(),
        ), "LE Set Scan Enable")

    # ---- extended

    def _extended_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        phys = QWidget()
        phy_layout = QHBoxLayout(phys)
        phy_layout.setContentsMargins(0, 0, 0, 0)
        self.ext_phy_1m = QCheckBox("LE 1M")
        self.ext_phy_1m.setChecked(True)
        self.ext_phy_coded = QCheckBox("LE Coded")
        phy_layout.addWidget(self.ext_phy_1m)
        phy_layout.addWidget(self.ext_phy_coded)
        phy_layout.addStretch(1)
        form.addRow("Scanning PHYs:", phys)

        self.ext_scan_type = _combo([("Passive", 0x00), ("Active", 0x01)], 1)
        form.addRow("Scan Type:", self.ext_scan_type)

        self.ext_interval = _spin(0x0004, 0xFFFF, 0x0060,
                                  "Scan interval (N * 0.625 ms)")
        self.ext_window = _spin(0x0004, 0xFFFF, 0x0030,
                                "Scan window (N * 0.625 ms)")
        form.addRow("Scan Interval:", self.ext_interval)
        form.addRow("Scan Window:", self.ext_window)

        self.ext_own_addr = _combo(_addr_types())
        form.addRow("Own Address Type:", self.ext_own_addr)

        self.ext_filter_policy = _combo([
            ("Accept all", 0x00),
            ("Filter Accept List only", 0x01),
            ("Accept all + directed RPA", 0x02),
            ("Filter Accept List + directed RPA", 0x03),
        ])
        form.addRow("Filter Policy:", self.ext_filter_policy)

        self.ext_filter_dup = _combo([
            ("Report everything", 0x00),
            ("Filter duplicates", 0x01),
            ("Reset filter each period", 0x02),
        ], 1)
        form.addRow("Duplicate Filtering:", self.ext_filter_dup)

        self.ext_duration = _spin(0x0000, 0xFFFF, 0x0000,
                                  "Duration in 10 ms units; 0 = until disabled")
        self.ext_period = _spin(0x0000, 0xFFFF, 0x0000,
                                "Period in 1.28 s units; 0 = continuous")
        form.addRow("Duration:", self.ext_duration)
        form.addRow("Period:", self.ext_period)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(self._ext_params)
        start_btn = QPushButton("Start Scan")
        start_btn.clicked.connect(self._ext_start)
        stop_btn = QPushButton("Stop Scan")
        stop_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetExtendedScanEnable(enable=False),
            "LE Set Extended Scan Disable"))
        form.addRow("", _button_row(params_btn, start_btn, stop_btn))

        return page

    def _ext_scan_params(self):
        if not (self.ext_phy_1m.isChecked() or self.ext_phy_coded.isChecked()):
            raise ValueError("select at least one scanning PHY")
        block = (self.ext_scan_type.currentData(), self.ext_interval.value(),
                 self.ext_window.value())
        phys = {}
        if self.ext_phy_1m.isChecked():
            phys[int(le_cmds.ScanPhy.LE_1M)] = block
        if self.ext_phy_coded.isChecked():
            phys[int(le_cmds.ScanPhy.LE_CODED)] = block
        return le_cmds.LeSetExtendedScanParameters(
            own_address_type=self.ext_own_addr.currentData(),
            scanning_filter_policy=self.ext_filter_policy.currentData(),
            scan_phys=phys,
        )

    def _ext_params(self):
        self.send(self._ext_scan_params, "LE Set Extended Scan Parameters")

    def _ext_start(self):
        self._ext_params()
        self.send(lambda: le_cmds.LeSetExtendedScanEnable(
            enable=True,
            filter_duplicates=self.ext_filter_dup.currentData(),
            duration=self.ext_duration.value(),
            period=self.ext_period.value(),
        ), "LE Set Extended Scan Enable")

    # ---- periodic sync

    def _periodic_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        note = QLabel(
            "Start an extended scan first -- the controller can only find a "
            "periodic train while it is scanning.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        form.addRow(note)

        self.sync_sid = _spin(0x00, 0x0F, 0x00, "Advertising SID to sync to")
        form.addRow("Advertising SID:", self.sync_sid)

        self.sync_addr_type = _combo([("PUBLIC", 0x00), ("RANDOM", 0x01)])
        form.addRow("Advertiser Address Type:", self.sync_addr_type)

        self.sync_address = QLineEdit("00:00:00:00:00:00")
        form.addRow("Advertiser Address:", self.sync_address)

        self.sync_skip = _spin(0x0000, 0x01F3, 0x0000,
                               "Periodic events that may be skipped")
        form.addRow("Skip:", self.sync_skip)

        self.sync_timeout = _spin(0x000A, 0x4000, 0x03E8,
                                  "Sync timeout (N * 10 ms)")
        form.addRow("Sync Timeout:", self.sync_timeout)

        self.sync_use_list = QCheckBox("Use the Periodic Advertiser List")
        form.addRow("Options:", self.sync_use_list)
        self.sync_reports_off = QCheckBox("Start with reports disabled")
        form.addRow("", self.sync_reports_off)

        create_btn = QPushButton("Create Sync")
        create_btn.clicked.connect(self._create_sync)
        cancel_btn = QPushButton("Cancel Pending Sync")
        cancel_btn.clicked.connect(lambda: self.send(
            le_cmds.LePeriodicAdvertisingCreateSyncCancel,
            "LE Periodic Advertising Create Sync Cancel"))
        form.addRow("", _button_row(create_btn, cancel_btn))

        self.sync_handle = _spin(0x0000, 0x0EFF, 0x0000,
                                 "Sync handle from the Sync Established event")
        form.addRow("Sync Handle:", self.sync_handle)

        terminate_btn = QPushButton("Terminate Sync")
        terminate_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LePeriodicAdvertisingTerminateSync(
                self.sync_handle.value()),
            "LE Periodic Advertising Terminate Sync"))
        reports_on_btn = QPushButton("Reports On")
        reports_on_btn.clicked.connect(lambda: self._receive_enable(True))
        reports_off_btn = QPushButton("Reports Off")
        reports_off_btn.clicked.connect(lambda: self._receive_enable(False))
        form.addRow("", _button_row(terminate_btn, reports_on_btn, reports_off_btn))

        return page

    def _create_sync(self):
        options = 0x00
        if self.sync_use_list.isChecked():
            options |= int(le_cmds.PeriodicSyncOptions.USE_PERIODIC_ADV_LIST)
        if self.sync_reports_off.isChecked():
            options |= int(le_cmds.PeriodicSyncOptions.REPORTS_INITIALLY_DISABLED)
        self.send(lambda: le_cmds.LePeriodicAdvertisingCreateSync(
            adv_sid=self.sync_sid.value(),
            advertiser_address=_parse_addr(self.sync_address.text()),
            advertiser_address_type=self.sync_addr_type.currentData(),
            options=options,
            skip=self.sync_skip.value(),
            sync_timeout=self.sync_timeout.value(),
        ), "LE Periodic Advertising Create Sync")

    def _receive_enable(self, enable: bool):
        self.send(lambda: le_cmds.LeSetPeriodicAdvertisingReceiveEnable(
            sync_handle=self.sync_handle.value(), enable=enable),
            f"LE Periodic Advertising Reports {'On' if enable else 'Off'}")

    # ---- results

    def add_report(self, report: dict) -> None:
        """One advertising report -- legacy or extended, same keys."""
        address = report.get('address_str') or ""
        if not address:
            return
        adv = report.get('adv_data')
        rssi = report.get('rssi')
        primary = report.get('primary_phy')
        values = [
            address,
            getattr(adv, 'local_name', None) or "",
            "" if rssi is None else f"{rssi} dBm",
            report.get('event_type_str')
            or f"0x{report.get('event_type', 0):02X}",
            str(report.get('adv_sid', "")),
            "-" if primary is None else
            f"{phy_name(primary)}/{phy_name(report.get('secondary_phy'))}",
            bytes(report.get('data') or b'').hex(' '),
        ]

        row = self._rows.get(address)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._rows[address] = row
        for column, text in enumerate(values):
            # A scan response carries no name; keep the one the earlier report
            # showed instead of blanking the column.
            if not text:
                item = self.table.item(row, column)
                if item is not None and item.text():
                    continue
            self.table.setItem(row, column, QTableWidgetItem(text))

    def clear_results(self) -> None:
        self._rows.clear()
        self.table.setRowCount(0)

    def _copy_selection(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.log("! select a row first")
            return
        address = self.table.item(row, 0).text()
        self.host.connection_panel.set_peer_address(address)
        sid_item = self.table.item(row, 4)
        if sid_item is not None and sid_item.text().isdigit():
            self.sync_sid.setValue(int(sid_item.text()))
        self.sync_address.setText(address)
        self.log(f"= {address} copied to the Connection tab")


# ------------------------------------------------------------------- connection

class ConnectionPanel(_Panel):
    """Legacy and extended initiation, plus the live connection list."""

    def build(self):
        root = QVBoxLayout(self)

        peer_box = QGroupBox("Peer")
        peer_form = QFormLayout(peer_box)
        self.peer_address = QLineEdit("00:00:00:00:00:00")
        peer_form.addRow("Peer Address:", self.peer_address)
        self.peer_addr_type = _combo(_addr_types())
        peer_form.addRow("Peer Address Type:", self.peer_addr_type)
        self.own_addr_type = _combo(_addr_types())
        peer_form.addRow("Own Address Type:", self.own_addr_type)
        self.filter_policy = _combo([
            ("Use the peer address", 0x00),
            ("Use the Filter Accept List", 0x01),
        ])
        peer_form.addRow("Initiator Filter Policy:", self.filter_policy)
        root.addWidget(peer_box)

        params_box = QGroupBox("Connection parameters")
        params_form = QFormLayout(params_box)
        self.scan_interval = _spin(0x0004, 0x4000, 0x0060,
                                   "Scan interval (N * 0.625 ms)")
        self.scan_window = _spin(0x0004, 0x4000, 0x0030,
                                 "Scan window (N * 0.625 ms)")
        params_form.addRow("Scan Interval:", self.scan_interval)
        params_form.addRow("Scan Window:", self.scan_window)

        self.conn_min = _spin(0x0006, 0x0C80, 0x0018,
                              "Connection interval min (N * 1.25 ms)")
        self.conn_max = _spin(0x0006, 0x0C80, 0x0028,
                              "Connection interval max (N * 1.25 ms)")
        params_form.addRow("Conn Interval Min:", self.conn_min)
        params_form.addRow("Conn Interval Max:", self.conn_max)

        self.latency = _spin(0x0000, 0x01F3, 0x0000)
        params_form.addRow("Latency:", self.latency)
        self.timeout = _spin(0x000A, 0x0C80, 0x01F4,
                             "Supervision timeout (N * 10 ms)")
        params_form.addRow("Supervision Timeout:", self.timeout)

        phys = QWidget()
        phy_layout = QHBoxLayout(phys)
        phy_layout.setContentsMargins(0, 0, 0, 0)
        self.phy_1m = QCheckBox("1M")
        self.phy_1m.setChecked(True)
        self.phy_2m = QCheckBox("2M")
        self.phy_coded = QCheckBox("Coded")
        for box in (self.phy_1m, self.phy_2m, self.phy_coded):
            phy_layout.addWidget(box)
        phy_layout.addStretch(1)
        params_form.addRow("Extended PHYs:", phys)
        root.addWidget(params_box)

        legacy_btn = QPushButton("Create Connection (legacy)")
        legacy_btn.clicked.connect(self._legacy_connect)
        extended_btn = QPushButton("Extended Create Connection")
        extended_btn.clicked.connect(self._extended_connect)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lambda: self.send(
            le_cmds.LeCreateConnectionCancel, "LE Create Connection Cancel"))
        root.addWidget(_button_row(legacy_btn, extended_btn, cancel_btn))

        conn_box = QGroupBox("Connections")
        conn_layout = QVBoxLayout(conn_box)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Handle", "Address", "Role", "Interval", "Timeout"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        conn_layout.addWidget(self.table)

        update_btn = QPushButton("Update Parameters")
        update_btn.clicked.connect(self._update_connection)
        features_btn = QPushButton("Read Remote Features")
        features_btn.clicked.connect(self._read_features)
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.clicked.connect(self._disconnect)
        conn_layout.addWidget(_button_row(update_btn, features_btn, disconnect_btn))
        root.addWidget(conn_box, 1)

    def set_peer_address(self, address: str) -> None:
        self.peer_address.setText(address)

    def selected_handle(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            self.log("! select a connection first")
            return None
        return int(self.table.item(row, 0).text(), 16)

    def _legacy_connect(self):
        self.send(lambda: le_cmds.LeCreateConnection(
            peer_address=_parse_addr(self.peer_address.text()),
            peer_address_type=self.peer_addr_type.currentData(),
            own_address_type=self.own_addr_type.currentData(),
            initiator_filter_policy=self.filter_policy.currentData(),
            scan_interval=self.scan_interval.value(),
            scan_window=self.scan_window.value(),
            conn_interval_min=self.conn_min.value(),
            conn_interval_max=self.conn_max.value(),
            conn_latency=self.latency.value(),
            supervision_timeout=self.timeout.value(),
        ), "LE Create Connection")

    def _extended_connect(self):
        def build():
            block = (self.scan_interval.value(), self.scan_window.value(),
                     self.conn_min.value(), self.conn_max.value(),
                     self.latency.value(), self.timeout.value(), 0x0000, 0x0000)
            cmd = le_cmds.LeExtendedCreateConnection
            phy_params = {}
            if self.phy_1m.isChecked():
                phy_params[cmd.PHY_1M] = block
            if self.phy_2m.isChecked():
                phy_params[cmd.PHY_2M] = block
            if self.phy_coded.isChecked():
                phy_params[cmd.PHY_CODED] = block
            if not phy_params:
                raise ValueError("select at least one initiating PHY")
            return cmd(
                peer_address=_parse_addr(self.peer_address.text()),
                peer_address_type=self.peer_addr_type.currentData(),
                own_address_type=self.own_addr_type.currentData(),
                initiator_filter_policy=self.filter_policy.currentData(),
                phy_params=phy_params,
            )

        self.send(build, "LE Extended Create Connection")

    def _update_connection(self):
        handle = self.selected_handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeConnectionUpdate(
            connection_handle=handle,
            conn_interval_min=self.conn_min.value(),
            conn_interval_max=self.conn_max.value(),
            conn_latency=self.latency.value(),
            supervision_timeout=self.timeout.value(),
        ), "LE Connection Update")

    def _read_features(self):
        handle = self.selected_handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeReadRemoteFeatures(handle),
                  "LE Read Remote Features")

    def _disconnect(self):
        handle = self.selected_handle()
        if handle is None:
            return
        # Disconnect is a Link Control command, not an LE one.
        from hci.cmd.link_controller.link_controller_cmds import Disconnect
        self.send(lambda: Disconnect(connection_handle=handle, reason=0x13),
                  "Disconnect")

    def refresh_connections(self) -> None:
        session = self.host.session
        self.table.setRowCount(0)
        if session is None:
            return
        for info in session.connections.all():
            row = self.table.rowCount()
            self.table.insertRow(row)
            interval, timeout = info.interval_ms, info.timeout_ms
            values = [
                f"{info.handle:04X}",
                info.bd_addr,
                info.role.value,
                "-" if interval is None else f"{interval:.2f} ms",
                "-" if timeout is None else f"{timeout} ms",
            ]
            for column, text in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(text)))
        self.host.cs_panel.refresh_handles()


# -------------------------------------------------------------- channel sounding

class ChannelSoundingPanel(_Panel):
    """
    Channel Sounding, laid out as the sequence a controller actually accepts.

    The buttons run top to bottom: capabilities, security, defaults, config,
    procedure parameters, enable. "Run full setup" queues steps 2-5 in order,
    which is what you want when re-testing after a disconnect.
    """

    def build(self):
        root = QVBoxLayout(self)

        target = QGroupBox("Target")
        target_form = QFormLayout(target)
        self.handle_combo = QComboBox()
        self.handle_combo.setEditable(False)
        self.handle_combo.setMaximumWidth(220)
        target_form.addRow("Connection:", self.handle_combo)
        self.config_id = _spin(0x00, 0x03, 0x00, "One of four CS configurations")
        target_form.addRow("Config ID:", self.config_id)
        root.addWidget(target)

        caps_box = QGroupBox("1. Capabilities and security")
        caps_layout = QVBoxLayout(caps_box)
        local_btn = QPushButton("Local Caps")
        local_btn.setToolTip("LE CS Read Local Supported Capabilities")
        local_btn.clicked.connect(lambda: self.send(
            le_cmds.LeCsReadLocalSupportedCapabilities,
            "LE CS Read Local Supported Capabilities"))
        remote_btn = QPushButton("Remote Caps")
        remote_btn.setToolTip("LE CS Read Remote Supported Capabilities")
        remote_btn.clicked.connect(lambda: self._with_handle(
            le_cmds.LeCsReadRemoteSupportedCapabilities,
            "LE CS Read Remote Supported Capabilities"))
        fae_btn = QPushButton("Remote FAE")
        fae_btn.setToolTip("LE CS Read Remote FAE Table")
        fae_btn.clicked.connect(lambda: self._with_handle(
            le_cmds.LeCsReadRemoteFaeTable, "LE CS Read Remote FAE Table"))
        security_btn = QPushButton("Security Enable")
        security_btn.clicked.connect(lambda: self._with_handle(
            le_cmds.LeCsSecurityEnable, "LE CS Security Enable"))
        caps_layout.addWidget(_button_row(local_btn, remote_btn, fae_btn,
                                          security_btn))
        root.addWidget(caps_box)

        defaults_box = QGroupBox("2. Default settings")
        defaults_form = QFormLayout(defaults_box)
        roles = QWidget()
        role_layout = QHBoxLayout(roles)
        role_layout.setContentsMargins(0, 0, 0, 0)
        self.role_initiator = QCheckBox("Initiator")
        self.role_initiator.setChecked(True)
        self.role_reflector = QCheckBox("Reflector")
        self.role_reflector.setChecked(True)
        role_layout.addWidget(self.role_initiator)
        role_layout.addWidget(self.role_reflector)
        role_layout.addStretch(1)
        defaults_form.addRow("Roles Enabled:", roles)

        self.sync_antenna = _combo(
            [("Controller's choice", 0xFF)] +
            [(f"Antenna {n}", n) for n in range(1, 5)] +
            [("Repeat in order", 0xFE)])
        defaults_form.addRow("CS Sync Antenna:", self.sync_antenna)

        self.max_tx_power = _spin(-127, 127, 0, "Maximum TX power in dBm")
        defaults_form.addRow("Max TX Power:", self.max_tx_power)

        defaults_btn = QPushButton("Set Default Settings")
        defaults_btn.clicked.connect(self._set_defaults)
        defaults_form.addRow("", _button_row(defaults_btn))
        root.addWidget(defaults_box)

        config_box = QGroupBox("3. Configuration")
        config_form = QFormLayout(config_box)
        self.main_mode = _combo(
            [(m.name.replace("_", "-"), m.value) for m in le_cmds.CsMainMode], 1)
        config_form.addRow("Main Mode:", self.main_mode)
        self.sub_mode = _combo(
            [("Unused", 0xFF)] +
            [(m.name.replace("_", "-"), m.value) for m in le_cmds.CsMainMode])
        config_form.addRow("Sub Mode:", self.sub_mode)
        self.cs_role = _combo([(r.name.title(), r.value) for r in le_cmds.CsRole])
        config_form.addRow("Role:", self.cs_role)
        self.rtt_type = _combo(
            [(r.name.replace("_", " ").title(), r.value) for r in le_cmds.CsRttType])
        config_form.addRow("RTT Type:", self.rtt_type)
        self.cs_phy = _combo(
            [(p.name.replace("_", " "), p.value) for p in le_cmds.CsSyncPhy])
        config_form.addRow("CS Sync PHY:", self.cs_phy)
        self.min_steps = _spin(0x02, 0xFF, 0x02)
        self.max_steps = _spin(0x02, 0xFF, 0x05)
        config_form.addRow("Min Main Mode Steps:", self.min_steps)
        config_form.addRow("Max Main Mode Steps:", self.max_steps)
        self.mode0_steps = _spin(0x01, 0x03, 0x03)
        config_form.addRow("Mode-0 Steps:", self.mode0_steps)

        create_btn = QPushButton("Create Config")
        create_btn.clicked.connect(self._create_config)
        remove_btn = QPushButton("Remove Config")
        remove_btn.clicked.connect(self._remove_config)
        config_form.addRow("", _button_row(create_btn, remove_btn))
        root.addWidget(config_box)

        procedure_box = QGroupBox("4. Procedure")
        procedure_form = QFormLayout(procedure_box)
        self.max_procedure_len = _spin(0x0001, 0xFFFF, 0x2710,
                                       "Max procedure length (N * 0.625 ms)")
        procedure_form.addRow("Max Procedure Length:", self.max_procedure_len)
        self.procedure_interval = _spin(0x0001, 0xFFFF, 0x0001,
                                        "Procedure interval, in connection events")
        procedure_form.addRow("Procedure Interval:", self.procedure_interval)
        self.procedure_count = _spin(0x0000, 0xFFFF, 0x0001,
                                     "Procedures to run; 0 = until disabled")
        procedure_form.addRow("Procedure Count:", self.procedure_count)
        self.min_subevent = _spin(0x0000004E, 0xFFFFFF, 0x0004E2,
                                  "Min subevent length in microseconds", 160)
        self.max_subevent = _spin(0x0000004E, 0xFFFFFF, 0x0F4240,
                                  "Max subevent length in microseconds", 160)
        procedure_form.addRow("Min Subevent Length:", self.min_subevent)
        procedure_form.addRow("Max Subevent Length:", self.max_subevent)
        self.tone_antenna = _spin(0x00, 0x07, 0x00,
                                  "Tone antenna configuration index")
        procedure_form.addRow("Tone Antenna Config:", self.tone_antenna)

        params_btn = QPushButton("Set Procedure Parameters")
        params_btn.clicked.connect(self._set_procedure_params)
        start_btn = QPushButton("Start Procedure")
        start_btn.clicked.connect(lambda: self._procedure_enable(True))
        stop_btn = QPushButton("Stop Procedure")
        stop_btn.clicked.connect(lambda: self._procedure_enable(False))
        procedure_form.addRow("", _button_row(params_btn, start_btn, stop_btn))

        full_btn = QPushButton("Run full setup")
        full_btn.setToolTip(
            "Security Enable, Set Default Settings, Create Config and Set "
            "Procedure Parameters, in that order")
        full_btn.clicked.connect(self._full_setup)
        procedure_form.addRow("", _button_row(full_btn))
        root.addWidget(procedure_box)

        results_box = QGroupBox("Ranging results")
        results_layout = QVBoxLayout(results_box)
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumBlockCount(500)
        self.results.setFont(QFont("Menlo", 10))
        results_layout.addWidget(self.results)
        root.addWidget(results_box, 1)

    # ---- helpers

    def refresh_handles(self) -> None:
        """Repopulate the connection picker from the session's table."""
        session = self.host.session
        previous = self.handle_combo.currentData()
        self.handle_combo.clear()
        if session is None:
            return
        for info in session.connections.all():
            self.handle_combo.addItem(
                f"0x{info.handle:04X}  {info.bd_addr}", info.handle)
        if previous is not None:
            index = self.handle_combo.findData(previous)
            if index >= 0:
                self.handle_combo.setCurrentIndex(index)

    def handle(self) -> Optional[int]:
        value = self.handle_combo.currentData()
        if value is None:
            self.log("! no LE connection -- Channel Sounding runs on a link")
        return value

    def _with_handle(self, command_class, label: str) -> None:
        handle = self.handle()
        if handle is None:
            return
        self.send(lambda: command_class(handle), label)

    def add_result(self, line: str) -> None:
        self.results.appendPlainText(line)

    # ---- actions

    def _roles(self) -> int:
        roles = 0
        if self.role_initiator.isChecked():
            roles |= int(le_cmds.CsRoleMask.INITIATOR)
        if self.role_reflector.isChecked():
            roles |= int(le_cmds.CsRoleMask.REFLECTOR)
        return roles

    def _set_defaults(self):
        handle = self.handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeCsSetDefaultSettings(
            connection_handle=handle,
            role_enable=self._roles(),
            cs_sync_antenna_selection=self.sync_antenna.currentData(),
            max_tx_power=self.max_tx_power.value(),
        ), "LE CS Set Default Settings")

    def _create_config(self):
        handle = self.handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeCsCreateConfig(
            connection_handle=handle,
            config_id=self.config_id.value(),
            main_mode_type=self.main_mode.currentData(),
            sub_mode_type=self.sub_mode.currentData(),
            min_main_mode_steps=self.min_steps.value(),
            max_main_mode_steps=self.max_steps.value(),
            mode_0_steps=self.mode0_steps.value(),
            role=self.cs_role.currentData(),
            rtt_type=self.rtt_type.currentData(),
            cs_sync_phy=self.cs_phy.currentData(),
        ), "LE CS Create Config")

    def _remove_config(self):
        handle = self.handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeCsRemoveConfig(handle, self.config_id.value()),
                  "LE CS Remove Config")

    def _set_procedure_params(self):
        handle = self.handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeCsSetProcedureParameters(
            connection_handle=handle,
            config_id=self.config_id.value(),
            max_procedure_len=self.max_procedure_len.value(),
            min_procedure_interval=self.procedure_interval.value(),
            max_procedure_interval=self.procedure_interval.value(),
            max_procedure_count=self.procedure_count.value(),
            min_subevent_len=self.min_subevent.value(),
            max_subevent_len=self.max_subevent.value(),
            tone_antenna_config_selection=self.tone_antenna.value(),
            phy=self.cs_phy.currentData(),
        ), "LE CS Set Procedure Parameters")

    def _procedure_enable(self, enable: bool):
        handle = self.handle()
        if handle is None:
            return
        if enable:
            self.results.clear()
        self.send(lambda: le_cmds.LeCsProcedureEnable(
            connection_handle=handle, config_id=self.config_id.value(),
            enable=enable),
            f"LE CS Procedure {'Enable' if enable else 'Disable'}")

    def _full_setup(self):
        handle = self.handle()
        if handle is None:
            return
        self.send(lambda: le_cmds.LeCsSecurityEnable(handle),
                  "LE CS Security Enable")
        self._set_defaults()
        self._create_config()
        self._set_procedure_params()


# ------------------------------------------------------------------ the window

class LeControlWindow(QWidget):
    """Attaches the LE panels to a chosen HCI session."""

    _instance: Optional['LeControlWindow'] = None

    # Session callbacks land on the I/O thread; these carry them to Qt.
    _result = pyqtSignal(str)
    _adv_report = pyqtSignal(object)
    _cs_line = pyqtSignal(str)
    _connections_changed = pyqtSignal()

    @classmethod
    def create_instance(cls, main_window: QMainWindow) -> 'LeControlWindow':
        existing = cls._instance
        if existing is not None:
            try:
                existing.sub_window.show()
                existing.sub_window.raise_()
                existing.sub_window.activateWindow()
                existing.refresh_sessions()
                return existing
            except RuntimeError:
                cls._instance = None

        cls._instance = cls(main_window)
        return cls._instance

    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.session = None
        self._attached: Optional[HciMainUI] = None
        self._is_destroyed = False

        self._build_ui()
        self._build_subwindow()

        self._result.connect(self._append_log)
        self._cs_line.connect(self.cs_panel.add_result)
        self._adv_report.connect(self.scanning_panel.add_report)
        self._connections_changed.connect(self.connection_panel.refresh_connections)

        self.refresh_sessions()

    # ---- layout

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("HCI session:"))
        self.session_combo = QComboBox()
        self.session_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.session_combo.currentIndexChanged.connect(self._on_session_chosen)
        source_row.addWidget(self.session_combo, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_sessions())
        source_row.addWidget(refresh_btn)

        self.state_label = QLabel("not attached")
        self.state_label.setStyleSheet("color: gray;")
        source_row.addWidget(self.state_label)
        root.addLayout(source_row)

        splitter = QSplitter(Qt.Vertical)

        self.tabs = QTabWidget()
        self.advertising_panel = AdvertisingPanel(self)
        self.scanning_panel = ScanningPanel(self)
        self.connection_panel = ConnectionPanel(self)
        self.cs_panel = ChannelSoundingPanel(self)
        # Scrolled: the Channel Sounding panel in particular is taller than any
        # sensible window, and without this its rows compress into each other.
        self.tabs.addTab(_scrolled(self.advertising_panel), "Advertising")
        self.tabs.addTab(_scrolled(self.scanning_panel), "Scanning")
        self.tabs.addTab(_scrolled(self.connection_panel), "Connection")
        self.tabs.addTab(_scrolled(self.cs_panel), "Channel Sounding")
        splitter.addWidget(self.tabs)

        log_box = QGroupBox("Command log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setFont(QFont("Menlo", 10))
        log_layout.addWidget(self.log_view)
        splitter.addWidget(log_box)

        splitter.setSizes([620, 180])
        root.addWidget(splitter, 1)

    def _build_subwindow(self) -> None:
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWindowTitle("LE Control")
        self.sub_window.setWidget(self)
        self.sub_window.setWindowFlags(Qt.Window)
        self.sub_window.resize(760, 900)
        self.sub_window.setMinimumSize(560, 560)
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)
        self.sub_window.destroyed.connect(lambda *_: self.cleanup())

        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        self.sub_window.raise_()
        self.sub_window.activateWindow()

    # ---- session attach

    def refresh_sessions(self, ignore: Optional[HciMainUI] = None) -> None:
        if self._is_destroyed:
            return
        previous = self.session_combo.currentData()
        instances = [inst for inst in HciMainUI.get_live_sessions()
                     if inst is not ignore]

        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        for instance in instances:
            self.session_combo.addItem(instance.title, instance)
        self.session_combo.blockSignals(False)

        if not instances:
            self._detach()
            self.state_label.setText("no HCI session -- open Tools > HCI")
            return

        index = self.session_combo.findData(previous)
        self.session_combo.setCurrentIndex(index if index >= 0 else 0)
        self._on_session_chosen(self.session_combo.currentIndex())

    def _on_session_chosen(self, index: int) -> None:
        if self._is_destroyed or index < 0:
            return
        instance = self.session_combo.itemData(index)
        if instance is None or instance is self._attached:
            return
        self._attach(instance)

    def _attach(self, instance: HciMainUI) -> None:
        self._detach()
        session = getattr(instance, 'session', None)
        if session is None:
            return

        self._attached = instance
        self.session = session

        session.on(EVT_ADV_REPORT, self._on_adv_report)
        session.on(EVT_CONNECTION_UP, self._on_connection_up)
        session.on(EVT_CONNECTION_DOWN, self._on_connection_down)
        session.on(EVT_STATE, self._on_state)
        session.on(EVT_ERROR, self._on_error)
        session.on(EVT_EVENT, self._on_event)

        instance.session_closing.connect(self._on_session_closing)

        self.sub_window.setWindowTitle(f"LE Control - {instance.title}")
        self.state_label.setText("attached")
        self.connection_panel.refresh_connections()
        self.log(f"= attached to {instance.title}")

    def _detach(self) -> None:
        session, self.session = self.session, None
        if session is not None:
            for channel, handler in (
                (EVT_ADV_REPORT, self._on_adv_report),
                (EVT_CONNECTION_UP, self._on_connection_up),
                (EVT_CONNECTION_DOWN, self._on_connection_down),
                (EVT_STATE, self._on_state),
                (EVT_ERROR, self._on_error),
                (EVT_EVENT, self._on_event),
            ):
                try:
                    session.off(channel, handler)
                except Exception:
                    pass

        if self._attached is not None:
            try:
                self._attached.session_closing.disconnect(self._on_session_closing)
            except (TypeError, RuntimeError):
                pass
            self._attached = None

        try:
            self.sub_window.setWindowTitle("LE Control")
            self.state_label.setText("not attached")
        except RuntimeError:
            pass

    def _on_session_closing(self, instance) -> None:
        self._detach()
        self.refresh_sessions(ignore=instance)

    # ---- sending

    def send(self, builder: Callable, label: str) -> None:
        """
        Build the command, send it, and log the completion.

        A build error (bad address, impossible interval) is reported here rather
        than raised: these are called straight from button clicks, where an
        exception would only reach the console.
        """
        if self.session is None:
            self.log("! no session attached")
            return
        try:
            command = builder()
        except Exception as exc:            # noqa: BLE001 - user input error
            self.log(f"! {label}: {exc}")
            return

        def _done(response, error) -> None:
            # I/O thread.
            if error is not None:
                self._result.emit(f"! {label}: {error}")
            else:
                status = None
                if response is not None:
                    status = getattr(response, 'params', {}).get('status')
                self._result.emit(
                    f"< {label}: ok" if status in (0x00, None)
                    else f"! {label}: status 0x{status:02X}")

        self.log(f"> {label}")
        try:
            self.session.send(command, on_complete=_done)
        except Exception as exc:            # noqa: BLE001
            self.log(f"! {label}: {exc}")

    def log(self, message: str) -> None:
        """Safe from any thread."""
        self._result.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    # ---- session observers (I/O thread)

    def _on_adv_report(self, report: dict) -> None:
        self._adv_report.emit(report)

    def _on_connection_up(self, info) -> None:
        self._result.emit(f"+ connected {info}")
        self._connections_changed.emit()

    def _on_connection_down(self, info, handle: int, reason: int) -> None:
        self._result.emit(f"- disconnected handle 0x{handle:04X} "
                          f"(reason 0x{reason:02X})")
        self._connections_changed.emit()

    def _on_state(self, name: str, value) -> None:
        if name in ("advertising", "scanning"):
            self._result.emit(f"= {name}: {'on' if value else 'off'}")

    def _on_error(self, message: str) -> None:
        self._result.emit(f"! {message}")

    #: LE meta sub-events the Channel Sounding tab mirrors into its result pane.
    _CS_SUBEVENTS = frozenset({
        LeMetaEventSubCode.CS_READ_REMOTE_SUPPORTED_CAPABILITIES_COMPLETE,
        LeMetaEventSubCode.CS_READ_REMOTE_FAE_TABLE_COMPLETE,
        LeMetaEventSubCode.CS_SECURITY_ENABLE_COMPLETE,
        LeMetaEventSubCode.CS_CONFIG_COMPLETE,
        LeMetaEventSubCode.CS_PROCEDURE_ENABLE_COMPLETE,
        LeMetaEventSubCode.CS_SUBEVENT_RESULT,
        LeMetaEventSubCode.CS_SUBEVENT_RESULT_CONTINUE,
        LeMetaEventSubCode.CS_TEST_END_COMPLETE,
    })

    def _on_event(self, event) -> None:
        """Mirror the events these panels care about; the rest is in the log window."""
        if getattr(event, 'EVENT_CODE', None) != HciEventCode.LE_META_EVENT:
            return
        sub = getattr(event, 'SUB_EVENT_CODE', None)
        if sub in self._CS_SUBEVENTS:
            self._cs_line.emit(str(event))
        elif sub in (LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_ESTABLISHED,
                     LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_LOST,
                     LeMetaEventSubCode.SCAN_TIMEOUT,
                     LeMetaEventSubCode.ADVERTISING_SET_TERMINATED):
            self._result.emit(f"< {event}")

    # ---- teardown

    def cleanup(self) -> None:
        if self._is_destroyed:
            return
        self._is_destroyed = True
        self._detach()
        if LeControlWindow._instance is self:
            LeControlWindow._instance = None


__all__ = ["LeControlWindow"]
