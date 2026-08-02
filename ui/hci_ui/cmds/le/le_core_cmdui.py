"""
Command dialogs for the core LE controller commands.

    0x2001  LE Set Event Mask
    0x2005  LE Set Random Address
    0x2009  LE Set Scan Response Data
    0x200A  LE Set Advertise Enable
    0x200D  LE Create Connection
    0x2011  LE Add Device To Filter Accept List
    0x2012  LE Remove Device From Filter Accept List
    0x2013  LE Connection Update
    0x2014  LE Set Host Channel Classification
    0x2015  LE Read Channel Map
    0x2016  LE Read Remote Features

The two bitmap dialogs (event mask, channel classification) each offer both a
tick-list and the raw hex, kept in sync: the list is how you find the bit you
want, the hex is how you paste one from a log or a bug report.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QWidget,
)

import hci.cmd.le_cmds as le_cmds
from hci.cmd.cmd_opcodes import LEControllerOCF, OGF, create_opcode
from hci.evt.evt_codes import LeMetaEventSubCode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI
from .le_cmdui import _parse_bd_addr


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


def _spin(minimum: int, maximum: int, value: int, tip: str = "") -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setValue(value)
    if tip:
        box.setToolTip(tip)
    return box


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: gray; font-size: 10pt;")
    label.setWordWrap(True)
    return label


def _address_type_combo() -> QComboBox:
    combo = QComboBox()
    for addr_type in le_cmds.AddressType:
        combo.addItem(addr_type.name, addr_type.value)
    return combo


def _title_case(name: str) -> str:
    """`PERIODIC_ADVERTISING_SYNC_LOST` -> `Periodic Advertising Sync Lost`."""
    text = name.replace("_", " ").title()
    # str.title() mangles the acronyms these names are full of.
    for wrong, right in (("Cs ", "CS "), ("Le ", "LE "), ("Iq ", "IQ "),
                         ("Dhkey", "DHKey"), ("Cte", "CTE"), ("Cis", "CIS"),
                         ("Big", "BIG"), ("Phy", "PHY"), ("Sca", "SCA"),
                         ("Fae", "FAE"), ("P256", "P-256")):
        text = text.replace(wrong, right)
    return text


class LeSetEventMaskUI(HCICmdUI):
    """
    UI for LE Set Event Mask (0x2001).

    The tick list is generated from `LeMetaEventSubCode`: mask bit N enables
    sub-event N+1, all the way through the Channel Sounding events. Deriving it
    means a new sub-event shows up here automatically instead of silently
    missing a checkbox.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EVENT_MASK)
    NAME = "LE Set Event Mask"

    #: Everything the tool can decode today: connection complete through the
    #: extended advertising report.
    RECOMMENDED_MASK = 0x0000000000001FFF

    def setup_ui(self):
        super().setup_ui()

        self.mask_input = QLineEdit()
        self.mask_input.setPlaceholderText("8-byte hex, e.g. 0000000000001FFF")
        self.mask_input.setToolTip("Little-endian on the wire; written here "
                                   "most-significant byte first")
        self.mask_input.editingFinished.connect(self._hex_to_checks)
        self.form_layout.addRow("Event Mask:", self.mask_input)

        presets = QWidget()
        preset_layout = QHBoxLayout(presets)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        for label, value in (("None", 0),
                             ("Recommended", self.RECOMMENDED_MASK),
                             ("All", (1 << 50) - 1)):
            button = QPushButton(label)
            button.clicked.connect(lambda _, v=value: self._set_mask(v))
            preset_layout.addWidget(button)
        preset_layout.addStretch(1)
        self.form_layout.addRow("Presets:", presets)

        # One checkbox per known sub-event. Single column: the names are long
        # enough that a second column only ever lands off the right edge.
        self.checks = {}
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        for index, sub in enumerate(LeMetaEventSubCode):
            bit = int(sub) - 1
            box = QCheckBox(f"{bit}: {_title_case(sub.name)}")
            box.setToolTip(f"LE meta sub-event 0x{int(sub):02X}")
            box.stateChanged.connect(self._checks_to_hex)
            grid.addWidget(box, index, 0)
            self.checks[bit] = box

        area = QScrollArea()
        area.setWidget(holder)
        area.setWidgetResizable(True)
        area.setMinimumHeight(240)
        self.form_layout.addRow("Events:", area)
        self.setMinimumWidth(520)

        self.form_layout.addRow("", _hint(
            "Controllers mask most LE meta events by default -- without this "
            "command advertising reports and the extended/periodic events never "
            "arrive."))

        self._set_mask(self.RECOMMENDED_MASK)

    def _set_mask(self, value: int) -> None:
        self.mask_input.setText(f"{value:016X}")
        self._hex_to_checks()

    def _hex_to_checks(self) -> None:
        try:
            value = int(self.mask_input.text().strip().replace("0x", "") or "0", 16)
        except ValueError:
            return
        for bit, box in self.checks.items():
            box.blockSignals(True)
            box.setChecked(bool(value >> bit & 1))
            box.blockSignals(False)

    def _checks_to_hex(self) -> None:
        # Bits with no checkbox (reserved, or newer than this build) are kept so
        # ticking a box never silently clears something that was pasted in.
        try:
            value = int(self.mask_input.text().strip().replace("0x", "") or "0", 16)
        except ValueError:
            value = 0
        for bit, box in self.checks.items():
            if box.isChecked():
                value |= 1 << bit
            else:
                value &= ~(1 << bit)
        self.mask_input.setText(f"{value:016X}")

    def validate_parameters(self) -> bool:
        text = self.mask_input.text().strip().replace("0x", "").replace(" ", "")
        try:
            mask = int(text or "0", 16)
        except ValueError:
            raise ValueError(f"event mask is not valid hex: {text!r}")
        self._cmd_instance = le_cmds.LeSetEventMask(event_mask=mask)


