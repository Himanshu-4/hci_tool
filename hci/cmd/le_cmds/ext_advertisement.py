"""
LE extended and periodic advertising commands (Core 5.0+).

    0x2035  LE_Set_Advertising_Set_Random_Address
    0x2036  LE_Set_Extended_Advertising_Parameters
    0x2037  LE_Set_Extended_Advertising_Data
    0x2038  LE_Set_Extended_Scan_Response_Data
    0x2039  LE_Set_Extended_Advertising_Enable
    0x203A  LE_Read_Maximum_Advertising_Data_Length
    0x203B  LE_Read_Number_Of_Supported_Advertising_Sets
    0x203C  LE_Remove_Advertising_Set
    0x203D  LE_Clear_Advertising_Sets
    0x203E  LE_Set_Periodic_Advertising_Parameters
    0x203F  LE_Set_Periodic_Advertising_Data
    0x2040  LE_Set_Periodic_Advertising_Enable

Extended advertising replaces the legacy set rather than extending it: a
controller rejects legacy commands once an extended set exists, and vice versa.
The two are kept in separate modules for that reason.

Note the interval fields here are **3 octets**, not 2 as in the legacy commands
-- that is the single most common source of malformed 0x2036 packets.
"""

from __future__ import annotations

import struct
from enum import IntEnum, IntFlag, unique
from typing import List, Sequence, Tuple, Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode
from .advertisement import _coerce_addr


class AdvEventProperties(IntFlag):
    """
    Bit field for `Advertising_Event_Properties` (0x2036).

    Legacy PDUs are reachable by combining LEGACY with the connectable/scannable
    bits; the controller then emits the matching legacy PDU type. Anything
    without LEGACY is an extended advertising PDU.
    """

    CONNECTABLE = 0x0001
    SCANNABLE = 0x0002
    DIRECTED = 0x0004
    HIGH_DUTY_DIRECTED = 0x0008
    LEGACY = 0x0010
    ANONYMOUS = 0x0020
    INCLUDE_TX_POWER = 0x0040


#: Ready-made legacy-compatible property words, for controllers/peers that still
#: expect legacy PDUs while the host uses the extended commands.
LEGACY_ADV_IND = (AdvEventProperties.LEGACY | AdvEventProperties.CONNECTABLE
                  | AdvEventProperties.SCANNABLE)
LEGACY_ADV_DIRECT_IND = (AdvEventProperties.LEGACY | AdvEventProperties.CONNECTABLE
                         | AdvEventProperties.DIRECTED)
LEGACY_ADV_SCAN_IND = AdvEventProperties.LEGACY | AdvEventProperties.SCANNABLE
LEGACY_ADV_NONCONN_IND = AdvEventProperties.LEGACY


@unique
class PrimaryPhy(IntEnum):
    """PHY for the primary advertising channels. 2M is not permitted here."""

    LE_1M = 0x01
    LE_CODED = 0x03


@unique
class SecondaryPhy(IntEnum):
    """PHY for the secondary (data) advertising channels."""

    LE_1M = 0x01
    LE_2M = 0x02
    LE_CODED = 0x03


@unique
class DataOperation(IntEnum):
    """`Operation` field shared by the extended/periodic data commands."""

    INTERMEDIATE_FRAGMENT = 0x00
    FIRST_FRAGMENT = 0x01
    LAST_FRAGMENT = 0x02
    COMPLETE = 0x03
    UNCHANGED = 0x04     # extended advertising data only


@unique
class FragmentPreference(IntEnum):
    MAY_FRAGMENT = 0x00
    SHOULD_NOT_FRAGMENT = 0x01


class PeriodicAdvProperties(IntFlag):
    INCLUDE_TX_POWER = 0x0040


def _u24(value: int) -> bytes:
    """Little-endian 3-octet field (the extended advertising intervals)."""
    if not (0 <= value <= 0xFFFFFF):
        raise ValueError(f"value 0x{value:X} does not fit in 3 octets")
    return value.to_bytes(3, "little")


