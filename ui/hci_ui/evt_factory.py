"""
HCI Event Factory.

Owns the event windows for one session: decides which arriving events deserve a
window, creates and reuses those windows, and feeds each one the parsed event.

Two rules shape it:

* **Parsing happens once.** Events arrive already decoded from `HciSession`;
  the factory never re-parses bytes.
* **Widgets are only touched on the Qt thread.** Session callbacks run on the
  reactor/I-O thread, so everything crosses `_SessionBridge`, a QObject whose
  signal is delivered queued to the main thread.

Which events pop a window is deliberately curated (`AUTO_POPUP` on the UI
class): advertising reports and inquiry results aggregate into one live table,
Connection Request pops with Accept/Reject, and the rest stay in the log until
someone asks for them via `open_event_window()`.
"""

from __future__ import annotations

import traceback
import weakref
from typing import Dict, Optional, Type

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMdiSubWindow

from hci.session.session import EVT_COMMAND_SENT, EVT_EVENT

from .evts import get_event_ui_class, get_event_ui_class_for, window_key_of
from .evts.evt_baseui import HCIEvtUI

from transports.transport import Transport

# @todo : move this to a separate module for logging the events
from ui.exts.log_window import LogWindow


class _SessionBridge(QObject):
    """Re-emits session events on the Qt main thread."""

    event_received = pyqtSignal(object)
    command_sent = pyqtSignal(object)

    def __init__(self, session, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.session = session
        self._attached = False
        self.attach()

    def attach(self) -> None:
        if self._attached or self.session is None:
            return
        self.session.on(EVT_EVENT, self._on_event)
        self.session.on(EVT_COMMAND_SENT, self._on_command_sent)
        self._attached = True

    def detach(self) -> None:
        if not self._attached or self.session is None:
            return
        for channel, handler in ((EVT_EVENT, self._on_event),
                                 (EVT_COMMAND_SENT, self._on_command_sent)):
            try:
                self.session.off(channel, handler)
            except Exception:
                pass
        self._attached = False

    def _on_event(self, event) -> None:
        # I/O thread: emit and get out.
        self.event_received.emit(event)

    def _on_command_sent(self, command, _raw) -> None:
        self.command_sent.emit(command)


#MARK: Event factory
class HCIEventFactory:
    """Creates and feeds the event windows for one HCI session."""

    def __init__(self,
                 title: str,
                 parent_window: QMdiSubWindow,
                 transport: Optional[Transport] = None,
                 session=None):
        self.title = title
        self.transport = transport
        self.session = session
        self.parent = weakref.ref(parent_window) if parent_window else None
        self._is_destroyed = False

        # window key -> live window. Several event codes may share a key.
        self.event_windows: Dict[str, HCIEvtUI] = {}

        self._bridge: Optional[_SessionBridge] = None
        if session is not None:
            self._bridge = _SessionBridge(session)
            self._bridge.event_received.connect(self.handle_event)
            self._bridge.event_received.connect(self._log_rx)
            self._bridge.command_sent.connect(self._log_tx)

    def __del__(self):
        """Destructor to ensure all event windows are closed"""
        if not self._is_destroyed:
            self.cleanup()

    def cleanup(self):
        """Explicit cleanup method to be called before destruction"""
        if self._is_destroyed:
            return

        self._is_destroyed = True
        if self._bridge is not None:
            self._bridge.detach()
            self._bridge = None
        self.close_all_event_windows()
        self.remove_from_parent()

    def get_parent(self):
        """Safely get the parent window"""
        if self.parent is None or self._is_destroyed:
            return None
        return self.parent()   # weakref -- deref it, do not hand back the ref

    def __repr__(self):
        return f"<HCIEventFactory title={self.title}, windows={len(self.event_windows)}>"

    def __str__(self):
        return f"HCIEventFactory(title={self.title}, windows={len(self.event_windows)})"

    def __len__(self):
        """Return the number of event windows currently managed"""
        return len(self.event_windows)

    def __contains__(self, window_key: str) -> bool:
        """Check if an event window with the given key exists"""
        return window_key in self.event_windows

    def __getitem__(self, window_key: str) -> Optional[HCIEvtUI]:
        """Get an event window by its key"""
        return self.event_windows.get(window_key, None)

    #MARK: logging
    def _log_rx(self, event) -> None:
        """Every received event, decoded, in the log window."""
        try:
            LogWindow.info(f"{self.title} < {event}")
        except Exception:
            pass

    def _log_tx(self, command) -> None:
        """Every command the session sends, decoded, in the log window."""
        try:
            LogWindow.info(f"{self.title} > {command}")
        except Exception:
            pass

    #MARK: dispatch
    def handle_event(self, event) -> Optional[HCIEvtUI]:
        """
        Route one parsed event to its window.

        Returns the window it went to, or None when the event has no window
        class or is not one of the curated auto-popup events and none is open.
        """
        if self._is_destroyed or event is None:
            return None

        try:
            ui_class = get_event_ui_class_for(event)
            if ui_class is None:
                return None

            key = window_key_of(ui_class, (getattr(event, 'EVENT_CODE', 0),
                                           getattr(event, 'SUB_EVENT_CODE', None)))
            window = self.event_windows.get(key)

            if window is None:
                # Only curated events open a window by themselves. Everything
                # else is already in the log; opening a window per Command
                # Complete would bury the screen.
                if not (ui_class.AUTO_POPUP or ui_class.ACTION_REQUIRED):
                    return None
                window = self._create_window(ui_class, key)
                if window is None:
                    return None

            window.update_event(event)
            if ui_class.ACTION_REQUIRED:
                # A question the user has to answer -- put it in front.
                window.bring_to_front()
            return window
        except Exception as exc:            # noqa: BLE001 - never break the RX path
            print(f"Error handling event UI: {exc}")
            traceback.print_exc()
            return None

    #MARK: window control
    def open_event_window(self, event_code: int,
                          sub_event_code: Optional[int] = None) -> Optional[HCIEvtUI]:
        """Open (or raise) the window for an event code, on demand."""
        ui_class = get_event_ui_class(event_code, sub_event_code)
        if ui_class is None:
            return None
        key = window_key_of(ui_class, (event_code, sub_event_code))
        window = self.event_windows.get(key)
        if window is not None:
            window.bring_to_front()
            return window
        return self._create_window(ui_class, key)

    def _create_window(self, ui_class: Type[HCIEvtUI], key: str) -> Optional[HCIEvtUI]:
        parent = self.get_parent()
        try:
            window = ui_class(self.title, parent, self.session)
        except Exception as exc:            # noqa: BLE001
            print(f"Could not build event window {ui_class.__name__}: {exc}")
            traceback.print_exc()
            return None

        window.window_closing.connect(lambda *_: self.close_event_window(key))
        self.event_windows[key] = window

        self.position_window(window)
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def position_window(self, window: HCIEvtUI):
        """Position the window relative to the main window"""
        parent = self.get_parent()
        if parent:
            try:
                main_rect = parent.geometry()
                offset = 50 + (len(self.event_windows) * 30)
                window.move(main_rect.x() + offset, main_rect.y() + offset)
            except RuntimeError:
                # Parent window has been deleted, skip positioning
                pass

    def get_event_window(self, window_key: str) -> Optional[HCIEvtUI]:
        """Get an event window by its key"""
        return self.event_windows.get(window_key, None)

    def get_event_window_by_name(self, window_name: str) -> Optional[HCIEvtUI]:
        """Get an event window by its human-readable name"""
        for window in self.event_windows.values():
            try:
                if window.NAME == window_name:
                    return window
            except RuntimeError:
                continue
        return None

    def get_event_window_by_type(self, evt_type: Type[HCIEvtUI]) -> Optional[HCIEvtUI]:
        """Get an event window by its type"""
        for window in self.event_windows.values():
            if isinstance(window, evt_type):
                return window
        return None

    def get_all_event_windows(self) -> list:
        """Get all event windows"""
        return list(self.event_windows.values())

    def add_to_parent(self):
        """Add this factory to the parent window's event tracking"""
        parent = self.get_parent()
        if parent and hasattr(parent, 'add_event_factory'):
            try:
                parent.add_event_factory(self)
            except RuntimeError:
                # Parent has been deleted
                pass

    def remove_from_parent(self):
        """Remove this factory from the parent window's event tracking"""
        parent = self.get_parent()
        if parent and hasattr(parent, 'remove_event_factory'):
            try:
                parent.remove_event_factory(self)
            except RuntimeError:
                # Parent has been deleted, nothing to do
                pass

    def raise_all_windows(self):
        """Raise all event windows to the front"""
        for key, window in list(self.event_windows.items()):
            try:
                if window.isVisible():
                    window.raise_()
                    window.activateWindow()
            except RuntimeError:
                # Window has been deleted, remove from tracking
                self.event_windows.pop(key, None)

    def close_event_window(self, window_key: str):
        """Close a specific event window by its key"""
        window = self.event_windows.pop(window_key, None)
        if window is None:
            return
        try:
            window.close()
        except RuntimeError:
            # Window already deleted
            pass

    def close_all_event_windows(self):
        """Close all open event windows"""
        for window_key in list(self.event_windows.keys()):
            self.close_event_window(window_key)
        self.event_windows.clear()


__all__ = ["HCIEventFactory"]
