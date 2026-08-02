"""
Command dialogs for extended/periodic advertising, extended scanning, extended
connection and Channel Sounding.

Each dialog builds its command object in `validate_parameters`; the base class
sends it and reports any ValueError from the packet layer in the dialog's error
label, so range checks live in `hci.cmd` and are not duplicated here.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QWidget,
)

import hci.cmd.le_cmds as le_cmds
from hci.cmd.cmd_opcodes import LEControllerOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI
from .le_cmdui import _parse_bd_addr


def _hex_bytes(text: str, field: str) -> bytes:
    """Parse a hex string from a line edit, tolerating spaces and 0x prefixes."""
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


# =========================================================== extended advertising

class LeSetAdvertisingSetRandomAddressUI(HCICmdUI):
    """UI for LE Set Advertising Set Random Address (0x2035)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_ADVERTISING_SET_RANDOM_ADDRESS)
    NAME = "LE Set Advertising Set Random Address"

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x00, 0xEF, 0x00, "Advertising set handle")
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.address_input = QLineEdit("C0:00:00:00:00:01")
        self.address_input.setToolTip(
            "Top two bits must be 11 for a static random address")
        self.form_layout.addRow("Random Address:", self.address_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetAdvertisingSetRandomAddress(
            adv_handle=self.handle_input.value(),
            random_address=_parse_bd_addr(self.address_input.text()),
        )


class LeSetExtendedAdvertisingParametersUI(HCICmdUI):
    """UI for LE Set Extended Advertising Parameters (0x2036)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_ADVERTISING_PARAMETERS)
    NAME = "LE Set Extended Advertising Parameters"

    #: Presets for the event-properties word, plus a free-form entry.
    _PROPERTY_PRESETS = (
        ("Extended, connectable (non-scannable)",
         int(le_cmds.AdvEventProperties.CONNECTABLE)),
        ("Extended, scannable (non-connectable)",
         int(le_cmds.AdvEventProperties.SCANNABLE)),
        ("Extended, non-connectable non-scannable", 0x0000),
        ("Extended, anonymous non-connectable",
         int(le_cmds.AdvEventProperties.ANONYMOUS)),
        ("Legacy ADV_IND", int(le_cmds.LEGACY_ADV_IND)),
        ("Legacy ADV_DIRECT_IND", int(le_cmds.LEGACY_ADV_DIRECT_IND)),
        ("Legacy ADV_SCAN_IND", int(le_cmds.LEGACY_ADV_SCAN_IND)),
        ("Legacy ADV_NONCONN_IND", int(le_cmds.LEGACY_ADV_NONCONN_IND)),
    )

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.properties_input = QComboBox()
        for label, value in self._PROPERTY_PRESETS:
            self.properties_input.addItem(label, value)
        self.form_layout.addRow("Event Properties:", self.properties_input)

        self.tx_power_flag = QCheckBox("Include TX power in the advertisement")
        self.form_layout.addRow("", self.tx_power_flag)

        # 3-octet field, 0.625 ms units.
        self.interval_min_input = _spin(0x000020, 0xFFFFFF, 0x000800,
                                        "Primary advertising interval min "
                                        "(N * 0.625 ms)")
        self.interval_max_input = _spin(0x000020, 0xFFFFFF, 0x000800,
                                        "Primary advertising interval max "
                                        "(N * 0.625 ms)")
        self.form_layout.addRow("Primary Interval Min:", self.interval_min_input)
        self.form_layout.addRow("Primary Interval Max:", self.interval_max_input)

        channels = QWidget()
        channel_layout = QHBoxLayout(channels)
        channel_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_checks = []
        for channel in (37, 38, 39):
            box = QCheckBox(f"Channel {channel}")
            box.setChecked(True)
            channel_layout.addWidget(box)
            self.channel_checks.append(box)
        self.form_layout.addRow("Primary Channel Map:", channels)

        self.own_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Own Address Type:", self.own_addr_type_input)

        self.peer_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Peer Address Type:", self.peer_addr_type_input)

        self.peer_addr_input = QLineEdit("00:00:00:00:00:00")
        self.form_layout.addRow("Peer Address:", self.peer_addr_input)

        self.filter_policy_input = QComboBox()
        self.filter_policy_input.addItem("Process all devices", 0x00)
        self.filter_policy_input.addItem("Filter scan requests", 0x01)
        self.filter_policy_input.addItem("Filter connection requests", 0x02)
        self.filter_policy_input.addItem("Filter both", 0x03)
        self.form_layout.addRow("Filter Policy:", self.filter_policy_input)

        self.tx_power_input = _spin(-127, 127, 127,
                                    "Requested TX power in dBm; 127 = no preference")
        self.form_layout.addRow("Advertising TX Power:", self.tx_power_input)

        self.primary_phy_input = QComboBox()
        for phy in le_cmds.PrimaryPhy:
            self.primary_phy_input.addItem(phy.name, phy.value)
        self.form_layout.addRow("Primary PHY:", self.primary_phy_input)

        self.secondary_phy_input = QComboBox()
        for phy in le_cmds.SecondaryPhy:
            self.secondary_phy_input.addItem(phy.name, phy.value)
        self.form_layout.addRow("Secondary PHY:", self.secondary_phy_input)

        self.max_skip_input = _spin(0x00, 0xFF, 0x00,
                                    "Secondary advertising max skip")
        self.form_layout.addRow("Secondary Max Skip:", self.max_skip_input)

        self.sid_input = _spin(0x00, 0x0F, 0x00, "Advertising Set ID")
        self.form_layout.addRow("Advertising SID:", self.sid_input)

        self.scan_notify_input = QCheckBox(
            "Notify the host when a scan request arrives")
        self.form_layout.addRow("", self.scan_notify_input)

        self.form_layout.addRow("", _hint(
            "A legacy preset makes the controller emit legacy PDUs (31-byte "
            "payload). Extended properties allow long data but cannot be both "
            "connectable and scannable."))

    def validate_parameters(self) -> bool:
        properties = self.properties_input.currentData()
        if self.tx_power_flag.isChecked():
            properties |= int(le_cmds.AdvEventProperties.INCLUDE_TX_POWER)

        channel_map = 0
        for index, box in enumerate(self.channel_checks):
            if box.isChecked():
                channel_map |= 1 << index

        self._cmd_instance = le_cmds.LeSetExtendedAdvertisingParameters(
            adv_handle=self.handle_input.value(),
            adv_event_properties=properties,
            primary_adv_interval_min=self.interval_min_input.value(),
            primary_adv_interval_max=self.interval_max_input.value(),
            primary_adv_channel_map=channel_map,
            own_address_type=self.own_addr_type_input.currentData(),
            peer_address_type=self.peer_addr_type_input.currentData(),
            peer_address=_parse_bd_addr(self.peer_addr_input.text()),
            adv_filter_policy=self.filter_policy_input.currentData(),
            adv_tx_power=self.tx_power_input.value(),
            primary_adv_phy=self.primary_phy_input.currentData(),
            secondary_adv_max_skip=self.max_skip_input.value(),
            secondary_adv_phy=self.secondary_phy_input.currentData(),
            adv_sid=self.sid_input.value(),
            scan_request_notification_enable=(
                0x01 if self.scan_notify_input.isChecked() else 0x00),
        )


class _ExtendedDataUI(HCICmdUI):
    """Shared dialog for the extended advertising/scan-response data commands."""

    COMMAND = None      # set by the subclass

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.operation_input = QComboBox()
        for operation in le_cmds.DataOperation:
            self.operation_input.addItem(
                operation.name.replace("_", " ").title(), operation.value)
        self.operation_input.setCurrentIndex(
            self.operation_input.findData(int(le_cmds.DataOperation.COMPLETE)))
        self.form_layout.addRow("Operation:", self.operation_input)

        self.fragment_input = QComboBox()
        self.fragment_input.addItem("Controller may fragment", 0x00)
        self.fragment_input.addItem("Controller should not fragment", 0x01)
        self.fragment_input.setCurrentIndex(1)
        self.form_layout.addRow("Fragment Preference:", self.fragment_input)

        self.length_label = QLabel("0 bytes")
        self.form_layout.addRow("Data Length:", self.length_label)

        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("Hex bytes, e.g. 020106")
        self.data_input.textChanged.connect(self._update_length)
        self.form_layout.addRow("Data:", self.data_input)

        self.form_layout.addRow("", _hint(
            "One command carries up to 251 bytes. For longer payloads send "
            "First / Intermediate / Last fragments in order."))

    def _update_length(self) -> None:
        try:
            length = len(_hex_bytes(self.data_input.text(), "data"))
        except ValueError:
            self.length_label.setText("invalid hex")
            return
        self.length_label.setText(f"{length} bytes")

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(
            adv_handle=self.handle_input.value(),
            data=_hex_bytes(self.data_input.text(), "data"),
            operation=self.operation_input.currentData(),
            fragment_preference=self.fragment_input.currentData(),
        )


class LeSetExtendedAdvertisingDataUI(_ExtendedDataUI):
    """UI for LE Set Extended Advertising Data (0x2037)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_ADVERTISING_DATA)
    NAME = "LE Set Extended Advertising Data"
    COMMAND = le_cmds.LeSetExtendedAdvertisingData


