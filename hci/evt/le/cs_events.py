"""
LE Channel Sounding events (Core 6.0).

    0x3E/0x29  LE_CS_Read_Remote_Supported_Capabilities_Complete
    0x3E/0x2A  LE_CS_Read_Remote_FAE_Table_Complete
    0x3E/0x2B  LE_CS_Security_Enable_Complete
    0x3E/0x2C  LE_CS_Config_Complete
    0x3E/0x2D  LE_CS_Procedure_Enable_Complete
    0x3E/0x2E  LE_CS_Subevent_Result
    0x3E/0x2F  LE_CS_Subevent_Result_Continue
    0x3E/0x30  LE_CS_Test_End_Complete

The subevent results carry the actual measurements. Their step data is a
variable-length, mode-dependent blob -- decoding it needs the mode of every step
plus the antenna configuration, which lives in the config rather than the event.
It is therefore kept as raw bytes per step here, with the step mode and channel
decoded, which is what a ranging UI needs to show progress and what a real
distance calculation would consume.
"""

from __future__ import annotations

import struct
from typing import List

from .. import register_event
from ..error_codes import get_status_description
from ..evt_base_packet import HciEvtBasePacket
from ..evt_codes import HciEventCode, LeMetaEventSubCode

#: `Procedure_Done_Status` / `Subevent_Done_Status` values.
DONE_STATUS_COMPLETE = 0x00
DONE_STATUS_PARTIAL = 0x01
DONE_STATUS_ABORTED = 0x0F

_DONE_STATUS_NAMES = {
    DONE_STATUS_COMPLETE: "complete",
    DONE_STATUS_PARTIAL: "partial",
    DONE_STATUS_ABORTED: "aborted",
}

_ABORT_REASONS = {
    0x00: "no abort",
    0x01: "local host or remote request",
    0x02: "channel map instant passed",
    0x03: "insufficient channels",
    0x0F: "unspecified",
}


def _done(value: int) -> str:
    return _DONE_STATUS_NAMES.get(value, f"0x{value:02X}")


def _parse_steps(data: bytes, offset: int, num_steps: int) -> List[dict]:
    """
    Decode `num_steps` step records starting at `offset`.

    Each record is mode(1), channel(1), data_length(1), data[data_length].
    Stops early on a short buffer rather than raising -- a partial result is
    still worth reporting.
    """
    steps = []
    off = offset
    for _ in range(num_steps):
        if off + 3 > len(data):
            break
        mode, channel, length = data[off], data[off + 1], data[off + 2]
        if off + 3 + length > len(data):
            break
        steps.append({
            'mode': mode,
            'channel': channel,
            'data': bytes(data[off + 3:off + 3 + length]),
        })
        off += 3 + length
    return steps


