"""
Command dialogs for the LE isochronous commands -- CIG/CIS, BIG/BIS, ISO data
paths and the ISO test modes.

    0x2060  LE Read ISO TX Sync            0x206A  LE BIG Create Sync
    0x2061  LE Set CIG Parameters          0x206B  LE BIG Terminate Sync
    0x2062  LE Set CIG Parameters Test     0x206C  LE Request Peer SCA
    0x2063  LE Create CIS                  0x206D  LE Setup ISO Data Path
    0x2064  LE Remove CIG                  0x206E  LE Remove ISO Data Path
    0x2065  LE Accept CIS Request          0x206F  LE ISO Transmit Test
    0x2066  LE Reject CIS Request          0x2070  LE ISO Receive Test
    0x2067  LE Create BIG                  0x2071  LE ISO Read Test Counters
    0x2068  LE Create BIG Test             0x2072  LE ISO Test End
    0x2069  LE Terminate BIG               0x2073  LE Set Host Feature
                                           0x2074  LE Read ISO Link Quality

Four of these carry a variable-length array (the two Set CIG Parameters forms,
Create CIS, and the BIS list in BIG Create Sync). Those get an editable table
with add/remove buttons rather than a pile of numbered spin boxes, because the
count is genuinely variable and a fixed form would cap it arbitrarily.
"""

from __future__ import annotations

from typing import List, Sequence

from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QWidget,
)

import hci.cmd.le_cmds as le_cmds
from hci.cmd.cmd_opcodes import LEControllerOCF, OGF, create_opcode

from .. import register_command_ui
from ..cmd_baseui import HCICmdUI


def _spin(minimum: int, maximum: int, value: int, tip: str = "",
          suffix: str = "") -> QSpinBox:
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


def _phy_combo(default: int = int(le_cmds.IsoPhy.LE_2M)) -> QComboBox:
    combo = QComboBox()
    for label, value in (("LE 1M", 0x01), ("LE 2M", 0x02), ("LE Coded", 0x04),
                         ("1M + 2M", 0x03), ("1M + 2M + Coded", 0x07)):
        combo.addItem(label, value)
    index = combo.findData(default)
    if index >= 0:
        combo.setCurrentIndex(index)
    return combo


def _packing_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("Sequential", int(le_cmds.IsoPacking.SEQUENTIAL))
    combo.addItem("Interleaved", int(le_cmds.IsoPacking.INTERLEAVED))
    return combo


def _framing_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("Unframed", int(le_cmds.IsoFraming.UNFRAMED))
    combo.addItem("Framed", int(le_cmds.IsoFraming.FRAMED))
    return combo


def _sca_combo() -> QComboBox:
    combo = QComboBox()
    for accuracy in le_cmds.ClockAccuracy:
        # PPM_251_TO_500 -> "251 to 500 ppm"
        label = accuracy.name.removeprefix("PPM_").replace("_", " ").lower()
        combo.addItem(f"{label} ppm", int(accuracy))
    return combo


def _payload_type_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("Zero length", int(le_cmds.IsoPayloadType.ZERO_LENGTH))
    combo.addItem("Variable length", int(le_cmds.IsoPayloadType.VARIABLE_LENGTH))
    combo.addItem("Maximum length", int(le_cmds.IsoPayloadType.MAXIMUM_LENGTH))
    combo.setCurrentIndex(2)
    return combo


