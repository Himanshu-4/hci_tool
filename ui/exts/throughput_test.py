"""
Throughput Test -- ACL data rate and latency over an open connection.

Configurable TX, RX or bidirectional runs: duration, payload size, data pattern,
send rate, and round-trip latency when the peer echoes the data back.

Two things make this more than a send loop:

* **Controller flow control is mandatory.** The controller advertises how many
  ACL packets it can hold (LE Read Buffer Size); writing past that wedges it and
  the measurement is meaningless. Credits here are decremented per packet and
  restored from Number Of Completed Packets, exactly as the spec requires.
* **Throughput is measured over the wire, not the API.** Bytes are counted when
  the packet is handed to the transport, and RX bytes when a complete ACL packet
  arrives, so a stalled link shows as a falling rate rather than a growing queue.

Latency needs a cooperating peer: each payload carries a marker, sequence number
and send timestamp, and RTT is the gap until that sequence comes back. Against a
peer that does not echo, the latency figures stay blank and the throughput
figures are still valid.

Threading: the sender runs on its own thread so the UI stays responsive at high
rates. It touches no widget -- the UI polls the counters on a timer.
"""

from __future__ import annotations

import random
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMdiSubWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hci.evt.evt_codes import HciEventCode
from hci.hci_packet import HciAclDataPacket
from hci.session.session import (
    EVT_CONNECTION_DOWN,
    EVT_CONNECTION_UP,
    EVT_EVENT,
    EVT_PACKET,
)
from ui.hci_ui.hci_main_ui import HciMainUI

#: Marks a payload as ours, so an echo can be told from unrelated ACL traffic.
_MAGIC = b"HCIT"
#: magic(4) + sequence(4) + send timestamp in nanoseconds(8)
_HEADER = struct.Struct("<4sIQ")
_HEADER_LEN = _HEADER.size

#: ACL packet boundary flag for "first packet of a higher-layer message".
_PB_FIRST_NON_FLUSHABLE = 0x00
_PB_FIRST_FLUSHABLE = 0x02


