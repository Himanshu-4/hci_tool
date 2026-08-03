"""
SCO / eSCO test screen.

Sets up a synchronous link on an existing ACL connection, streams audio over it
and counts what comes back. Both the plain and the enhanced setup forms are
here, because which one you need depends on the codec: CVSD can go through the
plain form and let the controller do the coding, while transparent and mSBC need
the enhanced form so the controller does not run its own codec over data that is
already coded.

Audio routing is the other half. Over HCI, SCO packets share the command link --
8 kB/s each way, which at 115200 baud is most of the link. Offloaded, the
controller is told to use a vendor data path and the audio rides a second UART
this tool opens separately (`audio_offload`), leaving HCI quiet.

SCO has no flow control: the link consumes one packet per interval whether or
not the host keeps up, so the transmit loop is paced by the clock rather than by
credits.
"""

from __future__ import annotations

import math
import struct
import threading
import time
from typing import Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

import hci.cmd.link_controller as lc_cmds
from hci.evt.evt_codes import HciEventCode
from hci.hci_packet import HciSynchronousDataPacket
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


#: Named codec setups. `enhanced` says whether the plain form can express it.
CODEC_PRESETS = {
    "CVSD (narrowband, 8 kHz)": dict(
        voice_setting=lc_cmds.VOICE_SETTING_CVSD,
        packet_type=lc_cmds.SYNC_PACKET_TYPE_EV3_ONLY,
        bandwidth=8000, enhanced=False,
        air_coding=int(lc_cmds.CodingFormat.CVSD),
        host_coding=int(lc_cmds.CodingFormat.LINEAR_PCM), sample_bits=16),
    "Transparent (host codes the audio)": dict(
        voice_setting=lc_cmds.VOICE_SETTING_TRANSPARENT,
        packet_type=lc_cmds.SYNC_PACKET_TYPE_EV3_ONLY,
        bandwidth=8000, enhanced=True,
        air_coding=int(lc_cmds.CodingFormat.TRANSPARENT),
        host_coding=int(lc_cmds.CodingFormat.TRANSPARENT), sample_bits=8),
    "mSBC (wideband, 16 kHz)": dict(
        voice_setting=lc_cmds.VOICE_SETTING_TRANSPARENT,
        packet_type=lc_cmds.SYNC_PACKET_TYPE_2EV3,
        bandwidth=8000, enhanced=True,
        air_coding=int(lc_cmds.CodingFormat.TRANSPARENT),
        host_coding=int(lc_cmds.CodingFormat.TRANSPARENT), sample_bits=16),
}


def _tone_frame(size: int, phase: int, tone_hz: int, sample_bits: int):
    """A sine tone frame, so what comes back is recognisable on a scope."""
    if tone_hz <= 0:
        return bytes(size), phase

    if sample_bits == 16:
        samples = size // 2
        out = bytearray()
        for i in range(samples):
            value = int(16000 * math.sin(2 * math.pi * tone_hz *
                                         ((phase + i) / 8000.0)))
            out += struct.pack("<h", value)
        return bytes(out), phase + samples

    out = bytearray()
    for i in range(size):
        value = int(100 * math.sin(2 * math.pi * tone_hz * ((phase + i) / 8000.0)))
        out.append((value + 128) & 0xFF)
    return bytes(out), phase + size


class _ScoSender(threading.Thread):
    """
    Paces SCO packets at the stream's natural rate.

    SCO has no credits and no Number Of Completed Packets: the air interface
    consumes one packet per interval regardless. Sending faster just overruns
    the controller's buffer, so this sleeps to the wall clock instead.
    """

    def __init__(self, window: "ScoTestWindow", handle: int, frame_size: int,
                 interval: float, duration: float, tone_hz: int, sample_bits: int):
        super().__init__(name="hci-sco-tx", daemon=True)
        self.window = window
        self.handle = handle
        self.frame_size = frame_size
        self.interval = interval
        self.duration = duration
        self.tone_hz = tone_hz
        self.sample_bits = sample_bits
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:            # noqa: BLE001
            self.window.log(f"! SCO sender stopped: {exc!r}")
        finally:
            self.window.sender_finished_signal.emit()

    def _run(self) -> None:
        phase = 0
        deadline = time.monotonic() + self.duration if self.duration else None
        next_send = time.monotonic()

        while not self._stop.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break

            payload, phase = _tone_frame(self.frame_size, phase, self.tone_hz,
                                         self.sample_bits)
            self.window.send_audio_frame(self.handle, payload)

            next_send += self.interval
            sleep_for = next_send - time.monotonic()
            if sleep_for > 0:
                self._stop.wait(sleep_for)
            else:
                # Behind schedule; resync rather than bursting to catch up.
                next_send = time.monotonic()