class _ArrayTableUI(HCICmdUI):
    """
    Base for the dialogs carrying a variable-length array.

    Subclasses declare `TABLE_COLUMNS` as `(header, default)` pairs and read the
    rows back with `table_rows()`. Everything is entered as decimal integers --
    these are counts, ids and handles, and a hex/decimal toggle per cell would
    cost more than it explains.
    """

    TABLE_COLUMNS: Sequence = ()
    TABLE_LABEL = "Entries:"
    MAX_ROWS = 0x1F

    def build_table(self) -> None:
        self.table = QTableWidget(0, len(self.TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in self.TABLE_COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Size to the headers rather than stretching evenly: the CIG test form
        # has ten columns, and an even split truncates every one of them.
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(140)
        self.form_layout.addRow(self.TABLE_LABEL, self.table)

        buttons = QWidget()
        layout = QHBoxLayout(buttons)
        layout.setContentsMargins(0, 0, 0, 0)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_row)
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self.remove_row)
        layout.addWidget(add_btn)
        layout.addWidget(remove_btn)
        layout.addStretch(1)
        self.form_layout.addRow("", buttons)

        self.add_row()
        self.setMinimumWidth(620)

    def add_row(self) -> None:
        if self.table.rowCount() >= self.MAX_ROWS:
            self.log_error(f"at most {self.MAX_ROWS} entries are allowed")
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, (_, default) in enumerate(self.TABLE_COLUMNS):
            # The first column of a new row is usually an id: step it so two
            # rows are not born with the same one.
            value = default + row if column == 0 else default
            self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def remove_row(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            row = self.table.rowCount() - 1
        if row >= 0:
            self.table.removeRow(row)

    def table_rows(self) -> List[tuple]:
        rows = []
        for row in range(self.table.rowCount()):
            values = []
            for column, (header, _) in enumerate(self.TABLE_COLUMNS):
                item = self.table.item(row, column)
                text = (item.text() if item else "").strip()
                try:
                    values.append(int(text, 0))
                except ValueError:
                    raise ValueError(
                        f"row {row + 1}, {header}: {text!r} is not a number")
            rows.append(tuple(values))
        if not rows:
            raise ValueError("at least one entry is required")
        return rows


# =================================================================== CIG / CIS

class LeSetCigParametersUI(_ArrayTableUI):
    """UI for LE Set CIG Parameters (0x2061)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_CIG_PARAMS)
    NAME = "LE Set CIG Parameters"

    TABLE_LABEL = "CIS list:"
    # Headers are kept short: the table stretches its columns evenly, so a
    # long one is simply truncated rather than widening the column.
    TABLE_COLUMNS = (
        ("CIS ID", 0), ("SDU C\u2192P", 40), ("SDU P\u2192C", 40),
        ("PHY C\u2192P", 0x02), ("PHY P\u2192C", 0x02),
        ("RTN C\u2192P", 2), ("RTN P\u2192C", 2),
    )

    def setup_ui(self):
        super().setup_ui()

        self.cig_id_input = _spin(0x00, 0xEF, 0x00, "Identifies the group")
        self.form_layout.addRow("CIG ID:", self.cig_id_input)

        self.sdu_c_input = _spin(255, 0x0FFFFF, 10000,
                                 "Central to peripheral SDU interval", " us")
        self.sdu_p_input = _spin(255, 0x0FFFFF, 10000,
                                 "Peripheral to central SDU interval", " us")
        self.form_layout.addRow("SDU Interval C->P:", self.sdu_c_input)
        self.form_layout.addRow("SDU Interval P->C:", self.sdu_p_input)

        self.sca_input = _sca_combo()
        self.form_layout.addRow("Worst Case SCA:", self.sca_input)

        self.packing_input = _packing_combo()
        self.form_layout.addRow("Packing:", self.packing_input)

        self.framing_input = _framing_combo()
        self.form_layout.addRow("Framing:", self.framing_input)

        self.latency_c_input = _spin(5, 4000, 10,
                                     "Max transport latency C->P", " ms")
        self.latency_p_input = _spin(5, 4000, 10,
                                     "Max transport latency P->C", " ms")
        self.form_layout.addRow("Max Latency C->P:", self.latency_c_input)
        self.form_layout.addRow("Max Latency P->C:", self.latency_p_input)

        self.build_table()

        self.form_layout.addRow("", _hint(
            "PHY values are a bitmap: 1 = 1M, 2 = 2M, 4 = Coded. The Command "
            "Complete returns one CIS connection handle per row, in this order "
            "-- those are what LE Create CIS then needs. A Max SDU of 0 makes "
            "that direction receive-only."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetCigParameters(
            cig_id=self.cig_id_input.value(),
            sdu_interval_c_to_p=self.sdu_c_input.value(),
            sdu_interval_p_to_c=self.sdu_p_input.value(),
            worst_case_sca=self.sca_input.currentData(),
            packing=self.packing_input.currentData(),
            framing=self.framing_input.currentData(),
            max_transport_latency_c_to_p=self.latency_c_input.value(),
            max_transport_latency_p_to_c=self.latency_p_input.value(),
            cis_params=self.table_rows(),
        )


class LeSetCigParametersTestUI(_ArrayTableUI):
    """UI for LE Set CIG Parameters Test (0x2062)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_CIG_PARAMS_TEST)
    NAME = "LE Set CIG Parameters Test"

    TABLE_LABEL = "CIS list:"
    TABLE_COLUMNS = (
        ("CIS ID", 0), ("NSE", 1), ("SDU C\u2192P", 40), ("SDU P\u2192C", 40),
        ("PDU C\u2192P", 40), ("PDU P\u2192C", 40),
        ("PHY C\u2192P", 0x02), ("PHY P\u2192C", 0x02),
        ("BN C\u2192P", 1), ("BN P\u2192C", 1),
    )

    def setup_ui(self):
        super().setup_ui()

        self.cig_id_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("CIG ID:", self.cig_id_input)

        self.sdu_c_input = _spin(255, 0x0FFFFF, 10000, "", " us")
        self.sdu_p_input = _spin(255, 0x0FFFFF, 10000, "", " us")
        self.form_layout.addRow("SDU Interval C->P:", self.sdu_c_input)
        self.form_layout.addRow("SDU Interval P->C:", self.sdu_p_input)

        self.ft_c_input = _spin(1, 255, 1, "Flush timeout C->P, in ISO intervals")
        self.ft_p_input = _spin(1, 255, 1, "Flush timeout P->C, in ISO intervals")
        self.form_layout.addRow("FT C->P:", self.ft_c_input)
        self.form_layout.addRow("FT P->C:", self.ft_p_input)

        self.iso_interval_input = _spin(4, 0x0C80, 8,
                                        "ISO interval in 1.25 ms units")
        self.form_layout.addRow("ISO Interval:", self.iso_interval_input)
        self.iso_ms_label = _hint("")
        self.iso_interval_input.valueChanged.connect(self._update_iso_ms)
        self.form_layout.addRow("", self.iso_ms_label)
        self._update_iso_ms()

        self.sca_input = _sca_combo()
        self.form_layout.addRow("Worst Case SCA:", self.sca_input)

        self.packing_input = _packing_combo()
        self.form_layout.addRow("Packing:", self.packing_input)

        self.framing_input = _framing_combo()
        self.form_layout.addRow("Framing:", self.framing_input)

        self.build_table()

        self.form_layout.addRow("", _hint(
            "Qualification form: the air schedule is given rather than derived. "
            "For ordinary use prefer LE Set CIG Parameters, which lets the "
            "controller pick NSE/BN/FT from the latency and RTN targets."))

    def _update_iso_ms(self) -> None:
        self.iso_ms_label.setText(f"= {self.iso_interval_input.value() * 1.25:.2f} ms")

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetCigParametersTest(
            cig_id=self.cig_id_input.value(),
            sdu_interval_c_to_p=self.sdu_c_input.value(),
            sdu_interval_p_to_c=self.sdu_p_input.value(),
            ft_c_to_p=self.ft_c_input.value(),
            ft_p_to_c=self.ft_p_input.value(),
            iso_interval=self.iso_interval_input.value(),
            worst_case_sca=self.sca_input.currentData(),
            packing=self.packing_input.currentData(),
            framing=self.framing_input.currentData(),
            cis_params=self.table_rows(),
        )