class LeSetExtendedScanResponseDataUI(_ExtendedDataUI):
    """UI for LE Set Extended Scan Response Data (0x2038)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_SCAN_RESPONSE_DATA)
    NAME = "LE Set Extended Scan Response Data"
    COMMAND = le_cmds.LeSetExtendedScanResponseData


class LeSetExtendedAdvertisingEnableUI(HCICmdUI):
    """UI for LE Set Extended Advertising Enable (0x2039)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_ADVERTISING_ENABLE)
    NAME = "LE Set Extended Advertising Enable"

    def setup_ui(self):
        super().setup_ui()

        self.enable_input = QCheckBox("Enable advertising")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.duration_input = _spin(0x0000, 0xFFFF, 0x0000,
                                    "Duration in 10 ms units; 0 = until disabled")
        self.form_layout.addRow("Duration:", self.duration_input)

        self.max_events_input = _spin(0x00, 0xFF, 0x00,
                                      "Stop after this many extended advertising "
                                      "events; 0 = no limit")
        self.form_layout.addRow("Max Ext Adv Events:", self.max_events_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetExtendedAdvertisingEnable(
            enable=self.enable_input.isChecked(),
            sets=[(self.handle_input.value(), self.duration_input.value(),
                   self.max_events_input.value())],
        )


class LeRemoveAdvertisingSetUI(HCICmdUI):
    """UI for LE Remove Advertising Set (0x203C)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_ADVERTISING_SET)
    NAME = "LE Remove Advertising Set"

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeRemoveAdvertisingSet(
            adv_handle=self.handle_input.value())


# ============================================================ periodic advertising

class LeSetPeriodicAdvertisingParametersUI(HCICmdUI):
    """UI for LE Set Periodic Advertising Parameters (0x203E)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADVERTISING_PARAMETERS)
    NAME = "LE Set Periodic Advertising Parameters"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.interval_min_input = _spin(0x0006, 0xFFFF, 0x0060,
                                        "Periodic interval min (N * 1.25 ms)")
        self.interval_max_input = _spin(0x0006, 0xFFFF, 0x0080,
                                        "Periodic interval max (N * 1.25 ms)")
        self.form_layout.addRow("Interval Min:", self.interval_min_input)
        self.form_layout.addRow("Interval Max:", self.interval_max_input)

        self.tx_power_input = QCheckBox("Include TX power")
        self.form_layout.addRow("Properties:", self.tx_power_input)

        self.form_layout.addRow("", _hint(
            "The advertising set must already exist and be non-connectable, "
            "non-scannable and non-anonymous."))

    def validate_parameters(self) -> bool:
        properties = 0x0040 if self.tx_power_input.isChecked() else 0x0000
        self._cmd_instance = le_cmds.LeSetPeriodicAdvertisingParameters(
            adv_handle=self.handle_input.value(),
            periodic_adv_interval_min=self.interval_min_input.value(),
            periodic_adv_interval_max=self.interval_max_input.value(),
            periodic_adv_properties=properties,
        )