class ScoTestWindow(SessionTestWindow):
    """SCO / eSCO setup and audio streaming."""

    WINDOW_TITLE = "SCO Test"
    WINDOW_SIZE = (760, 900)

    sender_finished_signal = pyqtSignal()

    def __init__(self, main_window):
        self._sender: Optional[_ScoSender] = None
        self._sco_handles: list = []
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
        tabs.addTab(self._setup_tab(), "Link Setup")
        tabs.addTab(self._stream_tab(), "Audio Stream")
        layout.addWidget(tabs)

    def _setup_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.acl_combo = QComboBox()
        self.acl_combo.setToolTip("The BR/EDR ACL link the SCO rides on")
        form.addRow("ACL Connection:", self.acl_combo)

        self.codec_combo = QComboBox()
        for name in CODEC_PRESETS:
            self.codec_combo.addItem(name)
        self.codec_combo.currentTextChanged.connect(self._on_codec_changed)
        form.addRow("Codec:", self.codec_combo)

        self.voice_label = _hint("")
        form.addRow("", self.voice_label)

        self.latency_input = _spin(0x0004, 0xFFFF, 0x000C,
                                   "Max latency; 0xFFFF for don't care", " ms")
        form.addRow("Max Latency:", self.latency_input)

        self.retransmission_combo = QComboBox()
        for label, value in (("No retransmissions", 0x00),
                             ("Optimise for power", 0x01),
                             ("Optimise for quality", 0x02),
                             ("Don't care", 0xFF)):
            self.retransmission_combo.addItem(label, value)
        self.retransmission_combo.setCurrentIndex(2)
        form.addRow("Retransmission Effort:", self.retransmission_combo)

        self.enhanced_check = QCheckBox(
            "Use the Enhanced form (required for transparent and mSBC)")
        form.addRow("", self.enhanced_check)

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        setup_btn = QPushButton("Setup SCO Link")
        setup_btn.clicked.connect(self._setup_link)
        button_layout.addWidget(setup_btn)
        disconnect_btn = QPushButton("Disconnect SCO")
        disconnect_btn.clicked.connect(self._disconnect_sco)
        button_layout.addWidget(disconnect_btn)
        button_layout.addStretch(1)
        form.addRow("", buttons)

        self.peer_input = QComboBox()
        self.peer_input.setEditable(True)
        self.peer_input.setToolTip(
            "Address from the Connection Request event; accept and reject are "
            "keyed by address because the link does not exist yet")
        form.addRow("Requesting BD_ADDR:", self.peer_input)

        incoming = QWidget()
        incoming_layout = QHBoxLayout(incoming)
        incoming_layout.setContentsMargins(0, 0, 0, 0)
        accept_btn = QPushButton("Accept Incoming")
        accept_btn.clicked.connect(self._accept_incoming)
        reject_btn = QPushButton("Reject Incoming")
        reject_btn.clicked.connect(self._reject_incoming)
        incoming_layout.addWidget(accept_btn)
        incoming_layout.addWidget(reject_btn)
        incoming_layout.addStretch(1)
        form.addRow("Incoming request:", incoming)

        self.sco_label = QLabel("none")
        form.addRow("SCO handles:", self.sco_label)

        form.addRow("", _hint(
            "The SCO handle arrives in Synchronous Connection Complete and is "
            "picked up automatically. It is not the ACL handle -- streaming to "
            "the wrong one silently goes nowhere."))

        self._on_codec_changed(self.codec_combo.currentText())
        return page

    def _stream_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        self.offload_panel = AudioOffloadPanel("Audio routing")
        root.addWidget(self.offload_panel)

        config = QGroupBox("Stream")
        form = QFormLayout(config)

        self.stream_handle_combo = QComboBox()
        form.addRow("SCO Handle:", self.stream_handle_combo)

        self.frame_size_input = _spin(1, 255, 60,
                                      "SCO payload per packet; 60 bytes is the "
                                      "usual eSCO EV3 frame", " bytes")
        form.addRow("Frame Size:", self.frame_size_input)

        self.interval_input = _spin(1, 1000, 8,
                                    "Time between packets; 7-8 ms matches a "
                                    "60-byte frame at 8 kHz", " ms")
        form.addRow("Packet Interval:", self.interval_input)

        self.duration_input = _spin(0, 3600, 10, "0 = until stopped", " s")
        form.addRow("Duration:", self.duration_input)

        self.tone_input = _spin(0, 4000, 440,
                                "Sine frequency in the generated audio; "
                                "0 = silence", " Hz")
        form.addRow("Test Tone:", self.tone_input)

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.start_btn = QPushButton("Start Streaming")
        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_stream)
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch(1)
        form.addRow("", buttons)

        root.addWidget(config)

        stats = QGroupBox("Statistics")
        grid = QGridLayout(stats)
        self._stat_labels = {}
        for index, (title, key) in enumerate((
                ("TX packets", "tx_packets"), ("TX bytes", "tx_bytes"),
                ("TX rate", "tx_rate"), ("RX packets", "rx_packets"),
                ("RX bytes", "rx_bytes"), ("RX rate", "rx_rate"))):
            caption = QLabel(title)
            caption.setStyleSheet("color: gray; font-size: 10pt;")
            value = QLabel("-")
            grid.addWidget(caption, index // 3 * 2, index % 3)
            grid.addWidget(value, index // 3 * 2 + 1, index % 3)
            self._stat_labels[key] = value
        root.addWidget(stats)

        root.addWidget(_hint(
            "SCO has no flow control -- the air interface consumes one packet "
            "per interval whatever the host does, so the sender is paced by "
            "the clock. Sending faster only overruns the controller."))
        root.addStretch(1)
        return page

    # ---------------------------------------------------------------- helpers

    def _preset(self) -> dict:
        return CODEC_PRESETS[self.codec_combo.currentText()]

    def _on_codec_changed(self, name: str) -> None:
        preset = CODEC_PRESETS[name]
        self.voice_label.setText(
            f"Voice_Setting 0x{preset['voice_setting']:04X}, "
            f"Packet_Type 0x{preset['packet_type']:04X}, "
            f"{preset['bandwidth']} B/s each way")
        self.enhanced_check.setChecked(preset['enhanced'])

    def on_connections_changed(self) -> None:
        current = self.acl_combo.currentData()
        self.acl_combo.clear()
        for label, handle in connection_combo_items(self.session, LinkType.BR_EDR):
            self.acl_combo.addItem(label, handle)
        if current is not None:
            index = self.acl_combo.findData(current)
            if index >= 0:
                self.acl_combo.setCurrentIndex(index)
        self._refresh_sco_handles()

    def _refresh_sco_handles(self) -> None:
        self.sco_label.setText(
            ", ".join(f"0x{h:04X}" for h in self._sco_handles) or "none")
        current = self.stream_handle_combo.currentData()
        self.stream_handle_combo.clear()
        for handle in self._sco_handles:
            self.stream_handle_combo.addItem(f"0x{handle:04X}", handle)
        if current is not None:
            index = self.stream_handle_combo.findData(current)
            if index >= 0:
                self.stream_handle_combo.setCurrentIndex(index)

    def _on_event(self, event) -> None:
        """Watch for the SCO handle and for incoming requests. I/O thread."""
        code = getattr(event, 'EVENT_CODE', None)
        params = getattr(event, 'params', {}) or {}

        if code == HciEventCode.SYNCHRONOUS_CONNECTION_COMPLETE:
            status = params.get('status', 0xFF)
            handle = params.get('connection_handle')
            if status == 0x00 and handle is not None:
                if handle not in self._sco_handles:
                    self._sco_handles.append(handle)
                self._line.emit(f"+ SCO link up, handle 0x{handle:04X}")
                self._connections_changed.emit()
            else:
                self._line.emit(f"! SCO setup failed, status 0x{status:02X}")

        elif code == HciEventCode.CONNECTION_REQUEST:
            link_type = params.get('link_type')
            if link_type in (0x00, 0x02):      # SCO or eSCO
                addr = params.get('bd_addr_str') or ""
                self._line.emit(
                    f"? incoming {'eSCO' if link_type == 0x02 else 'SCO'} "
                    f"request from {addr}")

        elif code == HciEventCode.DISCONNECTION_COMPLETE:
            handle = params.get('connection_handle')
            if handle in self._sco_handles:
                self._sco_handles.remove(handle)
                self._connections_changed.emit()

    # ---------------------------------------------------------------- actions

    def _setup_link(self) -> None:
        handle = self.acl_combo.currentData()
        if handle is None:
            self.log("! no ACL connection -- connect over BR/EDR first")
            return

        preset = self._preset()
        latency = self.latency_input.value()
        effort = self.retransmission_combo.currentData()

        if self.enhanced_check.isChecked():
            path = (self.offload_panel.data_path_id()
                    if self.offload_panel.route() is not AudioRoute.OVER_HCI
                    else 0x00)
            self.send(lambda: lc_cmds.EnhancedSetupSynchronousConnection(
                connection_handle=handle,
                transmit_bandwidth=preset['bandwidth'],
                receive_bandwidth=preset['bandwidth'],
                transmit_coding_format=lc_cmds.pack_coding_format(
                    preset['air_coding']),
                receive_coding_format=lc_cmds.pack_coding_format(
                    preset['air_coding']),
                input_coding_format=lc_cmds.pack_coding_format(
                    preset['host_coding']),
                output_coding_format=lc_cmds.pack_coding_format(
                    preset['host_coding']),
                input_coded_data_size=preset['sample_bits'],
                output_coded_data_size=preset['sample_bits'],
                input_transport_unit_size=preset['sample_bits'],
                output_transport_unit_size=preset['sample_bits'],
                input_data_path=path,
                output_data_path=path,
                max_latency=latency,
                packet_type=preset['packet_type'],
                retransmission_effort=effort,
            ), f"Enhanced Setup Synchronous Connection (data path {path})")
        else:
            self.send(lambda: lc_cmds.SetupSynchronousConnection(
                connection_handle=handle,
                transmit_bandwidth=preset['bandwidth'],
                receive_bandwidth=preset['bandwidth'],
                max_latency=latency,
                voice_setting=preset['voice_setting'],
                retransmission_effort=effort,
                packet_type=preset['packet_type'],
            ), "Setup Synchronous Connection")

    def _accept_incoming(self) -> None:
        address = self.peer_input.currentText().strip()
        if not address:
            self.log("! enter the address from the Connection Request event")
            return
        preset = self._preset()
        self.send(lambda: lc_cmds.AcceptSynchronousConnectionRequest(
            bd_addr=address,
            transmit_bandwidth=preset['bandwidth'],
            receive_bandwidth=preset['bandwidth'],
            max_latency=self.latency_input.value(),
            voice_setting=preset['voice_setting'],
            retransmission_effort=self.retransmission_combo.currentData(),
            packet_type=preset['packet_type'],
        ), "Accept Synchronous Connection Request")

    def _reject_incoming(self) -> None:
        address = self.peer_input.currentText().strip()
        if not address:
            self.log("! enter the address from the Connection Request event")
            return
        self.send(lambda: lc_cmds.RejectSynchronousConnectionRequest(
            bd_addr=address, reason=0x0D),
            "Reject Synchronous Connection Request")

    def _disconnect_sco(self) -> None:
        handle = self.stream_handle_combo.currentData()
        if handle is None:
            self.log("! no SCO link to disconnect")
            return
        self.send(lambda: lc_cmds.Disconnect(connection_handle=handle,
                                             reason=0x13), "Disconnect SCO")

    # --------------------------------------------------------------- streaming

    def send_audio_frame(self, handle: int, payload: bytes) -> None:
        """One frame out, over whichever route is selected. Called on the sender."""
        if self.offload_panel.is_offloaded():
            ok = self.offload_panel.link.write(payload)
        else:
            packet = HciSynchronousDataPacket(connection_handle=handle,
                                              packet_status_flag=0, data=payload)
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

        handle = self.stream_handle_combo.currentData()
        if handle is None and route is not AudioRoute.SEPARATE_INTERFACE:
            self.log("! no SCO handle -- set the link up first")
            return

        self.tx_packets = self.tx_bytes = 0
        self.rx_packets = self.rx_bytes = 0
        self._stream_started = time.monotonic()
        self.offload_panel.link.set_receiver(self._on_audio_rx)

        self._sender = _ScoSender(
            self, handle=handle or 0, frame_size=self.frame_size_input.value(),
            interval=self.interval_input.value() / 1000.0,
            duration=float(self.duration_input.value()),
            tone_hz=self.tone_input.value(),
            sample_bits=self._preset()['sample_bits'])
        self._sender.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log(f"> streaming {self.frame_size_input.value()} B every "
                 f"{self.interval_input.value()} ms over "
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
                     f"TX {self.tx_packets} pkt / {format_bytes(self.tx_bytes)}, "
                     f"RX {self.rx_packets} pkt / {format_bytes(self.rx_bytes)}")
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


__all__ = ["ScoTestWindow"]
