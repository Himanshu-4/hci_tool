"""
Quick Connect -- the guided-procedure window.

Advertise, scan, connect and inquire without hand-building each HCI command.
It owns no transport of its own: it attaches to an HCI window's `HciSession`,
so the connection, the credit accounting and the connection table are shared
with the per-command view rather than duplicated.

Open Tools > HCI first to get a session; then Tools > Quick Connect to drive it.
"""

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMdiSubWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.hci_ui.hci_main_ui import HciMainUI
from ui.hci_ui.procedure_panel import ProcedurePanel


class QuickConnectWindow(QWidget):
    """Attaches a ProcedurePanel to a chosen HCI session."""

    # One window is plenty -- it can be re-pointed at any open session.
    _instance: Optional['QuickConnectWindow'] = None

    @classmethod
    def create_instance(cls, main_window: QMainWindow) -> 'QuickConnectWindow':
        """Open the window, or raise it if it is already up."""
        existing = cls._instance
        if existing is not None:
            try:
                existing.sub_window.show()
                existing.sub_window.raise_()
                existing.sub_window.activateWindow()
                existing.refresh_sessions()
                return existing
            except RuntimeError:
                # Qt deleted it out from under us; fall through and rebuild.
                cls._instance = None

        cls._instance = cls(main_window)
        return cls._instance

    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self._is_destroyed = False
        self._attached: Optional[HciMainUI] = None
        self.panel: Optional[ProcedurePanel] = None

        self._build_ui()
        self._build_subwindow()
        self.refresh_sessions()

    # ------------------------------------------------------------------ setup

    def _build_ui(self) -> None:
        self._root = QVBoxLayout(self)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("HCI session:"))

        self.session_combo = QComboBox()
        self.session_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.session_combo.currentIndexChanged.connect(self._on_session_chosen)
        source_row.addWidget(self.session_combo, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setToolTip("Re-scan for open HCI windows")
        # Swallow clicked()'s bool -- it would otherwise land in `ignore`.
        refresh_btn.clicked.connect(lambda: self.refresh_sessions())
        source_row.addWidget(refresh_btn)
        self._root.addLayout(source_row)

        self.hint_label = QLabel(
            "No HCI session is open. Use Tools > HCI to connect to a "
            "controller, then press Refresh.")
        self.hint_label.setWordWrap(True)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: gray; padding: 24px;")
        self._root.addWidget(self.hint_label, 1)

    def _build_subwindow(self) -> None:
        self.sub_window = QMdiSubWindow()
        self.sub_window.setWindowTitle("Quick Connect")
        self.sub_window.setWidget(self)
        self.sub_window.setWindowFlags(Qt.Window)
        self.sub_window.resize(560, 720)
        self.sub_window.setMinimumSize(420, 480)
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)
        self.sub_window.destroyed.connect(self._on_subwindow_destroyed)

        self.main_window.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        self.sub_window.raise_()
        self.sub_window.activateWindow()

    # ------------------------------------------------------------- attaching

    def refresh_sessions(self, ignore: Optional[HciMainUI] = None) -> None:
        """
        Repopulate the session list, keeping the current pick if it survives.

        `ignore` skips a window that is mid-teardown: it announces the closure
        before it clears its own session, so it still looks live here.
        """
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
            self.hint_label.setVisible(True)
            self.hint_label.setText(
                "No HCI session is open. Use Tools > HCI to connect to a "
                "controller, then press Refresh.")
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
        """Swap in a fresh panel bound to `instance`'s session."""
        self._detach()

        session = getattr(instance, 'session', None)
        if session is None:
            return

        self._attached = instance
        self.panel = ProcedurePanel(session)
        self.hint_label.setVisible(False)
        self._root.addWidget(self.panel, 1)

        # If that window closes, its session dies with it -- drop ours first.
        instance.session_closing.connect(self._on_session_closing)

        self.sub_window.setWindowTitle(f"Quick Connect - {instance.title}")

    def _detach(self) -> None:
        if self.panel is not None:
            try:
                self.panel.cleanup()
                self._root.removeWidget(self.panel)
                self.panel.setParent(None)
                self.panel.deleteLater()
            except RuntimeError:
                pass
            self.panel = None

        if self._attached is not None:
            try:
                self._attached.session_closing.disconnect(self._on_session_closing)
            except (TypeError, RuntimeError):
                pass
            self._attached = None

        try:
            self.sub_window.setWindowTitle("Quick Connect")
        except RuntimeError:
            pass

    def _on_session_closing(self, instance) -> None:
        """The attached HCI window is going away."""
        self._detach()
        self.refresh_sessions(ignore=instance)

    # -------------------------------------------------------------- teardown

    def _on_subwindow_destroyed(self, *_args) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._is_destroyed:
            return
        self._is_destroyed = True
        self._detach()
        if QuickConnectWindow._instance is self:
            QuickConnectWindow._instance = None


__all__ = ["QuickConnectWindow"]