class LeSetPeriodicAdvertisingDataUI(HCICmdUI):
    """UI for LE Set Periodic Advertising Data (0x203F)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADVERTISING_DATA)
    NAME = "LE Set Periodic Advertising Data"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.operation_input = QComboBox()
        for operation in le_cmds.DataOperation:
            if operation is le_cmds.DataOperation.UNCHANGED:
                continue    # not valid for periodic data
            self.operation_input.addItem(
                operation.name.replace("_", " ").title(), operation.value)
        self.operation_input.setCurrentIndex(
            self.operation_input.findData(int(le_cmds.DataOperation.COMPLETE)))
        self.form_layout.addRow("Operation:", self.operation_input)

        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("Hex bytes, e.g. 0409546573742064617461")
        self.form_layout.addRow("Data:", self.data_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetPeriodicAdvertisingData(
            adv_handle=self.handle_input.value(),
            data=_hex_bytes(self.data_input.text(), "data"),
            operation=self.operation_input.currentData(),
        )


class LeSetPeriodicAdvertisingEnableUI(HCICmdUI):
    """UI for LE Set Periodic Advertising Enable (0x2040)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADVERTISING_ENABLE)
    NAME = "LE Set Periodic Advertising Enable"

    def setup_ui(self):
        super().setup_ui()

        self.enable_input = QCheckBox("Enable periodic advertising")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.adi_input = QCheckBox("Include ADI in AUX_SYNC_IND")
        self.form_layout.addRow("", self.adi_input)

        self.handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("Advertising Handle:", self.handle_input)

        self.form_layout.addRow("", _hint(
            "The advertising set itself still has to be enabled with "
            "LE Set Extended Advertising Enable."))

    def validate_parameters(self) -> bool:
        enable = 0x01 if self.enable_input.isChecked() else 0x00
        if enable and self.adi_input.isChecked():
            enable |= le_cmds.LeSetPeriodicAdvertisingEnable.INCLUDE_ADI
        self._cmd_instance = le_cmds.LeSetPeriodicAdvertisingEnable(
            enable=enable, adv_handle=self.handle_input.value())


# =============================================================== extended scanning