class LeCsReadRemoteSupportedCapabilitiesCompleteEvent(HciEvtBasePacket):
    """
    LE CS Read Remote Supported Capabilities Complete Event (0x3E / 0x29).

    The capability block is long and almost entirely bit fields; it is kept raw
    so it can be fed straight back to
    `LE_CS_Write_Cached_Remote_Supported_Capabilities` on a later connection.
    """

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_READ_REMOTE_SUPPORTED_CAPABILITIES_COMPLETE
    NAME = "LE_CS_Read_Remote_Supported_Capabilities_Complete"

    def __init__(self, status: int, connection_handle: int,
                 capabilities: bytes = b''):
        super().__init__(status=status, connection_handle=connection_handle,
                         capabilities=bytes(capabilities))

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([int(self.SUB_EVENT_CODE)])
                + struct.pack("<BH", p['status'], p['connection_handle'])
                + p['capabilities'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 4")
        status, handle = struct.unpack_from("<BH", data, 1)
        return cls(status, handle, data[4:])

    def __str__(self) -> str:
        p = self.params
        if p['status'] != 0x00:
            return (f"{self.NAME}: FAILED {get_status_description(p['status'])} "
                    f"(0x{p['status']:02X})")
        return (f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, "
                f"{len(p['capabilities'])} bytes of capabilities")


class LeCsReadRemoteFaeTableCompleteEvent(HciEvtBasePacket):
    """LE CS Read Remote FAE Table Complete Event (0x3E / 0x2A)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_READ_REMOTE_FAE_TABLE_COMPLETE
    NAME = "LE_CS_Read_Remote_FAE_Table_Complete"

    def __init__(self, status: int, connection_handle: int,
                 remote_fae_table: bytes = b''):
        super().__init__(status=status, connection_handle=connection_handle,
                         remote_fae_table=bytes(remote_fae_table))

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([int(self.SUB_EVENT_CODE)])
                + struct.pack("<BH", p['status'], p['connection_handle'])
                + p['remote_fae_table'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 4")
        status, handle = struct.unpack_from("<BH", data, 1)
        return cls(status, handle, data[4:])

    def __str__(self) -> str:
        p = self.params
        if p['status'] != 0x00:
            return (f"{self.NAME}: FAILED {get_status_description(p['status'])} "
                    f"(0x{p['status']:02X})")
        return (f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, "
                f"{len(p['remote_fae_table'])}-byte table")


class LeCsSecurityEnableCompleteEvent(HciEvtBasePacket):
    """LE CS Security Enable Complete Event (0x3E / 0x2B)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_SECURITY_ENABLE_COMPLETE
    NAME = "LE_CS_Security_Enable_Complete"

    def __init__(self, status: int, connection_handle: int):
        super().__init__(status=status, connection_handle=connection_handle)

    def _serialize_params(self) -> bytes:
        p = self.params
        return bytes([int(self.SUB_EVENT_CODE)]) + struct.pack(
            "<BH", p['status'], p['connection_handle'])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4")
        status, handle = struct.unpack_from("<BH", data, 1)
        return cls(status, handle)

    def __str__(self) -> str:
        p = self.params
        state = "enabled" if p['status'] == 0x00 else \
            f"FAILED {get_status_description(p['status'])} (0x{p['status']:02X})"
        return f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, {state}"


class LeCsConfigCompleteEvent(HciEvtBasePacket):
    """
    LE CS Config Complete Event (0x3E / 0x2C).

    Answers LE_CS_Create_Config and LE_CS_Remove_Config; `action` says which
    (0x00 removed, 0x01 created).
    """

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_CONFIG_COMPLETE
    NAME = "LE_CS_Config_Complete"

    def __init__(self, status: int, connection_handle: int, config_id: int,
                 action: int, main_mode_type: int = 0, sub_mode_type: int = 0,
                 min_main_mode_steps: int = 0, max_main_mode_steps: int = 0,
                 main_mode_repetition: int = 0, mode_0_steps: int = 0,
                 role: int = 0, rtt_type: int = 0, cs_sync_phy: int = 0,
                 channel_map: bytes = b'', channel_map_repetition: int = 0,
                 channel_selection_type: int = 0, ch3c_shape: int = 0,
                 ch3c_jump: int = 0, reserved: int = 0, t_ip1_time: int = 0,
                 t_ip2_time: int = 0, t_fcs_time: int = 0, t_pm_time: int = 0):
        super().__init__(
            status=status, connection_handle=connection_handle,
            config_id=config_id, action=action, main_mode_type=main_mode_type,
            sub_mode_type=sub_mode_type, min_main_mode_steps=min_main_mode_steps,
            max_main_mode_steps=max_main_mode_steps,
            main_mode_repetition=main_mode_repetition, mode_0_steps=mode_0_steps,
            role=role, rtt_type=rtt_type, cs_sync_phy=cs_sync_phy,
            channel_map=bytes(channel_map),
            channel_map_repetition=channel_map_repetition,
            channel_selection_type=channel_selection_type, ch3c_shape=ch3c_shape,
            ch3c_jump=ch3c_jump, reserved=reserved, t_ip1_time=t_ip1_time,
            t_ip2_time=t_ip2_time, t_fcs_time=t_fcs_time, t_pm_time=t_pm_time,
        )

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 5:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 5")
        status, handle, config_id, action = struct.unpack_from("<BHBB", data, 1)
        if status != 0x00 or action == 0x00 or len(data) < 32:
            # A removal or a failure carries nothing past the action byte.
            return cls(status, handle, config_id, action)

        (main_mode, sub_mode, min_steps, max_steps, repetition, mode0, role,
         rtt, phy) = data[6:15]
        channel_map = bytes(data[15:25])
        (map_rep, selection, shape, jump, reserved) = data[25:30]
        (ip1, ip2, fcs, pm) = data[30:34] if len(data) >= 34 else (0, 0, 0, 0)
        return cls(status, handle, config_id, action, main_mode, sub_mode,
                   min_steps, max_steps, repetition, mode0, role, rtt, phy,
                   channel_map, map_rep, selection, shape, jump, reserved,
                   ip1, ip2, fcs, pm)

    def __str__(self) -> str:
        p = self.params
        if p['status'] != 0x00:
            return (f"{self.NAME}: FAILED {get_status_description(p['status'])} "
                    f"(0x{p['status']:02X})")
        verb = "created" if p['action'] else "removed"
        return (f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, "
                f"config {p['config_id']} {verb}, mode-{p['main_mode_type']}, "
                f"role={'initiator' if p['role'] == 0 else 'reflector'}")


class LeCsProcedureEnableCompleteEvent(HciEvtBasePacket):
    """LE CS Procedure Enable Complete Event (0x3E / 0x2D)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_PROCEDURE_ENABLE_COMPLETE
    NAME = "LE_CS_Procedure_Enable_Complete"

    def __init__(self, status: int, connection_handle: int, config_id: int,
                 state: int, tone_antenna_config_selection: int = 0,
                 selected_tx_power: int = 0, subevent_len: int = 0,
                 subevents_per_event: int = 0, subevent_interval: int = 0,
                 event_interval: int = 0, procedure_interval: int = 0,
                 procedure_count: int = 0, max_procedure_len: int = 0):
        super().__init__(
            status=status, connection_handle=connection_handle,
            config_id=config_id, state=state,
            tone_antenna_config_selection=tone_antenna_config_selection,
            selected_tx_power=selected_tx_power, subevent_len=subevent_len,
            subevents_per_event=subevents_per_event,
            subevent_interval=subevent_interval, event_interval=event_interval,
            procedure_interval=procedure_interval,
            procedure_count=procedure_count, max_procedure_len=max_procedure_len,
        )

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 5:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 5")
        status, handle, config_id, state = struct.unpack_from("<BHBB", data, 1)
        if len(data) < 21:
            return cls(status, handle, config_id, state)

        antenna = data[6]
        tx_power = struct.unpack_from("<b", data, 7)[0]
        subevent_len = int.from_bytes(data[8:11], "little")
        subevents_per_event = data[11]
        (subevent_interval, event_interval, procedure_interval,
         procedure_count, max_procedure_len) = struct.unpack_from("<HHHHH", data, 12)
        return cls(status, handle, config_id, state, antenna, tx_power,
                   subevent_len, subevents_per_event, subevent_interval,
                   event_interval, procedure_interval, procedure_count,
                   max_procedure_len)

    def __str__(self) -> str:
        p = self.params
        if p['status'] != 0x00:
            return (f"{self.NAME}: FAILED {get_status_description(p['status'])} "
                    f"(0x{p['status']:02X})")
        return (f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, "
                f"config {p['config_id']} "
                f"{'enabled' if p['state'] else 'disabled'}, "
                f"subevent={p['subevent_len']}us x {p['subevents_per_event']}")


class LeCsSubeventResultEvent(HciEvtBasePacket):
    """
    LE CS Subevent Result Event (0x3E / 0x2E).

    One subevent's worth of ranging steps. `reference_power_level` and the
    per-step data are what a distance estimate is computed from.
    """

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_SUBEVENT_RESULT
    NAME = "LE_CS_Subevent_Result"

    def __init__(self, connection_handle: int, config_id: int,
                 start_acl_conn_event_counter: int, procedure_counter: int,
                 frequency_compensation: int, reference_power_level: int,
                 procedure_done_status: int, subevent_done_status: int,
                 abort_reason: int, num_antenna_paths: int, num_steps_reported: int,
                 steps: List[dict]):
        super().__init__(
            connection_handle=connection_handle, config_id=config_id,
            start_acl_conn_event_counter=start_acl_conn_event_counter,
            procedure_counter=procedure_counter,
            frequency_compensation=frequency_compensation,
            reference_power_level=reference_power_level,
            procedure_done_status=procedure_done_status,
            subevent_done_status=subevent_done_status,
            abort_reason=abort_reason, num_antenna_paths=num_antenna_paths,
            num_steps_reported=num_steps_reported, steps=steps,
        )

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 16:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 16")
        handle, config_id = struct.unpack_from("<HB", data, 1)
        (start_counter, procedure_counter, freq_comp) = \
            struct.unpack_from("<HHH", data, 4)
        ref_power = struct.unpack_from("<b", data, 10)[0]
        procedure_done, subevent_done = data[11], data[12]
        abort_reason, antenna_paths, num_steps = data[13], data[14], data[15]
        steps = _parse_steps(data, 16, num_steps)
        return cls(handle, config_id, start_counter, procedure_counter,
                   freq_comp, ref_power, procedure_done, subevent_done,
                   abort_reason, antenna_paths, num_steps, steps)

    @property
    def steps(self) -> List[dict]:
        return self.params.get('steps', [])

    def __str__(self) -> str:
        p = self.params
        tail = ""
        if p['abort_reason']:
            tail = f", abort: {_ABORT_REASONS.get(p['abort_reason'], 'unknown')}"
        return (f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, "
                f"config {p['config_id']}, procedure #{p['procedure_counter']}, "
                f"{len(self.steps)}/{p['num_steps_reported']} steps, "
                f"ref power {p['reference_power_level']}dBm, "
                f"procedure {_done(p['procedure_done_status'])}, "
                f"subevent {_done(p['subevent_done_status'])}{tail}")


class LeCsSubeventResultContinueEvent(HciEvtBasePacket):
    """
    LE CS Subevent Result Continue Event (0x3E / 0x2F).

    The rest of a subevent whose steps did not fit in one event. It repeats the
    handle/config so it can be matched to its LE_CS_Subevent_Result.
    """

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_SUBEVENT_RESULT_CONTINUE
    NAME = "LE_CS_Subevent_Result_Continue"

    def __init__(self, connection_handle: int, config_id: int,
                 procedure_done_status: int, subevent_done_status: int,
                 abort_reason: int, num_antenna_paths: int,
                 num_steps_reported: int, steps: List[dict]):
        super().__init__(
            connection_handle=connection_handle, config_id=config_id,
            procedure_done_status=procedure_done_status,
            subevent_done_status=subevent_done_status, abort_reason=abort_reason,
            num_antenna_paths=num_antenna_paths,
            num_steps_reported=num_steps_reported, steps=steps,
        )

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 9:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 9")
        handle, config_id = struct.unpack_from("<HB", data, 1)
        procedure_done, subevent_done = data[4], data[5]
        abort_reason, antenna_paths, num_steps = data[6], data[7], data[8]
        steps = _parse_steps(data, 9, num_steps)
        return cls(handle, config_id, procedure_done, subevent_done,
                   abort_reason, antenna_paths, num_steps, steps)

    @property
    def steps(self) -> List[dict]:
        return self.params.get('steps', [])

    def __str__(self) -> str:
        p = self.params
        return (f"{self.NAME}: Handle=0x{p['connection_handle']:04X}, "
                f"config {p['config_id']}, "
                f"{len(self.steps)}/{p['num_steps_reported']} more steps, "
                f"procedure {_done(p['procedure_done_status'])}")


class LeCsTestEndCompleteEvent(HciEvtBasePacket):
    """LE CS Test End Complete Event (0x3E / 0x30)."""

    EVENT_CODE = HciEventCode.LE_META_EVENT
    SUB_EVENT_CODE = LeMetaEventSubCode.CS_TEST_END_COMPLETE
    NAME = "LE_CS_Test_End_Complete"

    def __init__(self, status: int):
        super().__init__(status=status)

    def _serialize_params(self) -> bytes:
        return bytes([int(self.SUB_EVENT_CODE), self.params['status']])

    @classmethod
    def from_bytes_sub_event(cls, data: bytes, sub_event_code: int):
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(data[1])

    def __str__(self) -> str:
        status = self.params['status']
        if status == 0x00:
            return f"{self.NAME}: CS test stopped"
        return (f"{self.NAME}: FAILED {get_status_description(status)} "
                f"(0x{status:02X})")


for _cls in (LeCsReadRemoteSupportedCapabilitiesCompleteEvent,
             LeCsReadRemoteFaeTableCompleteEvent,
             LeCsSecurityEnableCompleteEvent,
             LeCsConfigCompleteEvent,
             LeCsProcedureEnableCompleteEvent,
             LeCsSubeventResultEvent,
             LeCsSubeventResultContinueEvent,
             LeCsTestEndCompleteEvent):
    register_event(_cls)
del _cls


__all__ = [
    'LeCsReadRemoteSupportedCapabilitiesCompleteEvent',
    'LeCsReadRemoteFaeTableCompleteEvent',
    'LeCsSecurityEnableCompleteEvent',
    'LeCsConfigCompleteEvent',
    'LeCsProcedureEnableCompleteEvent',
    'LeCsSubeventResultEvent',
    'LeCsSubeventResultContinueEvent',
    'LeCsTestEndCompleteEvent',
    'DONE_STATUS_COMPLETE',
    'DONE_STATUS_PARTIAL',
    'DONE_STATUS_ABORTED',
]