class LeSetRandomAddressUI(HCICmdUI):
    """UI for LE Set Random Address (0x2005)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_RANDOM_ADDRESS)
    NAME = "LE Set Random Address"

    def setup_ui(self):
        super().setup_ui()

        self.address_input = QLineEdit("C0:00:00:00:00:01")
        self.address_input.setToolTip(
            "Static random address: top two bits 11. Non-resolvable private: "
            "top two bits 00. Resolvable private: 01.")
        self.form_layout.addRow("Random Address:", self.address_input)

        self.form_layout.addRow("", _hint(
            "Must be set before advertising, scanning or initiating with an own "
            "address type of RANDOM, and cannot be changed while any of those "
            "is active."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetRandomAddress(
            random_address=_parse_bd_addr(self.address_input.text()))


class LeSetScanResponseDataUI(HCICmdUI):
    """UI for LE Set Scan Response Data (0x2009)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_SCAN_RESPONSE_DATA)
    NAME = "LE Set Scan Response Data"

    def setup_ui(self):
        super().setup_ui()

        self.length_label = QLabel("0 / 31 bytes")
        self.form_layout.addRow("Data Length:", self.length_label)

        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("Hex AD structures, e.g. 09084D79446576")
        self.data_input.textChanged.connect(self._update_length)
        self.form_layout.addRow("Scan Response Data:", self.data_input)

        examples = QWidget()
        example_layout = QHBoxLayout(examples)
        example_layout.setContentsMargins(0, 0, 0, 0)
        for label, value in (("Name 'HCI Tool'", "0A08" + b"HCI Tool".hex().upper()),
                             ("TX power 0 dBm", "020A00"),
                             ("Clear", "")):
            button = QPushButton(label)
            button.clicked.connect(lambda _, v=value: self.data_input.setText(v))
            example_layout.addWidget(button)
        example_layout.addStretch(1)
        self.form_layout.addRow("Examples:", examples)

        self.form_layout.addRow("", _hint(
            "Only sent in reply to a SCAN_REQ, so it needs a scannable "
            "advertising type and an active scanner on the other side."))

    def _update_length(self) -> None:
        try:
            length = len(_hex_bytes(self.data_input.text(), "scan response data"))
        except ValueError:
            self.length_label.setText("invalid hex")
            return
        self.length_label.setText(f"{length} / 31 bytes")

    def validate_parameters(self) -> bool:
        data = _hex_bytes(self.data_input.text(), "scan response data")
        if len(data) > 31:
            raise ValueError(
                f"scan response data is {len(data)} bytes; the legacy limit is 31 "
                "(use LE Set Extended Scan Response Data for more)")
        self._cmd_instance = le_cmds.LeSetScanResponseData(data=data)


