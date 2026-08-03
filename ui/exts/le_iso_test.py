"""
LE ISO test screen -- CIS, BIS and the controller's own ISO test modes.

Three ways to exercise an isochronous stream, on three tabs:

* **CIS** -- connected isochronous. Announce host support, configure a CIG,
  create the stream against an ACL link, then set up the data path.
* **BIS** -- broadcast isochronous. Create a BIG on an advertising set that is
  already running periodic advertising, or sync to someone else's.
* **ISO Test** -- the controller generates and checks the payloads itself
  (LE ISO Transmit/Receive Test), which is how you measure the air interface
  without the host being the bottleneck.

Audio routing works as it does for SCO. Over HCI, ISO SDUs are HCI ISO packets
on the command link. Offloaded, `LE_Setup_ISO_Data_Path` is given a vendor
Data_Path_ID instead of 0, the controller routes the audio to that interface,
and this tool streams it over a second UART -- so HCI carries only control.

The step people miss is the data path: a CIS that reports Established but never
had `LE_Setup_ISO_Data_Path` sent carries nothing in that direction, in either
routing mode.
"""

from __future__ import annotations

import struct
import threading
import time
from typing import Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

import hci.cmd.le_cmds as le_cmds
from hci.evt.evt_codes import HciEventCode, LeMetaEventSubCode
from hci.hci_packet import HciIsoDataPacket
from hci.session.connection import LinkType

from .audio_offload import AudioOffloadPanel, AudioRoute, format_bytes, format_rate
from .test_window_base import SessionTestWindow, connection_combo_items


def _spin(minimum, maximum, value, tip="", suffix="") -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    if tip:
        box.setToolTip(tip)
    if suffix:
        box.setSuffix(suffix)
    return box


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: gray; font-size: 10pt;")
    label.setWordWrap(True)
    return label