class LeCreateCisUI(_ArrayTableUI):
    """UI for LE Create CIS (0x2063)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_CIS)
    NAME = "LE Create CIS"

    TABLE_LABEL = "CIS / ACL pairs:"
    TABLE_COLUMNS = (("CIS Handle", 0x0060), ("ACL Handle", 0x0040))

    def setup_ui(self):
        super().setup_ui()
        self.build_table()
        self.form_layout.addRow("", _hint(
            "CIS handles come from the LE Set CIG Parameters Command Complete; "
            "the ACL handle is the existing connection each stream rides on. "
            "Central only -- a peripheral answers LE CIS Request instead. "
            "Answers with Command Status; each stream then reports its own "
            "LE CIS Established."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCreateCis(
            cis_connections=self.table_rows())


class LeRemoveCigUI(HCICmdUI):
    """UI for LE Remove CIG (0x2064)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_CIG)
    NAME = "LE Remove CIG"

    def setup_ui(self):
        super().setup_ui()
        self.cig_id_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("CIG ID:", self.cig_id_input)
        self.form_layout.addRow("", _hint(
            "Every CIS in the group has to be disconnected first, or the "
            "controller answers Command Disallowed."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeRemoveCig(self.cig_id_input.value())


class LeAcceptCisRequestUI(HCICmdUI):
    """UI for LE Accept CIS Request (0x2065)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ACCEPT_CIS_REQUEST)
    NAME = "LE Accept CIS Request"

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x0000, 0x0EFF, 0x0060,
                                  "CIS handle from the LE CIS Request event")
        self.form_layout.addRow("CIS Handle:", self.handle_input)
        self.form_layout.addRow("", _hint(
            "Peripheral side. Use the CIS connection handle from the event, "
            "not the ACL handle."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeAcceptCisRequest(self.handle_input.value())


class LeRejectCisRequestUI(HCICmdUI):
    """UI for LE Reject CIS Request (0x2066)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REJECT_CIS_REQUEST)
    NAME = "LE Reject CIS Request"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0060)
        self.form_layout.addRow("CIS Handle:", self.handle_input)

        self.reason_input = QComboBox()
        for label, value in (
                ("Remote user terminated (0x13)", 0x13),
                ("Remote device low resources (0x14)", 0x14),
                ("Remote device powering off (0x15)", 0x15),
                ("Unacceptable connection parameters (0x3B)", 0x3B),
                ("Unsupported remote feature (0x1A)", 0x1A)):
            self.reason_input.addItem(label, value)
        self.form_layout.addRow("Reason:", self.reason_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeRejectCisRequest(
            self.handle_input.value(), self.reason_input.currentData())


# =================================================================== BIG / BIS

class _BigCommonUI(HCICmdUI):
    """Fields shared by the two Create BIG forms."""

    def add_common_head(self) -> None:
        self.big_handle_input = _spin(0x00, 0xEF, 0x00, "Identifies the BIG")
        self.form_layout.addRow("BIG Handle:", self.big_handle_input)

        self.adv_handle_input = _spin(0x00, 0xEF, 0x00,
                                      "Advertising set carrying the periodic "
                                      "train this BIG hangs off")
        self.form_layout.addRow("Advertising Handle:", self.adv_handle_input)

        self.num_bis_input = _spin(1, 31, 1, "Streams in the group")
        self.form_layout.addRow("Number of BIS:", self.num_bis_input)

        self.sdu_interval_input = _spin(255, 0x0FFFFF, 10000, "", " us")
        self.form_layout.addRow("SDU Interval:", self.sdu_interval_input)

    def add_common_tail(self) -> None:
        self.phy_input = _phy_combo()
        self.form_layout.addRow("PHY:", self.phy_input)

        self.packing_input = _packing_combo()
        self.form_layout.addRow("Packing:", self.packing_input)

        self.framing_input = _framing_combo()
        self.form_layout.addRow("Framing:", self.framing_input)

        self.encryption_input = QCheckBox("Encrypt the BIG")
        self.encryption_input.stateChanged.connect(
            lambda: self.broadcast_code_input.setEnabled(
                self.encryption_input.isChecked()))
        self.form_layout.addRow("Encryption:", self.encryption_input)

        self.broadcast_code_input = QLineEdit()
        self.broadcast_code_input.setPlaceholderText(
            "16-byte broadcast code, hex; short values are zero-padded")
        self.broadcast_code_input.setEnabled(False)
        self.form_layout.addRow("Broadcast Code:", self.broadcast_code_input)

        self.form_layout.addRow("", _hint(
            "The advertising set must already have periodic advertising "
            "configured and enabled -- receivers find the BIG through the "
            "BIGInfo in that periodic train, so without it nothing can sync."))

    def broadcast_code(self) -> bytes:
        code = _hex_bytes(self.broadcast_code_input.text(), "broadcast code")
        if len(code) > 16:
            raise ValueError(f"broadcast code is {len(code)} bytes; 16 is the maximum")
        return code.ljust(16, b"\x00")


class LeCreateBigUI(_BigCommonUI):
    """UI for LE Create BIG (0x2067)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_BIG)
    NAME = "LE Create BIG"

    def setup_ui(self):
        super().setup_ui()
        self.add_common_head()

        self.max_sdu_input = _spin(1, 0x0FFF, 40, "Largest SDU, in bytes")
        self.form_layout.addRow("Max SDU:", self.max_sdu_input)

        self.latency_input = _spin(5, 4000, 10, "Max transport latency", " ms")
        self.form_layout.addRow("Max Transport Latency:", self.latency_input)

        self.rtn_input = _spin(0, 30, 2, "Retransmission count target")
        self.form_layout.addRow("RTN:", self.rtn_input)

        self.add_common_tail()

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCreateBig(
            big_handle=self.big_handle_input.value(),
            adv_handle=self.adv_handle_input.value(),
            num_bis=self.num_bis_input.value(),
            sdu_interval=self.sdu_interval_input.value(),
            max_sdu=self.max_sdu_input.value(),
            max_transport_latency=self.latency_input.value(),
            rtn=self.rtn_input.value(),
            phy=self.phy_input.currentData(),
            packing=self.packing_input.currentData(),
            framing=self.framing_input.currentData(),
            encryption=self.encryption_input.isChecked(),
            broadcast_code=self.broadcast_code(),
        )


class LeCreateBigTestUI(_BigCommonUI):
    """UI for LE Create BIG Test (0x2068)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_BIG_TEST)
    NAME = "LE Create BIG Test"

    def setup_ui(self):
        super().setup_ui()
        self.add_common_head()

        self.iso_interval_input = _spin(4, 0x0C80, 8,
                                        "ISO interval in 1.25 ms units")
        self.form_layout.addRow("ISO Interval:", self.iso_interval_input)
        self.iso_ms_label = _hint("")
        self.iso_interval_input.valueChanged.connect(self._update_iso_ms)
        self.form_layout.addRow("", self.iso_ms_label)
        self._update_iso_ms()

        self.nse_input = _spin(1, 31, 1, "Subevents per BIS per ISO interval")
        self.form_layout.addRow("NSE:", self.nse_input)

        self.max_sdu_input = _spin(1, 0x0FFF, 40, "", " bytes")
        self.form_layout.addRow("Max SDU:", self.max_sdu_input)

        self.max_pdu_input = _spin(0, 251, 40, "", " bytes")
        self.form_layout.addRow("Max PDU:", self.max_pdu_input)

        self.add_common_tail()

        self.bn_input = _spin(1, 7, 1, "Burst number -- new payloads per interval")
        self.form_layout.addRow("BN:", self.bn_input)

        self.irc_input = _spin(1, 15, 1, "Immediate repetition count")
        self.form_layout.addRow("IRC:", self.irc_input)

        self.pto_input = _spin(0, 15, 0, "Pre-transmission offset")
        self.form_layout.addRow("PTO:", self.pto_input)

        self.form_layout.addRow("", _hint(
            "NSE must be a multiple of BN, and NSE / BN is normally IRC plus "
            "the pre-transmissions. Qualification form -- prefer LE Create BIG "
            "for ordinary use."))

    def _update_iso_ms(self) -> None:
        self.iso_ms_label.setText(f"= {self.iso_interval_input.value() * 1.25:.2f} ms")

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeCreateBigTest(
            big_handle=self.big_handle_input.value(),
            adv_handle=self.adv_handle_input.value(),
            num_bis=self.num_bis_input.value(),
            sdu_interval=self.sdu_interval_input.value(),
            iso_interval=self.iso_interval_input.value(),
            nse=self.nse_input.value(),
            max_sdu=self.max_sdu_input.value(),
            max_pdu=self.max_pdu_input.value(),
            phy=self.phy_input.currentData(),
            packing=self.packing_input.currentData(),
            framing=self.framing_input.currentData(),
            bn=self.bn_input.value(),
            irc=self.irc_input.value(),
            pto=self.pto_input.value(),
            encryption=self.encryption_input.isChecked(),
            broadcast_code=self.broadcast_code(),
        )