class LeSetExtendedScanParametersUI(HCICmdUI):
    """UI for LE Set Extended Scan Parameters (0x2041)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_SCAN_PARAMETERS)
    NAME = "LE Set Extended Scan Parameters"

    def setup_ui(self):
        super().setup_ui()

        self.own_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Own Address Type:", self.own_addr_type_input)

        self.filter_policy_input = QComboBox()
        self.filter_policy_input.addItem("Accept all advertisements", 0x00)
        self.filter_policy_input.addItem("Filter Accept List only", 0x01)
        self.filter_policy_input.addItem("Accept all + directed RPA", 0x02)
        self.filter_policy_input.addItem("Filter Accept List + directed RPA", 0x03)
        self.form_layout.addRow("Filter Policy:", self.filter_policy_input)

        self.phy_1m_input = QCheckBox("LE 1M")
        self.phy_1m_input.setChecked(True)
        self.phy_coded_input = QCheckBox("LE Coded")
        phys = QWidget()
        phy_layout = QHBoxLayout(phys)
        phy_layout.setContentsMargins(0, 0, 0, 0)
        phy_layout.addWidget(self.phy_1m_input)
        phy_layout.addWidget(self.phy_coded_input)
        self.form_layout.addRow("Scanning PHYs:", phys)

        self.scan_type_input = QComboBox()
        self.scan_type_input.addItem("Passive Scanning", 0x00)
        self.scan_type_input.addItem("Active Scanning", 0x01)
        self.scan_type_input.setCurrentIndex(1)
        self.form_layout.addRow("Scan Type:", self.scan_type_input)

        self.interval_input = _spin(0x0004, 0xFFFF, 0x0060,
                                    "Scan interval (N * 0.625 ms)")
        self.window_input = _spin(0x0004, 0xFFFF, 0x0030,
                                  "Scan window (N * 0.625 ms)")
        self.form_layout.addRow("Scan Interval:", self.interval_input)
        self.form_layout.addRow("Scan Window:", self.window_input)

        self.form_layout.addRow("", _hint(
            "The type/interval/window apply to every selected PHY. Must be sent "
            "while scanning is disabled."))

    def validate_parameters(self) -> bool:
        if not (self.phy_1m_input.isChecked() or self.phy_coded_input.isChecked()):
            raise ValueError("select at least one scanning PHY")

        block = (self.scan_type_input.currentData(),
                 self.interval_input.value(), self.window_input.value())
        phys = {}
        if self.phy_1m_input.isChecked():
            phys[int(le_cmds.ScanPhy.LE_1M)] = block
        if self.phy_coded_input.isChecked():
            phys[int(le_cmds.ScanPhy.LE_CODED)] = block

        self._cmd_instance = le_cmds.LeSetExtendedScanParameters(
            own_address_type=self.own_addr_type_input.currentData(),
            scanning_filter_policy=self.filter_policy_input.currentData(),
            scan_phys=phys,
        )


class LeSetExtendedScanEnableUI(HCICmdUI):
    """UI for LE Set Extended Scan Enable (0x2042)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_SCAN_ENABLE)
    NAME = "LE Set Extended Scan Enable"

    def setup_ui(self):
        super().setup_ui()

        self.enable_input = QCheckBox("Enable scanning")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.filter_input = QComboBox()
        self.filter_input.addItem("Report every advertisement", 0x00)
        self.filter_input.addItem("Filter duplicates", 0x01)
        self.filter_input.addItem("Reset duplicate filter each period", 0x02)
        self.filter_input.setCurrentIndex(1)
        self.form_layout.addRow("Filter Duplicates:", self.filter_input)

        self.duration_input = _spin(0x0000, 0xFFFF, 0x0000,
                                    "Scan duration in 10 ms units; 0 = until "
                                    "disabled")
        self.form_layout.addRow("Duration:", self.duration_input)

        self.period_input = _spin(0x0000, 0xFFFF, 0x0000,
                                  "Repeat period in 1.28 s units; 0 = scan "
                                  "continuously")
        self.form_layout.addRow("Period:", self.period_input)

        self.form_layout.addRow("", _hint(
            "A non-zero duration ends with an LE Scan Timeout event."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetExtendedScanEnable(
            enable=self.enable_input.isChecked(),
            filter_duplicates=self.filter_input.currentData(),
            duration=self.duration_input.value(),
            period=self.period_input.value(),
        )


class LePeriodicAdvertisingCreateSyncUI(HCICmdUI):
    """UI for LE Periodic Advertising Create Sync (0x2044)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.PERIODIC_ADV_CREATE_SYNC)
    NAME = "LE Periodic Advertising Create Sync"

    def setup_ui(self):
        super().setup_ui()

        self.use_list_input = QCheckBox("Use the Periodic Advertiser List")
        self.form_layout.addRow("Options:", self.use_list_input)

        self.reports_off_input = QCheckBox("Start with reports disabled")
        self.form_layout.addRow("", self.reports_off_input)

        self.sid_input = _spin(0x00, 0x0F, 0x00, "Advertising SID to sync to")
        self.form_layout.addRow("Advertising SID:", self.sid_input)

        self.addr_type_input = QComboBox()
        self.addr_type_input.addItem("PUBLIC", 0x00)
        self.addr_type_input.addItem("RANDOM", 0x01)
        self.form_layout.addRow("Advertiser Address Type:", self.addr_type_input)

        self.address_input = QLineEdit("00:00:00:00:00:00")
        self.form_layout.addRow("Advertiser Address:", self.address_input)

        self.skip_input = _spin(0x0000, 0x01F3, 0x0000,
                                "Periodic events that may be skipped")
        self.form_layout.addRow("Skip:", self.skip_input)

        self.timeout_input = _spin(0x000A, 0x4000, 0x03E8,
                                   "Sync timeout (N * 10 ms)")
        self.form_layout.addRow("Sync Timeout:", self.timeout_input)

        self.form_layout.addRow("", _hint(
            "Scanning must be enabled for the controller to find the periodic "
            "train; otherwise this stays pending until cancelled."))

    def validate_parameters(self) -> bool:
        options = 0x00
        if self.use_list_input.isChecked():
            options |= int(le_cmds.PeriodicSyncOptions.USE_PERIODIC_ADV_LIST)
        if self.reports_off_input.isChecked():
            options |= int(le_cmds.PeriodicSyncOptions.REPORTS_INITIALLY_DISABLED)

        self._cmd_instance = le_cmds.LePeriodicAdvertisingCreateSync(
            adv_sid=self.sid_input.value(),
            advertiser_address=_parse_bd_addr(self.address_input.text()),
            advertiser_address_type=self.addr_type_input.currentData(),
            options=options,
            skip=self.skip_input.value(),
            sync_timeout=self.timeout_input.value(),
        )


class LePeriodicAdvertisingTerminateSyncUI(HCICmdUI):
    """UI for LE Periodic Advertising Terminate Sync (0x2046)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.PERIODIC_ADV_TERMINATE_SYNC)
    NAME = "LE Periodic Advertising Terminate Sync"

    def setup_ui(self):
        super().setup_ui()
        self.sync_handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Sync Handle:", self.sync_handle_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LePeriodicAdvertisingTerminateSync(
            sync_handle=self.sync_handle_input.value())


