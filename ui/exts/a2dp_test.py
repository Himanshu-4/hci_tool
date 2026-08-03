"""
A2DP test screen -- AVDTP signalling and media streaming as an A2DP source.

Two L2CAP channels, as A2DP always uses: a signalling channel (PSM 0x0019)
carrying the AVDTP command sequence, and a media channel carrying RTP-framed
audio. This screen drives both.

The signalling tab walks the sequence a source actually performs -- Discover,
Get Capabilities, Set Configuration, Open, Start, then Suspend/Close -- with the
SBC capability record built from the codec form, so what goes out is a real
Set Configuration and not a canned blob.

**On the audio itself:** there is no SBC encoder here. Over HCI the media tab
sends correctly framed RTP + SBC payload headers carrying filler of the right
size, which exercises the transport, the packet timing and the peer's buffering
but is not decodable music. Offloaded, that limitation goes away for the reason
that makes offload worth doing: the controller runs the encoder, so this tool
sends **PCM** over the second UART and the chip produces the SBC on air.

That is the practical difference between the two routes here, and it is why the
media tab changes what it sends when the route changes.
"""

from __future__ import annotations

import math
import struct
import threading
import time
from typing import Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from .audio_offload import AudioOffloadPanel, AudioRoute, format_bytes, format_rate
from .l2cap_util import PSM_AVDTP, L2capReassembler, acl_packets_for
from .test_window_base import SessionTestWindow, connection_combo_items

#: AVDTP signal identifiers.
AVDTP_DISCOVER = 0x01
AVDTP_GET_CAPABILITIES = 0x02
AVDTP_SET_CONFIGURATION = 0x03
AVDTP_GET_CONFIGURATION = 0x04
AVDTP_RECONFIGURE = 0x05
AVDTP_OPEN = 0x06
AVDTP_START = 0x07
AVDTP_CLOSE = 0x08
AVDTP_SUSPEND = 0x09
AVDTP_ABORT = 0x0A
AVDTP_GET_ALL_CAPABILITIES = 0x0C

SIGNAL_NAMES = {
    AVDTP_DISCOVER: "Discover", AVDTP_GET_CAPABILITIES: "Get Capabilities",
    AVDTP_SET_CONFIGURATION: "Set Configuration",
    AVDTP_GET_CONFIGURATION: "Get Configuration",
    AVDTP_RECONFIGURE: "Reconfigure", AVDTP_OPEN: "Open", AVDTP_START: "Start",
    AVDTP_CLOSE: "Close", AVDTP_SUSPEND: "Suspend", AVDTP_ABORT: "Abort",
    AVDTP_GET_ALL_CAPABILITIES: "Get All Capabilities",
}

#: AVDTP message types, in the low two bits of the header.
MSG_COMMAND = 0x00
MSG_GENERAL_REJECT = 0x01
MSG_RESPONSE_ACCEPT = 0x02
MSG_RESPONSE_REJECT = 0x03

#: Service capability categories.
CAT_MEDIA_TRANSPORT = 0x01
CAT_MEDIA_CODEC = 0x07

#: SBC sampling frequency bits, in the top nibble of codec byte 0.
SBC_FREQ = {"16 kHz": 0x80, "32 kHz": 0x40, "44.1 kHz": 0x20, "48 kHz": 0x10}
#: SBC channel mode bits, low nibble of byte 0.
SBC_CHANNEL_MODE = {"Mono": 0x08, "Dual channel": 0x04,
                    "Stereo": 0x02, "Joint stereo": 0x01}
#: Block length bits, top nibble of byte 1.
SBC_BLOCKS = {"4": 0x80, "8": 0x40, "12": 0x20, "16": 0x10}
#: Subband bits, bits 3-2 of byte 1.
SBC_SUBBANDS = {"4": 0x08, "8": 0x04}
#: Allocation method bits, bits 1-0 of byte 1.
SBC_ALLOCATION = {"SNR": 0x02, "Loudness": 0x01}

#: RTP payload type A2DP uses for SBC.
RTP_PAYLOAD_TYPE_SBC = 96


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


def avdtp_command(transaction: int, signal_id: int, payload: bytes = b'') -> bytes:
    """
    A single-packet AVDTP command.

    Header: transaction (4 bits) | packet type (2 bits, 0 = single) |
    message type (2 bits), then the signal identifier.
    """
    header = ((transaction & 0x0F) << 4) | (0x00 << 2) | MSG_COMMAND
    return bytes([header, signal_id & 0x3F]) + bytes(payload)


