"""
Qt marshalling for transport callbacks.

Transport callbacks fire on the I/O thread. Qt widgets may only be touched from
the thread that owns them. This bridge sits between the two: it subscribes to the
transport on the I/O thread and re-emits as Qt signals with a queued connection,
so slots run on the main thread.

Nothing else in `transports/` imports Qt -- keeping the dependency isolated here
is what lets the transport layer and its tests run headless.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .base_lib import TransportEvent, TransportState
from .transport import Transport


class QtTransportBridge(QObject):
    """
    Re-emits transport events as Qt signals on the receiving thread.

    Signals are emitted from the I/O thread; because `QtTransportBridge` lives in
    the main thread, Qt's automatic connection type queues them and the slots run
    on the main thread. That is the whole point of this class.
    """

    packet_received = pyqtSignal(bytes)   # one complete H4 packet
    packet_sent = pyqtSignal(bytes)
    raw_rx = pyqtSignal(bytes)
    raw_tx = pyqtSignal(bytes)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(object)
    state_changed = pyqtSignal(object, object)   # (old, new) TransportState

    def __init__(self, transport: Transport, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.transport = transport
        self._subscribed = False
        self.attach()

    def attach(self) -> None:
        if self._subscribed:
            return
        t = self.transport
        t.add_callback(TransportEvent.READ, self._on_packet)
        t.add_callback(TransportEvent.WRITE, self._on_written)
        t.add_callback(TransportEvent.RAW_RX, self._on_raw_rx)
        t.add_callback(TransportEvent.RAW_TX, self._on_raw_tx)
        t.add_callback(TransportEvent.CONNECT, self._on_connect)
        t.add_callback(TransportEvent.DISCONNECT, self._on_disconnect)
        t.add_callback(TransportEvent.ERROR, self._on_error)
        t.add_callback(TransportEvent.STATE_CHANGED, self._on_state)
        self._subscribed = True

    def detach(self) -> None:
        if not self._subscribed:
            return
        t = self.transport
        for event, handler in (
            (TransportEvent.READ, self._on_packet),
            (TransportEvent.WRITE, self._on_written),
            (TransportEvent.RAW_RX, self._on_raw_rx),
            (TransportEvent.RAW_TX, self._on_raw_tx),
            (TransportEvent.CONNECT, self._on_connect),
            (TransportEvent.DISCONNECT, self._on_disconnect),
            (TransportEvent.ERROR, self._on_error),
            (TransportEvent.STATE_CHANGED, self._on_state),
        ):
            try:
                t.remove_callback(event, handler)
            except Exception:
                pass
        self._subscribed = False

    # -- I/O-thread side: do nothing but emit ------------------------------

    def _on_packet(self, packet: bytes) -> None:
        self.packet_received.emit(bytes(packet))

    def _on_written(self, data: bytes) -> None:
        self.packet_sent.emit(bytes(data))

    def _on_raw_rx(self, chunk: bytes) -> None:
        self.raw_rx.emit(bytes(chunk))

    def _on_raw_tx(self, chunk: bytes) -> None:
        self.raw_tx.emit(bytes(chunk))

    def _on_connect(self, *_args) -> None:
        self.connected.emit()

    def _on_disconnect(self, *_args) -> None:
        self.disconnected.emit()

    def _on_error(self, exc) -> None:
        self.error.emit(exc)

    def _on_state(self, old: TransportState, new: TransportState) -> None:
        self.state_changed.emit(old, new)


__all__ = ["QtTransportBridge"]