class LeSetPeriodicAdvertisingReceiveEnableUI(HCICmdUI):
    """UI for LE Set Periodic Advertising Receive Enable (0x2059)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADV_RECEIVE_ENABLE)
    NAME = "LE Set Periodic Advertising Receive Enable"

    def setup_ui(self):
        super().setup_ui()

        self.sync_handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Sync Handle:", self.sync_handle_input)

        self.enable_input = QCheckBox("Report periodic advertisements")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.duplicate_input = QCheckBox("Filter duplicates")
        self.form_layout.addRow("", self.duplicate_input)

    def validate_parameters(self) -> bool:
        enable = 0x01 if self.enable_input.isChecked() else 0x00
        if enable and self.duplicate_input.isChecked():
            enable |= le_cmds.LeSetPeriodicAdvertisingReceiveEnable.DUPLICATE_FILTERING
        self._cmd_instance = le_cmds.LeSetPeriodicAdvertisingReceiveEnable(
            sync_handle=self.sync_handle_input.value(), enable=enable)


# ============================================================ extended connection

class LeExtendedCreateConnectionUI(HCICmdUI):
    """UI for LE Extended Create Connection (0x2043)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.EXTENDED_CREATE_CONNECTION)
    NAME = "LE Extended Create Connection"

    def setup_ui(self):
        super().setup_ui()

        self.filter_policy_input = QComboBox()
        self.filter_policy_input.addItem("Use the peer address below", 0x00)
        self.filter_policy_input.addItem("Use the Filter Accept List", 0x01)
        self.form_layout.addRow("Initiator Filter Policy:", self.filter_policy_input)

        self.own_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Own Address Type:", self.own_addr_type_input)

        self.peer_addr_type_input = _address_type_combo()
        self.form_layout.addRow("Peer Address Type:", self.peer_addr_type_input)

        self.peer_addr_input = QLineEdit("00:00:00:00:00:00")
        self.form_layout.addRow("Peer Address:", self.peer_addr_input)

        phys = QWidget()
        phy_layout = QHBoxLayout(phys)
        phy_layout.setContentsMargins(0, 0, 0, 0)
        self.phy_1m_input = QCheckBox("1M")
        self.phy_1m_input.setChecked(True)
        self.phy_2m_input = QCheckBox("2M")
        self.phy_coded_input = QCheckBox("Coded")
        for box in (self.phy_1m_input, self.phy_2m_input, self.phy_coded_input):
            phy_layout.addWidget(box)
        self.form_layout.addRow("Initiating PHYs:", phys)

        self.scan_interval_input = _spin(0x0004, 0xFFFF, 0x0060,
                                         "Scan interval (N * 0.625 ms)")
        self.scan_window_input = _spin(0x0004, 0xFFFF, 0x0030,
                                       "Scan window (N * 0.625 ms)")
        self.form_layout.addRow("Scan Interval:", self.scan_interval_input)
        self.form_layout.addRow("Scan Window:", self.scan_window_input)

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

        self.form_layout.addRow("", _hint(
            "The same parameter block is used for each selected PHY. 2M cannot "
            "be selected on its own -- there is no 2M primary channel to scan."))

    def validate_parameters(self) -> bool:
        block = (self.scan_interval_input.value(), self.scan_window_input.value(),
                 self.conn_min_input.value(), self.conn_max_input.value(),
                 self.latency_input.value(), self.timeout_input.value(),
                 0x0000, 0x0000)

        cmd = le_cmds.LeExtendedCreateConnection
        phy_params = {}
        if self.phy_1m_input.isChecked():
            phy_params[cmd.PHY_1M] = block
        if self.phy_2m_input.isChecked():
            phy_params[cmd.PHY_2M] = block
        if self.phy_coded_input.isChecked():
            phy_params[cmd.PHY_CODED] = block
        if not phy_params:
            raise ValueError("select at least one initiating PHY")

        self._cmd_instance = cmd(
            peer_address=_parse_bd_addr(self.peer_addr_input.text()),
            peer_address_type=self.peer_addr_type_input.currentData(),
            own_address_type=self.own_addr_type_input.currentData(),
            initiator_filter_policy=self.filter_policy_input.currentData(),
            phy_params=phy_params,
        )