def sbc_capability(freq_bits: int, channel_bits: int, block_bits: int,
                   subband_bits: int, allocation_bits: int,
                   min_bitpool: int, max_bitpool: int) -> bytes:
    """
    The Media Codec service capability for SBC.

    Category, length, media type (audio), codec type (SBC), then the four
    SBC-specific octets. In a Set Configuration exactly one bit may be set in
    each field -- a capability advertisement may set several, a configuration
    may not, and peers reject the difference.
    """
    codec = bytes([
        (freq_bits & 0xF0) | (channel_bits & 0x0F),
        (block_bits & 0xF0) | (subband_bits & 0x0C) | (allocation_bits & 0x03),
        min_bitpool & 0xFF,
        max_bitpool & 0xFF,
    ])
    return bytes([CAT_MEDIA_CODEC, 2 + len(codec), 0x00, 0x00]) + codec


def rtp_media_packet(sequence: int, timestamp: int, ssrc: int,
                     frame_count: int, payload: bytes) -> bytes:
    """
    RTP header + the one-byte SBC payload header + frames.

    The SBC payload header's low bits are the frame count; a receiver uses it to
    know how many frames to hand the decoder.
    """
    header = struct.pack(">BBHII",
                         0x80,                       # version 2, no padding
                         RTP_PAYLOAD_TYPE_SBC,       # marker clear
                         sequence & 0xFFFF,
                         timestamp & 0xFFFFFFFF,
                         ssrc & 0xFFFFFFFF)
    return header + bytes([frame_count & 0x0F]) + bytes(payload)


def _pcm_block(size: int, phase: int, tone_hz: int, sample_rate: int):
    """16-bit stereo PCM, as a sine so the output is checkable."""
    if tone_hz <= 0:
        return bytes(size), phase
    frames = size // 4          # 2 channels * 2 bytes
    out = bytearray()
    for i in range(frames):
        value = int(12000 * math.sin(2 * math.pi * tone_hz *
                                     ((phase + i) / float(sample_rate))))
        out += struct.pack("<hh", value, value)
    return bytes(out), phase + frames


class _MediaSender(threading.Thread):
    """
    Paces media packets at the stream's real rate.

    A2DP is not rate-controlled by the peer: sending faster than the audio's
    natural rate just fills the sink's buffer until it drops, so the packet
    period is computed from the codec configuration rather than being a free
    parameter.
    """

    def __init__(self, window: "A2dpTestWindow", interval: float,
                 duration: float, frames_per_packet: int, frame_size: int,
                 samples_per_frame: int, offloaded: bool, pcm_bytes: int,
                 sample_rate: int):
        super().__init__(name="hci-a2dp-tx", daemon=True)
        self.window = window
        self.interval = interval
        self.duration = duration
        self.frames_per_packet = frames_per_packet
        self.frame_size = frame_size
        self.samples_per_frame = samples_per_frame
        self.offloaded = offloaded
        self.pcm_bytes = pcm_bytes
        self.sample_rate = sample_rate
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:            # noqa: BLE001
            self.window.log(f"! media sender stopped: {exc!r}")
        finally:
            self.window.sender_finished_signal.emit()

    def _run(self) -> None:
        sequence = 0
        timestamp = 0
        phase = 0
        deadline = time.monotonic() + self.duration if self.duration else None
        next_send = time.monotonic()

        while not self._stop.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break

            if self.offloaded:
                # The controller encodes, so what goes over the audio link is
                # PCM, not SBC.
                payload, phase = _pcm_block(self.pcm_bytes, phase,
                                            self.window.tone_hz(),
                                            self.sample_rate)
                self.window.send_pcm(payload)
            else:
                frames = self.window.build_sbc_frames(self.frames_per_packet,
                                                      self.frame_size)
                self.window.send_media(sequence, timestamp,
                                       self.frames_per_packet, frames)
                sequence += 1
                timestamp += self.samples_per_frame * self.frames_per_packet

            next_send += self.interval
            sleep_for = next_send - time.monotonic()
            if sleep_for > 0:
                self._stop.wait(sleep_for)
            else:
                next_send = time.monotonic()