class LeTerminateBigUI(HCICmdUI):
    """UI for LE Terminate BIG (0x2069)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.TERMINATE_BIG)
    NAME = "LE Terminate BIG"

    def setup_ui(self):
        super().setup_ui()

        self.big_handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("BIG Handle:", self.big_handle_input)

        self.reason_input = QComboBox()
        for label, value in (("Terminated by local host (0x16)", 0x16),
                             ("Remote user terminated (0x13)", 0x13),
                             ("Remote device powering off (0x15)", 0x15)):
            self.reason_input.addItem(label, value)
        self.form_layout.addRow("Reason:", self.reason_input)

        self.form_layout.addRow("", _hint(
            "Transmitter side. Receivers use LE BIG Terminate Sync instead."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeTerminateBig(
            self.big_handle_input.value(), self.reason_input.currentData())


class LeBigCreateSyncUI(HCICmdUI):
    """UI for LE BIG Create Sync (0x206A)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.BIG_CREATE_SYNC)
    NAME = "LE BIG Create Sync"

    def setup_ui(self):
        super().setup_ui()

        self.big_handle_input = _spin(0x00, 0xEF, 0x00,
                                      "Handle to give the synced BIG locally")
        self.form_layout.addRow("BIG Handle:", self.big_handle_input)

        self.sync_handle_input = _spin(0x0000, 0x0EFF, 0x0000,
                                       "Sync handle from LE Periodic "
                                       "Advertising Sync Established")
        self.form_layout.addRow("Sync Handle:", self.sync_handle_input)

        self.encryption_input = QCheckBox("The BIG is encrypted")
        self.encryption_input.stateChanged.connect(
            lambda: self.broadcast_code_input.setEnabled(
                self.encryption_input.isChecked()))
        self.form_layout.addRow("Encryption:", self.encryption_input)

        self.broadcast_code_input = QLineEdit()
        self.broadcast_code_input.setPlaceholderText(
            "16-byte broadcast code, hex; short values are zero-padded")
        self.broadcast_code_input.setEnabled(False)
        self.form_layout.addRow("Broadcast Code:", self.broadcast_code_input)

        self.mse_input = _spin(0, 31, 0,
                               "Max subevents to receive per interval; "
                               "0 = the controller decides")
        self.form_layout.addRow("MSE:", self.mse_input)

        self.timeout_input = _spin(0x000A, 0x4000, 100,
                                   "BIG sync timeout in 10 ms units")
        self.form_layout.addRow("BIG Sync Timeout:", self.timeout_input)
        self.timeout_label = _hint("")
        self.timeout_input.valueChanged.connect(self._update_timeout)
        self.form_layout.addRow("", self.timeout_label)
        self._update_timeout()

        self.bis_input = QLineEdit("1")
        self.bis_input.setPlaceholderText("Comma-separated BIS indices, e.g. 1,2")
        self.bis_input.setToolTip("Which streams to receive; numbered from 1")
        self.form_layout.addRow("BIS Indices:", self.bis_input)

        self.form_layout.addRow("", _hint(
            "Receiver side. A periodic sync to the broadcaster has to exist "
            "first -- its sync handle is what identifies the BIG."))

    def _update_timeout(self) -> None:
        self.timeout_label.setText(f"= {self.timeout_input.value() * 10} ms")

    def validate_parameters(self) -> bool:
        text = self.bis_input.text().replace(" ", "")
        if not text:
            raise ValueError("at least one BIS index is required")
        try:
            indices = [int(part, 0) for part in text.split(",") if part]
        except ValueError:
            raise ValueError(f"BIS indices are not a comma-separated list of "
                             f"numbers: {self.bis_input.text()!r}")

        code = _hex_bytes(self.broadcast_code_input.text(), "broadcast code")
        if len(code) > 16:
            raise ValueError(f"broadcast code is {len(code)} bytes; 16 is the maximum")

        self._cmd_instance = le_cmds.LeBigCreateSync(
            big_handle=self.big_handle_input.value(),
            sync_handle=self.sync_handle_input.value(),
            encryption=self.encryption_input.isChecked(),
            broadcast_code=code.ljust(16, b"\x00"),
            mse=self.mse_input.value(),
            big_sync_timeout=self.timeout_input.value(),
            bis_indices=indices,
        )