def _s8(value: int) -> int:
    """Coerce a signed dBm/level byte into its unsigned wire form."""
    return value & 0xFF if value < 0 else value


class LeSetAdvertisingSetRandomAddress(HciCmdBasePacket):
    """LE Set Advertising Set Random Address Command (0x2035)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_ADVERTISING_SET_RANDOM_ADDRESS)
    NAME = "LE_Set_Advertising_Set_Random_Address"

    def __init__(self, adv_handle: int, random_address: Union[bytes, str]):
        super().__init__(adv_handle=adv_handle,
                         random_address=_coerce_addr(random_address))

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{self.params['adv_handle']:02X} out of "
                             "range (0x00..0xEF)")

    def _serialize_params(self) -> bytes:
        return (bytes([self.params['adv_handle']])
                + bytes(reversed(self.params['random_address'])))

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetAdvertisingSetRandomAddress":
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected 7")
        return cls(data[0], bytes(reversed(data[1:7])))


class LeSetExtendedAdvertisingParameters(HciCmdBasePacket):
    """LE Set Extended Advertising Parameters Command (0x2036)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_ADVERTISING_PARAMETERS)
    NAME = "LE_Set_Extended_Advertising_Parameters"

    def __init__(self,
                 adv_handle: int = 0x00,
                 adv_event_properties: int = int(LEGACY_ADV_IND),
                 primary_adv_interval_min: int = 0x000800,   # 1.28 s
                 primary_adv_interval_max: int = 0x000800,
                 primary_adv_channel_map: int = 0x07,
                 own_address_type: int = 0x00,
                 peer_address_type: int = 0x00,
                 peer_address: Union[bytes, str] = b"\x00" * 6,
                 adv_filter_policy: int = 0x00,
                 adv_tx_power: int = 0x7F,                   # 0x7F: host has no preference
                 primary_adv_phy: int = PrimaryPhy.LE_1M,
                 secondary_adv_max_skip: int = 0x00,
                 secondary_adv_phy: int = SecondaryPhy.LE_1M,
                 adv_sid: int = 0x00,
                 scan_request_notification_enable: int = 0x00):
        super().__init__(
            adv_handle=adv_handle,
            adv_event_properties=int(adv_event_properties),
            primary_adv_interval_min=primary_adv_interval_min,
            primary_adv_interval_max=primary_adv_interval_max,
            primary_adv_channel_map=primary_adv_channel_map,
            own_address_type=own_address_type,
            peer_address_type=peer_address_type,
            peer_address=_coerce_addr(peer_address),
            adv_filter_policy=adv_filter_policy,
            adv_tx_power=adv_tx_power,
            primary_adv_phy=int(primary_adv_phy),
            secondary_adv_max_skip=secondary_adv_max_skip,
            secondary_adv_phy=int(secondary_adv_phy),
            adv_sid=adv_sid,
            scan_request_notification_enable=scan_request_notification_enable,
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{p['adv_handle']:02X} out of range "
                             "(0x00..0xEF)")
        for field in ('primary_adv_interval_min', 'primary_adv_interval_max'):
            if not (0x000020 <= p[field] <= 0xFFFFFF):
                raise ValueError(f"{field} 0x{p[field]:06X} out of range "
                                 "(0x000020..0xFFFFFF)")
        if p['primary_adv_interval_min'] > p['primary_adv_interval_max']:
            raise ValueError("primary_adv_interval_min must be <= "
                             "primary_adv_interval_max")
        if not (p['primary_adv_channel_map'] & 0x07):
            raise ValueError("primary_adv_channel_map must enable at least one "
                             "of channels 37/38/39")
        if p['primary_adv_phy'] not in (0x01, 0x03):
            raise ValueError("primary_adv_phy must be LE_1M (0x01) or LE_CODED "
                             "(0x03); 2M is not allowed on the primary channels")
        if p['secondary_adv_phy'] not in (0x01, 0x02, 0x03):
            raise ValueError(f"Invalid secondary_adv_phy: {p['secondary_adv_phy']}")
        if not (0x00 <= p['adv_sid'] <= 0x0F):
            raise ValueError(f"adv_sid {p['adv_sid']} out of range (0x00..0x0F)")

        props = p['adv_event_properties']
        if props & AdvEventProperties.LEGACY:
            # A legacy PDU carries at most 31 bytes and cannot be both
            # connectable and non-scannable, so the controller only accepts the
            # four canonical combinations.
            if props not in (int(LEGACY_ADV_IND), int(LEGACY_ADV_DIRECT_IND),
                             int(LEGACY_ADV_SCAN_IND), int(LEGACY_ADV_NONCONN_IND),
                             int(LEGACY_ADV_DIRECT_IND | AdvEventProperties.HIGH_DUTY_DIRECTED)):
                raise ValueError(
                    f"adv_event_properties 0x{props:04X} is not a valid legacy "
                    "combination")
        elif (props & AdvEventProperties.CONNECTABLE) and \
                (props & AdvEventProperties.SCANNABLE):
            raise ValueError("extended advertising cannot be connectable and "
                             "scannable at the same time")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (
            bytes([p['adv_handle']])
            + struct.pack("<H", p['adv_event_properties'])
            + _u24(p['primary_adv_interval_min'])
            + _u24(p['primary_adv_interval_max'])
            + bytes([p['primary_adv_channel_map'], p['own_address_type'],
                     p['peer_address_type']])
            + bytes(reversed(p['peer_address']))
            + bytes([p['adv_filter_policy'], _s8(p['adv_tx_power']),
                     p['primary_adv_phy'], p['secondary_adv_max_skip'],
                     p['secondary_adv_phy'], p['adv_sid'],
                     p['scan_request_notification_enable']])
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetExtendedAdvertisingParameters":
        if len(data) < 25:
            raise ValueError(f"Invalid data length: {len(data)}, expected 25")
        handle = data[0]
        props = struct.unpack_from("<H", data, 1)[0]
        itv_min = int.from_bytes(data[3:6], "little")
        itv_max = int.from_bytes(data[6:9], "little")
        chan_map, own_type, peer_type = data[9], data[10], data[11]
        peer = bytes(reversed(data[12:18]))
        (policy, tx_power, prim_phy, skip, sec_phy, sid, notify) = data[18:25]
        return cls(handle, props, itv_min, itv_max, chan_map, own_type,
                   peer_type, peer, policy,
                   tx_power - 256 if tx_power > 0x7F else tx_power,
                   prim_phy, skip, sec_phy, sid, notify)


class _ExtendedDataCommand(HciCmdBasePacket):
    """
    Shared body for 0x2037 / 0x2038.

    Both take the same five fields; only the opcode and name differ, and
    duplicating 40 lines of fragmentation handling for that is how the two drift
    apart.
    """

    def __init__(self, adv_handle: int = 0x00, data: bytes = b'',
                 operation: int = DataOperation.COMPLETE,
                 fragment_preference: int = FragmentPreference.SHOULD_NOT_FRAGMENT):
        super().__init__(adv_handle=adv_handle,
                         operation=int(operation),
                         fragment_preference=int(fragment_preference),
                         data=bytes(data))

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{p['adv_handle']:02X} out of range")
        if p['operation'] not in tuple(int(op) for op in DataOperation):
            raise ValueError(f"Invalid operation: {p['operation']}")
        # 251 is what fits in one HCI command; longer payloads must be sent as
        # FIRST/INTERMEDIATE/LAST fragments.
        if len(p['data']) > 251:
            raise ValueError(
                f"data is {len(p['data'])} bytes; one command carries at most "
                "251 -- split it into fragments")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([p['adv_handle'], p['operation'], p['fragment_preference'],
                       len(p['data'])]) + p['data'])

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 4")
        handle, operation, fragment, length = data[:4]
        return cls(handle, data[4:4 + length], operation, fragment)

    @staticmethod
    def fragments(data: bytes, chunk: int = 251) -> List[Tuple[int, bytes]]:
        """
        Split `data` into (operation, chunk) pairs ready for successive sends.

        A single payload comes back as one COMPLETE chunk, which is the common
        case and keeps callers from special-casing it.
        """
        data = bytes(data)
        if len(data) <= chunk:
            return [(int(DataOperation.COMPLETE), data)]

        pieces = [data[i:i + chunk] for i in range(0, len(data), chunk)]
        out = [(int(DataOperation.FIRST_FRAGMENT), pieces[0])]
        out += [(int(DataOperation.INTERMEDIATE_FRAGMENT), piece)
                for piece in pieces[1:-1]]
        out.append((int(DataOperation.LAST_FRAGMENT), pieces[-1]))
        return out