class A2dpTestWindow(SessionTestWindow):
    """A2DP source: AVDTP signalling plus media streaming."""

    WINDOW_TITLE = "A2DP Test"
    WINDOW_SIZE = (820, 960)

    sender_finished_signal = pyqtSignal()

    def __init__(self, main_window):
        self._sender: Optional[_MediaSender] = None
        self._reassembler = L2capReassembler()
        self._transaction = 0
        self.tx_packets = self.tx_bytes = 0
        self._started = 0.0
        super().__init__(main_window)

        self.sender_finished_signal.connect(self.sender_finished)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(400)

    # ----------------------------------------------------------------- layout

    def build_body(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._channel_box())
        tabs = QTabWidget()
        tabs.addTab(_scrolled(self._signalling_tab()), "AVDTP Signalling")
        tabs.addTab(_scrolled(self._codec_tab()), "SBC Codec")
        tabs.addTab(_scrolled(self._media_tab()), "Media Stream")
        layout.addWidget(tabs)

    def _channel_box(self) -> QWidget:
        box = QGroupBox("A2DP channels")
        form = QFormLayout(box)

        self.acl_combo = QComboBox()
        form.addRow("ACL Connection:", self.acl_combo)

        self.signalling_cid_input = _spin(
            0x0001, 0xFFFF, 0x0040,
            f"L2CAP CID of the AVDTP signalling channel (PSM 0x{PSM_AVDTP:04X})")
        form.addRow("Signalling CID:", self.signalling_cid_input)

        self.media_cid_input = _spin(0x0001, 0xFFFF, 0x0041,
                                     "L2CAP CID of the media transport channel")
        form.addRow("Media CID:", self.media_cid_input)

        self.max_acl_input = _spin(23, 0xFFFF, 1021,
                                   "Controller's ACL data length; media packets "
                                   "are fragmented to fit", " bytes")
        form.addRow("Max ACL Payload:", self.max_acl_input)

        self.seid_input = _spin(1, 0x3E, 1,
                                "Stream endpoint id on the peer, from the "
                                "Discover response")
        form.addRow("Peer SEID:", self.seid_input)

        form.addRow("", _hint(
            "Both channels have to exist already -- this screen speaks AVDTP "
            "and RTP on them, it does not run L2CAP. The media CID is the "
            "second channel, opened after AVDTP Open."))
        return box

    def _signalling_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        form.addRow("", _hint(
            "The sequence a source performs, in order. Each button sends one "
            "AVDTP command on the signalling channel; responses appear in the "
            "log."))

        discover_btn = QPushButton("1. Discover")
        discover_btn.clicked.connect(lambda: self._send_signal(AVDTP_DISCOVER))
        caps_btn = QPushButton("2. Get Capabilities")
        caps_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_GET_CAPABILITIES,
                                      bytes([self.seid_input.value() << 2])))
        all_caps_btn = QPushButton("Get All Capabilities")
        all_caps_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_GET_ALL_CAPABILITIES,
                                      bytes([self.seid_input.value() << 2])))
        form.addRow("Discovery:", self._row(discover_btn, caps_btn, all_caps_btn))

        self.local_seid_input = _spin(1, 0x3E, 1, "This device's endpoint id")
        form.addRow("Local SEID:", self.local_seid_input)

        configure_btn = QPushButton("3. Set Configuration")
        configure_btn.clicked.connect(lambda: self._set_configuration())
        get_config_btn = QPushButton("Get Configuration")
        get_config_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_GET_CONFIGURATION,
                                      bytes([self.seid_input.value() << 2])))
        reconfigure_btn = QPushButton("Reconfigure")
        reconfigure_btn.clicked.connect(
            lambda: self._set_configuration(AVDTP_RECONFIGURE))
        form.addRow("Configuration:",
                    self._row(configure_btn, get_config_btn, reconfigure_btn))

        open_btn = QPushButton("4. Open")
        open_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_OPEN,
                                      bytes([self.seid_input.value() << 2])))
        start_btn = QPushButton("5. Start")
        start_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_START,
                                      bytes([self.seid_input.value() << 2])))
        form.addRow("Streaming:", self._row(open_btn, start_btn))

        suspend_btn = QPushButton("Suspend")
        suspend_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_SUSPEND,
                                      bytes([self.seid_input.value() << 2])))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_CLOSE,
                                      bytes([self.seid_input.value() << 2])))
        abort_btn = QPushButton("Abort")
        abort_btn.clicked.connect(
            lambda: self._send_signal(AVDTP_ABORT,
                                      bytes([self.seid_input.value() << 2])))
        form.addRow("Teardown:", self._row(suspend_btn, close_btn, abort_btn))

        form.addRow("", _hint(
            "SEIDs go on the wire shifted left by two bits -- the low bits are "
            "flags. That shift is applied automatically here."))
        return page

    def _codec_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.freq_combo = QComboBox()
        for label, bits in SBC_FREQ.items():
            self.freq_combo.addItem(label, bits)
        self.freq_combo.setCurrentIndex(2)          # 44.1 kHz
        self.freq_combo.currentIndexChanged.connect(self._update_codec_summary)
        form.addRow("Sampling Frequency:", self.freq_combo)

        self.channel_combo = QComboBox()
        for label, bits in SBC_CHANNEL_MODE.items():
            self.channel_combo.addItem(label, bits)
        self.channel_combo.setCurrentIndex(3)       # joint stereo
        self.channel_combo.currentIndexChanged.connect(self._update_codec_summary)
        form.addRow("Channel Mode:", self.channel_combo)

        self.blocks_combo = QComboBox()
        for label, bits in SBC_BLOCKS.items():
            self.blocks_combo.addItem(label, bits)
        self.blocks_combo.setCurrentIndex(3)        # 16 blocks
        self.blocks_combo.currentIndexChanged.connect(self._update_codec_summary)
        form.addRow("Block Length:", self.blocks_combo)

        self.subbands_combo = QComboBox()
        for label, bits in SBC_SUBBANDS.items():
            self.subbands_combo.addItem(label, bits)
        self.subbands_combo.setCurrentIndex(1)      # 8 subbands
        self.subbands_combo.currentIndexChanged.connect(self._update_codec_summary)
        form.addRow("Subbands:", self.subbands_combo)

        self.allocation_combo = QComboBox()
        for label, bits in SBC_ALLOCATION.items():
            self.allocation_combo.addItem(label, bits)
        self.allocation_combo.setCurrentIndex(1)    # loudness
        self.allocation_combo.currentIndexChanged.connect(self._update_codec_summary)
        form.addRow("Allocation Method:", self.allocation_combo)

        self.min_bitpool_input = _spin(2, 250, 2)
        self.max_bitpool_input = _spin(2, 250, 53,
                                       "53 is the usual maximum for 44.1 kHz "
                                       "joint stereo")
        self.min_bitpool_input.valueChanged.connect(self._update_codec_summary)
        self.max_bitpool_input.valueChanged.connect(self._update_codec_summary)
        form.addRow("Min Bitpool:", self.min_bitpool_input)
        form.addRow("Max Bitpool:", self.max_bitpool_input)

        self.codec_summary = _hint("")
        form.addRow("Capability:", self.codec_summary)

        form.addRow("", _hint(
            "In a Set Configuration exactly one bit may be set per field, so "
            "these are single-choice rather than checkboxes -- a peer rejects "
            "a configuration that leaves a choice open."))

        self._update_codec_summary()
        return page

    def _media_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        self.offload_panel = AudioOffloadPanel("Audio routing")
        root.addWidget(self.offload_panel)
        self.offload_panel.route_combo.currentIndexChanged.connect(
            self._update_stream_summary)

        stream = QGroupBox("Stream")
        form = QFormLayout(stream)

        self.frames_input = _spin(1, 15, 5,
                                  "SBC frames per RTP packet; the payload "
                                  "header only has four bits for the count")
        self.frames_input.valueChanged.connect(self._update_stream_summary)
        form.addRow("Frames per Packet:", self.frames_input)

        self.frame_size_input = _spin(1, 512, 119,
                                      "Encoded SBC frame size; 119 bytes is "
                                      "typical for 44.1 kHz joint stereo at "
                                      "bitpool 53", " bytes")
        self.frame_size_input.valueChanged.connect(self._update_stream_summary)
        form.addRow("Frame Size:", self.frame_size_input)

        self.tone_input = _spin(0, 20000, 440,
                                "Sine frequency in the generated PCM when "
                                "offloaded; 0 = silence", " Hz")
        form.addRow("Test Tone:", self.tone_input)

        self.duration_input = _spin(0, 3600, 10, "0 = until stopped", " s")
        form.addRow("Duration:", self.duration_input)

        self.stream_summary = _hint("")
        form.addRow("", self.stream_summary)

        self.start_btn = QPushButton("Start Streaming")
        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_stream)
        form.addRow("", self._row(self.start_btn, self.stop_btn))

        root.addWidget(stream)

        stats = QGroupBox("Statistics")
        grid = QGridLayout(stats)
        self._stat_labels = {}
        for index, (title, key) in enumerate((
                ("Packets sent", "tx_packets"), ("Bytes sent", "tx_bytes"),
                ("Rate", "tx_rate"), ("Packet rate", "tx_pps"))):
            caption = QLabel(title)
            caption.setStyleSheet("color: gray; font-size: 10pt;")
            value = QLabel("-")
            grid.addWidget(caption, 0, index)
            grid.addWidget(value, 1, index)
            self._stat_labels[key] = value
        root.addWidget(stats)

        root.addWidget(_hint(
            "There is no SBC encoder here. Over HCI this sends correctly framed "
            "RTP packets carrying filler of the right size -- good for checking "
            "transport, timing and buffering, not for listening to. Offloaded, "
            "the controller encodes, so what goes over the audio interface is "
            "PCM and the audio on air is real."))
        root.addStretch(1)
        self._update_stream_summary()
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
        for label, handle in connection_combo_items(self.session):
            self.acl_combo.addItem(label, handle)
        if current is not None:
            index = self.acl_combo.findData(current)
            if index >= 0:
                self.acl_combo.setCurrentIndex(index)

    def tone_hz(self) -> int:
        return self.tone_input.value()

    def _sample_rate(self) -> int:
        return {0x80: 16000, 0x40: 32000,
                0x20: 44100, 0x10: 48000}[self.freq_combo.currentData()]

    def _samples_per_frame(self) -> int:
        blocks = int(self.blocks_combo.currentText())
        subbands = int(self.subbands_combo.currentText())
        return blocks * subbands

    def _codec_capability(self) -> bytes:
        return sbc_capability(
            self.freq_combo.currentData(), self.channel_combo.currentData(),
            self.blocks_combo.currentData(), self.subbands_combo.currentData(),
            self.allocation_combo.currentData(),
            self.min_bitpool_input.value(), self.max_bitpool_input.value())

    def _update_codec_summary(self) -> None:
        capability = self._codec_capability()
        self.codec_summary.setText(
            f"{capability.hex(' ')}   ({self._sample_rate()} Hz, "
            f"{self._samples_per_frame()} samples/frame)")
        if hasattr(self, "stream_summary"):
            self._update_stream_summary()

    def _update_stream_summary(self) -> None:
        samples = self._samples_per_frame() * self.frames_input.value()
        interval = samples / self._sample_rate()
        if self.offload_panel.is_offloaded():
            pcm = int(self._sample_rate() * 4 * interval)
            self.stream_summary.setText(
                f"offloaded: {pcm} bytes of PCM every {interval * 1000:.2f} ms "
                f"({self._sample_rate() * 4 / 1024:.0f} kB/s)")
        else:
            size = self.frames_input.value() * self.frame_size_input.value()
            self.stream_summary.setText(
                f"over HCI: {size} bytes of SBC every {interval * 1000:.2f} ms "
                f"({size / interval / 1024:.1f} kB/s)")

    def _next_transaction(self) -> int:
        self._transaction = (self._transaction + 1) & 0x0F
        return self._transaction

    # ---------------------------------------------------------------- actions

    def _send_signal(self, signal_id: int, payload: bytes = b'') -> None:
        handle = self.acl_combo.currentData()
        if handle is None:
            self.log("! no ACL connection selected")
            return
        frame = avdtp_command(self._next_transaction(), signal_id, payload)
        ok = True
        for packet in acl_packets_for(handle, self.signalling_cid_input.value(),
                                      frame, self.max_acl_input.value()):
            ok = self.write_packet(packet) and ok
        name = SIGNAL_NAMES.get(signal_id, f"0x{signal_id:02X}")
        self.log(f"> AVDTP {name}: {frame.hex(' ')}"
                 if ok else f"! AVDTP {name} write refused")

    def _set_configuration(self, signal_id: int = AVDTP_SET_CONFIGURATION) -> None:
        if signal_id == AVDTP_RECONFIGURE:
            # Reconfigure carries only the ACP SEID and the changed capability.
            payload = (bytes([self.seid_input.value() << 2])
                       + self._codec_capability())
        else:
            payload = (bytes([self.seid_input.value() << 2,
                              self.local_seid_input.value() << 2])
                       + bytes([CAT_MEDIA_TRANSPORT, 0x00])
                       + self._codec_capability())
        self._send_signal(signal_id, payload)

    def build_sbc_frames(self, count: int, frame_size: int) -> bytes:
        """
        Filler frames of the right shape.

        Each starts with the SBC sync word 0x9C so a capture looks like SBC to
        anything scanning for frame boundaries; the contents are not encoded
        audio and will not decode to sound.
        """
        frame = bytes([0x9C]) + bytes((i * 7) & 0xFF
                                      for i in range(max(frame_size - 1, 0)))
        return frame * count

    def send_media(self, sequence: int, timestamp: int, frame_count: int,
                   frames: bytes) -> None:
        handle = self.acl_combo.currentData()
        if handle is None:
            return
        packet = rtp_media_packet(sequence, timestamp, 0x12345678,
                                  frame_count, frames)
        ok = True
        for fragment in acl_packets_for(handle, self.media_cid_input.value(),
                                        packet, self.max_acl_input.value()):
            ok = self.write_packet(fragment) and ok
        if ok:
            self.tx_packets += 1
            self.tx_bytes += len(packet)

    def send_pcm(self, payload: bytes) -> None:
        if self.offload_panel.link.write(payload):
            self.tx_packets += 1
            self.tx_bytes += len(payload)

    def start_stream(self) -> None:
        if self._sender is not None:
            return

        route = self.offload_panel.route()
        if route is AudioRoute.CONTROLLER_INTERNAL:
            self.log("! route is controller-internal: the controller sources "
                     "the audio itself, so there is nothing to send from here")
            return
        offloaded = route is AudioRoute.SEPARATE_INTERFACE
        if offloaded and not self.offload_panel.link.is_open:
            self.log("! open the audio interface first")
            return
        if not offloaded and self.acl_combo.currentData() is None:
            self.log("! no ACL connection selected")
            return

        samples = self._samples_per_frame() * self.frames_input.value()
        interval = samples / self._sample_rate()
        pcm_bytes = int(self._sample_rate() * 4 * interval)

        self.tx_packets = self.tx_bytes = 0
        self._started = time.monotonic()

        self._sender = _MediaSender(
            self, interval=interval, duration=float(self.duration_input.value()),
            frames_per_packet=self.frames_input.value(),
            frame_size=self.frame_size_input.value(),
            samples_per_frame=self._samples_per_frame(),
            offloaded=offloaded, pcm_bytes=pcm_bytes,
            sample_rate=self._sample_rate())
        self._sender.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log(f"> streaming "
                 f"{'PCM over the audio interface' if offloaded else 'SBC over HCI'}, "
                 f"one packet every {interval * 1000:.2f} ms")

    def stop_stream(self) -> None:
        if self._sender is not None:
            self._sender.stop()
            self._sender.join(timeout=1.0)
            self._sender = None
        self.sender_finished()

    def sender_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self._started:
            elapsed = max(time.monotonic() - self._started, 1e-9)
            self.log(f"= stream finished after {elapsed:.1f}s: "
                     f"{self.tx_packets} packets / "
                     f"{format_bytes(self.tx_bytes)} "
                     f"({format_rate(self.tx_bytes, elapsed)})")
        self._started = 0.0

    # ---------------------------------------------------------- receive path

    def on_session_attached(self) -> None:
        from hci.session.session import EVT_PACKET
        self.session.on(EVT_PACKET, self._on_packet)

    def on_session_detached(self) -> None:
        from hci.session.session import EVT_PACKET
        try:
            self.session.off(EVT_PACKET, self._on_packet)
        except Exception:
            pass

    def _on_packet(self, raw: bytes, event) -> None:
        """Decode AVDTP responses on the signalling channel. I/O thread."""
        for handle, cid, payload in self._reassembler.feed(raw):
            if cid != self.signalling_cid_input.value() or len(payload) < 2:
                continue
            message_type = payload[0] & 0x03
            signal = payload[1] & 0x3F
            name = SIGNAL_NAMES.get(signal, f"0x{signal:02X}")
            kind = {MSG_COMMAND: "command",
                    MSG_GENERAL_REJECT: "general reject",
                    MSG_RESPONSE_ACCEPT: "accept",
                    MSG_RESPONSE_REJECT: "reject"}.get(message_type, "?")
            self._line.emit(f"< AVDTP {name} {kind}: {payload.hex(' ')}")

    def _refresh_stats(self) -> None:
        if self._is_destroyed:
            return
        elapsed = time.monotonic() - self._started if self._started else 0.0
        labels = self._stat_labels
        labels["tx_packets"].setText(str(self.tx_packets))
        labels["tx_bytes"].setText(format_bytes(self.tx_bytes))
        labels["tx_rate"].setText(format_rate(self.tx_bytes, elapsed))
        labels["tx_pps"].setText(
            f"{self.tx_packets / elapsed:.1f}/s" if elapsed else "-")

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


__all__ = ["A2dpTestWindow"]