class LeBigTerminateSyncUI(HCICmdUI):
    """UI for LE BIG Terminate Sync (0x206B)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.BIG_TERMINATE_SYNC)
    NAME = "LE BIG Terminate Sync"

    def setup_ui(self):
        super().setup_ui()
        self.big_handle_input = _spin(0x00, 0xEF, 0x00)
        self.form_layout.addRow("BIG Handle:", self.big_handle_input)
        self.form_layout.addRow("", _hint(
            "Receiver side -- stops receiving a BIG this device synced to."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeBigTerminateSync(
            self.big_handle_input.value())


# ============================================================== ISO data paths

class LeSetupIsoDataPathUI(HCICmdUI):
    """UI for LE Setup ISO Data Path (0x206D)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SETUP_ISO_DATA_PATH)
    NAME = "LE Setup ISO Data Path"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0060,
                                  "CIS or BIS connection handle")
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.direction_input = QComboBox()
        self.direction_input.addItem("Input (host -> controller, TX)",
                                     int(le_cmds.DataPathDirection.INPUT))
        self.direction_input.addItem("Output (controller -> host, RX)",
                                     int(le_cmds.DataPathDirection.OUTPUT))
        self.form_layout.addRow("Data Path Direction:", self.direction_input)

        self.path_id_input = _spin(0x00, 0xFF, 0x00,
                                   "0 = HCI transport, 1..254 = vendor path, "
                                   "255 = disabled")
        self.form_layout.addRow("Data Path ID:", self.path_id_input)

        self.coding_input = QComboBox()
        for coding in le_cmds.CodingFormat:
            self.coding_input.addItem(
                f"{coding.name.replace('_', ' ').title()} (0x{int(coding):02X})",
                int(coding))
        self.coding_input.setCurrentIndex(
            self.coding_input.findData(int(le_cmds.CodingFormat.TRANSPARENT)))
        self.form_layout.addRow("Coding Format:", self.coding_input)

        self.company_input = _spin(0x0000, 0xFFFF, 0x0000,
                                   "Only meaningful for a vendor coding format")
        self.form_layout.addRow("Company ID:", self.company_input)

        self.vendor_codec_input = _spin(0x0000, 0xFFFF, 0x0000)
        self.form_layout.addRow("Vendor Codec ID:", self.vendor_codec_input)

        self.delay_input = _spin(0, 4000000, 0,
                                 "Controller delay in microseconds", " us")
        self.form_layout.addRow("Controller Delay:", self.delay_input)

        self.codec_config_input = QLineEdit()
        self.codec_config_input.setPlaceholderText("Codec configuration, hex "
                                                   "(optional)")
        self.form_layout.addRow("Codec Configuration:", self.codec_config_input)

        self.form_layout.addRow("", _hint(
            "One command per direction. A direction that is never set up "
            "carries nothing -- the usual reason a stream establishes but no "
            "data ever flows. Use Data Path ID 0 and Transparent when the host "
            "sends or receives the ISO data itself over HCI."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetupIsoDataPath(
            connection_handle=self.handle_input.value(),
            data_path_direction=self.direction_input.currentData(),
            data_path_id=self.path_id_input.value(),
            coding_format=self.coding_input.currentData(),
            company_id=self.company_input.value(),
            vendor_codec_id=self.vendor_codec_input.value(),
            controller_delay=self.delay_input.value(),
            codec_configuration=_hex_bytes(self.codec_config_input.text(),
                                           "codec configuration"),
        )


class LeRemoveIsoDataPathUI(HCICmdUI):
    """UI for LE Remove ISO Data Path (0x206E)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_ISO_DATA_PATH)
    NAME = "LE Remove ISO Data Path"

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0060)
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.input_check = QCheckBox("Input (host -> controller)")
        self.input_check.setChecked(True)
        self.input_check.stateChanged.connect(self._update_summary)
        self.form_layout.addRow("Directions:", self.input_check)

        self.output_check = QCheckBox("Output (controller -> host)")
        self.output_check.setChecked(True)
        self.output_check.stateChanged.connect(self._update_summary)
        self.form_layout.addRow("", self.output_check)

        self.summary_label = _hint("")
        self.form_layout.addRow("Value:", self.summary_label)
        self._update_summary()

        self.form_layout.addRow("", _hint(
            "Unlike Setup, this field is a bitmap, so both directions can be "
            "removed in one command."))

    def _value(self) -> int:
        value = 0
        if self.input_check.isChecked():
            value |= int(le_cmds.DataPathDirectionMask.INPUT)
        if self.output_check.isChecked():
            value |= int(le_cmds.DataPathDirectionMask.OUTPUT)
        return value

    def _update_summary(self) -> None:
        self.summary_label.setText(f"0x{self._value():02X}")

    def validate_parameters(self) -> bool:
        value = self._value()
        if not value:
            raise ValueError("select at least one direction to remove")
        self._cmd_instance = le_cmds.LeRemoveIsoDataPath(
            self.handle_input.value(), value)


# =============================================================== ISO test mode

class _IsoTestUI(HCICmdUI):
    """Shared dialog for the two ISO test-mode start commands."""

    COMMAND = None

    def setup_ui(self):
        super().setup_ui()

        self.handle_input = _spin(0x0000, 0x0EFF, 0x0060,
                                  "CIS or BIS connection handle")
        self.form_layout.addRow("Connection Handle:", self.handle_input)

        self.payload_input = _payload_type_combo()
        self.form_layout.addRow("Payload Type:", self.payload_input)

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(self.handle_input.value(),
                                          self.payload_input.currentData())


class LeIsoTransmitTestUI(_IsoTestUI):
    """UI for LE ISO Transmit Test (0x206F)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_TRANSMIT_TEST)
    NAME = "LE ISO Transmit Test"
    COMMAND = le_cmds.LeIsoTransmitTest

    def setup_ui(self):
        super().setup_ui()
        self.form_layout.addRow("", _hint(
            "The controller generates the payloads itself, so no ISO data "
            "crosses HCI while this runs. End it with LE ISO Test End."))


class LeIsoReceiveTestUI(_IsoTestUI):
    """UI for LE ISO Receive Test (0x2070)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_RECEIVE_TEST)
    NAME = "LE ISO Receive Test"
    COMMAND = le_cmds.LeIsoReceiveTest

    def setup_ui(self):
        super().setup_ui()
        self.form_layout.addRow("", _hint(
            "The payload type must match what the transmitter is sending, or "
            "every SDU counts as failed. Read the tally with LE ISO Read Test "
            "Counters."))


class _IsoHandleUI(HCICmdUI):
    """Shared dialog for the ISO commands whose only parameter is a handle."""

    COMMAND = None
    HANDLE_LABEL = "Connection Handle:"
    HANDLE_TIP = "CIS or BIS connection handle"
    HINT = ""

    def setup_ui(self):
        super().setup_ui()
        self.handle_input = _spin(0x0000, 0x0EFF, 0x0060, self.HANDLE_TIP)
        self.form_layout.addRow(self.HANDLE_LABEL, self.handle_input)
        if self.HINT:
            self.form_layout.addRow("", _hint(self.HINT))

    def validate_parameters(self) -> bool:
        self._cmd_instance = self.COMMAND(self.handle_input.value())


class LeIsoReadTestCountersUI(_IsoHandleUI):
    """UI for LE ISO Read Test Counters (0x2071)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_READ_TEST_COUNTERS)
    NAME = "LE ISO Read Test Counters"
    COMMAND = le_cmds.LeIsoReadTestCounters
    HINT = ("Returns received / missed / failed SDU counts. Only meaningful "
            "while a receive test is running.")