class LeSetExtendedAdvertisingData(_ExtendedDataCommand):
    """LE Set Extended Advertising Data Command (0x2037)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_ADVERTISING_DATA)
    NAME = "LE_Set_Extended_Advertising_Data"


class LeSetExtendedScanResponseData(_ExtendedDataCommand):
    """LE Set Extended Scan Response Data Command (0x2038)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_SCAN_RESPONSE_DATA)
    NAME = "LE_Set_Extended_Scan_Response_Data"


class LeSetExtendedAdvertisingEnable(HciCmdBasePacket):
    """
    LE Set Extended Advertising Enable Command (0x2039).

    `sets` is a list of (adv_handle, duration, max_ext_adv_events). Duration is
    in 10 ms units, 0 for "until disabled"; max events 0 for "no limit". When
    disabling, an empty list stops *every* set at once.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_EXTENDED_ADVERTISING_ENABLE)
    NAME = "LE_Set_Extended_Advertising_Enable"

    def __init__(self, enable: bool = True,
                 sets: Sequence[Tuple[int, int, int]] = ((0x00, 0x0000, 0x00),)):
        super().__init__(enable=bool(enable),
                         sets=[tuple(entry) for entry in sets])

    def _validate_params(self) -> None:
        p = self.params
        if p['enable'] and not p['sets']:
            raise ValueError("enabling requires at least one advertising set")
        for handle, duration, max_events in p['sets']:
            if not (0x00 <= handle <= 0xEF):
                raise ValueError(f"adv_handle 0x{handle:02X} out of range")
            if not (0x0000 <= duration <= 0xFFFF):
                raise ValueError(f"duration {duration} out of range")
            if not (0x00 <= max_events <= 0xFF):
                raise ValueError(f"max_ext_adv_events {max_events} out of range")

    def _serialize_params(self) -> bytes:
        p = self.params
        out = bytearray([0x01 if p['enable'] else 0x00, len(p['sets'])])
        for handle, duration, max_events in p['sets']:
            out += struct.pack("<BHB", handle, duration, max_events)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetExtendedAdvertisingEnable":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 2")
        enable, num_sets = data[0], data[1]
        sets = [struct.unpack_from("<BHB", data, 2 + i * 4) for i in range(num_sets)]
        return cls(bool(enable), sets)


class LeReadMaximumAdvertisingDataLength(HciCmdBasePacket):
    """LE Read Maximum Advertising Data Length Command (0x203A)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_MAXIMUM_ADVERTISING_DATA_LENGTH)
    NAME = "LE_Read_Maximum_Advertising_Data_Length"

    def __init__(self):
        super().__init__()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadMaximumAdvertisingDataLength":
        return cls()