def _scrolled(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidget(widget)
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    return area


class _IsoSender(threading.Thread):
    """
    Paces ISO SDUs at the configured SDU interval.

    Like SCO, an isochronous stream is rate-driven: the controller transmits one
    SDU per interval whether or not the host supplied one. Sending faster does
    not raise the throughput, it just backs up.
    """

    def __init__(self, window: "LeIsoTestWindow", handle: int, sdu_size: int,
                 interval_us: int, duration: float):
        super().__init__(name="hci-iso-tx", daemon=True)
        self.window = window
        self.handle = handle
        self.sdu_size = sdu_size
        self.interval = interval_us / 1_000_000.0
        self.duration = duration
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:            # noqa: BLE001
            self.window.log(f"! ISO sender stopped: {exc!r}")
        finally:
            self.window.sender_finished_signal.emit()

    def _run(self) -> None:
        sequence = 0
        deadline = time.monotonic() + self.duration if self.duration else None
        next_send = time.monotonic()

        while not self._stop.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break

            # A counted payload: the sequence number appears in the data as well
            # as the header, so a capture on the far side can be checked without
            # decoding ISO headers.
            payload = struct.pack("<I", sequence & 0xFFFFFFFF) + bytes(
                (sequence + i) & 0xFF for i in range(max(self.sdu_size - 4, 0)))
            self.window.send_sdu(self.handle, payload, sequence)
            sequence += 1

            next_send += self.interval
            sleep_for = next_send - time.monotonic()
            if sleep_for > 0:
                self._stop.wait(sleep_for)
            else:
                next_send = time.monotonic()


class LeIsoTestWindow(SessionTestWindow):
    """CIS / BIS setup, ISO data streaming and the ISO test modes."""

    WINDOW_TITLE = "LE ISO Test"
    WINDOW_SIZE = (800, 940)

    sender_finished_signal = pyqtSignal()

    def __init__(self, main_window):
        self._sender: Optional[_IsoSender] = None
        self._iso_handles: list = []
        self.tx_packets = self.tx_bytes = 0
        self.rx_packets = self.rx_bytes = 0
        self._stream_started = 0.0
        super().__init__(main_window)

        self.sender_finished_signal.connect(self.sender_finished)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(400)

    # ----------------------------------------------------------------- layout

    def build_body(self, layout: QVBoxLayout) -> None:
        tabs = QTabWidget()
        tabs.addTab(_scrolled(self._cis_tab()), "CIS")
        tabs.addTab(_scrolled(self._bis_tab()), "BIS")
        tabs.addTab(_scrolled(self._stream_tab()), "Data Path && Stream")
        tabs.addTab(_scrolled(self._test_tab()), "ISO Test Mode")
        layout.addWidget(tabs)

    def _cis_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        host_btn = QPushButton("Set Host Feature: Connected ISO (bit 32)")
        host_btn.setToolTip("Required before the controller accepts any CIG "
                            "command, and only accepted with no connections up")
        host_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeSetHostFeature(
                bit_number=le_cmds.HostFeatureBit.CONNECTED_ISOCHRONOUS_STREAMS,
                bit_value=1),
            "LE Set Host Feature (CIS)"))
        form.addRow("Step 1:", host_btn)

        self.cig_id_input = _spin(0x00, 0xEF, 0x00)
        form.addRow("CIG ID:", self.cig_id_input)

        self.cis_id_input = _spin(0x00, 0xEF, 0x00)
        form.addRow("CIS ID:", self.cis_id_input)

        self.sdu_interval_input = _spin(255, 0x0FFFFF, 10000,
                                        "SDU interval each way", " us")
        form.addRow("SDU Interval:", self.sdu_interval_input)

        self.max_sdu_input = _spin(0, 0x0FFF, 40, "Largest SDU each way", " bytes")
        form.addRow("Max SDU:", self.max_sdu_input)

        self.phy_combo = QComboBox()
        for label, value in (("LE 2M", 0x02), ("LE 1M", 0x01), ("LE Coded", 0x04)):
            self.phy_combo.addItem(label, value)
        form.addRow("PHY:", self.phy_combo)

        self.rtn_input = _spin(0, 255, 2, "Retransmission count target")
        form.addRow("RTN:", self.rtn_input)

        self.latency_input = _spin(5, 4000, 10, "Max transport latency", " ms")
        form.addRow("Max Transport Latency:", self.latency_input)

        self.framing_combo = QComboBox()
        self.framing_combo.addItem("Unframed", 0x00)
        self.framing_combo.addItem("Framed", 0x01)
        form.addRow("Framing:", self.framing_combo)

        cig_btn = QPushButton("Set CIG Parameters")
        cig_btn.clicked.connect(self._set_cig)
        remove_btn = QPushButton("Remove CIG")
        remove_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeRemoveCig(self.cig_id_input.value()),
            "LE Remove CIG"))
        form.addRow("Step 2:", self._row(cig_btn, remove_btn))

        self.acl_combo = QComboBox()
        self.acl_combo.setToolTip("The LE ACL link the CIS rides on")
        form.addRow("ACL Connection:", self.acl_combo)

        self.cis_handle_input = _spin(0x0000, 0x0EFF, 0x0060,
                                      "CIS handle from the Set CIG Parameters "
                                      "Command Complete")
        form.addRow("CIS Handle:", self.cis_handle_input)

        create_btn = QPushButton("Create CIS")
        create_btn.clicked.connect(self._create_cis)
        accept_btn = QPushButton("Accept CIS Request")
        accept_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeAcceptCisRequest(self.cis_handle_input.value()),
            "LE Accept CIS Request"))
        reject_btn = QPushButton("Reject")
        reject_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeRejectCisRequest(self.cis_handle_input.value(), 0x13),
            "LE Reject CIS Request"))
        form.addRow("Step 3:", self._row(create_btn, accept_btn, reject_btn))

        form.addRow("", _hint(
            "The central creates the CIS; a peripheral answers the incoming "
            "LE CIS Request with accept or reject instead. The Set CIG "
            "Parameters Command Complete is what tells you the CIS handle."))
        return page

    def _bis_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.big_handle_input = _spin(0x00, 0xEF, 0x00)
        form.addRow("BIG Handle:", self.big_handle_input)

        self.big_adv_handle_input = _spin(0x00, 0xEF, 0x00,
                                          "Advertising set already running "
                                          "periodic advertising")
        form.addRow("Advertising Handle:", self.big_adv_handle_input)

        self.num_bis_input = _spin(1, 31, 1)
        form.addRow("Number of BIS:", self.num_bis_input)

        self.big_sdu_interval_input = _spin(255, 0x0FFFFF, 10000, "", " us")
        form.addRow("SDU Interval:", self.big_sdu_interval_input)

        self.big_max_sdu_input = _spin(1, 0x0FFF, 40, "", " bytes")
        form.addRow("Max SDU:", self.big_max_sdu_input)

        self.big_latency_input = _spin(5, 4000, 10, "", " ms")
        form.addRow("Max Transport Latency:", self.big_latency_input)

        self.big_rtn_input = _spin(0, 30, 2)
        form.addRow("RTN:", self.big_rtn_input)

        self.big_encrypt_input = QCheckBox("Encrypt the BIG")
        self.big_encrypt_input.stateChanged.connect(
            lambda: self.big_code_input.setEnabled(
                self.big_encrypt_input.isChecked()))
        form.addRow("Encryption:", self.big_encrypt_input)

        self.big_code_input = QLineEdit()
        self.big_code_input.setPlaceholderText("16-byte broadcast code, hex")
        self.big_code_input.setEnabled(False)
        form.addRow("Broadcast Code:", self.big_code_input)

        create_btn = QPushButton("Create BIG")
        create_btn.clicked.connect(self._create_big)
        terminate_btn = QPushButton("Terminate BIG")
        terminate_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeTerminateBig(self.big_handle_input.value(), 0x16),
            "LE Terminate BIG"))
        form.addRow("Transmitter:", self._row(create_btn, terminate_btn))

        self.sync_handle_input = _spin(0x0000, 0x0EFF, 0x0000,
                                       "Sync handle from LE Periodic "
                                       "Advertising Sync Established")
        form.addRow("Sync Handle:", self.sync_handle_input)

        self.bis_indices_input = QLineEdit("1")
        self.bis_indices_input.setPlaceholderText("Comma-separated, e.g. 1,2")
        form.addRow("BIS Indices:", self.bis_indices_input)

        self.big_timeout_input = _spin(0x000A, 0x4000, 100,
                                       "BIG sync timeout, in 10 ms units")
        form.addRow("BIG Sync Timeout:", self.big_timeout_input)

        sync_btn = QPushButton("BIG Create Sync")
        sync_btn.clicked.connect(self._big_create_sync)
        unsync_btn = QPushButton("BIG Terminate Sync")
        unsync_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeBigTerminateSync(self.big_handle_input.value()),
            "LE BIG Terminate Sync"))
        form.addRow("Receiver:", self._row(sync_btn, unsync_btn))

        form.addRow("", _hint(
            "A BIG hangs off a periodic advertising train -- set up extended "
            "and periodic advertising on that handle first (Tools > LE "
            "Control), or receivers have no BIGInfo to find and nothing can "
            "ever sync."))
        return page

    def _stream_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        self.offload_panel = AudioOffloadPanel("Audio routing")
        root.addWidget(self.offload_panel)

        path_box = QGroupBox("ISO data path")
        path_form = QFormLayout(path_box)

        self.path_handle_input = _spin(0x0000, 0x0EFF, 0x0060,
                                       "CIS or BIS connection handle")
        path_form.addRow("Connection Handle:", self.path_handle_input)

        self.coding_combo = QComboBox()
        for coding in le_cmds.CodingFormat:
            self.coding_combo.addItem(
                coding.name.replace('_', ' ').title(), int(coding))
        index = self.coding_combo.findData(int(le_cmds.CodingFormat.TRANSPARENT))
        if index >= 0:
            self.coding_combo.setCurrentIndex(index)
        path_form.addRow("Coding Format:", self.coding_combo)

        self.delay_input = _spin(0, 4000000, 0, "Controller delay", " us")
        path_form.addRow("Controller Delay:", self.delay_input)

        input_btn = QPushButton("Setup Input Path (TX)")
        input_btn.clicked.connect(lambda: self._setup_path(
            le_cmds.DataPathDirection.INPUT))
        output_btn = QPushButton("Setup Output Path (RX)")
        output_btn.clicked.connect(lambda: self._setup_path(
            le_cmds.DataPathDirection.OUTPUT))
        remove_btn = QPushButton("Remove Both")
        remove_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeRemoveIsoDataPath(
                self.path_handle_input.value(),
                le_cmds.DataPathDirectionMask.BOTH),
            "LE Remove ISO Data Path"))
        path_form.addRow("", self._row(input_btn, output_btn, remove_btn))

        path_form.addRow("", _hint(
            "One command per direction. The Data_Path_ID comes from the "
            "routing panel above: 0 keeps the audio on HCI, a vendor id sends "
            "it to the offload interface. A direction never set up carries "
            "nothing, which is the usual reason a stream establishes but no "
            "audio flows."))
        root.addWidget(path_box)

        stream_box = QGroupBox("Stream")
        stream_form = QFormLayout(stream_box)

        self.stream_handle_combo = QComboBox()
        self.stream_handle_combo.setEditable(True)
        stream_form.addRow("ISO Handle:", self.stream_handle_combo)

        self.sdu_size_input = _spin(1, 0x0FFF, 40, "", " bytes")
        stream_form.addRow("SDU Size:", self.sdu_size_input)

        self.stream_interval_input = _spin(255, 0x0FFFFF, 10000,
                                           "Must match the SDU interval the "
                                           "CIG or BIG was configured with",
                                           " us")
        stream_form.addRow("SDU Interval:", self.stream_interval_input)

        self.stream_duration_input = _spin(0, 3600, 10, "0 = until stopped", " s")
        stream_form.addRow("Duration:", self.stream_duration_input)

        self.start_btn = QPushButton("Start Streaming")
        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_stream)
        stream_form.addRow("", self._row(self.start_btn, self.stop_btn))

        root.addWidget(stream_box)

        stats = QGroupBox("Statistics")
        grid = QGridLayout(stats)
        self._stat_labels = {}
        for index, (title, key) in enumerate((
                ("TX SDUs", "tx_packets"), ("TX bytes", "tx_bytes"),
                ("TX rate", "tx_rate"), ("RX SDUs", "rx_packets"),
                ("RX bytes", "rx_bytes"), ("RX rate", "rx_rate"))):
            caption = QLabel(title)
            caption.setStyleSheet("color: gray; font-size: 10pt;")
            value = QLabel("-")
            grid.addWidget(caption, index // 3 * 2, index % 3)
            grid.addWidget(value, index // 3 * 2 + 1, index % 3)
            self._stat_labels[key] = value
        root.addWidget(stats)
        root.addStretch(1)
        return page

    def _test_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.test_handle_input = _spin(0x0000, 0x0EFF, 0x0060)
        form.addRow("Connection Handle:", self.test_handle_input)

        self.payload_combo = QComboBox()
        self.payload_combo.addItem("Zero length", 0x00)
        self.payload_combo.addItem("Variable length", 0x01)
        self.payload_combo.addItem("Maximum length", 0x02)
        self.payload_combo.setCurrentIndex(2)
        form.addRow("Payload Type:", self.payload_combo)

        tx_btn = QPushButton("Start Transmit Test")
        tx_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeIsoTransmitTest(self.test_handle_input.value(),
                                              self.payload_combo.currentData()),
            "LE ISO Transmit Test"))
        rx_btn = QPushButton("Start Receive Test")
        rx_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeIsoReceiveTest(self.test_handle_input.value(),
                                             self.payload_combo.currentData()),
            "LE ISO Receive Test"))
        form.addRow("", self._row(tx_btn, rx_btn))

        counters_btn = QPushButton("Read Test Counters")
        counters_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeIsoReadTestCounters(self.test_handle_input.value()),
            "LE ISO Read Test Counters", self._log_counters))
        end_btn = QPushButton("End Test")
        end_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeIsoTestEnd(self.test_handle_input.value()),
            "LE ISO Test End", self._log_counters))
        form.addRow("", self._row(counters_btn, end_btn))

        quality_btn = QPushButton("Read ISO Link Quality")
        quality_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeReadIsoLinkQuality(self.test_handle_input.value()),
            "LE Read ISO Link Quality", self._log_return_params))
        tx_sync_btn = QPushButton("Read ISO TX Sync")
        tx_sync_btn.clicked.connect(lambda: self.send(
            lambda: le_cmds.LeReadIsoTxSync(self.test_handle_input.value()),
            "LE Read ISO TX Sync", self._log_return_params))
        form.addRow("Diagnostics:", self._row(quality_btn, tx_sync_btn))

        form.addRow("", _hint(
            "In test mode the controller generates and checks the payloads "
            "itself, so no ISO data crosses HCI and the host is not the "
            "bottleneck. The receive side only counts correctly if its payload "
            "type matches what the transmitter is sending."))
        return page

    @staticmethod
    def _row(*widgets) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        return holder

    # ---------------------------------------------------------------- helpers

    def on_connections_changed(self) -> None:
        current = self.acl_combo.currentData()
        self.acl_combo.clear()
        for label, handle in connection_combo_items(self.session, LinkType.LE):
            self.acl_combo.addItem(label, handle)
        if current is not None:
            index = self.acl_combo.findData(current)
            if index >= 0:
                self.acl_combo.setCurrentIndex(index)

        text = self.stream_handle_combo.currentText()
        self.stream_handle_combo.clear()
        for handle in self._iso_handles:
            self.stream_handle_combo.addItem(f"0x{handle:04X}", handle)
        if text:
            self.stream_handle_combo.setEditText(text)

    def _stream_handle(self) -> Optional[int]:
        data = self.stream_handle_combo.currentData()
        if data is not None:
            return data
        text = self.stream_handle_combo.currentText().strip()
        try:
            return int(text, 0) if text else None
        except ValueError:
            return None

    def _log_counters(self, response, error) -> None:
        if error is not None or response is None:
            return
        extra = (getattr(response, 'params', {}) or {}).get('return_params') or b''
        # status(1) handle(2) received(4) missed(4) failed(4)
        if len(extra) >= 15:
            received, missed, failed = struct.unpack_from("<III", extra, 3)
            self._line.emit(f"= ISO counters: received={received} "
                            f"missed={missed} failed={failed}")

    def _log_return_params(self, response, error) -> None:
        if error is not None or response is None:
            return
        extra = (getattr(response, 'params', {}) or {}).get('return_params') or b''
        if extra:
            self._line.emit(f"= return parameters: {bytes(extra).hex(' ')}")

    def _on_event(self, event) -> None:
        """Pick up ISO handles as streams establish. I/O thread."""
        if getattr(event, 'EVENT_CODE', None) != HciEventCode.LE_META_EVENT:
            return
        sub = getattr(event, 'SUB_EVENT_CODE', None)
        params = getattr(event, 'params', {}) or {}

        if sub == LeMetaEventSubCode.CIS_ESTABLISHED:
            status = params.get('status', 0xFF)
            handle = params.get('connection_handle')
            if status == 0x00 and handle is not None:
                if handle not in self._iso_handles:
                    self._iso_handles.append(handle)
                self._line.emit(f"+ CIS established, handle 0x{handle:04X}")
                self._connections_changed.emit()
            else:
                self._line.emit(f"! CIS establish failed, status 0x{status:02X}")

        elif sub == LeMetaEventSubCode.CIS_REQUEST:
            handle = params.get('cis_connection_handle')
            self._line.emit(
                f"? incoming CIS request, handle 0x{handle:04X}"
                if handle is not None else "? incoming CIS request")

        elif sub in (LeMetaEventSubCode.CREATE_BIG_COMPLETE,
                     LeMetaEventSubCode.BIG_SYNC_ESTABLISHED):
            self._line.emit(f"< {event}")
            for handle in params.get('bis_connection_handles') or []:
                if handle not in self._iso_handles:
                    self._iso_handles.append(handle)
            self._connections_changed.emit()

    # ---------------------------------------------------------------- actions

    def _set_cig(self) -> None:
        phy = self.phy_combo.currentData()
        max_sdu = self.max_sdu_input.value()
        rtn = self.rtn_input.value()
        self.send(lambda: le_cmds.LeSetCigParameters(
            cig_id=self.cig_id_input.value(),
            sdu_interval_c_to_p=self.sdu_interval_input.value(),
            sdu_interval_p_to_c=self.sdu_interval_input.value(),
            framing=self.framing_combo.currentData(),
            max_transport_latency_c_to_p=self.latency_input.value(),
            max_transport_latency_p_to_c=self.latency_input.value(),
            cis_params=[(self.cis_id_input.value(), max_sdu, max_sdu,
                         phy, phy, rtn, rtn)],
        ), "LE Set CIG Parameters", self._log_cis_handles)

    def _log_cis_handles(self, response, error) -> None:
        if error is not None or response is None:
            return
        extra = (getattr(response, 'params', {}) or {}).get('return_params') or b''
        # status(1) cig_id(1) cis_count(1) then one handle per CIS
        if len(extra) >= 3:
            count = extra[2]
            handles = [struct.unpack_from("<H", extra, 3 + i * 2)[0]
                       for i in range(count) if len(extra) >= 5 + i * 2]
            if handles:
                self._line.emit("= CIS handles: "
                                + ", ".join(f"0x{h:04X}" for h in handles))

    def _create_cis(self) -> None:
        acl = self.acl_combo.currentData()
        if acl is None:
            self.log("! no LE connection -- connect first")
            return
        self.send(lambda: le_cmds.LeCreateCis(
            [(self.cis_handle_input.value(), acl)]), "LE Create CIS")

    def _broadcast_code(self) -> bytes:
        text = self.big_code_input.text().strip().replace(" ", "").replace("0x", "")
        if not text:
            return bytes(16)
        if len(text) % 2:
            text = "0" + text
        try:
            code = bytes.fromhex(text)
        except ValueError:
            raise ValueError(f"broadcast code is not valid hex: {text!r}")
        if len(code) > 16:
            raise ValueError(f"broadcast code is {len(code)} bytes; 16 is the max")
        return code.ljust(16, b"\x00")

    def _create_big(self) -> None:
        self.send(lambda: le_cmds.LeCreateBig(
            big_handle=self.big_handle_input.value(),
            adv_handle=self.big_adv_handle_input.value(),
            num_bis=self.num_bis_input.value(),
            sdu_interval=self.big_sdu_interval_input.value(),
            max_sdu=self.big_max_sdu_input.value(),
            max_transport_latency=self.big_latency_input.value(),
            rtn=self.big_rtn_input.value(),
            encryption=self.big_encrypt_input.isChecked(),
            broadcast_code=self._broadcast_code(),
        ), "LE Create BIG")

    def _big_create_sync(self) -> None:
        def build():
            text = self.bis_indices_input.text().replace(" ", "")
            if not text:
                raise ValueError("at least one BIS index is required")
            indices = [int(part, 0) for part in text.split(",") if part]
            return le_cmds.LeBigCreateSync(
                big_handle=self.big_handle_input.value(),
                sync_handle=self.sync_handle_input.value(),
                encryption=self.big_encrypt_input.isChecked(),
                broadcast_code=self._broadcast_code(),
                big_sync_timeout=self.big_timeout_input.value(),
                bis_indices=indices)

        self.send(build, "LE BIG Create Sync")

    def _setup_path(self, direction) -> None:
        path_id = self.offload_panel.data_path_id()
        name = ("input" if direction == le_cmds.DataPathDirection.INPUT
                else "output")
        self.send(lambda: le_cmds.LeSetupIsoDataPath(
            connection_handle=self.path_handle_input.value(),
            data_path_direction=direction,
            data_path_id=path_id,
            coding_format=self.coding_combo.currentData(),
            controller_delay=self.delay_input.value(),
        ), f"LE Setup ISO Data Path ({name}, path {path_id})")

    # --------------------------------------------------------------- streaming

    def send_sdu(self, handle: int, payload: bytes, sequence: int) -> None:
        """One SDU out, over whichever route is selected. Called on the sender."""
        if self.offload_panel.is_offloaded():
            ok = self.offload_panel.link.write(payload)
        else:
            packet = HciIsoDataPacket(connection_handle=handle, data=payload,
                                      packet_sequence_number=sequence & 0xFFFF)
            ok = self.write_packet(packet.to_bytes())
        if ok:
            self.tx_packets += 1
            self.tx_bytes += len(payload)

    def start_stream(self) -> None:
        if self._sender is not None:
            return

        route = self.offload_panel.route()
        if route is AudioRoute.CONTROLLER_INTERNAL:
            self.log("! route is controller-internal: the audio never reaches "
                     "the host, so there is nothing to stream from here")
            return
        if route is AudioRoute.SEPARATE_INTERFACE and not self.offload_panel.link.is_open:
            self.log("! open the audio interface first")
            return

        handle = self._stream_handle()
        if handle is None and route is not AudioRoute.SEPARATE_INTERFACE:
            self.log("! no ISO handle -- establish a CIS or BIG first")
            return

        self.tx_packets = self.tx_bytes = 0
        self.rx_packets = self.rx_bytes = 0
        self._stream_started = time.monotonic()
        self.offload_panel.link.set_receiver(self._on_audio_rx)

        self._sender = _IsoSender(
            self, handle=handle or 0, sdu_size=self.sdu_size_input.value(),
            interval_us=self.stream_interval_input.value(),
            duration=float(self.stream_duration_input.value()))
        self._sender.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log(f"> streaming {self.sdu_size_input.value()} B SDUs every "
                 f"{self.stream_interval_input.value()} us over "
                 f"{'the audio interface' if route is AudioRoute.SEPARATE_INTERFACE else 'HCI'}")

    def stop_stream(self) -> None:
        if self._sender is not None:
            self._sender.stop()
            self._sender.join(timeout=1.0)
            self._sender = None
        self.sender_finished()

    def sender_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self._stream_started:
            elapsed = max(time.monotonic() - self._stream_started, 1e-9)
            self.log(f"= stream finished after {elapsed:.1f}s: "
                     f"TX {self.tx_packets} SDU / {format_bytes(self.tx_bytes)}, "
                     f"RX {self.rx_packets} / {format_bytes(self.rx_bytes)}")
        self._stream_started = 0.0

    def _on_audio_rx(self, chunk: bytes) -> None:
        # Audio-link I/O thread: counters only.
        self.rx_packets += 1
        self.rx_bytes += len(chunk)

    def _refresh_stats(self) -> None:
        if self._is_destroyed:
            return
        elapsed = (time.monotonic() - self._stream_started
                   if self._stream_started else 0.0)
        labels = self._stat_labels
        labels["tx_packets"].setText(str(self.tx_packets))
        labels["tx_bytes"].setText(format_bytes(self.tx_bytes))
        labels["tx_rate"].setText(format_rate(self.tx_bytes, elapsed))
        labels["rx_packets"].setText(str(self.rx_packets))
        labels["rx_bytes"].setText(format_bytes(self.rx_bytes))
        labels["rx_rate"].setText(format_rate(self.rx_bytes, elapsed))

    # ---------------------------------------------------------------- teardown

    def on_cleanup(self) -> None:
        try:
            self._timer.stop()
        except RuntimeError:
            pass
        if self._sender is not None:
            self._sender.stop()
            self._sender = None
        self.offload_panel.cleanup()


__all__ = ["LeIsoTestWindow"]
