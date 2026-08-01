"""
Base classes for event windows.

An event window is bound to a parsed event object (`HciEvtBasePacket`), not to
raw bytes -- parsing already happened in `hci.evt`, and doing it twice is how the
two layers drift apart. Each window receives every event it is registered for
via `update_event()`.

Three flavours, by how noisy the event is:

* **one-shot**   -- Connection Complete, Disconnection Complete. The window shows
  the latest event; a repeat replaces the contents.
* **aggregating** -- advertising reports, inquiry results. Dozens per second, so
  they accumulate rows in one table instead of spawning windows.
* **action-required** -- Connection Request. Pops immediately and offers the
  buttons that send the answering command.

`AUTO_POPUP` decides whether the factory opens a window on arrival;
`ACTION_REQUIRED` implies it.
"""

from __future__ import annotations

from typing import Any, ClassVar, Optional, Sequence, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..hci_base_ui import HCIEvtBaseUI


def fmt_value(value: Any) -> str:
    """Render a parameter value for display."""
    if isinstance(value, (bytes, bytearray)):
        return value.hex(' ') if value else "(empty)"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"0x{value:02X} ({value})" if value <= 0xFF else f"0x{value:04X} ({value})"
    if isinstance(value, (list, tuple)):
        return f"{len(value)} item(s)"
    return str(value)


def addr_str(raw: Any) -> str:
    """BD_ADDR bytes (big-endian, as the event layer stores them) to text."""
    if isinstance(raw, (bytes, bytearray)) and len(raw) == 6:
        return ":".join(f"{b:02X}" for b in raw)
    return str(raw)


class HCIEvtUI(HCIEvtBaseUI):
    """Base window for a received HCI event."""

    # ((event_code, sub_event_code), ...) this window handles. sub is None for
    # everything that is not an LE meta event.
    EVENT_KEYS: ClassVar[Sequence[Tuple[int, Optional[int]]]] = ()

    # Windows sharing a WINDOW_KEY share one instance -- that is how the three
    # inquiry-result event codes end up in a single results table.
    WINDOW_KEY: ClassVar[Optional[str]] = None

    AUTO_POPUP: ClassVar[bool] = False
    ACTION_REQUIRED: ClassVar[bool] = False

    NAME: ClassVar[str] = "HCI Event"

    def __init__(self, title: str = "HCI Event", parent=None, session=None):
        # Set before super(): setup_ui() runs inside HciBaseUI.__init__.
        self.session = session
        self.event_count = 0
        super().__init__(title, parent)

    # ---------------------------------------------------------------- layout

    def setup_ui(self):
        super().setup_ui()

        self.param_group = QGroupBox("Event Parameters")
        self.form_layout = QFormLayout()
        self.param_group.setLayout(self.form_layout)
        self.content_layout.addWidget(self.param_group)

        self.build_content()

        # An event window has nothing to cancel.
        self.ok_button.setText("Close")
        self.cancel_button.setVisible(False)

    def build_content(self) -> None:
        """Subclass hook: add widgets to `self.form_layout`. Default: nothing."""

    # ----------------------------------------------------------------- feed

    def update_event(self, event) -> None:
        """
        Called for every matching event. Default renders the parameter dict.

        Never raises: this runs off the receive path, and a display bug must not
        take the session down with it.
        """
        if self._is_destroyed:
            return
        self.event_instance = event
        self.event_count += 1
        try:
            self.render(event)
        except Exception as exc:            # noqa: BLE001 - display must not kill RX
            self.log_error(f"could not render event: {exc}")

    def render(self, event) -> None:
        """Subclass hook: show `event`. Default is a name/value table."""
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        for key, value in (event.params or {}).items():
            self.form_layout.addRow(f"{key}:", QLabel(fmt_value(value)))

    # ------------------------------------------------------------- helpers

    def display_event_details(self):
        """Kept for the older `set_event_instance` path."""
        if self.event_instance is not None:
            self.render(self.event_instance)

    def send(self, command) -> bool:
        """Send an answering command through the session, if we have one."""
        if self.session is None:
            self.log_error("no session attached -- cannot send the reply")
            return False
        try:
            self.session.send(command)
            return True
        except Exception as exc:            # noqa: BLE001 - surfaced in the window
            self.log_error(f"send failed: {exc}")
            return False


class GenericEventUI(HCIEvtUI):
    """Fallback window: parameter table plus the decoded one-liner."""

    NAME = "HCI Event"

    def build_content(self):
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumHeight(80)
        self.content_layout.addWidget(self.summary)

    def render(self, event):
        super().render(event)
        self.summary.setPlainText(str(event))
        self.setWindowTitle(f"{getattr(event, 'NAME', 'Event')} - {self.title}")


class AggregatingEvtUI(HCIEvtUI):
    """
    Base for events that arrive in floods.

    Rows accumulate in one table, keyed so a repeat updates its row instead of
    appending a duplicate -- otherwise a 30-second scan produces thousands of
    rows for the same three devices.
    """

    COLUMNS: ClassVar[Sequence[str]] = ()
    KEY_COLUMN: ClassVar[int] = 0
    STRETCH_COLUMN: ClassVar[int] = 1

    def build_content(self):
        # The parameter form is not useful here; the table replaces it.
        self.param_group.setVisible(False)

        self.counter_label = QLabel("0 events, 0 rows")
        self.counter_label.setStyleSheet("color: gray;")
        self.content_layout.addWidget(self.counter_label)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(list(self.COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        if len(self.COLUMNS) > self.STRETCH_COLUMN:
            self.table.horizontalHeader().setSectionResizeMode(
                self.STRETCH_COLUMN, QHeaderView.Stretch)
        self.content_layout.addWidget(self.table, 1)

        self._rows: dict = {}

    def rows_for(self, event) -> Sequence[Sequence[str]]:
        """Subclass hook: turn one event into zero or more table rows."""
        return ()

    def render(self, event):
        for cells in self.rows_for(event):
            self._upsert(list(cells))
        self.counter_label.setText(
            f"{self.event_count} events, {self.table.rowCount()} rows")

    def _upsert(self, cells) -> None:
        key = cells[self.KEY_COLUMN]
        row = self._rows.get(key)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._rows[key] = row
        for column, text in enumerate(cells):
            self.table.setItem(row, column, QTableWidgetItem(str(text)))


__all__ = [
    "HCIEvtUI",
    "GenericEventUI",
    "AggregatingEvtUI",
    "fmt_value",
    "addr_str",
]