class LeReadNumberOfSupportedAdvertisingSets(HciCmdBasePacket):
    """LE Read Number of Supported Advertising Sets Command (0x203B)."""

    OPCODE = create_opcode(OGF.LE,
                           LEControllerOCF.READ_NUMBER_OF_SUPPORTED_ADVERTISING_SETS)
    NAME = "LE_Read_Number_Of_Supported_Advertising_Sets"

    def __init__(self):
        super().__init__()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadNumberOfSupportedAdvertisingSets":
        return cls()


class LeRemoveAdvertisingSet(HciCmdBasePacket):
    """LE Remove Advertising Set Command (0x203C)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_ADVERTISING_SET)
    NAME = "LE_Remove_Advertising_Set"

    def __init__(self, adv_handle: int = 0x00):
        super().__init__(adv_handle=adv_handle)

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{self.params['adv_handle']:02X} out of range")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['adv_handle']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeRemoveAdvertisingSet":
        if not data:
            raise ValueError("Invalid data length: 0, expected 1")
        return cls(data[0])


class LeClearAdvertisingSets(HciCmdBasePacket):
    """LE Clear Advertising Sets Command (0x203D)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CLEAR_ADVERTISING_SETS)
    NAME = "LE_Clear_Advertising_Sets"

    def __init__(self):
        super().__init__()

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeClearAdvertisingSets":
        return cls()


