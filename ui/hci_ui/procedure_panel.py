"""
Procedures panel -- the UI for the four POC flows.

Buttons for advertise / scan / LE connect / BR-EDR inquiry, a live device table,
a connection list, and a log. The per-command dialogs stay available for expert
use; this panel is for "just connect to that thing".

Threading: procedures block (they wait on controller events), so every one of
them runs on a worker thread. Results come back to the Qt main thread through
signals -- never touch a widget from the worker.
"""

from __future__ import annotations

from typing import Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hci.session import HciSession, procedures
from hci.session.connection import ConnectionInfo, LinkType
from hci.session.procedures import DiscoveredDevice
from hci.session.session import (
    EVT_CONNECTION_DOWN,
    EVT_CONNECTION_UP,
    EVT_ERROR,
    EVT_STATE,
    CommandError,
)


class ProcedurePanel(QWidget):
    """Drives advertise / scan / connect / inquiry against one session."""

    # Cross-thread plumbing: workers emit, the main thread renders.
    _log_line = pyqtSignal(str)
    _device_found = pyqtSignal(object)
    _refresh_connections = pyqtSignal()
    _busy_changed = pyqtSignal(bool)

    def __init__(self, session: HciSession, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session = session
        self._devices: Dict[str, DiscoveredDevice] = {}
        self._busy = False

        self._build_ui()

        self._log_line.connect(self._append_log)
        self._device_found.connect(self._add_device_row)
        self._refresh_connections.connect(self._rebuild_connection_list)
        self._busy_changed.connect(self._set_busy)

        self.session.on(EVT_CONNECTION_UP, self._on_connection_up)
        self.session.on(EVT_CONNECTION_DOWN, self._on_connection_down)
        self.session.on(EVT_ERROR, lambda msg: self._log_line.emit(f"! {msg}"))
        self.session.on(EVT_STATE, self._on_state)

    # --------------------------------------------------------------- layout

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # ---- controller row
        controller_box = QGroupBox("Controller")
        controller_row = QHBoxLayout(controller_box)
        self.init_btn = QPushButton("Initialise")
        self.init_btn.setToolTip(
            "Reset, read BD_ADDR/version, unmask events. Run this first.")
        self.init_btn.clicked.connect(self._do_initialize)
        self.status_label = QLabel("not initialised")
        self.status_label.setStyleSheet("color: gray;")
        controller_row.addWidget(self.init_btn)
        controller_row.addWidget(self.status_label, 1)
        root.addWidget(controller_box)

        # ---- LE row
        le_box = QGroupBox("LE")
        le_layout = QVBoxLayout(le_box)

        adv_row = QHBoxLayout()
        adv_row.addWidget(QLabel("Name:"))
        self.adv_name = QLineEdit("HCI Tool")
        self.adv_name.setMaximumWidth(160)
        adv_row.addWidget(self.adv_name)
        self.adv_btn = QPushButton("Start Advertising")
        self.adv_btn.clicked.connect(self._toggle_advertising)
        adv_row.addWidget(self.adv_btn)
        adv_row.addStretch(1)
        le_layout.addLayout(adv_row)

        scan_row = QHBoxLayout()
        scan_row.addWidget(QLabel("Scan for:"))
        self.scan_duration = QDoubleSpinBox()
        self.scan_duration.setRange(1.0, 120.0)
        self.scan_duration.setValue(5.0)
        self.scan_duration.setSuffix(" s")
        self.scan_duration.setMaximumWidth(80)
        scan_row.addWidget(self.scan_duration)
        self.scan_active = QCheckBox("Active")
        self.scan_active.setChecked(True)
        self.scan_active.setToolTip(
            "Active scanning sends SCAN_REQ, which collects scan response data "
            "(usually the device name).")
        scan_row.addWidget(self.scan_active)
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self._do_scan)
        scan_row.addWidget(self.scan_btn)
        scan_row.addStretch(1)
        le_layout.addLayout(scan_row)
        root.addWidget(le_box)

        # ---- BR/EDR row
        bredr_box = QGroupBox("BR/EDR")
        bredr_row = QHBoxLayout(bredr_box)
        bredr_row.addWidget(QLabel("Inquiry:"))
        self.inquiry_units = QComboBox()
        for units in (4, 8, 12, 16):
            self.inquiry_units.addItem(f"{units * 1.28:.1f} s", units)
        self.inquiry_units.setCurrentIndex(1)
        bredr_row.addWidget(self.inquiry_units)
        self.inquiry_btn = QPushButton("Inquiry")
        self.inquiry_btn.clicked.connect(self._do_inquiry)
        bredr_row.addWidget(self.inquiry_btn)
        bredr_row.addStretch(1)
        root.addWidget(bredr_box)

        # ---- devices + connections + log
        splitter = QSplitter(Qt.Vertical)

        device_box = QGroupBox("Discovered devices")
        device_layout = QVBoxLayout(device_box)
        self.device_table = QTableWidget(0, 5)
        self.device_table.setHorizontalHeaderLabels(
            ["Address", "Name", "RSSI", "Type", "Info"])
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.device_table.itemDoubleClicked.connect(lambda _: self._do_connect())
        device_layout.addWidget(self.device_table)

        device_buttons = QHBoxLayout()
        self.connect_btn = QPushButton("Connect to selected")
        self.connect_btn.clicked.connect(self._do_connect)
        device_buttons.addWidget(self.connect_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_devices)
        device_buttons.addWidget(clear_btn)
        device_buttons.addStretch(1)
        device_layout.addLayout(device_buttons)
        splitter.addWidget(device_box)

        conn_box = QGroupBox("Connections")
        conn_layout = QVBoxLayout(conn_box)
        self.conn_table = QTableWidget(0, 4)
        self.conn_table.setHorizontalHeaderLabels(
            ["Handle", "Address", "Type", "Role"])
        self.conn_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.conn_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.conn_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        conn_layout.addWidget(self.conn_table)
        disconnect_btn = QPushButton("Disconnect selected")
        disconnect_btn.clicked.connect(self._do_disconnect)
        conn_layout.addWidget(disconnect_btn)
        splitter.addWidget(conn_box)

        log_box = QGroupBox("Procedure log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setFont(QFont("Menlo", 10))
        log_layout.addWidget(self.log_view)
        splitter.addWidget(log_box)

        splitter.setSizes([260, 140, 200])
        root.addWidget(splitter, 1)

    # -------------------------------------------------------- worker helpers

    def _run(self, fn, *args, **kwargs) -> None:
        """
        Run a procedure on a worker thread.

        Procedures block waiting on controller events; running one on the Qt
        thread would freeze the UI and deadlock the packet callbacks.
        """
        if self._busy:
            self._append_log("! a procedure is already running")
            return

        def _wrapped():
            self._busy_changed.emit(True)
            try:
                fn(*args, **kwargs)
            except CommandError as exc:
                self._log_line.emit(f"! {exc}")
            except Exception as exc:  # noqa: BLE001 - surface anything to the log
                self._log_line.emit(f"! unexpected error: {exc!r}")
            finally:
                self._busy_changed.emit(False)
                self._refresh_connections.emit()

        procedures.run_in_thread(_wrapped)

    def _report(self, message: str) -> None:
        """Reporter handed to the procedures; called from the worker thread."""
        self._log_line.emit(message)

    # --------------------------------------------------------------- actions

    def _do_initialize(self) -> None:
        def work():
            procedures.initialize_controller(self.session, reporter=self._report)
            summary = self.session.status_summary()
            self._log_line.emit(
                f"= {summary['local_bd_addr']} HCI v{summary['hci_version']}")

        self._run(work)

    def _toggle_advertising(self) -> None:
        if self.session.is_advertising:
            self._run(procedures.stop_advertising, self.session,
                      reporter=self._report)
        else:
            self._run(procedures.start_advertising, self.session,
                      local_name=self.adv_name.text() or "HCI Tool",
                      reporter=self._report)

    def _do_scan(self) -> None:
        self._run(procedures.scan_le, self.session,
                  duration=self.scan_duration.value(),
                  active=self.scan_active.isChecked(),
                  on_device=lambda d: self._device_found.emit(d),
                  reporter=self._report)

    def _do_inquiry(self) -> None:
        self._run(procedures.inquiry, self.session,
                  duration_units=self.inquiry_units.currentData(),
                  on_device=lambda d: self._device_found.emit(d),
                  reporter=self._report)

    def _do_connect(self) -> None:
        row = self.device_table.currentRow()
        if row < 0:
            self._append_log("! select a device first")
            return
        address = self.device_table.item(row, 0).text()
        device = self._devices.get(address)
        if device is None:
            self._append_log(f"! unknown device {address}")
            return

        if device.link_type is LinkType.BR_EDR:
            self._run(procedures.connect_bredr, self.session, address,
                      reporter=self._report)
        else:
            self._run(procedures.connect_le, self.session, address,
                      peer_address_type=device.address_type,
                      reporter=self._report)

    def _do_disconnect(self) -> None:
        row = self.conn_table.currentRow()
        if row < 0:
            self._append_log("! select a connection first")
            return
        handle = int(self.conn_table.item(row, 0).text(), 16)
        self._run(procedures.disconnect, self.session, handle,
                  reporter=self._report)

    def _clear_devices(self) -> None:
        self._devices.clear()
        self.device_table.setRowCount(0)

    # ------------------------------------------------- main-thread rendering

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for widget in (self.init_btn, self.adv_btn, self.scan_btn,
                       self.inquiry_btn, self.connect_btn):
            widget.setEnabled(not busy)
        if not busy:
            self._sync_adv_button()

    def _sync_adv_button(self) -> None:
        self.adv_btn.setText(
            "Stop Advertising" if self.session.is_advertising else "Start Advertising")

    def _add_device_row(self, device: DiscoveredDevice) -> None:
        if device.address in self._devices:
            self._devices[device.address] = device
            return
        self._devices[device.address] = device

        row = self.device_table.rowCount()
        self.device_table.insertRow(row)

        info_bits = []
        if device.services:
            info_bits.append(f"services: {', '.join(device.services[:3])}")
        if device.manufacturer_id is not None:
            info_bits.append(f"mfr 0x{device.manufacturer_id:04X}")
        if device.class_of_device is not None:
            info_bits.append(f"CoD 0x{device.class_of_device:06X}")

        values = [
            device.address,
            device.name or "",
            "" if device.rssi is None else f"{device.rssi} dBm",
            device.link_type.value,
            "; ".join(info_bits),
        ]
        for column, text in enumerate(values):
            item = QTableWidgetItem(text)
            if column == 2 and device.rssi is not None:
                # Green for strong, amber mid, red for marginal.
                if device.rssi >= -60:
                    item.setForeground(QColor("#2e7d32"))
                elif device.rssi >= -80:
                    item.setForeground(QColor("#ef6c00"))
                else:
                    item.setForeground(QColor("#c62828"))
            self.device_table.setItem(row, column, item)

    def _rebuild_connection_list(self) -> None:
        self.conn_table.setRowCount(0)
        for info in self.session.connections.all():
            row = self.conn_table.rowCount()
            self.conn_table.insertRow(row)
            for column, text in enumerate([
                f"{info.handle:04X}",
                info.bd_addr,
                info.link_type.value,
                info.role.value,
            ]):
                self.conn_table.setItem(row, column, QTableWidgetItem(text))

    # -------------------------------------------------- session observers

    def _on_connection_up(self, info: ConnectionInfo) -> None:
        self._log_line.emit(f"+ connected {info}")
        self._refresh_connections.emit()

    def _on_connection_down(self, info, handle: int, reason: int) -> None:
        self._log_line.emit(f"- disconnected handle 0x{handle:04X} "
                            f"(reason 0x{reason:02X})")
        self._refresh_connections.emit()

    def _on_state(self, name: str, value) -> None:
        if name in ("advertising", "scanning", "inquiring"):
            self._log_line.emit(f"= {name}: {'on' if value else 'off'}")
        elif name == "local_bd_addr":
            self._log_line.emit(f"= local address {value}")

    def cleanup(self) -> None:
        for channel, handler in (
            (EVT_CONNECTION_UP, self._on_connection_up),
            (EVT_CONNECTION_DOWN, self._on_connection_down),
            (EVT_STATE, self._on_state),
        ):
            try:
                self.session.off(channel, handler)
            except Exception:
                pass


__all__ = ["ProcedurePanel"]