class LeIsoTestEndUI(_IsoHandleUI):
    """UI for LE ISO Test End (0x2072)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_TEST_END)
    NAME = "LE ISO Test End"
    COMMAND = le_cmds.LeIsoTestEnd
    HINT = "Stops a transmit or receive test and returns the final counters."


class LeReadIsoTxSyncUI(_IsoHandleUI):
    """UI for LE Read ISO TX Sync (0x2060)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_ISO_TX_SYNC)
    NAME = "LE Read ISO TX Sync"
    COMMAND = le_cmds.LeReadIsoTxSync
    HINT = ("Sequence number and TX timestamp of the most recent SDU -- what a "
            "host uses to align its audio clock to the controller's.")


class LeReadIsoLinkQualityUI(_IsoHandleUI):
    """UI for LE Read ISO Link Quality (0x2074)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_ISO_LINK_QUALITY)
    NAME = "LE Read ISO Link Quality"
    COMMAND = le_cmds.LeReadIsoLinkQuality
    HINT = "Per-stream CRC failures, unreceived and missed packet counters."


class LeRequestPeerScaUI(_IsoHandleUI):
    """UI for LE Request Peer SCA (0x206C)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REQUEST_PEER_SCA)
    NAME = "LE Request Peer SCA"
    COMMAND = le_cmds.LeRequestPeerSca
    HANDLE_LABEL = "ACL Connection Handle:"
    HANDLE_TIP = "The ACL link to ask, not a CIS handle"
    HINT = ("Worth doing before setting up a CIG: the group takes the worst "
            "case SCA, and guessing pessimistically costs airtime. The answer "
            "arrives as LE Request Peer SCA Complete.")

    def setup_ui(self):
        super().setup_ui()
        self.handle_input.setValue(0x0040)


