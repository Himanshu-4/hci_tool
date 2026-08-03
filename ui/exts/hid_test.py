"""
HID test screen -- send HID reports as a Bluetooth HID Device.

HID over BR/EDR is HID reports wrapped in a one-byte transaction header, sent
on an L2CAP channel: the interrupt channel (PSM 0x0013) for input reports, the
control channel (PSM 0x0011) for handshakes and control messages.

This screen builds and sends those reports. It does **not** run L2CAP: the CIDs
have to come from whatever established the channels, which is why they are
fields rather than something discovered. See `l2cap_util` for why that limit
exists.

Keyboard and mouse use the boot protocol report layouts, which every host
understands without a report descriptor -- so a report sent from here lands as a
real keypress or pointer movement on the other side.
"""

from __future__ import annotations

import struct
import threading
import time
from typing import Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from .l2cap_util import (
    PSM_HID_CONTROL, PSM_HID_INTERRUPT, L2capReassembler, acl_packets_for,
)
from .test_window_base import SessionTestWindow, connection_combo_items

#: HIDP transaction header: message type in the top nibble.
HIDP_HANDSHAKE = 0x00
HIDP_CONTROL = 0x10
HIDP_GET_REPORT = 0x40
HIDP_SET_REPORT = 0x50
HIDP_GET_PROTOCOL = 0x60
HIDP_SET_PROTOCOL = 0x70
HIDP_DATA = 0xA0

#: Report type, in the bottom nibble of a DATA/GET_REPORT/SET_REPORT header.
REPORT_TYPE_OTHER = 0x00
REPORT_TYPE_INPUT = 0x01
REPORT_TYPE_OUTPUT = 0x02
REPORT_TYPE_FEATURE = 0x03

#: HID modifier bits for the boot keyboard report.
MODIFIERS = (
    ("Left Ctrl", 0x01), ("Left Shift", 0x02), ("Left Alt", 0x04),
    ("Left GUI", 0x08), ("Right Ctrl", 0x10), ("Right Shift", 0x20),
    ("Right Alt", 0x40), ("Right GUI", 0x80),
)

#: A few HID usage codes, enough to type with.
KEY_CODES = {
    **{chr(ord('a') + i): 0x04 + i for i in range(26)},
    **{str((i + 1) % 10): 0x1E + i for i in range(10)},
    "Enter": 0x28, "Escape": 0x29, "Backspace": 0x2A, "Tab": 0x2B,
    "Space": 0x2C, "Caps Lock": 0x39,
    "F1": 0x3A, "F2": 0x3B, "F3": 0x3C, "F4": 0x3D,
    "Right Arrow": 0x4F, "Left Arrow": 0x50, "Down Arrow": 0x51, "Up Arrow": 0x52,
}


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


def keyboard_report(modifiers: int = 0, keys=()) -> bytes:
    """Boot keyboard input report: modifiers, reserved, then up to six keys."""
    codes = list(keys)[:6]
    return bytes([modifiers & 0xFF, 0x00]) + bytes(codes).ljust(6, b"\x00")


def mouse_report(buttons: int = 0, dx: int = 0, dy: int = 0,
                 wheel: int = 0) -> bytes:
    """Boot mouse input report, plus the wheel byte most descriptors add."""
    return struct.pack("<Bbbb", buttons & 0x07,
                       max(-127, min(127, dx)), max(-127, min(127, dy)),
                       max(-127, min(127, wheel)))


class _HidRepeater(threading.Thread):
    """Sends a report at a fixed rate, for latency and throughput checks."""

    def __init__(self, window: "HidTestWindow", report: bytes, report_id: int,
                 interval: float, duration: float, moving: bool):
        super().__init__(name="hci-hid-tx", daemon=True)
        self.window = window
        self.report = report
        self.report_id = report_id
        self.interval = interval
        self.duration = duration
        self.moving = moving
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:            # noqa: BLE001
            self.window.log(f"! HID repeater stopped: {exc!r}")
        finally:
            self.window.repeater_finished_signal.emit()

    def _run(self) -> None:
        deadline = time.monotonic() + self.duration if self.duration else None
        next_send = time.monotonic()
        step = 0

        while not self._stop.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break

            report = self.report
            if self.moving:
                # Trace a small square so the pointer visibly moves rather than
                # drifting off the screen in one direction.
                dx, dy = ((5, 0), (0, 5), (-5, 0), (0, -5))[step % 4]
                report = mouse_report(0, dx, dy)
                step += 1

            self.window.send_report(report, self.report_id)

            next_send += self.interval
            sleep_for = next_send - time.monotonic()
            if sleep_for > 0:
                self._stop.wait(sleep_for)
            else:
                next_send = time.monotonic()


