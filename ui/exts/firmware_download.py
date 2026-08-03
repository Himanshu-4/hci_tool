"""
Firmware download screen -- patches, full ROM images and NVM settings.

Three tabs, because the three jobs have genuinely different risk profiles:

* **Patch** -- a RAM patch or service pack (.hcd, .bts, HCI script). Volatile:
  a bad one is undone by a power cycle, so this is the safe one to iterate on.
* **Full ROM / Image** -- a raw binary written to a base address in chunks.
  Persistent, and on most parts a failed write in the boot region leaves a
  device that will not enumerate. Guarded behind an explicit confirmation.
* **NVM Settings** -- individual non-volatile items: BD_ADDR, crystal trim,
  power tables. Small writes, equally persistent.

Downloads run on a worker thread and drive commands through the session one at a
time, waiting for each completion before sending the next. That is not caution
for its own sake: vendor loaders keep an internal write pointer, so a command
sent before the previous one completed does not merely get lost, it corrupts the
sequence.

`.bts` service packs can also change the UART baud mid-download. Those steps are
honoured -- the transport is reconfigured and the download continues at the new
rate, which is why the port must be left alone while it runs.
"""

from __future__ import annotations

import os
import threading
import time
from typing import List, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from hci.cmd import hci_create_cmd_packet

from .fw_formats import (
    PROFILES, FwCommand, FwImage, detect_format, nvm_read_command,
    nvm_write_command, parse_bts, parse_hci_script, parse_hcd, parse_raw_image,
)
from .test_window_base import SessionTestWindow


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


def _parse_int(text: str, field: str) -> int:
    text = text.strip()
    if not text:
        raise ValueError(f"{field} is empty")
    try:
        return int(text, 0)
    except ValueError:
        raise ValueError(f"{field} is not a number: {text!r}")


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


class _Downloader(threading.Thread):
    """
    Runs a command sequence against the controller, one command at a time.

    Each command is sent through the session and *waited on*: vendor loaders
    track an internal write pointer, so overlapping commands corrupt the
    sequence rather than merely losing one. That makes the download slower than
    the link could manage, and correct.
    """

    def __init__(self, window: "FirmwareDownloadWindow", commands: List[FwCommand],
                 timeout: float, settle_ms: int, stop_on_error: bool):
        super().__init__(name="hci-fw-download", daemon=True)
        self.window = window
        self.commands = commands
        self.timeout = timeout
        self.settle_ms = settle_ms
        self.stop_on_error = stop_on_error
        self._stop = threading.Event()
        self.sent = 0
        self.failed = 0

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        started = time.monotonic()
        try:
            self._run()
        except Exception as exc:            # noqa: BLE001
            self.window.log(f"! download aborted: {exc!r}")
            self.failed += 1
        finally:
            self.window.download_finished_signal.emit(
                self.sent, self.failed, time.monotonic() - started)

    def _run(self) -> None:
        window = self.window
        total = len(self.commands)

        for index, command in enumerate(self.commands):
            if self._stop.is_set():
                window.log("= download stopped by the user")
                return

            window.progress_signal.emit(index, total)

            if command.kind == "remark":
                window.log(f"  {command.text}")
                continue

            if command.kind == "delay":
                self._stop.wait(command.delay_ms / 1000.0)
                continue

            if command.kind == "baud":
                # The controller has already switched; the host must follow or
                # everything after this is framing errors.
                window.log(f"= switching the port to {command.baudrate} baud")
                if not window.reconfigure_transport(command.baudrate,
                                                    command.flow_control):
                    window.log("! could not change the port baud -- the rest of "
                               "the download would be garbage, stopping")
                    self.failed += 1
                    return
                self._stop.wait(0.05)
                continue

            ok, detail = window.send_and_wait(command, self.timeout)
            if ok:
                self.sent += 1
            else:
                self.failed += 1
                window.log(f"! step {index + 1}/{total} "
                           f"(0x{command.opcode:04X}): {detail}")
                if self.stop_on_error:
                    window.log("= stopping on first error")
                    return

            if self.settle_ms:
                self._stop.wait(self.settle_ms / 1000.0)

        window.progress_signal.emit(total, total)


