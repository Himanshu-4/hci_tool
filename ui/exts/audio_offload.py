"""
Audio offload -- routing audio off the HCI link onto a separate interface.

Three routes, and the difference matters:

* **Over HCI** -- audio rides the same UART as commands and events, as SCO or
  ISO packets. Simple, works everywhere, and the reason a busy HCI link stutters
  audio: 8 kB/s of SCO competing with command traffic on one 115200 baud line is
  already 70% utilisation.
* **Separate interface** -- the controller is told to route audio to a vendor
  data path, and the audio itself is carried on a *second* UART this tool opens
  independently. HCI stays quiet, and the audio link can run at whatever baud
  the stream needs. This is what `AudioLink` below manages.
* **Controller internal** -- the controller routes audio to on-chip I2S/PCM
  hardware and the host never sees it. The tool still selects the data path, but
  there is nothing to stream.

The host cannot invent the data path: `Data_Path_ID` values 0x01..0xFE are
vendor-defined, so which id corresponds to which physical pin is a property of
the controller's firmware. The panel therefore lets the id be set rather than
guessing, and defaults to 0x01 only because that is the most common choice.

`AudioLink` deliberately owns its own `Transport` instance, separate from the
HCI one, so opening or losing the audio interface cannot disturb the HCI link.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from transports.base_lib import TransportEvent
from transports.transport import Transport


class AudioRoute(Enum):
    """Where the audio for a stream goes."""

    OVER_HCI = "hci"
    SEPARATE_INTERFACE = "separate"
    CONTROLLER_INTERNAL = "internal"


@dataclass
class AudioStats:
    """Byte and packet counters for one direction pair on the audio link."""

    tx_packets: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    rx_bytes: int = 0
    errors: int = 0
    started_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def elapsed(self) -> float:
        return max(time.monotonic() - self.started_at, 1e-9) if self.started_at else 0.0

    def reset(self) -> None:
        with self.lock:
            self.tx_packets = self.tx_bytes = 0
            self.rx_packets = self.rx_bytes = 0
            self.errors = 0
            self.started_at = time.monotonic()


class AudioLink:
    """
    The second interface that carries offloaded audio.

    Raw bytes only: no H4 framing, no HCI. What arrives is whatever the
    controller's audio path emits -- PCM, SBC frames, or a vendor container --
    so the caller decides how to interpret it.
    """

    def __init__(self, name: str = "AudioOffload"):
        self.name = name
        self.transport: Optional[Transport] = None
        self.stats = AudioStats()
        self._on_data: Optional[Callable[[bytes], None]] = None

    @property
    def is_open(self) -> bool:
        try:
            return self.transport is not None and self.transport.is_connected()
        except Exception:
            return False

    def open(self, interface: str, config: dict) -> None:
        """Open the audio interface. Raises on failure -- the caller reports it."""
        self.close()
        # A distinct instance name keeps this out of the HCI transport registry
        # slot, so closing one never touches the other.
        self.transport = Transport.get_instance(self.name)
        self.transport.select_interface(interface)
        self.transport.configure(config)
        self.transport.add_callback(TransportEvent.RAW_RX, self._on_raw_rx)
        self.transport.connect()
        self.stats.reset()

    def close(self) -> None:
        if self.transport is None:
            return
        try:
            self.transport.remove_callback(TransportEvent.RAW_RX, self._on_raw_rx)
        except Exception:
            pass
        try:
            self.transport.disconnect()
        except Exception:
            pass
        try:
            Transport.remove_instance(self.name)
        except Exception:
            pass
        self.transport = None

    def set_receiver(self, callback: Optional[Callable[[bytes], None]]) -> None:
        """Called from the audio link's I/O thread with each received chunk."""
        self._on_data = callback

    def write(self, data: bytes) -> bool:
        if not self.is_open:
            return False
        try:
            ok = bool(self.transport.write(data))
        except Exception:
            with self.stats.lock:
                self.stats.errors += 1
            return False
        if ok:
            with self.stats.lock:
                self.stats.tx_packets += 1
                self.stats.tx_bytes += len(data)
        else:
            with self.stats.lock:
                self.stats.errors += 1
        return ok

    def _on_raw_rx(self, chunk: bytes) -> None:
        # I/O thread. Count, then hand on; never touch a widget from here.
        with self.stats.lock:
            self.stats.rx_packets += 1
            self.stats.rx_bytes += len(chunk)
        if self._on_data is not None:
            try:
                self._on_data(bytes(chunk))
            except Exception:
                with self.stats.lock:
                    self.stats.errors += 1


def format_rate(byte_count: int, seconds: float) -> str:
    if seconds <= 0:
        return "-"
    bits = byte_count * 8 / seconds
    if bits >= 1e6:
        return f"{bits / 1e6:.3f} Mbps"
    if bits >= 1e3:
        return f"{bits / 1e3:.1f} kbps"
    return f"{bits:.0f} bps"


def format_bytes(value: int) -> str:
    for unit, scale in (("MB", 1 << 20), ("kB", 1 << 10)):
        if value >= scale:
            return f"{value / scale:.2f} {unit}"
    return f"{value} B"