# ============================================================== channel sounding

class _HandleOnlyUI(HCICmdUI):
    """Dialog for the CS commands whose only parameter is a connection handle."""

    COMMAND = None

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000,
                                  "Handle of the LE connection to range over")
        self.form_layout.addRow("Connection Handle:", self.handle_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(self.handle_input.value())


class LeCsReadRemoteSupportedCapabilitiesUI(_HandleOnlyUI):
    """UI for LE CS Read Remote Supported Capabilities (0x2083)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_READ_REMOTE_SUPPORTED_CAPABILITIES)
    NAME = "LE CS Read Remote Supported Capabilities"
    COMMAND = le_cmds.LeCsReadRemoteSupportedCapabilities


class LeCsSecurityEnableUI(_HandleOnlyUI):
    """UI for LE CS Security Enable (0x2087)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SECURITY_ENABLE)
    NAME = "LE CS Security Enable"
    COMMAND = le_cmds.LeCsSecurityEnable


class LeCsReadRemoteFaeTableUI(_HandleOnlyUI):
    """UI for LE CS Read Remote FAE Table (0x2089)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_READ_REMOTE_FAE_TABLE)
    NAME = "LE CS Read Remote FAE Table"
    COMMAND = le_cmds.LeCsReadRemoteFaeTable


class LeCsSetDefaultSettingsUI(HCICmdUI):
    """UI for LE CS Set Default Settings (0x2088)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SET_DEFAULT_SETTINGS)
    NAME = "LE CS Set Default Settings"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        roles = QWidget()
        role_layout = QHBoxLayout(roles)
        role_layout.setContentsMargins(0, 0, 0, 0)
        self.initiator_input = QCheckBox("Initiator")
        self.initiator_input.setChecked(True)
        self.reflector_input = QCheckBox("Reflector")
        self.reflector_input.setChecked(True)
        role_layout.addWidget(self.initiator_input)
        role_layout.addWidget(self.reflector_input)
        self.form_layout.addRow("Roles Enabled:", roles)

        self.antenna_input = QComboBox()
        self.antenna_input.addItem("Controller's choice (0xFF)", 0xFF)
        for antenna in range(1, 5):
            self.antenna_input.addItem(f"Antenna {antenna}", antenna)
        self.antenna_input.addItem("Repeat in order (0xFE)", 0xFE)
        self.form_layout.addRow("CS Sync Antenna:", self.antenna_input)

        self.tx_power_input = _spin(-127, 127, 0, "Maximum TX power in dBm")
        self.form_layout.addRow("Max TX Power:", self.tx_power_input)

    def validate_parameters(self) -> bool:
        roles = 0
        if self.initiator_input.isChecked():
            roles |= int(le_cmds.CsRoleMask.INITIATOR)
        if self.reflector_input.isChecked():
            roles |= int(le_cmds.CsRoleMask.REFLECTOR)
        if not roles:
            raise ValueError("enable at least one role")

        self._cmd_instance = le_cmds.LeCsSetDefaultSettings(
            connection_handle=self.handle_input.value(),
            role_enable=roles,
            cs_sync_antenna_selection=self.antenna_input.currentData(),
            max_tx_power=self.tx_power_input.value(),
        )