class FirmwareDownloadWindow(SessionTestWindow):
    """Load and download patches, ROM images and NVM settings."""

    WINDOW_TITLE = "Firmware Download"
    WINDOW_SIZE = (820, 940)

    progress_signal = pyqtSignal(int, int)
    download_finished_signal = pyqtSignal(int, int, float)

    def __init__(self, main_window):
        self._downloader: Optional[_Downloader] = None
        self._image: Optional[FwImage] = None
        self._rom_data: bytes = b''
        self._rom_name: str = ""
        super().__init__(main_window)

        self.progress_signal.connect(self._on_progress)
        self.download_finished_signal.connect(self._on_finished)

    # ----------------------------------------------------------------- layout

    def build_body(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._profile_box())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._patch_tab(), "Patch / Service Pack")
        self.tabs.addTab(self._rom_tab(), "Full ROM / Image")
        self.tabs.addTab(self._nvm_tab(), "NVM Settings")
        layout.addWidget(self.tabs, 1)

        layout.addWidget(self._progress_box())

    def _profile_box(self) -> QWidget:
        box = QGroupBox("Controller profile")
        form = QFormLayout(box)

        self.profile_combo = QComboBox()
        for name in PROFILES:
            self.profile_combo.addItem(name)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        form.addRow("Vendor:", self.profile_combo)

        self.write_opcode_input = QLineEdit("0xFC4C")
        self.write_opcode_input.setToolTip("Vendor write/download opcode")
        form.addRow("Write Opcode:", self.write_opcode_input)

        self.launch_opcode_input = QLineEdit("0xFC4E")
        self.launch_opcode_input.setToolTip(
            "Vendor launch opcode; 0 if the image runs on the last write")
        form.addRow("Launch Opcode:", self.launch_opcode_input)

        self.profile_note = _hint("")
        form.addRow("", self.profile_note)

        self.timeout_input = _spin(1, 60, 5,
                                   "How long to wait for each command's "
                                   "completion", " s")
        form.addRow("Command Timeout:", self.timeout_input)

        self.settle_input = _spin(0, 1000, 0,
                                  "Pause after each command; some loaders need "
                                  "a few ms to flush a write", " ms")
        form.addRow("Inter-command Delay:", self.settle_input)

        self.stop_on_error_input = QCheckBox("Stop at the first failed command")
        self.stop_on_error_input.setChecked(True)
        self.stop_on_error_input.setToolTip(
            "Continuing past a failed write usually produces a corrupt image "
            "rather than a partial one")
        form.addRow("", self.stop_on_error_input)

        self._on_profile_changed(self.profile_combo.currentText())
        return box

    def _patch_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        form = QFormLayout()
        root.addLayout(form)

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.patch_path_input = QLineEdit()
        self.patch_path_input.setPlaceholderText(
            "Patch file: .hcd, .bts service pack, or an HCI text script")
        file_layout.addWidget(self.patch_path_input, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_patch)
        file_layout.addWidget(browse_btn)
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load_patch)
        file_layout.addWidget(load_btn)
        form.addRow("Patch File:", file_row)

        self.patch_format_combo = QComboBox()
        self.patch_format_combo.addItem("Detect automatically", "auto")
        self.patch_format_combo.addItem("Broadcom/Cypress .hcd", "hcd")
        self.patch_format_combo.addItem("TI .bts service pack", "bts")
        self.patch_format_combo.addItem("HCI text script", "script")
        form.addRow("Format:", self.patch_format_combo)

        self.patch_summary = QLabel("no file loaded")
        self.patch_summary.setWordWrap(True)
        form.addRow("Contents:", self.patch_summary)

        self.patch_table = QTableWidget(0, 3)
        self.patch_table.setHorizontalHeaderLabels(["#", "Step", "Detail"])
        self.patch_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch)
        self.patch_table.setMinimumHeight(160)
        root.addWidget(self.patch_table, 1)

        self.patch_reset_input = QCheckBox("Send HCI Reset when the patch finishes")
        self.patch_reset_input.setChecked(True)
        self.patch_reset_input.setToolTip(
            "Most patches need a reset before the new code is in use")
        root.addWidget(self.patch_reset_input)

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.patch_download_btn = QPushButton("Download Patch")
        self.patch_download_btn.clicked.connect(self._download_patch)
        button_layout.addWidget(self.patch_download_btn)
        button_layout.addStretch(1)
        root.addWidget(buttons)

        root.addWidget(_hint(
            "A RAM patch is volatile: a power cycle undoes it, which makes this "
            "the safe place to iterate. A .bts service pack carries its own "
            "delays and baud changes and those are honoured -- do not touch the "
            "port while it runs."))
        return page

    def _rom_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        form = QFormLayout()
        root.addLayout(form)

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.rom_path_input = QLineEdit()
        self.rom_path_input.setPlaceholderText("Raw firmware image (.bin, .rom)")
        file_layout.addWidget(self.rom_path_input, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_rom)
        file_layout.addWidget(browse_btn)
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load_rom)
        file_layout.addWidget(load_btn)
        form.addRow("Image File:", file_row)

        self.rom_base_input = QLineEdit("0x00200000")
        self.rom_base_input.setToolTip("Address the first chunk is written to")
        form.addRow("Base Address:", self.rom_base_input)

        self.rom_address_bytes_combo = QComboBox()
        for label, value in (("4 bytes", 4), ("2 bytes", 2), ("3 bytes", 3)):
            self.rom_address_bytes_combo.addItem(label, value)
        form.addRow("Address Width:", self.rom_address_bytes_combo)

        self.rom_chunk_input = _spin(1, 251, 240,
                                     "Payload bytes per write command; the "
                                     "address field shares the 255-byte limit",
                                     " bytes")
        self.rom_chunk_input.valueChanged.connect(self._update_rom_summary)
        form.addRow("Chunk Size:", self.rom_chunk_input)

        self.rom_prepare_input = QCheckBox("Send the loader prepare command first")
        self.rom_prepare_input.setChecked(True)
        form.addRow("", self.rom_prepare_input)

        self.rom_launch_input = QCheckBox("Launch the image when writing finishes")
        self.rom_launch_input.setChecked(True)
        form.addRow("", self.rom_launch_input)

        self.rom_summary = QLabel("no image loaded")
        self.rom_summary.setWordWrap(True)
        form.addRow("Image:", self.rom_summary)

        self.rom_download_btn = QPushButton("Write Image")
        self.rom_download_btn.clicked.connect(self._download_rom)
        form.addRow("", self.rom_download_btn)

        root.addWidget(_hint(
            "This writes a persistent image. On most parts a failed write in "
            "the boot region leaves a controller that will not enumerate and "
            "cannot be recovered over HCI -- so the write asks for confirmation, "
            "and the base address is worth checking twice against the vendor's "
            "memory map."))
        root.addStretch(1)
        return page

    def _nvm_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        form = QFormLayout()
        root.addLayout(form)

        self.nvm_read_opcode_input = QLineEdit("0xFE81")
        form.addRow("NV Read Opcode:", self.nvm_read_opcode_input)

        self.nvm_write_opcode_input = QLineEdit("0xFE82")
        form.addRow("NV Write Opcode:", self.nvm_write_opcode_input)

        self.nvm_id_bytes_combo = QComboBox()
        self.nvm_id_bytes_combo.addItem("2-byte item id", 2)
        self.nvm_id_bytes_combo.addItem("1-byte item id", 1)
        form.addRow("Item ID Width:", self.nvm_id_bytes_combo)

        self.nvm_length_input = QCheckBox("Command carries an explicit length byte")
        self.nvm_length_input.setChecked(True)
        form.addRow("", self.nvm_length_input)

        self.nvm_item_input = QLineEdit("0x0021")
        self.nvm_item_input.setToolTip("NV item identifier")
        form.addRow("Item ID:", self.nvm_item_input)

        self.nvm_value_input = QLineEdit()
        self.nvm_value_input.setPlaceholderText("Value, hex")
        form.addRow("Value:", self.nvm_value_input)

        self.nvm_read_length_input = _spin(0, 255, 8, "Bytes to read back",
                                           " bytes")
        form.addRow("Read Length:", self.nvm_read_length_input)

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        read_btn = QPushButton("Read Item")
        read_btn.clicked.connect(self._nvm_read)
        write_btn = QPushButton("Write Item")
        write_btn.clicked.connect(self._nvm_write)
        queue_btn = QPushButton("Add to Batch")
        queue_btn.clicked.connect(self._nvm_queue)
        button_layout.addWidget(read_btn)
        button_layout.addWidget(write_btn)
        button_layout.addWidget(queue_btn)
        button_layout.addStretch(1)
        form.addRow("", buttons)

        batch = QGroupBox("Batch")
        batch_layout = QVBoxLayout(batch)
        self.nvm_table = QTableWidget(0, 3)
        self.nvm_table.setHorizontalHeaderLabels(["Item ID", "Length", "Value"])
        self.nvm_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch)
        self.nvm_table.setMinimumHeight(130)
        batch_layout.addWidget(self.nvm_table)

        batch_buttons = QWidget()
        batch_button_layout = QHBoxLayout(batch_buttons)
        batch_button_layout.setContentsMargins(0, 0, 0, 0)
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._nvm_remove)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.nvm_table.setRowCount(0))
        write_all_btn = QPushButton("Write All")
        write_all_btn.clicked.connect(self._nvm_write_batch)
        batch_button_layout.addWidget(remove_btn)
        batch_button_layout.addWidget(clear_btn)
        batch_button_layout.addWidget(write_all_btn)
        batch_button_layout.addStretch(1)
        batch_layout.addWidget(batch_buttons)
        root.addWidget(batch)

        root.addWidget(_hint(
            "NV item layouts are vendor-specific -- the id width and whether a "
            "length byte is present differ between families, which is why they "
            "are settings here. These writes are persistent: a wrong crystal "
            "trim or power table survives a power cycle."))
        root.addStretch(1)
        return page

    def _progress_box(self) -> QWidget:
        box = QGroupBox("Progress")
        layout = QVBoxLayout(box)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        row_layout.addWidget(self.progress_bar, 1)
        self.abort_btn = QPushButton("Abort")
        self.abort_btn.setEnabled(False)
        self.abort_btn.clicked.connect(self._abort)
        row_layout.addWidget(self.abort_btn)
        layout.addWidget(row)

        self.progress_label = QLabel("idle")
        self.progress_label.setStyleSheet("color: gray;")
        layout.addWidget(self.progress_label)
        return box

    # ---------------------------------------------------------------- helpers

    def _profile(self):
        return PROFILES[self.profile_combo.currentText()]

    def _on_profile_changed(self, name: str) -> None:
        profile = PROFILES[name]
        self.write_opcode_input.setText(f"0x{profile.write_opcode:04X}")
        self.launch_opcode_input.setText(f"0x{profile.launch_opcode:04X}")
        self.profile_note.setText(profile.notes)
        # TI service packs carry their own commands, so the opcode fields have
        # nothing to act on.
        editable = profile.write_opcode != 0
        self.write_opcode_input.setEnabled(editable)
        self.launch_opcode_input.setEnabled(editable)

    def _busy(self) -> bool:
        if self._downloader is not None:
            self.log("! a download is already running")
            return True
        if self.session is None:
            self.log("! no session attached -- open Tools > HCI first")
            return True
        return False

    # ------------------------------------------------- worker-thread services

    def send_and_wait(self, command: FwCommand, timeout: float):
        """
        Send one command and block until it completes. Called on the worker.

        Returns (ok, detail). Goes through the session's own token so the
        controller's command credits are respected -- a loader is exactly the
        situation where overrunning them corrupts things silently.
        """
        session = self.session
        if session is None:
            return False, "session went away"
        try:
            packet = hci_create_cmd_packet(command.opcode,
                                           params=command.payload)
            token = session.send(packet, timeout=timeout)
            response = token.wait(timeout + 1.0)
        except Exception as exc:            # noqa: BLE001
            return False, str(exc)

        status = None
        if response is not None:
            status = (getattr(response, 'params', {}) or {}).get('status')
        if status not in (None, 0x00):
            return False, f"status 0x{status:02X}"
        return True, "ok"

    def reconfigure_transport(self, baudrate: int, flow_control: bool) -> bool:
        """Follow a mid-download baud change. Called on the worker."""
        session = self.session
        if session is None:
            return False
        try:
            transport = session.transport
            config = dict(transport.get_config() or {})
            config["baudrate"] = baudrate
            if flow_control:
                config["rtscts"] = True
            transport.disconnect()
            transport.configure(config)
            return bool(transport.connect())
        except Exception as exc:            # noqa: BLE001
            self.log(f"! reconfigure failed: {exc}")
            return False

    # ---------------------------------------------------------- patch loading

    def _browse_patch(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a patch file", "",
            "Firmware (*.hcd *.bts *.txt *.script *.hci);;All files (*)")
        if path:
            self.patch_path_input.setText(path)
            self._load_patch()

    def _load_patch(self) -> None:
        path = self.patch_path_input.text().strip()
        if not path:
            self.log("! choose a patch file first")
            return
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError as exc:
            self.log(f"! could not read {path}: {exc}")
            return

        name = os.path.basename(path)
        fmt = self.patch_format_combo.currentData()
        if fmt == "auto":
            fmt = detect_format(name, data)
            self.log(f"= detected format: {fmt}")

        try:
            if fmt == "hcd":
                image = parse_hcd(data, name)
            elif fmt == "bts":
                image = parse_bts(data, name)
            elif fmt == "script":
                image = parse_hci_script(data.decode("utf-8", "replace"), name)
            else:
                raise ValueError(
                    f"{name} looks like a raw image, not a patch -- use the "
                    "Full ROM / Image tab for that")
        except ValueError as exc:
            self._image = None
            self.patch_summary.setText(f"could not parse: {exc}")
            self.patch_table.setRowCount(0)
            self.log(f"! {name}: {exc}")
            return

        self._image = image
        self.patch_summary.setText(f"{name}: {image.summary()}")
        for note in image.notes:
            self.log(f"= note: {note}")
        self._fill_patch_table(image)
        self.log(f"= loaded {name}: {image.summary()}")

    def _fill_patch_table(self, image: FwImage) -> None:
        # A large patch is thousands of writes; building a row for every one
        # costs seconds for no benefit.
        limit = 500
        rows = image.commands[:limit]
        self.patch_table.setRowCount(len(rows))
        for index, command in enumerate(rows):
            self.patch_table.setItem(index, 0, QTableWidgetItem(str(index + 1)))
            self.patch_table.setItem(index, 1, QTableWidgetItem(command.kind))
            self.patch_table.setItem(index, 2,
                                     QTableWidgetItem(command.describe()))
        if len(image.commands) > limit:
            self.log(f"= showing the first {limit} of {len(image.commands)} steps")

    def _download_patch(self) -> None:
        if self._busy():
            return
        if self._image is None:
            self.log("! load a patch file first")
            return

        commands = list(self._image.commands)
        if self.patch_reset_input.isChecked():
            commands.append(FwCommand(opcode=0x0C03, text="HCI Reset"))
        self._start(commands, f"patch {self._image.name}")

    # ------------------------------------------------------------ ROM loading

    def _browse_rom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a firmware image", "",
            "Images (*.bin *.rom *.img *.nvm);;All files (*)")
        if path:
            self.rom_path_input.setText(path)
            self._load_rom()

    def _load_rom(self) -> None:
        path = self.rom_path_input.text().strip()
        if not path:
            self.log("! choose an image file first")
            return
        try:
            with open(path, "rb") as handle:
                self._rom_data = handle.read()
        except OSError as exc:
            self.log(f"! could not read {path}: {exc}")
            return

        self._rom_name = os.path.basename(path)
        self._update_rom_summary()
        self.log(f"= loaded {self._rom_name}: {len(self._rom_data)} bytes")

    def _update_rom_summary(self) -> None:
        if not self._rom_data:
            return
        chunk = max(self.rom_chunk_input.value(), 1)
        chunks = (len(self._rom_data) + chunk - 1) // chunk
        self.rom_summary.setText(
            f"{self._rom_name}: {len(self._rom_data)} bytes, {chunks} write "
            f"commands at {chunk} bytes each")

    def _download_rom(self) -> None:
        if self._busy():
            return
        if not self._rom_data:
            self.log("! load an image file first")
            return

        try:
            base = _parse_int(self.rom_base_input.text(), "base address")
            write_opcode = _parse_int(self.write_opcode_input.text(),
                                      "write opcode")
            launch_opcode = _parse_int(self.launch_opcode_input.text(),
                                       "launch opcode")
            image = parse_raw_image(
                self._rom_data, self._rom_name, base, write_opcode,
                self.rom_chunk_input.value(),
                self.rom_address_bytes_combo.currentData())
        except ValueError as exc:
            self.log(f"! {exc}")
            return

        answer = QMessageBox.warning(
            self, "Write firmware image?",
            f"About to write {len(self._rom_data)} bytes to "
            f"0x{base:08X} as {image.command_count} commands.\n\n"
            "This is a persistent write. If it fails partway through, the "
            "controller may not start again -- and on most parts that cannot "
            "be recovered over HCI.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer != QMessageBox.Yes:
            self.log("= image write cancelled")
            return

        commands: List[FwCommand] = []
        if self.rom_prepare_input.isChecked():
            prepare = self._profile().prepare_command()
            if prepare is not None:
                commands.append(prepare)
        commands.extend(image.commands)
        if self.rom_launch_input.isChecked() and launch_opcode:
            commands.append(FwCommand(
                opcode=launch_opcode,
                payload=base.to_bytes(
                    self.rom_address_bytes_combo.currentData(), "little"),
                text=f"launch @ 0x{base:08X}"))

        self._start(commands, f"image {self._rom_name}")

    # ------------------------------------------------------------------- NVM

    def _nvm_settings(self):
        return (_parse_int(self.nvm_read_opcode_input.text(), "NV read opcode"),
                _parse_int(self.nvm_write_opcode_input.text(), "NV write opcode"),
                self.nvm_id_bytes_combo.currentData(),
                self.nvm_length_input.isChecked())

    def _nvm_read(self) -> None:
        if self.session is None:
            self.log("! no session attached")
            return
        try:
            read_opcode, _, id_bytes, with_length = self._nvm_settings()
            item = _parse_int(self.nvm_item_input.text(), "item id")
            command = nvm_read_command(read_opcode, item,
                                       self.nvm_read_length_input.value(),
                                       id_bytes, with_length)
        except ValueError as exc:
            self.log(f"! {exc}")
            return

        def _done(response, error) -> None:
            if error is not None:
                return
            extra = (getattr(response, 'params', {}) or {}).get('return_params') or b''
            self._line.emit(f"< NV item 0x{item:04X}: {bytes(extra).hex(' ')}"
                            if extra else
                            f"< NV item 0x{item:04X}: empty response")

        self.send(lambda: hci_create_cmd_packet(command.opcode,
                                                params=command.payload),
                  f"NV read item 0x{item:04X}", _done)

    def _build_nvm_write(self, item: int, value: bytes) -> FwCommand:
        if not value:
            raise ValueError("the NV value is empty -- nothing to write")
        _, write_opcode, id_bytes, with_length = self._nvm_settings()
        return nvm_write_command(write_opcode, item, value, id_bytes,
                                 with_length)

    def _nvm_write(self) -> None:
        if self.session is None:
            self.log("! no session attached")
            return
        try:
            command = self._build_nvm_write(
                _parse_int(self.nvm_item_input.text(), "item id"),
                _hex_bytes(self.nvm_value_input.text(), "value"))
        except ValueError as exc:
            self.log(f"! {exc}")
            return
        self.send(lambda: hci_create_cmd_packet(command.opcode,
                                                params=command.payload),
                  command.text)

    def _nvm_queue(self) -> None:
        try:
            item = _parse_int(self.nvm_item_input.text(), "item id")
            value = _hex_bytes(self.nvm_value_input.text(), "value")
            if not value:
                raise ValueError("the NV value is empty")
        except ValueError as exc:
            self.log(f"! {exc}")
            return

        row = self.nvm_table.rowCount()
        self.nvm_table.insertRow(row)
        self.nvm_table.setItem(row, 0, QTableWidgetItem(f"0x{item:04X}"))
        self.nvm_table.setItem(row, 1, QTableWidgetItem(str(len(value))))
        self.nvm_table.setItem(row, 2, QTableWidgetItem(value.hex(' ')))
        self.log(f"= queued NV item 0x{item:04X} ({len(value)} bytes)")

    def _nvm_remove(self) -> None:
        row = self.nvm_table.currentRow()
        if row >= 0:
            self.nvm_table.removeRow(row)

    def _nvm_write_batch(self) -> None:
        if self._busy():
            return
        if self.nvm_table.rowCount() == 0:
            self.log("! the batch is empty")
            return

        commands = []
        try:
            for row in range(self.nvm_table.rowCount()):
                item = _parse_int(self.nvm_table.item(row, 0).text(),
                                  f"row {row + 1} item id")
                value = _hex_bytes(self.nvm_table.item(row, 2).text(),
                                   f"row {row + 1} value")
                commands.append(self._build_nvm_write(item, value))
        except ValueError as exc:
            self.log(f"! {exc}")
            return

        answer = QMessageBox.warning(
            self, "Write NVM settings?",
            f"About to write {len(commands)} NV item(s).\n\n"
            "NVM writes are persistent and survive a power cycle. A wrong "
            "crystal trim or power table can leave the controller misbehaving "
            "in ways that are hard to trace back here.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer != QMessageBox.Yes:
            self.log("= NVM batch cancelled")
            return

        self._start(commands, f"{len(commands)} NV item(s)")

    # ------------------------------------------------------------- the engine

    def _start(self, commands: List[FwCommand], what: str) -> None:
        if not commands:
            self.log("! nothing to download")
            return

        self.progress_bar.setValue(0)
        self.progress_label.setText(f"downloading {what}...")
        self.abort_btn.setEnabled(True)
        for button in (self.patch_download_btn, self.rom_download_btn):
            button.setEnabled(False)

        self.log(f"> downloading {what}: {len(commands)} steps")
        self._downloader = _Downloader(
            self, commands, float(self.timeout_input.value()),
            self.settle_input.value(),
            self.stop_on_error_input.isChecked())
        self._downloader.start()

    def _abort(self) -> None:
        if self._downloader is not None:
            self._downloader.stop()
            self.log("= abort requested")

    def _on_progress(self, done: int, total: int) -> None:
        self.progress_bar.setValue(int(done / total * 100) if total else 0)
        self.progress_label.setText(f"step {done} of {total}")

    def _on_finished(self, sent: int, failed: int, elapsed: float) -> None:
        self._downloader = None
        self.abort_btn.setEnabled(False)
        for button in (self.patch_download_btn, self.rom_download_btn):
            button.setEnabled(True)
        rate = sent / elapsed if elapsed else 0
        self.progress_label.setText(
            f"finished: {sent} sent, {failed} failed in {elapsed:.1f}s")
        self.log(f"= download finished: {sent} commands sent, {failed} failed, "
                 f"{elapsed:.1f}s ({rate:.0f} commands/s)")

    # ---------------------------------------------------------------- teardown

    def on_cleanup(self) -> None:
        if self._downloader is not None:
            self._downloader.stop()
            self._downloader = None


__all__ = ["FirmwareDownloadWindow"]