class AudioOffloadPanel(QGroupBox):
    """
    Reusable audio-routing panel.

    Drop it into a test screen, read `route()` and `data_path_id()` when
    building the data-path command, and stream through `link` when the route is
    SEPARATE_INTERFACE.
    """

    def __init__(self, title: str = "Audio routing", parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self.link = AudioLink()
        self._build()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(500)

    # ---------------------------------------------------------------- layout

    def _build(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self.route_combo = QComboBox()
        self.route_combo.addItem("Over HCI (same link as commands)",
                                 AudioRoute.OVER_HCI)
        self.route_combo.addItem("Separate interface (offload to another UART)",
                                 AudioRoute.SEPARATE_INTERFACE)
        self.route_combo.addItem("Controller internal (I2S/PCM, host sees nothing)",
                                 AudioRoute.CONTROLLER_INTERNAL)
        self.route_combo.currentIndexChanged.connect(self._on_route_changed)
        form.addRow("Route:", self.route_combo)

        self.path_id_input = QSpinBox()
        self.path_id_input.setRange(0x00, 0xFF)
        self.path_id_input.setValue(0x00)
        self.path_id_input.setToolTip(
            "Data_Path_ID sent in the setup command. 0 = HCI; 1..254 are "
            "vendor-defined, so check the controller's documentation for which "
            "id maps to which physical interface.")
        form.addRow("Data Path ID:", self.path_id_input)

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setToolTip("Serial port carrying the offloaded audio")
        port_row = QWidget()
        port_layout = QHBoxLayout(port_row)
        port_layout.setContentsMargins(0, 0, 0, 0)
        port_layout.addWidget(self.port_combo, 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_btn)
        form.addRow("Audio Port:", port_row)

        self.baud_combo = QComboBox()
        for baud in (115200, 230400, 460800, 921600, 1000000, 1500000, 3000000):
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.setCurrentIndex(3)
        self.baud_combo.setToolTip(
            "Wideband audio needs headroom: 16 kB/s of PCM is 160 kbps of raw "
            "payload before framing")
        form.addRow("Audio Baud:", self.baud_combo)

        self.rtscts_input = QCheckBox("Hardware flow control (RTS/CTS)")
        self.rtscts_input.setChecked(True)
        form.addRow("", self.rtscts_input)

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.open_btn = QPushButton("Open Audio Interface")
        self.open_btn.clicked.connect(self.open_link)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close_link)
        self.close_btn.setEnabled(False)
        button_layout.addWidget(self.open_btn)
        button_layout.addWidget(self.close_btn)
        button_layout.addStretch(1)
        form.addRow("", buttons)

        self.status_label = QLabel("closed")
        self.status_label.setStyleSheet("color: gray;")
        form.addRow("Audio link:", self.status_label)

        self.stats_label = QLabel("-")
        self.stats_label.setStyleSheet("color: gray;")
        form.addRow("Audio traffic:", self.stats_label)

        self.refresh_ports()
        self._on_route_changed()

    # --------------------------------------------------------------- helpers

    def route(self) -> AudioRoute:
        return self.route_combo.currentData()

    def data_path_id(self) -> int:
        return self.path_id_input.value()

    def is_offloaded(self) -> bool:
        return self.route() is AudioRoute.SEPARATE_INTERFACE

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                self.port_combo.addItem(port.device)
        except Exception:
            pass
        if current:
            self.port_combo.setEditText(current)

    def _on_route_changed(self) -> None:
        separate = self.is_offloaded()
        for widget in (self.port_combo, self.baud_combo, self.rtscts_input,
                       self.open_btn):
            widget.setEnabled(separate)
        if not separate and self.link.is_open:
            self.close_link()

        # Route and data path have to agree, or the controller sends audio
        # somewhere the tool is not listening. Nudge the id to match.
        if self.route() is AudioRoute.OVER_HCI:
            self.path_id_input.setValue(0x00)
        elif self.path_id_input.value() == 0x00:
            self.path_id_input.setValue(0x01)

    # ---------------------------------------------------------------- actions

    def open_link(self) -> bool:
        port = self.port_combo.currentText().strip()
        if not port:
            self.status_label.setText("no port selected")
            self.status_label.setStyleSheet("color: red;")
            return False
        try:
            self.link.open("UART", {
                "port": port,
                "baudrate": self.baud_combo.currentData(),
                "rtscts": self.rtscts_input.isChecked(),
            })
        except Exception as exc:            # noqa: BLE001 - reported in the panel
            self.status_label.setText(f"open failed: {exc}")
            self.status_label.setStyleSheet("color: red;")
            return False

        self.status_label.setText(
            f"open on {port} @ {self.baud_combo.currentData()}")
        self.status_label.setStyleSheet("color: green;")
        self.open_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        return True

    def close_link(self) -> None:
        self.link.close()
        self.status_label.setText("closed")
        self.status_label.setStyleSheet("color: gray;")
        self.open_btn.setEnabled(self.is_offloaded())
        self.close_btn.setEnabled(False)

    def _refresh_stats(self) -> None:
        stats = self.link.stats
        if not stats.started_at:
            self.stats_label.setText("-")
            return
        elapsed = stats.elapsed()
        self.stats_label.setText(
            f"TX {stats.tx_packets} pkt / {format_bytes(stats.tx_bytes)} "
            f"({format_rate(stats.tx_bytes, elapsed)}),  "
            f"RX {stats.rx_packets} pkt / {format_bytes(stats.rx_bytes)} "
            f"({format_rate(stats.rx_bytes, elapsed)})"
            + (f",  {stats.errors} errors" if stats.errors else ""))

    def cleanup(self) -> None:
        try:
            self._timer.stop()
        except RuntimeError:
            pass
        self.link.close()


__all__ = [
    "AudioRoute",
    "AudioLink",
    "AudioStats",
    "AudioOffloadPanel",
    "format_rate",
    "format_bytes",
]