class LeSetAdvertiseEnableUI(HCICmdUI):
    """UI for LE Set Advertise Enable (0x200A)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_ADVERTISE_ENABLE)
    NAME = "LE Set Advertise Enable"

    def setup_ui(self):
        super().setup_ui()

        self.enable_input = QCheckBox("Start advertising")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Advertising Enable:", self.enable_input)

        self.form_layout.addRow("", _hint(
            "Set the parameters and the advertising data first -- neither can "
            "be changed while advertising is enabled. A connectable advertiser "
            "stops on its own the moment a connection is established."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetAdvertiseEnable(
            enable=self.enable_input.isChecked())


class LeCreateConnectionUI(HCICmdUI):
    """UI for LE Create Connection (0x200D)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_CONNECTION)
    NAME = "LE Create Connection"

    def setup_ui(self):
        super().setup_ui()

        self.scan_interval_input = _spin(0x0004, 0x4000, 0x0060,
                                         "Scan interval while initiating "
                                         "(N * 0.625 ms)")
        self.scan_window_input = _spin(0x0004, 0x4000, 0x0030,
                                       "Scan window while initiating "
                                       "(N * 0.625 ms)")
        self.form_layout.addRow("Scan Interval:", self.scan_interval_input)
        self.form_layout.addRow("Scan Window:", self.scan_window_input)

        self.filter_policy_input = QComboBox()
        self.filter_policy_input.addItem("Use the peer address below", 0x00)
        self.filter_policy_input.addItem("Use the Filter Accept List", 0x01)
        self.form_layout.addRow("Initiator Filter Policy:", self.filter_policy_input)

        self.peer_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Peer Address Type:", self.peer_addr_type_input)

        self.peer_addr_input = QLineEdit("00:00:00:00:00:00")
        self.peer_addr_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.form_layout.addRow("Peer Address:", self.peer_addr_input)

        self.own_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Own Address Type:", self.own_addr_type_input)

        self.conn_min_input = _spin(0x0006, 0x0C80, 0x0018,
                                    "Connection interval min (N * 1.25 ms)")
        self.conn_max_input = _spin(0x0006, 0x0C80, 0x0028,
                                    "Connection interval max (N * 1.25 ms)")
        self.form_layout.addRow("Conn Interval Min:", self.conn_min_input)
        self.form_layout.addRow("Conn Interval Max:", self.conn_max_input)

        self.latency_input = _spin(0x0000, 0x01F3, 0x0000,
                                   "Connection events the peripheral may skip")
        self.form_layout.addRow("Connection Latency:", self.latency_input)

        self.timeout_input = _spin(0x000A, 0x0C80, 0x01F4,
                                   "Supervision timeout (N * 10 ms)")
        self.form_layout.addRow("Supervision Timeout:", self.timeout_input)

        self.min_ce_input = _spin(0x0000, 0xFFFF, 0x0000,
                                  "Minimum connection event length "
                                  "(N * 0.625 ms); 0 = controller decides")
        self.max_ce_input = _spin(0x0000, 0xFFFF, 0x0000,
                                  "Maximum connection event length "
                                  "(N * 0.625 ms); 0 = controller decides")
        self.form_layout.addRow("Min CE Length:", self.min_ce_input)
        self.form_layout.addRow("Max CE Length:", self.max_ce_input)

        self.form_layout.addRow("", _hint(
            "Scanning must be off first -- the controller answers Command "
            "Disallowed otherwise. The result arrives as LE Connection Complete, "
            "not in the Command Status."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCreateConnection(
            peer_address=_parse_bd_addr(self.peer_addr_input.text()),
            peer_address_type=self.peer_addr_type_input.currentData(),
            own_address_type=self.own_addr_type_input.currentData(),
            scan_interval=self.scan_interval_input.value(),
            scan_window=self.scan_window_input.value(),
            initiator_filter_policy=self.filter_policy_input.currentData(),
            conn_interval_min=self.conn_min_input.value(),
            conn_interval_max=self.conn_max_input.value(),
            conn_latency=self.latency_input.value(),
            supervision_timeout=self.timeout_input.value(),
            min_ce_length=self.min_ce_input.value(),
            max_ce_length=self.max_ce_input.value(),
        )


class LeConnectionUpdateUI(HCICmdUI):
    """UI for LE Connection Update (0x2013)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CONNECTION_UPDATE)
    NAME = "LE Connection Update"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.conn_min_input = _spin(0x0006, 0x0C80, 0x0018,
                                    "Connection interval min (N * 1.25 ms)")
        self.conn_max_input = _spin(0x0006, 0x0C80, 0x0028,
                                    "Connection interval max (N * 1.25 ms)")
        self.form_layout.addRow("Conn Interval Min:", self.conn_min_input)
        self.form_layout.addRow("Conn Interval Max:", self.conn_max_input)

        self.latency_input = _spin(0x0000, 0x01F3, 0x0000)
        self.form_layout.addRow("Connection Latency:", self.latency_input)

        self.timeout_input = _spin(0x000A, 0x0C80, 0x01F4,
                                   "Supervision timeout (N * 10 ms)")
        self.form_layout.addRow("Supervision Timeout:", self.timeout_input)

        self.min_ce_input = _spin(0x0000, 0xFFFF, 0x0000)
        self.max_ce_input = _spin(0x0000, 0xFFFF, 0x0000)
        self.form_layout.addRow("Min CE Length:", self.min_ce_input)
        self.form_layout.addRow("Max CE Length:", self.max_ce_input)

        self.form_layout.addRow("", _hint(
            "Only the central may send this; a peripheral has to ask via an L2CAP "
            "connection parameter update request instead."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeConnectionUpdate(
            connection_handle=self.handle_input.value(),
            conn_interval_min=self.conn_min_input.value(),
            conn_interval_max=self.conn_max_input.value(),
            conn_latency=self.latency_input.value(),
            supervision_timeout=self.timeout_input.value(),
            min_ce_length=self.min_ce_input.value(),
            max_ce_length=self.max_ce_input.value(),
        )


class LeReadRemoteFeaturesUI(HCICmdUI):
    """UI for LE Read Remote Features (0x2016)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_REMOTE_USED_FEATURES)
    NAME = "LE Read Remote Features"

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)
        self.form_layout.addRow("", _hint(
            "Answers with Command Status; the features arrive later in "
            "LE Read Remote Features Complete."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeReadRemoteFeatures(self.handle_input.value())


class _FilterAcceptListEntryUI(HCICmdUI):
    """Shared dialog for adding to / removing from the Filter Accept List."""

    COMMAND = None

    def setup_ui(self):
        super().setup_ui()

        self.addr_type_input = QComboBox()
        self.addr_type_input.addItem("Public", 0x00)
        self.addr_type_input.addItem("Random", 0x01)
        self.addr_type_input.addItem("Anonymous advertisers (0xFF)", 0xFF)
        self.addr_type_input.currentIndexChanged.connect(self._sync_address_enable)
        self.form_layout.addRow("Address Type:", self.addr_type_input)

        self.address_input = QLineEdit("00:00:00:00:00:00")
        self.form_layout.addRow("Address:", self.address_input)

        self.form_layout.addRow("", _hint(
            "Rejected with Command Disallowed while advertising, scanning or "
            "initiating with a policy that uses the list -- stop those first."))

    def _sync_address_enable(self) -> None:
        # 0xFF matches anonymous advertisers, which have no address at all.
        anonymous = self.addr_type_input.currentData() == 0xFF
        self.address_input.setEnabled(not anonymous)

    def validate_parameters(self) -> bool:
        addr_type = self.addr_type_input.currentData()
        address = (b"\x00" * 6 if addr_type == 0xFF
                   else _parse_bd_addr(self.address_input.text()))
        self._cmd_instance = self.COMMAND(address=address, address_type=addr_type)


class LeAddDeviceToFilterAcceptListUI(_FilterAcceptListEntryUI):
    """UI for LE Add Device To Filter Accept List (0x2011)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ADD_DEVICE_TO_WHITE_LIST)
    NAME = "LE Add Device To Filter Accept List"
    COMMAND = le_cmds.LeAddDeviceToFilterAcceptList


class LeRemoveDeviceFromFilterAcceptListUI(_FilterAcceptListEntryUI):
    """UI for LE Remove Device From Filter Accept List (0x2012)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_DEVICE_FROM_WHITE_LIST)
    NAME = "LE Remove Device From Filter Accept List"
    COMMAND = le_cmds.LeRemoveDeviceFromFilterAcceptList


class LeSetHostChannelClassificationUI(HCICmdUI):
    """
    UI for LE Set Host Channel Classification (0x2014).

    37 channels, so the tick list is a grid with the hex kept in sync -- same
    arrangement as the event mask, for the same reason.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_HOST_CHANNEL_CLASSIFICATION)
    NAME = "LE Set Host Channel Classification"

    #: The three channels adjacent to the 2.4 GHz Wi-Fi channel 1/6/11 centres
    #: are the usual first thing to drop when a link is fighting Wi-Fi.
    WIFI_AVOID = tuple(ch for ch in range(37)
                       if ch not in (0, 1, 2, 11, 12, 13, 23, 24, 25))

    def setup_ui(self):
        super().setup_ui()

        self.map_input = QLineEdit()
        self.map_input.setPlaceholderText("5-byte hex, e.g. FFFFFFFF1F")
        self.map_input.setToolTip("Little-endian: byte 0 bit 0 is channel 0")
        self.map_input.editingFinished.connect(self._hex_to_checks)
        self.form_layout.addRow("Channel Map:", self.map_input)

        self.count_label = QLabel("37 / 37 channels enabled")
        self.form_layout.addRow("Enabled:", self.count_label)

        presets = QWidget()
        preset_layout = QHBoxLayout(presets)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        for label, channels in (
                ("All 37", tuple(range(37))),
                ("Avoid Wi-Fi", self.WIFI_AVOID),
                ("Lower half", tuple(range(0, 19))),
                ("Upper half", tuple(range(19, 37)))):
            button = QPushButton(label)
            button.clicked.connect(lambda _, c=channels: self._set_channels(c))
            preset_layout.addWidget(button)
        preset_layout.addStretch(1)
        self.form_layout.addRow("Presets:", presets)

        self.checks = {}
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        columns = 6
        for channel in range(le_cmds.LeSetHostChannelClassification.NUM_CHANNELS):
            box = QCheckBox(f"{channel}")
            box.stateChanged.connect(self._checks_to_hex)
            grid.addWidget(box, channel // columns, channel % columns)
            self.checks[channel] = box

        area = QScrollArea()
        area.setWidget(holder)
        area.setWidgetResizable(True)
        area.setMinimumHeight(180)
        self.form_layout.addRow("Channels:", area)
        self.setMinimumWidth(520)

        self.form_layout.addRow("", _hint(
            "Data channels 0-36 only; the advertising channels are not covered. "
            "At least two must stay enabled. The controller applies this on "
            "links where it is the central, and combines it with its own "
            "assessment -- read back the result with LE Read Channel Map."))

        self._set_channels(tuple(range(37)))

    def _set_channels(self, channels) -> None:
        value = 0
        for channel in channels:
            value |= 1 << channel
        self.map_input.setText(value.to_bytes(5, "little").hex().upper())
        self._hex_to_checks()

    def _hex_to_checks(self) -> None:
        try:
            raw = _hex_bytes(self.map_input.text(), "channel map")
        except ValueError:
            return
        value = int.from_bytes(raw.ljust(5, b"\x00")[:5], "little")
        for channel, box in self.checks.items():
            box.blockSignals(True)
            box.setChecked(bool(value >> channel & 1))
            box.blockSignals(False)
        self._update_count()

    def _checks_to_hex(self) -> None:
        value = 0
        for channel, box in self.checks.items():
            if box.isChecked():
                value |= 1 << channel
        self.map_input.setText(value.to_bytes(5, "little").hex().upper())
        self._update_count()

    def _update_count(self) -> None:
        enabled = sum(1 for box in self.checks.values() if box.isChecked())
        self.count_label.setText(f"{enabled} / 37 channels enabled")

    def validate_parameters(self) -> bool:
        channel_map = _hex_bytes(self.map_input.text(), "channel map")
        self._cmd_instance = le_cmds.LeSetHostChannelClassification(
            channel_map=channel_map)


class LeReadChannelMapUI(HCICmdUI):
    """UI for LE Read Channel Map (0x2015)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_CHANNEL_MAP)
    NAME = "LE Read Channel Map"

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)
        self.form_layout.addRow("", _hint(
            "Returns the map in use on that link -- the host classification "
            "intersected with the controller's own channel assessment."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeReadChannelMap(self.handle_input.value())


for _cls in (LeSetEventMaskUI,
             LeSetRandomAddressUI,
             LeSetScanResponseDataUI,
             LeSetAdvertiseEnableUI,
             LeCreateConnectionUI,
             LeConnectionUpdateUI,
             LeReadRemoteFeaturesUI,
             LeAddDeviceToFilterAcceptListUI,
             LeRemoveDeviceFromFilterAcceptListUI,
             LeSetHostChannelClassificationUI,
             LeReadChannelMapUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'LeSetEventMaskUI',
    'LeSetRandomAddressUI',
    'LeSetScanResponseDataUI',
    'LeSetAdvertiseEnableUI',
    'LeCreateConnectionUI',
    'LeConnectionUpdateUI',
    'LeReadRemoteFeaturesUI',
    'LeAddDeviceToFilterAcceptListUI',
    'LeRemoveDeviceFromFilterAcceptListUI',
    'LeSetHostChannelClassificationUI',
    'LeReadChannelMapUI',
]
