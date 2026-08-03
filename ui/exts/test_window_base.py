"""
Common shell for the profile test screens (SCO, LE ISO, HID, A2DP).

Each of them needs the same four things: a single instance in the MDI area, a
picker that attaches to an open `HciSession`, a way to send a command and log
its completion, and a log pane. That is all this provides -- the actual test
logic lives in the subclasses.

Threading: `HciSession` fires completions on the transport I/O thread, so
`log()` is safe to call from anywhere; it goes through a signal.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMdiSubWindow,
    QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.hci_ui.hci_main_ui import HciMainUI


class SessionTestWindow(QWidget):
    """Base for a test screen that drives one attached HCI session."""

    #: Subclasses override these.
    WINDOW_TITLE = "Test"
    WINDOW_SIZE = (720, 820)
    MIN_SIZE = (560, 520)

    _instance: Optional['SessionTestWindow'] = None

    # I/O thread -> Qt thread.
    _line = pyqtSignal(str)
    _connections_changed = pyqtSignal()

    @classmethod
    def create_instance(cls, main_window: QMainWindow) -> 'SessionTestWindow':
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

        self._build_shell()
        self.build_body(self._body_layout)

        self._line.connect(self._append_log)
        self._connections_changed.connect(self.on_connections_changed)

        self.refresh_sessions()

    # ----------------------------------------------------------------- shell

    def _build_shell(self) -> None:
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
        self.state_label = QLabel("not attached")
        self.state_label.setStyleSheet("color: gray;")
        source_row.addWidget(self.state_label)
        root.addLayout(source_row)

        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(body, 1)

        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setFont(QFont("Menlo", 10))
        log_layout.addWidget(self.log_view)
        # Capped, so the controls above keep the window's height rather than
        # being squeezed into a strip by an empty log.
        log_box.setMinimumHeight(110)
        log_box.setMaximumHeight(200)
        root.addWidget(log_box)

        self.sub_window = QMdiSubWindow()
        self.sub_window.setWindowTitle(self.WINDOW_TITLE)
        self.sub_window.setWidget(self)
        self.sub_window.setWindowFlags(Qt.Window)
        self.sub_window.resize(*self.WINDOW_SIZE)
        self.sub_window.setMinimumSize(*self.MIN_SIZE)
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)
        self.sub_window.destroyed.connect(lambda *_: self.cleanup())

        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        self.sub_window.raise_()
        self.sub_window.activateWindow()

    # -------------------------------------------------------- subclass hooks

    def build_body(self, layout: QVBoxLayout) -> None:
        """Add the screen's own widgets. Subclasses must implement."""

    def on_session_attached(self) -> None:
        """The session just became available."""

    def on_session_detached(self) -> None:
        """The session is about to go away."""

    def on_connections_changed(self) -> None:
        """A connection came up or went down (already on the Qt thread)."""

    # ------------------------------------------------------------- attaching

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
            self.state_label.setText("no HCI session -- open Tools > HCI")
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
        from hci.session.session import (
            EVT_CONNECTION_DOWN, EVT_CONNECTION_UP, EVT_ERROR, EVT_EVENT,
        )

        self._detach()
        session = getattr(instance, 'session', None)
        if session is None:
            return

        self._attached = instance
        self.session = session
        session.on(EVT_CONNECTION_UP, self._on_connection_up)
        session.on(EVT_CONNECTION_DOWN, self._on_connection_down)
        session.on(EVT_ERROR, self._on_error)
        session.on(EVT_EVENT, self._on_event)
        instance.session_closing.connect(self._on_session_closing)

        self.sub_window.setWindowTitle(f"{self.WINDOW_TITLE} - {instance.title}")
        self.state_label.setText("attached")
        self.log(f"= attached to {instance.title}")
        self.on_session_attached()
        self._connections_changed.emit()

    def _detach(self) -> None:
        from hci.session.session import (
            EVT_CONNECTION_DOWN, EVT_CONNECTION_UP, EVT_ERROR, EVT_EVENT,
        )

        session, self.session = self.session, None
        if session is not None:
            self.on_session_detached()
            for channel, handler in ((EVT_CONNECTION_UP, self._on_connection_up),
                                     (EVT_CONNECTION_DOWN, self._on_connection_down),
                                     (EVT_ERROR, self._on_error),
                                     (EVT_EVENT, self._on_event)):
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
            self.sub_window.setWindowTitle(self.WINDOW_TITLE)
            self.state_label.setText("not attached")
        except RuntimeError:
            pass

    def _on_session_closing(self, instance) -> None:
        self._detach()
        self.refresh_sessions(ignore=instance)

    # --------------------------------------------------------------- sending

    def send(self, builder: Callable, label: str,
             on_done: Optional[Callable] = None) -> bool:
        """
        Build and send one command, logging the completion.

        `builder` is a callable so a parameter error is raised here and shown in
        the log, rather than escaping from a button-click slot to the console.
        """
        if self.session is None:
            self.log("! no session attached")
            return False
        try:
            command = builder()
        except Exception as exc:            # noqa: BLE001 - user input error
            self.log(f"! {label}: {exc}")
            return False

        def _done(response, error) -> None:
            # I/O thread.
            if error is not None:
                self._line.emit(f"! {label}: {error}")
            else:
                status = None
                if response is not None:
                    status = getattr(response, 'params', {}).get('status')
                self._line.emit(f"< {label}: ok" if status in (0x00, None)
                                else f"! {label}: status 0x{status:02X}")
            if on_done is not None:
                try:
                    on_done(response, error)
                except Exception as exc:    # noqa: BLE001
                    self._line.emit(f"! {label} handler: {exc!r}")

        self.log(f"> {label}")
        try:
            self.session.send(command, on_complete=_done)
            return True
        except Exception as exc:            # noqa: BLE001
            self.log(f"! {label}: {exc}")
            return False

    def write_packet(self, raw: bytes) -> bool:
        """Put a data packet straight on the HCI transport, bypassing the queue."""
        if self.session is None:
            return False
        try:
            return bool(self.session.transport.write(raw))
        except Exception:
            return False

    def log(self, message: str) -> None:
        """Safe from any thread."""
        self._line.emit(message)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    # ------------------------------------------------- session observers (I/O)

    def _on_connection_up(self, info) -> None:
        self._line.emit(f"+ connected {info}")
        self._connections_changed.emit()

    def _on_connection_down(self, info, handle: int, reason: int) -> None:
        self._line.emit(f"- disconnected handle 0x{handle:04X} "
                        f"(reason 0x{reason:02X})")
        self._connections_changed.emit()

    def _on_error(self, message: str) -> None:
        self._line.emit(f"! {message}")

    def _on_event(self, event) -> None:
        """Subclasses override to watch for their own events."""

    # -------------------------------------------------------------- teardown

    def cleanup(self) -> None:
        if self._is_destroyed:
            return
        self._is_destroyed = True
        self.on_cleanup()
        self._detach()
        if type(self)._instance is self:
            type(self)._instance = None

    def on_cleanup(self) -> None:
        """Subclass hook, called before the session is detached."""


def connection_combo_items(session, link_type=None):
    """(label, handle) for each connection, optionally filtered by link type."""
    if session is None:
        return []
    items = []
    for info in session.connections.all():
        if link_type is not None and info.link_type is not link_type:
            continue
        items.append((f"0x{info.handle:04X}  {info.bd_addr}", info.handle))
    return items


__all__ = ["SessionTestWindow", "connection_combo_items"]
