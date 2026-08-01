"""
Event windows for the BR/EDR link-control events.

The interesting one is `ConnectionRequestEventUI`: an incoming connection is a
question the controller is asking, and it will time out if nobody answers. That
window pops with Accept and Reject buttons wired to the real commands.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QComboBox, QLabel

from hci.evt.evt_codes import HciEventCode
from hci.cmd.link_controller import AcceptConnectionRequest, RejectConnectionRequest

from ..evt_baseui import AggregatingEvtUI, HCIEvtUI, addr_str
from .. import register_event_ui


_LINK_TYPES = {0x00: "SCO", 0x01: "ACL", 0x02: "eSCO"}


def _status_text(status: int) -> str:
    return "Success" if status == 0x00 else f"Error 0x{status:02X}"


@register_event_ui
class ConnectionRequestEventUI(HCIEvtUI):
    """Incoming BR/EDR connection -- needs an answer from the user."""

    EVENT_KEYS = ((HciEventCode.CONNECTION_REQUEST, None),)
    NAME = "Connection Request"
    AUTO_POPUP = True
    ACTION_REQUIRED = True

    def build_content(self):
        self.addr_label = QLabel("-")
        self.cod_label = QLabel("-")
        self.link_type_label = QLabel("-")
        self.form_layout.addRow("BD_ADDR:", self.addr_label)
        self.form_layout.addRow("Class of Device:", self.cod_label)
        self.form_layout.addRow("Link Type:", self.link_type_label)

        self.role_combo = QComboBox()
        self.role_combo.addItem("Become central (do not switch)", 0x00)
        self.role_combo.addItem("Remain peripheral (allow switch)", 0x01)
        self.form_layout.addRow("Accept as:", self.role_combo)

        self.reason_combo = QComboBox()
        self.reason_combo.addItem("Limited resources (0x0D)", 0x0D)
        self.reason_combo.addItem("Security reasons (0x0E)", 0x0E)
        self.reason_combo.addItem("Unacceptable BD_ADDR (0x0F)", 0x0F)
        self.form_layout.addRow("Reject with:", self.reason_combo)

        # This dialog answers rather than dismisses.
        self.ok_button.setText("Accept")
        self.cancel_button.setText("Reject")
        self.cancel_button.setVisible(True)

    def render(self, event):
        self._bd_addr = event.params.get('bd_addr')
        cod = event.params.get('class_of_device')
        if isinstance(cod, (bytes, bytearray)):
            cod = int.from_bytes(cod, 'little')

        self.addr_label.setText(addr_str(self._bd_addr))
        self.cod_label.setText("-" if cod is None else f"0x{cod:06X}")
        link_type = event.params.get('link_type')
        self.link_type_label.setText(
            _LINK_TYPES.get(link_type, f"0x{link_type:02X}" if link_type is not None else "-"))
        self.clear_error()

    def on_ok_button_clicked(self):
        """Accept the connection."""
        if self._accepted_address() is None:
            return
        if self.send(AcceptConnectionRequest(
                bd_addr=self._accepted_address(),
                role=self.role_combo.currentData())):
            self.close()

    def on_cancel_button_clicked(self):
        """Reject the connection."""
        if self._accepted_address() is None:
            return
        if self.send(RejectConnectionRequest(
                bd_addr=self._accepted_address(),
                reason=self.reason_combo.currentData())):
            self.close()

    def _accepted_address(self):
        addr = getattr(self, '_bd_addr', None)
        if addr is None:
            self.log_error("no address in the request -- cannot answer")
            return None
        return addr


@register_event_ui
class ConnectionCompleteEventUI(HCIEvtUI):
    """BR/EDR connection established (or failed)."""

    EVENT_KEYS = ((HciEventCode.CONNECTION_COMPLETE, None),)
    NAME = "Connection Complete"
    AUTO_POPUP = True

    def build_content(self):
        self.status_label = QLabel("-")
        self.handle_label = QLabel("-")
        self.addr_label = QLabel("-")
        self.link_type_label = QLabel("-")
        self.encryption_label = QLabel("-")
        self.form_layout.addRow("Status:", self.status_label)
        self.form_layout.addRow("Connection Handle:", self.handle_label)
        self.form_layout.addRow("BD_ADDR:", self.addr_label)
        self.form_layout.addRow("Link Type:", self.link_type_label)
        self.form_layout.addRow("Encryption:", self.encryption_label)

    def render(self, event):
        params = event.params
        status = params.get('status', 0xFF)
        self.status_label.setText(_status_text(status))
        self.status_label.setStyleSheet(
            "color: #2e7d32;" if status == 0 else "color: #c62828;")
        handle = params.get('connection_handle')
        self.handle_label.setText("-" if handle is None else f"0x{handle:04X}")
        self.addr_label.setText(addr_str(params.get('bd_addr')))
        link_type = params.get('link_type')
        self.link_type_label.setText(
            _LINK_TYPES.get(link_type, f"0x{link_type:02X}" if link_type is not None else "-"))
        self.encryption_label.setText(
            "enabled" if params.get('encryption_enabled') else "disabled")


@register_event_ui
class DisconnectionCompleteEventUI(HCIEvtUI):
    """A link went away."""

    EVENT_KEYS = ((HciEventCode.DISCONNECTION_COMPLETE, None),)
    NAME = "Disconnection Complete"
    AUTO_POPUP = True

    def build_content(self):
        self.status_label = QLabel("-")
        self.handle_label = QLabel("-")
        self.reason_label = QLabel("-")
        self.form_layout.addRow("Status:", self.status_label)
        self.form_layout.addRow("Connection Handle:", self.handle_label)
        self.form_layout.addRow("Reason:", self.reason_label)

    def render(self, event):
        params = event.params
        self.status_label.setText(_status_text(params.get('status', 0xFF)))
        handle = params.get('connection_handle')
        self.handle_label.setText("-" if handle is None else f"0x{handle:04X}")
        reason = params.get('reason')
        self.reason_label.setText("-" if reason is None else f"0x{reason:02X}")


@register_event_ui
class RemoteNameRequestCompleteEventUI(HCIEvtUI):
    """The answer to a Remote Name Request."""

    EVENT_KEYS = ((HciEventCode.REMOTE_NAME_REQUEST_COMPLETE, None),)
    NAME = "Remote Name Request Complete"
    AUTO_POPUP = True

    def build_content(self):
        self.status_label = QLabel("-")
        self.addr_label = QLabel("-")
        self.name_label = QLabel("-")
        self.form_layout.addRow("Status:", self.status_label)
        self.form_layout.addRow("BD_ADDR:", self.addr_label)
        self.form_layout.addRow("Remote Name:", self.name_label)

    def render(self, event):
        params = event.params
        self.status_label.setText(_status_text(params.get('status', 0xFF)))
        self.addr_label.setText(addr_str(params.get('bd_addr')))
        name = params.get('remote_name', b'')
        if isinstance(name, (bytes, bytearray)):
            name = name.split(b'\x00', 1)[0].decode('utf-8', 'replace')
        self.name_label.setText(name or "(none)")


@register_event_ui
class EncryptionChangeEventUI(HCIEvtUI):
    """Encryption turned on or off on a link."""

    EVENT_KEYS = ((HciEventCode.ENCRYPTION_CHANGE, None),)
    NAME = "Encryption Change"
    AUTO_POPUP = True

    _STATES = {0: "off", 1: "on (E0 / AES-CCM)", 2: "on (AES-CCM)"}

    def build_content(self):
        self.status_label = QLabel("-")
        self.handle_label = QLabel("-")
        self.state_label = QLabel("-")
        self.form_layout.addRow("Status:", self.status_label)
        self.form_layout.addRow("Connection Handle:", self.handle_label)
        self.form_layout.addRow("Encryption:", self.state_label)

    def render(self, event):
        params = event.params
        self.status_label.setText(_status_text(params.get('status', 0xFF)))
        handle = params.get('connection_handle')
        self.handle_label.setText("-" if handle is None else f"0x{handle:04X}")
        enabled = params.get('encryption_enabled')
        self.state_label.setText(self._STATES.get(enabled, f"0x{enabled:02X}"
                                                  if enabled is not None else "-"))


@register_event_ui
class InquiryResultsUI(AggregatingEvtUI):
    """
    Every inquiry response, in one table.

    All three result event codes land here -- a controller may send plain,
    with-RSSI and extended results in the same inquiry, and they describe the
    same devices.
    """

    EVENT_KEYS = (
        (HciEventCode.INQUIRY_RESULT, None),
        (HciEventCode.INQUIRY_RESULT_WITH_RSSI, None),
        (HciEventCode.EXTENDED_INQUIRY_RESULT, None),
        (HciEventCode.INQUIRY_COMPLETE, None),
    )
    WINDOW_KEY = "inquiry_results"
    NAME = "Inquiry Results"
    AUTO_POPUP = True

    COLUMNS = ("BD_ADDR", "Name", "RSSI", "Class of Device", "Clock Offset")
    STRETCH_COLUMN = 1

    def build_content(self):
        super().build_content()
        self.state_label = QLabel("inquiry running")
        self.content_layout.addWidget(self.state_label)

    def rows_for(self, event):
        code = int(getattr(event, 'EVENT_CODE', 0))
        params = event.params

        if code == HciEventCode.INQUIRY_COMPLETE:
            self.state_label.setText(
                f"inquiry complete ({_status_text(params.get('status', 0))})")
            return ()

        self.state_label.setText("inquiry running")

        if code == HciEventCode.EXTENDED_INQUIRY_RESULT:
            return (self._row(
                addr=params.get('bd_addr'),
                rssi=params.get('rssi'),
                cod=params.get('class_of_device'),
                clock=params.get('clock_offset'),
                eir=params.get('extended_inquiry_response'),
            ),)

        if code == HciEventCode.INQUIRY_RESULT_WITH_RSSI:
            return tuple(self._row(
                addr=r.get('bd_addr'),
                rssi=r.get('rssi'),
                cod=r.get('class_of_device'),
                clock=r.get('clock_offset'),
            ) for r in params.get('responses', ()))

        # Plain Inquiry Result: parallel lists, no RSSI.
        addrs = params.get('bd_addrs', ())
        cods = params.get('class_of_devices', ())
        clocks = params.get('clock_offsets', ())
        rows = []
        for index, addr in enumerate(addrs):
            cod = cods[index] if index < len(cods) else None
            if isinstance(cod, (bytes, bytearray)):
                cod = int.from_bytes(cod, 'little')
            rows.append(self._row(
                addr=addr,
                rssi=None,
                cod=cod,
                clock=clocks[index] if index < len(clocks) else None,
            ))
        return tuple(rows)

    def _row(self, addr, rssi, cod, clock, eir=None):
        name = ""
        if eir:
            # An EIR payload is AD structures, same encoding as LE adv data.
            from hci.evt.le.adv_data import parse_adv_data
            name = parse_adv_data(bytes(eir)).local_name or ""
        return (
            addr_str(addr),
            name,
            "" if rssi is None else f"{rssi} dBm",
            "" if cod is None else f"0x{cod:06X}",
            "" if clock is None else f"0x{clock:04X}",
        )


__all__ = [
    "ConnectionRequestEventUI",
    "ConnectionCompleteEventUI",
    "DisconnectionCompleteEventUI",
    "RemoteNameRequestCompleteEventUI",
    "EncryptionChangeEventUI",
    "InquiryResultsUI",
]