class LeSetPeriodicAdvertisingParameters(HciCmdBasePacket):
    """
    LE Set Periodic Advertising Parameters Command (0x203E).

    The set named by `adv_handle` must already exist (0x2036) and must be
    non-connectable, non-scannable and non-anonymous, or the controller answers
    Command Disallowed.

    Intervals are in 1.25 ms units.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADVERTISING_PARAMETERS)
    NAME = "LE_Set_Periodic_Advertising_Parameters"

    def __init__(self, adv_handle: int = 0x00,
                 periodic_adv_interval_min: int = 0x0060,   # 120 ms
                 periodic_adv_interval_max: int = 0x0080,   # 160 ms
                 periodic_adv_properties: int = 0x0000):
        super().__init__(adv_handle=adv_handle,
                         periodic_adv_interval_min=periodic_adv_interval_min,
                         periodic_adv_interval_max=periodic_adv_interval_max,
                         periodic_adv_properties=int(periodic_adv_properties))

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{p['adv_handle']:02X} out of range")
        for field in ('periodic_adv_interval_min', 'periodic_adv_interval_max'):
            if not (0x0006 <= p[field] <= 0xFFFF):
                raise ValueError(f"{field} 0x{p[field]:04X} out of range "
                                 "(0x0006..0xFFFF)")
        if p['periodic_adv_interval_min'] > p['periodic_adv_interval_max']:
            raise ValueError("periodic_adv_interval_min must be <= "
                             "periodic_adv_interval_max")

    def _serialize_params(self) -> bytes:
        p = self.params
        return struct.pack("<BHHH", p['adv_handle'],
                           p['periodic_adv_interval_min'],
                           p['periodic_adv_interval_max'],
                           p['periodic_adv_properties'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetPeriodicAdvertisingParameters":
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected 7")
        return cls(*struct.unpack_from("<BHHH", data, 0))


class LeSetPeriodicAdvertisingData(HciCmdBasePacket):
    """LE Set Periodic Advertising Data Command (0x203F)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADVERTISING_DATA)
    NAME = "LE_Set_Periodic_Advertising_Data"

    def __init__(self, adv_handle: int = 0x00, data: bytes = b'',
                 operation: int = DataOperation.COMPLETE):
        super().__init__(adv_handle=adv_handle, operation=int(operation),
                         data=bytes(data))

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{p['adv_handle']:02X} out of range")
        if p['operation'] == int(DataOperation.UNCHANGED):
            raise ValueError("operation 0x04 (unchanged) is not valid for "
                             "periodic advertising data")
        if len(p['data']) > 252:
            raise ValueError(
                f"data is {len(p['data'])} bytes; one command carries at most 252")

    def _serialize_params(self) -> bytes:
        p = self.params
        return bytes([p['adv_handle'], p['operation'], len(p['data'])]) + p['data']

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetPeriodicAdvertisingData":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 3")
        handle, operation, length = data[:3]
        return cls(handle, data[3:3 + length], operation)