class HidTestWindow(SessionTestWindow):
    """Bluetooth HID Device: send input reports over the interrupt channel."""

    WINDOW_TITLE = "HID Test"
    WINDOW_SIZE = (780, 900)

    repeater_finished_signal = pyqtSignal()

    def __init__(self, main_window):
        self._repeater: Optional[_HidRepeater] = None
        self._reassembler = L2capReassembler()
        self.tx_reports = self.tx_bytes = 0
        self.rx_frames = self.rx_bytes = 0
        self._started = 0.0
        super().__init__(main_window)

        self.repeater_finished_signal.connect(self.repeater_finished)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(400)

    # ----------------------------------------------------------------- layout

    def build_body(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._channel_box())
        tabs = QTabWidget()
        tabs.addTab(self._keyboard_tab(), "Keyboard")
        tabs.addTab(self._mouse_tab(), "Mouse")
        tabs.addTab(self._raw_tab(), "Raw Report")
        layout.addWidget(tabs)
        layout.addWidget(self._stats_box())

    def _channel_box(self) -> QWidget:
        box = QGroupBox("HID channels")
        form = QFormLayout(box)

        self.acl_combo = QComboBox()
        form.addRow("ACL Connection:", self.acl_combo)

        self.interrupt_cid_input = _spin(0x0001, 0xFFFF, 0x0041,
                                         f"L2CAP CID of the interrupt channel "
                                         f"(PSM 0x{PSM_HID_INTERRUPT:04X}) -- "
                                         "input reports go here")
        form.addRow("Interrupt CID:", self.interrupt_cid_input)

        self.control_cid_input = _spin(0x0001, 0xFFFF, 0x0040,
                                       f"L2CAP CID of the control channel "
                                       f"(PSM 0x{PSM_HID_CONTROL:04X})")
        form.addRow("Control CID:", self.control_cid_input)

        self.max_acl_input = _spin(23, 0xFFFF, 27,
                                   "Controller's ACL data length, from Read "
                                   "Buffer Size; longer frames are fragmented",
                                   " bytes")
        form.addRow("Max ACL Payload:", self.max_acl_input)

        self.report_id_input = _spin(0, 255, 0,
                                     "Prefixed to the report when non-zero; "
                                     "0 means the descriptor uses no report IDs")
        form.addRow("Report ID:", self.report_id_input)

        form.addRow("", _hint(
            "This screen speaks HIDP on channels that already exist -- it does "
            "not run L2CAP, so the CIDs have to come from whatever set the "
            "channels up. Sending on the wrong CID is silently dropped by the "
            "peer."))
        return box

    def _keyboard_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        modifiers = QWidget()
        modifier_layout = QGridLayout(modifiers)
        modifier_layout.setContentsMargins(0, 0, 0, 0)
        self.modifier_checks = {}
        for index, (label, bit) in enumerate(MODIFIERS):
            box = QCheckBox(label)
            modifier_layout.addWidget(box, index // 4, index % 4)
            self.modifier_checks[bit] = box
        form.addRow("Modifiers:", modifiers)

        self.key_combo = QComboBox()
        for name in KEY_CODES:
            self.key_combo.addItem(name, KEY_CODES[name])
        form.addRow("Key:", self.key_combo)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a string to send as keystrokes")
        form.addRow("Text:", self.text_input)

        press_btn = QPushButton("Press && Release")
        press_btn.clicked.connect(lambda: self._send_key(True))
        hold_btn = QPushButton("Press (hold)")
        hold_btn.clicked.connect(lambda: self._send_key(False))
        release_btn = QPushButton("Release All")
        release_btn.clicked.connect(
            lambda: self.send_report(keyboard_report(),
                                     self.report_id_input.value()))
        type_btn = QPushButton("Type Text")
        type_btn.clicked.connect(self._type_text)
        form.addRow("", self._row(press_btn, hold_btn, release_btn, type_btn))

        form.addRow("", _hint(
            "Boot keyboard layout: modifiers, a reserved byte, then up to six "
            "key codes. A key stays down until a report without that code is "
            "sent, which is what Release All does."))
        return page

    def _mouse_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_checks = {}
        for label, bit in (("Left", 0x01), ("Right", 0x02), ("Middle", 0x04)):
            box = QCheckBox(label)
            button_layout.addWidget(box)
            self.button_checks[bit] = box
        button_layout.addStretch(1)
        form.addRow("Buttons:", buttons)

        self.dx_input = _spin(-127, 127, 10, "Horizontal movement")
        self.dy_input = _spin(-127, 127, 0, "Vertical movement")
        self.wheel_input = _spin(-127, 127, 0, "Wheel movement")
        form.addRow("X:", self.dx_input)
        form.addRow("Y:", self.dy_input)
        form.addRow("Wheel:", self.wheel_input)

        move_btn = QPushButton("Send Movement")
        move_btn.clicked.connect(self._send_mouse)
        click_btn = QPushButton("Click")
        click_btn.clicked.connect(self._send_click)
        form.addRow("", self._row(move_btn, click_btn))

        repeat_box = QGroupBox("Repeat")
        repeat_form = QFormLayout(repeat_box)

        self.interval_input = _spin(1, 5000, 11,
                                    "Report interval; 11 ms is roughly the "
                                    "90 Hz a real mouse uses", " ms")
        repeat_form.addRow("Interval:", self.interval_input)

        self.duration_input = _spin(0, 3600, 5, "0 = until stopped", " s")
        repeat_form.addRow("Duration:", self.duration_input)

        self.square_check = QCheckBox("Trace a square (so the pointer stays put)")
        self.square_check.setChecked(True)
        repeat_form.addRow("", self.square_check)

        self.start_btn = QPushButton("Start Repeating")
        self.start_btn.clicked.connect(self._start_repeat)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_repeat)
        repeat_form.addRow("", self._row(self.start_btn, self.stop_btn))

        form.addRow(repeat_box)
        return page

    def _raw_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.report_type_combo = QComboBox()
        self.report_type_combo.addItem("Input", REPORT_TYPE_INPUT)
        self.report_type_combo.addItem("Output", REPORT_TYPE_OUTPUT)
        self.report_type_combo.addItem("Feature", REPORT_TYPE_FEATURE)
        form.addRow("Report Type:", self.report_type_combo)

        self.channel_combo = QComboBox()
        self.channel_combo.addItem("Interrupt channel", "interrupt")
        self.channel_combo.addItem("Control channel", "control")
        form.addRow("Channel:", self.channel_combo)

        self.raw_input = QLineEdit()
        self.raw_input.setPlaceholderText("Report payload, hex (no HIDP header)")
        form.addRow("Report:", self.raw_input)

        send_btn = QPushButton("Send Report")
        send_btn.clicked.connect(self._send_raw)
        form.addRow("", self._row(send_btn))

        control = QGroupBox("Control channel messages")
        control_form = QFormLayout(control)
        suspend_btn = QPushButton("Suspend")
        suspend_btn.clicked.connect(lambda: self._send_control(0x03))
        resume_btn = QPushButton("Exit Suspend")
        resume_btn.clicked.connect(lambda: self._send_control(0x04))
        unplug_btn = QPushButton("Virtual Cable Unplug")
        unplug_btn.clicked.connect(lambda: self._send_control(0x05))
        control_form.addRow("", self._row(suspend_btn, resume_btn, unplug_btn))
        form.addRow(control)

        form.addRow("", _hint(
            "The HIDP transaction header is added automatically: 0xA1 for an "
            "input DATA report, 0xA2 output, 0xA3 feature. Enter only the "
            "report payload here."))
        return page

    def _stats_box(self) -> QWidget:
        box = QGroupBox("Statistics")
        grid = QGridLayout(box)
        self._stat_labels = {}
        for index, (title, key) in enumerate((
                ("Reports sent", "tx_reports"), ("Bytes sent", "tx_bytes"),
                ("Report rate", "tx_rate"), ("Frames received", "rx_frames"))):
            caption = QLabel(title)
            caption.setStyleSheet("color: gray; font-size: 10pt;")
            value = QLabel("-")
            grid.addWidget(caption, 0, index)
            grid.addWidget(value, 1, index)
            self._stat_labels[key] = value
        return box

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

    def send_report(self, payload: bytes, report_id: int = 0,
                    report_type: int = REPORT_TYPE_INPUT,
                    channel: str = "interrupt") -> bool:
        """Wrap a report in its HIDP header and put it on the channel."""
        handle = self.acl_combo.currentData()
        if handle is None:
            self.log("! no ACL connection selected")
            return False

        cid = (self.interrupt_cid_input.value() if channel == "interrupt"
               else self.control_cid_input.value())

        body = bytes([HIDP_DATA | report_type])
        if report_id:
            body += bytes([report_id])
        body += bytes(payload)

        ok = True
        for packet in acl_packets_for(handle, cid, body,
                                      self.max_acl_input.value()):
            ok = self.write_packet(packet) and ok
        if ok:
            self.tx_reports += 1
            self.tx_bytes += len(body)
            if not self._started:
                self._started = time.monotonic()
        else:
            self.log("! write refused -- check the ACL payload size")
        return ok

    def _modifier_value(self) -> int:
        value = 0
        for bit, box in self.modifier_checks.items():
            if box.isChecked():
                value |= bit
        return value

    def _button_value(self) -> int:
        value = 0
        for bit, box in self.button_checks.items():
            if box.isChecked():
                value |= bit
        return value

    # ---------------------------------------------------------------- actions

    def _send_key(self, release: bool = True) -> None:
        code = self.key_combo.currentData()
        report_id = self.report_id_input.value()
        self.send_report(keyboard_report(self._modifier_value(), [code]),
                         report_id)
        if release:
            self.send_report(keyboard_report(), report_id)
        self.log(f"> key {self.key_combo.currentText()}"
                 f"{'' if release else ' (held)'}")

    def _type_text(self) -> None:
        text = self.text_input.text()
        if not text:
            self.log("! nothing to type")
            return
        report_id = self.report_id_input.value()
        sent = 0
        for char in text:
            code = KEY_CODES.get(char.lower())
            if code is None and char == " ":
                code = KEY_CODES["Space"]
            if code is None:
                continue
            # A capital is the same usage code with shift held.
            modifiers = 0x02 if char.isupper() else 0x00
            self.send_report(keyboard_report(modifiers, [code]), report_id)
            self.send_report(keyboard_report(), report_id)
            sent += 1
        self.log(f"> typed {sent} character(s)")

    def _send_mouse(self) -> None:
        self.send_report(mouse_report(self._button_value(),
                                      self.dx_input.value(),
                                      self.dy_input.value(),
                                      self.wheel_input.value()),
                         self.report_id_input.value())

    def _send_click(self) -> None:
        report_id = self.report_id_input.value()
        buttons = self._button_value() or 0x01
        self.send_report(mouse_report(buttons), report_id)
        self.send_report(mouse_report(0), report_id)
        self.log("> click")

    def _send_raw(self) -> None:
        text = self.raw_input.text().strip().replace(" ", "").replace("0x", "")
        if not text:
            self.log("! enter a report payload")
            return
        if len(text) % 2:
            text = "0" + text
        try:
            payload = bytes.fromhex(text)
        except ValueError:
            self.log(f"! report is not valid hex: {self.raw_input.text()!r}")
            return
        self.send_report(payload, self.report_id_input.value(),
                         self.report_type_combo.currentData(),
                         self.channel_combo.currentData())
        self.log(f"> raw report, {len(payload)} bytes")

    def _send_control(self, control_code: int) -> None:
        handle = self.acl_combo.currentData()
        if handle is None:
            self.log("! no ACL connection selected")
            return
        body = bytes([HIDP_CONTROL | (control_code & 0x0F)])
        for packet in acl_packets_for(handle, self.control_cid_input.value(),
                                      body, self.max_acl_input.value()):
            self.write_packet(packet)
        self.log(f"> HIDP control 0x{body[0]:02X}")

    def _start_repeat(self) -> None:
        if self._repeater is not None:
            return
        if self.acl_combo.currentData() is None:
            self.log("! no ACL connection selected")
            return

        self.tx_reports = self.tx_bytes = 0
        self._started = time.monotonic()
        self._repeater = _HidRepeater(
            self,
            report=mouse_report(self._button_value(), self.dx_input.value(),
                                self.dy_input.value(), self.wheel_input.value()),
            report_id=self.report_id_input.value(),
            interval=self.interval_input.value() / 1000.0,
            duration=float(self.duration_input.value()),
            moving=self.square_check.isChecked())
        self._repeater.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log(f"> repeating a mouse report every "
                 f"{self.interval_input.value()} ms")

    def _stop_repeat(self) -> None:
        if self._repeater is not None:
            self._repeater.stop()
            self._repeater.join(timeout=1.0)
            self._repeater = None
        self.repeater_finished()

    def repeater_finished(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

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
        """Reassemble incoming HIDP frames. I/O thread."""
        for handle, cid, payload in self._reassembler.feed(raw):
            if cid not in (self.interrupt_cid_input.value(),
                           self.control_cid_input.value()):
                continue
            self.rx_frames += 1
            self.rx_bytes += len(payload)
            if payload:
                kind = {HIDP_HANDSHAKE: "handshake", HIDP_CONTROL: "control",
                        HIDP_GET_REPORT: "get report",
                        HIDP_SET_REPORT: "set report",
                        HIDP_DATA: "data"}.get(payload[0] & 0xF0, "?")
                self._line.emit(f"< HIDP {kind} on CID 0x{cid:04X}: "
                                f"{payload.hex(' ')}")

    def _refresh_stats(self) -> None:
        if self._is_destroyed:
            return
        elapsed = time.monotonic() - self._started if self._started else 0.0
        labels = self._stat_labels
        labels["tx_reports"].setText(str(self.tx_reports))
        labels["tx_bytes"].setText(str(self.tx_bytes))
        labels["tx_rate"].setText(
            f"{self.tx_reports / elapsed:.1f}/s" if elapsed else "-")
        labels["rx_frames"].setText(str(self.rx_frames))

    # ---------------------------------------------------------------- teardown

    def on_cleanup(self) -> None:
        try:
            self._timer.stop()
        except RuntimeError:
            pass
        if self._repeater is not None:
            self._repeater.stop()
            self._repeater = None


__all__ = ["HidTestWindow"]