def _pattern_bytes(pattern: str, length: int, custom: bytes = b'') -> bytes:
    """
    Build `length` bytes of the named filler pattern.

    The pattern matters: a run of zeros compresses on some links and hides
    whitening problems, while PRBS and random data exercise the radio the way a
    real payload would.
    """
    if length <= 0:
        return b''
    if pattern == "Zeros (0x00)":
        return bytes(length)
    if pattern == "Ones (0xFF)":
        return b"\xFF" * length
    if pattern == "Alternating (0x55/0xAA)":
        return (b"\x55\xAA" * (length // 2 + 1))[:length]
    if pattern == "Incrementing":
        return bytes(i & 0xFF for i in range(length))
    if pattern == "Random":
        return random.randbytes(length)
    if pattern == "PRBS9":
        return _prbs9(length)
    if pattern == "Custom hex":
        if not custom:
            raise ValueError("custom pattern is empty")
        return (custom * (length // len(custom) + 1))[:length]
    return bytes(length)


def _prbs9(length: int) -> bytes:
    """
    PRBS9 (x^9 + x^5 + 1), the sequence the LE test modes use.

    Generated once per call rather than cached: at the sizes involved it is
    cheaper than the bookkeeping to invalidate a cache when the size changes.
    """
    state = 0x1FF
    out = bytearray()
    for _ in range(length):
        byte = 0
        for bit in range(8):
            feedback = ((state >> 8) ^ (state >> 4)) & 0x01
            state = ((state << 1) | feedback) & 0x1FF
            byte |= feedback << bit
        out.append(byte)
    return bytes(out)


@dataclass
class Stats:
    """Counters shared between the sender thread and the UI timer."""

    started_at: float = 0.0
    stopped_at: float = 0.0

    tx_packets: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    rx_bytes: int = 0

    # Round trips, in milliseconds.
    latency_count: int = 0
    latency_total: float = 0.0
    latency_min: Optional[float] = None
    latency_max: Optional[float] = None
    latency_last: Optional[float] = None

    stalls: int = 0          # times the sender waited on credits
    errors: int = 0
    out_of_order: int = 0

    lock: threading.Lock = field(default_factory=threading.Lock)

    def elapsed(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.stopped_at or time.monotonic()
        return max(end - self.started_at, 1e-9)

    def add_latency(self, milliseconds: float) -> None:
        with self.lock:
            self.latency_count += 1
            self.latency_total += milliseconds
            self.latency_last = milliseconds
            if self.latency_min is None or milliseconds < self.latency_min:
                self.latency_min = milliseconds
            if self.latency_max is None or milliseconds > self.latency_max:
                self.latency_max = milliseconds

    @property
    def latency_avg(self) -> Optional[float]:
        return (self.latency_total / self.latency_count
                if self.latency_count else None)


class _Sender(threading.Thread):
    """
    Feeds ACL packets to the transport under the controller's flow control.

    Stops on duration, on packet count, or when `stop()` is called. Never
    touches a widget: the UI reads `stats` on a timer.
    """

    def __init__(self, window: "ThroughputWindow", handle: int, payload_size: int,
                 pattern: str, custom: bytes, duration: float,
                 packet_limit: int, rate_pps: int, flushable: bool):
        super().__init__(name="hci-throughput-tx", daemon=True)
        self.window = window
        self.handle = handle
        self.payload_size = payload_size
        self.pattern = pattern
        self.custom = custom
        self.duration = duration
        self.packet_limit = packet_limit
        self.rate_pps = rate_pps
        self.pb_flag = _PB_FIRST_FLUSHABLE if flushable else _PB_FIRST_NON_FLUSHABLE
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        # Whatever happens, the UI has to learn the run ended -- a thread that
        # dies quietly leaves Stop enabled and Start disabled forever.
        try:
            self._run()
        except Exception as exc:            # noqa: BLE001
            self.window.report(f"! sender stopped: {exc!r}")
            with self.window.stats.lock:
                self.window.stats.errors += 1
        finally:
            self.window.sender_finished()

    def _run(self) -> None:
        window = self.window
        stats = window.stats
        # Filler is constant for the run; only the 16-byte header changes per
        # packet, so building it once keeps the sender off the CPU.
        filler = _pattern_bytes(self.pattern, max(self.payload_size - _HEADER_LEN, 0),
                                self.custom)

        sequence = 0
        deadline = time.monotonic() + self.duration if self.duration else None
        interval = 1.0 / self.rate_pps if self.rate_pps else 0.0
        next_send = time.monotonic()

        while not self._stop.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break
            if self.packet_limit and sequence >= self.packet_limit:
                break

            if not window.acquire_credit(timeout=0.25):
                with stats.lock:
                    stats.stalls += 1
                continue

            payload = _HEADER.pack(_MAGIC, sequence, time.monotonic_ns()) + filler
            packet = HciAclDataPacket(connection_handle=self.handle,
                                      pb_flag=self.pb_flag, bc_flag=0x00,
                                      data=payload)
            window.note_sent(sequence)

            try:
                ok = window.transport_write(packet.to_bytes())
            except Exception as exc:            # noqa: BLE001
                window.report(f"! send failed: {exc}")
                window.release_credit()
                with stats.lock:
                    stats.errors += 1
                break

            if not ok:
                window.release_credit()
                with stats.lock:
                    stats.errors += 1
                # A refused write means the transport is backed up; easing off
                # is better than spinning on it.
                time.sleep(0.005)
                continue

            with stats.lock:
                stats.tx_packets += 1
                stats.tx_bytes += len(payload)
            sequence += 1

            if interval:
                next_send += interval
                sleep_for = next_send - time.monotonic()
                if sleep_for > 0:
                    self._stop.wait(sleep_for)
                else:
                    # Behind schedule: reset the clock rather than trying to
                    # catch up in a burst.
                    next_send = time.monotonic()


class ThroughputWindow(QWidget):
    """Throughput and latency test over an attached HCI session."""

    _instance: Optional['ThroughputWindow'] = None

    _report = pyqtSignal(str)
    _finished = pyqtSignal()

    #: Fallback when the controller has not been asked for its buffer size.
    DEFAULT_CREDITS = 8
    DEFAULT_MAX_PAYLOAD = 251

    @classmethod
    def create_instance(cls, main_window: QMainWindow) -> 'ThroughputWindow':
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

        self.stats = Stats()
        self._sender: Optional[_Sender] = None
        self._running = False

        # Flow control. `_credit_cv` is what the sender blocks on.
        self._credit_cv = threading.Condition()
        self._credits = self.DEFAULT_CREDITS
        self._max_credits = self.DEFAULT_CREDITS
        self._max_payload = self.DEFAULT_MAX_PAYLOAD

        # sequence -> send time, for the RTT match. Bounded: a peer that never
        # echoes must not turn this into a memory leak.
        self._pending: dict = {}
        self._pending_lock = threading.Lock()
        self._last_seen_sequence = -1

        self._build_ui()
        self._build_subwindow()

        self._report.connect(self._append_log)
        self._finished.connect(self._on_finished)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(250)

        self.refresh_sessions()

    # ------------------------------------------------------------------ layout

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
        root.addLayout(source_row)

        root.addWidget(self._config_box())
        root.addWidget(self._control_row())
        root.addWidget(self._stats_box())

        log_box = QGroupBox("Test log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setFont(QFont("Menlo", 10))
        log_layout.addWidget(self.log_view)
        root.addWidget(log_box, 1)

    def _config_box(self) -> QWidget:
        box = QGroupBox("Test configuration")
        form = QFormLayout(box)

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("TX (send to the peer)", "tx")
        self.direction_combo.addItem("RX (count what arrives)", "rx")
        self.direction_combo.addItem("Bidirectional (send and count)", "both")
        self.direction_combo.setToolTip(
            "RX only counts; the peer has to be the one sending.")
        form.addRow("Direction:", self.direction_combo)

        self.handle_combo = QComboBox()
        form.addRow("Connection:", self.handle_combo)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 3600)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.setToolTip("0 = run until stopped")
        form.addRow("Duration:", self.duration_spin)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(_HEADER_LEN, 0xFFFF)
        self.size_spin.setValue(self.DEFAULT_MAX_PAYLOAD)
        self.size_spin.setSuffix(" bytes")
        self.size_spin.setToolTip(
            "ACL payload per packet, including the 16-byte test header. "
            "Above the controller's max ACL length the controller will reject "
            "the write.")
        form.addRow("Payload Size:", self.size_spin)

        self.pattern_combo = QComboBox()
        for pattern in ("Incrementing", "Zeros (0x00)", "Ones (0xFF)",
                        "Alternating (0x55/0xAA)", "PRBS9", "Random",
                        "Custom hex"):
            self.pattern_combo.addItem(pattern)
        self.pattern_combo.currentTextChanged.connect(
            lambda text: self.custom_input.setEnabled(text == "Custom hex"))
        form.addRow("Data Pattern:", self.pattern_combo)

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Hex bytes, repeated to fill the payload")
        self.custom_input.setEnabled(False)
        form.addRow("Custom Pattern:", self.custom_input)

        self.packets_spin = QSpinBox()
        self.packets_spin.setRange(0, 10_000_000)
        self.packets_spin.setValue(0)
        self.packets_spin.setToolTip("0 = no packet limit; stop on duration only")
        form.addRow("Packet Limit:", self.packets_spin)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(0, 100_000)
        self.rate_spin.setValue(0)
        self.rate_spin.setSuffix(" pkt/s")
        self.rate_spin.setToolTip(
            "0 = send as fast as the controller's credits allow")
        form.addRow("Send Rate:", self.rate_spin)

        self.credits_spin = QSpinBox()
        self.credits_spin.setRange(1, 255)
        self.credits_spin.setValue(self.DEFAULT_CREDITS)
        self.credits_spin.setToolTip(
            "ACL packets the controller can hold. Read it from the controller "
            "with the button below rather than guessing.")
        form.addRow("Controller Buffers:", self.credits_spin)

        self.latency_check = QCheckBox(
            "Measure round-trip latency (needs a peer that echoes the payload)")
        self.latency_check.setChecked(True)
        form.addRow("", self.latency_check)

        self.flushable_check = QCheckBox(
            "Send as flushable (automatically-flushable ACL packets)")
        form.addRow("", self.flushable_check)

        read_btn = QPushButton("Read buffer size from controller")
        read_btn.setToolTip("LE Read Buffer Size -- fills in the fields above")
        read_btn.clicked.connect(self._read_buffer_size)
        form.addRow("", read_btn)

        return box

    def _control_row(self) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)

        self.start_btn = QPushButton("Start Test")
        self.start_btn.clicked.connect(self.start_test)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_test)
        layout.addWidget(self.stop_btn)

        reset_btn = QPushButton("Reset Counters")
        reset_btn.clicked.connect(self.reset_stats)
        layout.addWidget(reset_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress, 1)

        return holder

    def _stats_box(self) -> QWidget:
        box = QGroupBox("Results")
        grid = QGridLayout(box)
        self._value_labels = {}

        fields = [
            ("Elapsed", "elapsed"), ("TX throughput", "tx_rate"),
            ("RX throughput", "rx_rate"), ("TX packets", "tx_packets"),
            ("TX bytes", "tx_bytes"), ("RX packets", "rx_packets"),
            ("RX bytes", "rx_bytes"), ("Packet rate", "pps"),
            ("Latency last", "lat_last"), ("Latency min", "lat_min"),
            ("Latency avg", "lat_avg"), ("Latency max", "lat_max"),
            ("Credits free", "credits"), ("Flow stalls", "stalls"),
            ("Out of order", "ooo"), ("Errors", "errors"),
        ]
        mono = QFont("Menlo", 11)
        for index, (title, key) in enumerate(fields):
            row, column = divmod(index, 4)
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.setSpacing(1)

            caption = QLabel(title)
            caption.setStyleSheet("color: gray; font-size: 10pt;")
            value = QLabel("-")
            value.setFont(mono)
            cell_layout.addWidget(caption)
            cell_layout.addWidget(value)

            grid.addWidget(cell, row, column)
            self._value_labels[key] = value

        return box

    def _build_subwindow(self) -> None:
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWindowTitle("Throughput Test")
        self.sub_window.setWidget(self)
        self.sub_window.setWindowFlags(Qt.Window)
        self.sub_window.resize(820, 860)
        self.sub_window.setMinimumSize(620, 560)
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)
        self.sub_window.destroyed.connect(lambda *_: self.cleanup())

        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        self.sub_window.raise_()
        self.sub_window.activateWindow()

    # ------------------------------------------------------------ attaching

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
            self.log("! no HCI session -- open Tools > HCI and connect first")
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
        session.on(EVT_PACKET, self._on_packet)
        session.on(EVT_EVENT, self._on_event)
        session.on(EVT_CONNECTION_UP, self._on_connections_changed)
        session.on(EVT_CONNECTION_DOWN, self._on_connections_changed)
        instance.session_closing.connect(self._on_session_closing)

        self._apply_buffer_size()
        self.refresh_handles()
        self.sub_window.setWindowTitle(f"Throughput Test - {instance.title}")
        self.log(f"= attached to {instance.title}")

    def _detach(self) -> None:
        if self._running:
            self.stop_test()
        session, self.session = self.session, None
        if session is not None:
            for channel, handler in (
                (EVT_PACKET, self._on_packet),
                (EVT_EVENT, self._on_event),
                (EVT_CONNECTION_UP, self._on_connections_changed),
                (EVT_CONNECTION_DOWN, self._on_connections_changed),
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
            self.sub_window.setWindowTitle("Throughput Test")
        except RuntimeError:
            pass

    def _on_session_closing(self, instance) -> None:
        self._detach()
        self.refresh_sessions(ignore=instance)

    def refresh_handles(self) -> None:
        previous = self.handle_combo.currentData()
        self.handle_combo.clear()
        if self.session is None:
            return
        for info in self.session.connections.all():
            self.handle_combo.addItem(
                f"0x{info.handle:04X}  {info.bd_addr}  ({info.link_type.value})",
                info.handle)
        if previous is not None:
            index = self.handle_combo.findData(previous)
            if index >= 0:
                self.handle_combo.setCurrentIndex(index)

    def _apply_buffer_size(self) -> None:
        """Take the ACL buffer figures the session already learned, if any."""
        if self.session is None:
            return
        buffers = self.session.le_buffer_size or self.session.acl_buffer_size
        if not buffers:
            return
        payload, count = buffers
        if payload:
            self._max_payload = payload
            self.size_spin.setMaximum(max(payload, _HEADER_LEN))
            self.size_spin.setValue(min(self.size_spin.value(), payload))
        if count:
            self.credits_spin.setValue(min(count, 255))
        self.log(f"= controller buffers: {count} x {payload} bytes")

    def _read_buffer_size(self) -> None:
        if self.session is None:
            self.log("! no session attached")
            return
        import hci.cmd.le_cmds as le_cmds

        def _done(response, error):
            if error is not None:
                self._report.emit(f"! LE Read Buffer Size: {error}")
                return
            # The session decodes this into le_buffer_size for us.
            self._report.emit("< LE Read Buffer Size: ok")

        self.log("> LE Read Buffer Size")
        self.session.send(le_cmds.LeReadBufferSize(), on_complete=_done)
        QTimer.singleShot(600, self._apply_buffer_size)

    # ------------------------------------------------------------ flow control

    def acquire_credit(self, timeout: float) -> bool:
        """Block until the controller can take another ACL packet."""
        with self._credit_cv:
            if self._credits <= 0:
                if not self._credit_cv.wait_for(lambda: self._credits > 0, timeout):
                    return False
            self._credits -= 1
            return True

    def release_credit(self, count: int = 1) -> None:
        with self._credit_cv:
            self._credits = min(self._credits + count, self._max_credits)
            self._credit_cv.notify_all()

    def transport_write(self, data: bytes) -> bool:
        session = self.session
        if session is None:
            return False
        return bool(session.transport.write(data))

    def note_sent(self, sequence: int) -> None:
        if not self._latency_enabled:
            return
        with self._pending_lock:
            # Only the recent window can plausibly still be in flight; capping
            # it keeps a non-echoing peer from growing this without bound.
            if len(self._pending) > 512:
                for key in sorted(self._pending)[:256]:
                    del self._pending[key]
            self._pending[sequence] = time.monotonic_ns()

    def report(self, message: str) -> None:
        self._report.emit(message)

    def sender_finished(self) -> None:
        self._finished.emit()

    # -------------------------------------------------- session observers (I/O)

    def _on_packet(self, raw: bytes, event) -> None:
        """Every packet the transport delivered. ACL data is what we count."""
        if not raw or raw[0] != 0x02 or len(raw) < 5:
            return
        payload = raw[5:]
        with self.stats.lock:
            self.stats.rx_packets += 1
            self.stats.rx_bytes += len(payload)

        if not self._latency_enabled or len(payload) < _HEADER_LEN:
            return
        magic, sequence, _sent_ns = _HEADER.unpack_from(payload, 0)
        if magic != _MAGIC:
            return

        # An echo of our own packet: the round trip is now minus when we sent it.
        with self._pending_lock:
            sent_at = self._pending.pop(sequence, None)
        if sent_at is None:
            return
        self.stats.add_latency((time.monotonic_ns() - sent_at) / 1e6)

        if sequence < self._last_seen_sequence:
            with self.stats.lock:
                self.stats.out_of_order += 1
        self._last_seen_sequence = sequence

    def _on_event(self, event) -> None:
        """Number Of Completed Packets is what gives our credits back."""
        if getattr(event, 'EVENT_CODE', None) != HciEventCode.NUMBER_OF_COMPLETED_PACKETS:
            return
        counts = event.params.get('num_completed_packets') or []
        total = sum(counts) if counts else 1
        self.release_credit(total)

    def _on_connections_changed(self, *_args) -> None:
        # Runs on the I/O thread; the combo is repopulated on the UI timer tick.
        self._connections_dirty = True

    # ------------------------------------------------------------------ actions

    _connections_dirty = False
    _latency_enabled = True

    def start_test(self) -> None:
        if self._running:
            return
        if self.session is None:
            self.log("! no session attached")
            return

        handle = self.handle_combo.currentData()
        direction = self.direction_combo.currentData()
        if handle is None and direction != "rx":
            self.log("! no connection selected -- connect first, then Refresh")
            return

        try:
            custom = bytes.fromhex(
                self.custom_input.text().replace(" ", "").replace("0x", ""))
        except ValueError:
            self.log("! custom pattern is not valid hex")
            return

        size = self.size_spin.value()
        if size > self._max_payload:
            self.log(f"! payload {size} exceeds the controller's max ACL length "
                     f"({self._max_payload}); the write will be rejected")

        self.reset_stats()
        self._latency_enabled = self.latency_check.isChecked()
        self._max_credits = self.credits_spin.value()
        with self._credit_cv:
            self._credits = self._max_credits

        self.stats.started_at = time.monotonic()
        self._running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        duration = float(self.duration_spin.value())
        if direction == "rx":
            # Nothing to send: the timer stops the run when the duration is up.
            self._sender = None
            self.log(f"> RX test started ({'until stopped' if not duration else f'{duration:.0f}s'})")
            return

        self._sender = _Sender(
            self, handle=handle, payload_size=size,
            pattern=self.pattern_combo.currentText(), custom=custom,
            duration=duration, packet_limit=self.packets_spin.value(),
            rate_pps=self.rate_spin.value(),
            flushable=self.flushable_check.isChecked(),
        )
        self._sender.start()
        self.log(f"> {direction.upper()} test started: {size}B payload, "
                 f"{self.pattern_combo.currentText()}, "
                 f"{'unlimited' if not duration else f'{duration:.0f}s'}, "
                 f"{self._max_credits} credits")

    def stop_test(self) -> None:
        if not self._running:
            return
        if self._sender is not None:
            self._sender.stop()
            self._sender.join(timeout=1.0)
            self._sender = None
        self._on_finished()

    def _on_finished(self) -> None:
        if not self._running:
            return
        self._running = False
        self.stats.stopped_at = time.monotonic()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._refresh_stats()

        elapsed = self.stats.elapsed()
        self.log(
            f"= finished after {elapsed:.2f}s: "
            f"TX {self.stats.tx_packets} pkt / {self._fmt_bytes(self.stats.tx_bytes)} "
            f"({self._fmt_rate(self.stats.tx_bytes, elapsed)}), "
            f"RX {self.stats.rx_packets} pkt / {self._fmt_bytes(self.stats.rx_bytes)} "
            f"({self._fmt_rate(self.stats.rx_bytes, elapsed)})")
        if self.stats.latency_count:
            self.log(f"= latency min/avg/max: {self.stats.latency_min:.2f} / "
                     f"{self.stats.latency_avg:.2f} / {self.stats.latency_max:.2f} ms "
                     f"over {self.stats.latency_count} round trips")
        elif self._latency_enabled and self.stats.tx_packets:
            self.log("= no echoes seen, so no latency figures; the peer has to "
                     "send the payload back for a round trip to be measurable")

    def reset_stats(self) -> None:
        self.stats = Stats()
        with self._pending_lock:
            self._pending.clear()
        self._last_seen_sequence = -1
        self.progress.setValue(0)
        self._refresh_stats()

    # ------------------------------------------------------------- rendering

    @staticmethod
    def _fmt_bytes(value: int) -> str:
        for unit, scale in (("MB", 1 << 20), ("kB", 1 << 10)):
            if value >= scale:
                return f"{value / scale:.2f} {unit}"
        return f"{value} B"

    @staticmethod
    def _fmt_rate(byte_count: int, seconds: float) -> str:
        if seconds <= 0:
            return "-"
        bits = byte_count * 8 / seconds
        if bits >= 1e6:
            return f"{bits / 1e6:.3f} Mbps"
        if bits >= 1e3:
            return f"{bits / 1e3:.1f} kbps"
        return f"{bits:.0f} bps"

    def _refresh_stats(self) -> None:
        if self._is_destroyed:
            return
        if self._connections_dirty:
            self._connections_dirty = False
            self.refresh_handles()

        stats = self.stats
        elapsed = stats.elapsed() if stats.started_at else 0.0
        labels = self._value_labels

        labels["elapsed"].setText(f"{elapsed:.2f} s" if elapsed else "-")
        labels["tx_rate"].setText(self._fmt_rate(stats.tx_bytes, elapsed))
        labels["rx_rate"].setText(self._fmt_rate(stats.rx_bytes, elapsed))
        labels["tx_packets"].setText(str(stats.tx_packets))
        labels["tx_bytes"].setText(self._fmt_bytes(stats.tx_bytes))
        labels["rx_packets"].setText(str(stats.rx_packets))
        labels["rx_bytes"].setText(self._fmt_bytes(stats.rx_bytes))
        labels["pps"].setText(
            f"{stats.tx_packets / elapsed:.0f}/s" if elapsed else "-")

        for key, value in (("lat_last", stats.latency_last),
                           ("lat_min", stats.latency_min),
                           ("lat_avg", stats.latency_avg),
                           ("lat_max", stats.latency_max)):
            labels[key].setText("-" if value is None else f"{value:.2f} ms")

        with self._credit_cv:
            credits_free = self._credits
        labels["credits"].setText(f"{credits_free}/{self._max_credits}")
        labels["stalls"].setText(str(stats.stalls))
        labels["ooo"].setText(str(stats.out_of_order))
        labels["errors"].setText(str(stats.errors))
        labels["errors"].setStyleSheet("color: red;" if stats.errors else "")

        duration = self.duration_spin.value()
        if self._running and duration:
            self.progress.setValue(min(int(elapsed / duration * 100), 100))
            # An RX-only run has no sender thread to notice the deadline.
            if self._sender is None and elapsed >= duration:
                self._on_finished()
        elif self._running:
            self.progress.setValue(0)

    def log(self, message: str) -> None:
        self._report.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    # ------------------------------------------------------------------ teardown

    def cleanup(self) -> None:
        if self._is_destroyed:
            return
        self._is_destroyed = True
        try:
            self._timer.stop()
        except RuntimeError:
            pass
        if self._sender is not None:
            self._sender.stop()
            self._sender = None
        self._running = False
        self._detach()
        if ThroughputWindow._instance is self:
            ThroughputWindow._instance = None


__all__ = ["ThroughputWindow"]