class LeSetPeriodicAdvertisingEnable(HciCmdBasePacket):
    """
    LE Set Periodic Advertising Enable Command (0x2040).

    Enabling periodic advertising does not start the advertising set itself --
    0x2039 still has to be sent, otherwise nothing is transmitted and nothing
    can sync.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_PERIODIC_ADVERTISING_ENABLE)
    NAME = "LE_Set_Periodic_Advertising_Enable"

    #: Enable bit 1: include the ADI field in AUX_SYNC_IND PDUs.
    INCLUDE_ADI = 0x02

    def __init__(self, enable: Union[bool, int] = True, adv_handle: int = 0x00):
        super().__init__(enable=int(enable), adv_handle=adv_handle)

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{self.params['adv_handle']:02X} out of range")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['enable'] & 0xFF, self.params['adv_handle']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetPeriodicAdvertisingEnable":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(data[0], data[1])


# ------------------------------------------------------------ helper builders

def le_set_advertising_set_random_address(adv_handle, address):
    return LeSetAdvertisingSetRandomAddress(adv_handle, address)


def le_set_extended_advertising_parameters(**kwargs):
    return LeSetExtendedAdvertisingParameters(**kwargs)


def le_set_extended_advertising_data(adv_handle=0x00, data=b'', **kwargs):
    return LeSetExtendedAdvertisingData(adv_handle, data, **kwargs)


def le_set_extended_scan_response_data(adv_handle=0x00, data=b'', **kwargs):
    return LeSetExtendedScanResponseData(adv_handle, data, **kwargs)


def le_set_extended_advertising_enable(enable=True, adv_handle=0x00,
                                       duration=0x0000, max_ext_adv_events=0x00):
    """Enable/disable one set -- the common case behind the list-taking command."""
    return LeSetExtendedAdvertisingEnable(
        enable, [(adv_handle, duration, max_ext_adv_events)])


def le_remove_advertising_set(adv_handle=0x00):
    return LeRemoveAdvertisingSet(adv_handle)


def le_clear_advertising_sets():
    return LeClearAdvertisingSets()


def le_set_periodic_advertising_parameters(**kwargs):
    return LeSetPeriodicAdvertisingParameters(**kwargs)


def le_set_periodic_advertising_data(adv_handle=0x00, data=b'', **kwargs):
    return LeSetPeriodicAdvertisingData(adv_handle, data, **kwargs)


def le_set_periodic_advertising_enable(enable=True, adv_handle=0x00):
    return LeSetPeriodicAdvertisingEnable(enable, adv_handle)


for _cls in (LeSetAdvertisingSetRandomAddress, LeSetExtendedAdvertisingParameters,
             LeSetExtendedAdvertisingData, LeSetExtendedScanResponseData,
             LeSetExtendedAdvertisingEnable, LeReadMaximumAdvertisingDataLength,
             LeReadNumberOfSupportedAdvertisingSets, LeRemoveAdvertisingSet,
             LeClearAdvertisingSets, LeSetPeriodicAdvertisingParameters,
             LeSetPeriodicAdvertisingData, LeSetPeriodicAdvertisingEnable):
    register_command(_cls)
del _cls


__all__ = [
    'AdvEventProperties',
    'PrimaryPhy',
    'SecondaryPhy',
    'DataOperation',
    'FragmentPreference',
    'PeriodicAdvProperties',
    'LEGACY_ADV_IND',
    'LEGACY_ADV_DIRECT_IND',
    'LEGACY_ADV_SCAN_IND',
    'LEGACY_ADV_NONCONN_IND',
    'LeSetAdvertisingSetRandomAddress',
    'LeSetExtendedAdvertisingParameters',
    'LeSetExtendedAdvertisingData',
    'LeSetExtendedScanResponseData',
    'LeSetExtendedAdvertisingEnable',
    'LeReadMaximumAdvertisingDataLength',
    'LeReadNumberOfSupportedAdvertisingSets',
    'LeRemoveAdvertisingSet',
    'LeClearAdvertisingSets',
    'LeSetPeriodicAdvertisingParameters',
    'LeSetPeriodicAdvertisingData',
    'LeSetPeriodicAdvertisingEnable',
    'le_set_advertising_set_random_address',
    'le_set_extended_advertising_parameters',
    'le_set_extended_advertising_data',
    'le_set_extended_scan_response_data',
    'le_set_extended_advertising_enable',
    'le_remove_advertising_set',
    'le_clear_advertising_sets',
    'le_set_periodic_advertising_parameters',
    'le_set_periodic_advertising_data',
    'le_set_periodic_advertising_enable',
]