class LeCsCreateConfigUI(HCICmdUI):
    """UI for LE CS Create Config (0x208B)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_CREATE_CONFIG)
    NAME = "LE CS Create Config"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.config_id_input = _spin(0x00, 0x03, 0x00)
        self.form_layout.addRow("Config ID:", self.config_id_input)

        self.context_input = QComboBox()
        self.context_input.addItem("Local and remote controller", 0x01)
        self.context_input.addItem("Local controller only", 0x00)
        self.form_layout.addRow("Create Context:", self.context_input)

        self.main_mode_input = QComboBox()
        for mode in le_cmds.CsMainMode:
            self.main_mode_input.addItem(mode.name.replace("_", "-"), mode.value)
        self.main_mode_input.setCurrentIndex(1)     # Mode-2
        self.form_layout.addRow("Main Mode:", self.main_mode_input)

        self.sub_mode_input = QComboBox()
        self.sub_mode_input.addItem("Unused", 0xFF)
        for mode in (le_cmds.CsMainMode.MODE_1, le_cmds.CsMainMode.MODE_2,
                     le_cmds.CsMainMode.MODE_3):
            self.sub_mode_input.addItem(mode.name.replace("_", "-"), mode.value)
        self.form_layout.addRow("Sub Mode:", self.sub_mode_input)

        self.min_steps_input = _spin(0x02, 0xFF, 0x02)
        self.max_steps_input = _spin(0x02, 0xFF, 0x05)
        self.form_layout.addRow("Min Main Mode Steps:", self.min_steps_input)
        self.form_layout.addRow("Max Main Mode Steps:", self.max_steps_input)

        self.repetition_input = _spin(0x00, 0x03, 0x00)
        self.form_layout.addRow("Main Mode Repetition:", self.repetition_input)

        self.mode0_steps_input = _spin(0x01, 0x03, 0x03)
        self.form_layout.addRow("Mode-0 Steps:", self.mode0_steps_input)

        self.role_input = QComboBox()
        for role in le_cmds.CsRole:
            self.role_input.addItem(role.name.title(), role.value)
        self.form_layout.addRow("Role:", self.role_input)

        self.rtt_type_input = QComboBox()
        for rtt in le_cmds.CsRttType:
            self.rtt_type_input.addItem(rtt.name.replace("_", " ").title(), rtt.value)
        self.form_layout.addRow("RTT Type:", self.rtt_type_input)

        self.phy_input = QComboBox()
        for phy in le_cmds.CsSyncPhy:
            self.phy_input.addItem(phy.name.replace("_", " "), phy.value)
        self.form_layout.addRow("CS Sync PHY:", self.phy_input)

        self.channel_map_input = QLineEdit(
            le_cmds.LeCsCreateConfig.DEFAULT_CHANNEL_MAP.hex())
        self.channel_map_input.setToolTip(
            "10-octet bitmap over channels 0..78, CS-reserved channels cleared")
        self.form_layout.addRow("Channel Map:", self.channel_map_input)

        self.map_repetition_input = _spin(0x01, 0xFF, 0x01)
        self.form_layout.addRow("Channel Map Repetition:", self.map_repetition_input)

        self.selection_input = QComboBox()
        self.selection_input.addItem("Algorithm #3b", 0x00)
        self.selection_input.addItem("Algorithm #3c", 0x01)
        self.form_layout.addRow("Channel Selection:", self.selection_input)

        self.shape_input = QComboBox()
        self.shape_input.addItem("Hat shape", 0x00)
        self.shape_input.addItem("X shape", 0x01)
        self.form_layout.addRow("Ch3c Shape:", self.shape_input)

        self.jump_input = _spin(0x02, 0x08, 0x02)
        self.form_layout.addRow("Ch3c Jump:", self.jump_input)

    def validate_parameters(self) -> bool:
        channel_map = _hex_bytes(self.channel_map_input.text(), "channel map")
        self._cmd_instance = le_cmds.LeCsCreateConfig(
            connection_handle=self.handle_input.value(),
            config_id=self.config_id_input.value(),
            create_context=self.context_input.currentData(),
            main_mode_type=self.main_mode_input.currentData(),
            sub_mode_type=self.sub_mode_input.currentData(),
            min_main_mode_steps=self.min_steps_input.value(),
            max_main_mode_steps=self.max_steps_input.value(),
            main_mode_repetition=self.repetition_input.value(),
            mode_0_steps=self.mode0_steps_input.value(),
            role=self.role_input.currentData(),
            rtt_type=self.rtt_type_input.currentData(),
            cs_sync_phy=self.phy_input.currentData(),
            channel_map=channel_map,
            channel_map_repetition=self.map_repetition_input.value(),
            channel_selection_type=self.selection_input.currentData(),
            ch3c_shape=self.shape_input.currentData(),
            ch3c_jump=self.jump_input.value(),
        )


class LeCsRemoveConfigUI(HCICmdUI):
    """UI for LE CS Remove Config (0x208C)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_REMOVE_CONFIG)
    NAME = "LE CS Remove Config"

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)
        self.config_id_input = _spin(0x00, 0x03, 0x00)
        self.form_layout.addRow("Config ID:", self.config_id_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCsRemoveConfig(
            connection_handle=self.handle_input.value(),
            config_id=self.config_id_input.value())


class LeCsSetProcedureParametersUI(HCICmdUI):
    """UI for LE CS Set Procedure Parameters (0x208E)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_SET_PROCEDURE_PARAMETERS)
    NAME = "LE CS Set Procedure Parameters"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.config_id_input = _spin(0x00, 0x03, 0x00)
        self.form_layout.addRow("Config ID:", self.config_id_input)

        self.max_len_input = _spin(0x0001, 0xFFFF, 0x2710,
                                   "Max procedure length (N * 0.625 ms)")
        self.form_layout.addRow("Max Procedure Length:", self.max_len_input)

        self.min_interval_input = _spin(0x0001, 0xFFFF, 0x0001,
                                        "Min procedure interval, in connection "
                                        "events")
        self.max_interval_input = _spin(0x0001, 0xFFFF, 0x0001,
                                        "Max procedure interval, in connection "
                                        "events")
        self.form_layout.addRow("Min Procedure Interval:", self.min_interval_input)
        self.form_layout.addRow("Max Procedure Interval:", self.max_interval_input)

        self.count_input = _spin(0x0000, 0xFFFF, 0x0001,
                                 "Procedures to run; 0 = until disabled")
        self.form_layout.addRow("Max Procedure Count:", self.count_input)

        self.min_subevent_input = _spin(0x0000004E, 0xFFFFFF, 0x0004E2,
                                        "Min subevent length in microseconds")
        self.max_subevent_input = _spin(0x0000004E, 0xFFFFFF, 0x0F4240,
                                        "Max subevent length in microseconds")
        self.form_layout.addRow("Min Subevent Length:", self.min_subevent_input)
        self.form_layout.addRow("Max Subevent Length:", self.max_subevent_input)

        self.antenna_input = _spin(0x00, 0x07, 0x00,
                                   "Tone antenna configuration index")
        self.form_layout.addRow("Tone Antenna Config:", self.antenna_input)

        self.phy_input = QComboBox()
        for phy in le_cmds.CsSyncPhy:
            self.phy_input.addItem(phy.name.replace("_", " "), phy.value)
        self.form_layout.addRow("PHY:", self.phy_input)

        self.tx_delta_input = _spin(-127, 127, 0, "TX power delta in dB")
        self.form_layout.addRow("TX Power Delta:", self.tx_delta_input)

        self.peer_antenna_input = _spin(0x01, 0x0F, 0x01,
                                        "Preferred peer antenna bitmap")
        self.form_layout.addRow("Preferred Peer Antenna:", self.peer_antenna_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCsSetProcedureParameters(
            connection_handle=self.handle_input.value(),
            config_id=self.config_id_input.value(),
            max_procedure_len=self.max_len_input.value(),
            min_procedure_interval=self.min_interval_input.value(),
            max_procedure_interval=self.max_interval_input.value(),
            max_procedure_count=self.count_input.value(),
            min_subevent_len=self.min_subevent_input.value(),
            max_subevent_len=self.max_subevent_input.value(),
            tone_antenna_config_selection=self.antenna_input.value(),
            phy=self.phy_input.currentData(),
            tx_power_delta=self.tx_delta_input.value(),
            preferred_peer_antenna=self.peer_antenna_input.value(),
        )


class LeCsProcedureEnableUI(HCICmdUI):
    """UI for LE CS Procedure Enable (0x208F)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CS_PROCEDURE_ENABLE)
    NAME = "LE CS Procedure Enable"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0000)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.config_id_input = _spin(0x00, 0x03, 0x00)
        self.form_layout.addRow("Config ID:", self.config_id_input)

        self.enable_input = QCheckBox("Start the CS procedure")
        self.enable_input.setChecked(True)
        self.form_layout.addRow("Enable:", self.enable_input)

        self.form_layout.addRow("", _hint(
            "Security Enable, Set Default Settings, Create Config and Set "
            "Procedure Parameters must all have completed for this config, or "
            "the controller answers Command Disallowed."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCsProcedureEnable(
            connection_handle=self.handle_input.value(),
            config_id=self.config_id_input.value(),
            enable=self.enable_input.isChecked(),
        )


for _cls in (LeSetAdvertisingSetRandomAddressUI,
             LeSetExtendedAdvertisingParametersUI,
             LeSetExtendedAdvertisingDataUI,
             LeSetExtendedScanResponseDataUI,
             LeSetExtendedAdvertisingEnableUI,
             LeRemoveAdvertisingSetUI,
             LeSetPeriodicAdvertisingParametersUI,
             LeSetPeriodicAdvertisingDataUI,
             LeSetPeriodicAdvertisingEnableUI,
             LeSetExtendedScanParametersUI,
             LeSetExtendedScanEnableUI,
             LePeriodicAdvertisingCreateSyncUI,
             LePeriodicAdvertisingTerminateSyncUI,
             LeSetPeriodicAdvertisingReceiveEnableUI,
             LeExtendedCreateConnectionUI,
             LeCsReadRemoteSupportedCapabilitiesUI,
             LeCsSecurityEnableUI,
             LeCsReadRemoteFaeTableUI,
             LeCsSetDefaultSettingsUI,
             LeCsCreateConfigUI,
             LeCsRemoveConfigUI,
             LeCsSetProcedureParametersUI,
             LeCsProcedureEnableUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'LeSetAdvertisingSetRandomAddressUI',
    'LeSetExtendedAdvertisingParametersUI',
    'LeSetExtendedAdvertisingDataUI',
    'LeSetExtendedScanResponseDataUI',
    'LeSetExtendedAdvertisingEnableUI',
    'LeRemoveAdvertisingSetUI',
    'LeSetPeriodicAdvertisingParametersUI',
    'LeSetPeriodicAdvertisingDataUI',
    'LeSetPeriodicAdvertisingEnableUI',
    'LeSetExtendedScanParametersUI',
    'LeSetExtendedScanEnableUI',
    'LePeriodicAdvertisingCreateSyncUI',
    'LePeriodicAdvertisingTerminateSyncUI',
    'LeSetPeriodicAdvertisingReceiveEnableUI',
    'LeExtendedCreateConnectionUI',
    'LeCsReadRemoteSupportedCapabilitiesUI',
    'LeCsSecurityEnableUI',
    'LeCsReadRemoteFaeTableUI',
    'LeCsSetDefaultSettingsUI',
    'LeCsCreateConfigUI',
    'LeCsRemoveConfigUI',
    'LeCsSetProcedureParametersUI',
    'LeCsProcedureEnableUI',
]