class LeSetHostFeatureUI(HCICmdUI):
    """UI for LE Set Host Feature (0x2073)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_HOST_FEATURE)
    NAME = "LE Set Host Feature"

    def setup_ui(self):
        super().setup_ui()

        self.bit_input = QComboBox()
        for feature in le_cmds.HostFeatureBit:
            label = feature.name.replace("_", " ").title()
            self.bit_input.addItem(f"{int(feature)}: {label}", int(feature))
        self.bit_input.setEditable(False)
        self.form_layout.addRow("Feature Bit:", self.bit_input)

        self.value_input = QCheckBox("Enable the feature")
        self.value_input.setChecked(True)
        self.form_layout.addRow("Bit Value:", self.value_input)

        self.form_layout.addRow("", _hint(
            "Bit 32 (Connected Isochronous Streams) has to be set before the "
            "controller accepts any CIG command. Only accepted while there are "
            "no connections, so send it during init."))

    def validate_parameters(self) -> bool:
        self._cmd_instance = le_cmds.LeSetHostFeature(
            bit_number=self.bit_input.currentData(),
            bit_value=1 if self.value_input.isChecked() else 0,
        )


for _cls in (LeReadIsoTxSyncUI,
             LeSetCigParametersUI,
             LeSetCigParametersTestUI,
             LeCreateCisUI,
             LeRemoveCigUI,
             LeAcceptCisRequestUI,
             LeRejectCisRequestUI,
             LeCreateBigUI,
             LeCreateBigTestUI,
             LeTerminateBigUI,
             LeBigCreateSyncUI,
             LeBigTerminateSyncUI,
             LeRequestPeerScaUI,
             LeSetupIsoDataPathUI,
             LeRemoveIsoDataPathUI,
             LeIsoTransmitTestUI,
             LeIsoReceiveTestUI,
             LeIsoReadTestCountersUI,
             LeIsoTestEndUI,
             LeSetHostFeatureUI,
             LeReadIsoLinkQualityUI):
    register_command_ui(_cls)
del _cls


__all__ = [
    'LeReadIsoTxSyncUI',
    'LeSetCigParametersUI',
    'LeSetCigParametersTestUI',
    'LeCreateCisUI',
    'LeRemoveCigUI',
    'LeAcceptCisRequestUI',
    'LeRejectCisRequestUI',
    'LeCreateBigUI',
    'LeCreateBigTestUI',
    'LeTerminateBigUI',
    'LeBigCreateSyncUI',
    'LeBigTerminateSyncUI',
    'LeRequestPeerScaUI',
    'LeSetupIsoDataPathUI',
    'LeRemoveIsoDataPathUI',
    'LeIsoTransmitTestUI',
    'LeIsoReceiveTestUI',
    'LeIsoReadTestCountersUI',
    'LeIsoTestEndUI',
    'LeSetHostFeatureUI',
    'LeReadIsoLinkQualityUI',
]
