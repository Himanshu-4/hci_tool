"""
LE isochronous commands: CIG/CIS, BIG/BIS, ISO data paths and the ISO test modes.

    0x2060  LE_Read_ISO_TX_Sync
    0x2061  LE_Set_CIG_Parameters
    0x2062  LE_Set_CIG_Parameters_Test
    0x2063  LE_Create_CIS
    0x2064  LE_Remove_CIG
    0x2065  LE_Accept_CIS_Request
    0x2066  LE_Reject_CIS_Request
    0x2067  LE_Create_BIG
    0x2068  LE_Create_BIG_Test
    0x2069  LE_Terminate_BIG
    0x206A  LE_BIG_Create_Sync
    0x206B  LE_BIG_Terminate_Sync
    0x206C  LE_Request_Peer_SCA
    0x206D  LE_Setup_ISO_Data_Path
    0x206E  LE_Remove_ISO_Data_Path
    0x206F  LE_ISO_Transmit_Test
    0x2070  LE_ISO_Receive_Test
    0x2071  LE_ISO_Read_Test_Counters
    0x2072  LE_ISO_Test_End
    0x2073  LE_Set_Host_Feature
    0x2074  LE_Read_ISO_Link_Quality

Two families that look similar and are not:

* **CIG / CIS** -- connected isochronous. A CIG is configured against existing
  ACL links, then `LE_Create_CIS` pairs each CIS handle with the ACL handle it
  rides on. Central side only; a peripheral answers the incoming CIS Request
  with accept/reject instead.
* **BIG / BIS** -- broadcast isochronous. A BIG hangs off a *periodic
  advertising set*, so the extended + periodic advertising commands have to have
  run first. Receivers sync to it with `LE_BIG_Create_Sync` against a sync
  handle from LE Periodic Advertising Sync Established.

The `_Test` variants of Set CIG Parameters and Create BIG expose the raw air
schedule (NSE, BN, IRC, PTO, FT) instead of letting the controller derive it
from latency and retransmission targets. They are for qualification and for
reproducing an exact schedule -- not for ordinary use, where the controller
picks better numbers than a human will.

Units, since they are not consistent: SDU intervals and controller delay are in
**microseconds** (3 octets), transport latency in **milliseconds**, ISO interval
in 1.25 ms units, and BIG sync timeout in 10 ms units.
"""

from __future__ import annotations

import struct
from enum import IntEnum, IntFlag, unique
from typing import Sequence, Tuple

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode


@unique
class IsoPacking(IntEnum):
    """How the controller lays subevents out in time."""

    SEQUENTIAL = 0x00
    INTERLEAVED = 0x01


@unique
class IsoFraming(IntEnum):
    """
    Unframed needs the SDU interval to line up with the ISO interval; framed
    adds a header and lifts that restriction at the cost of overhead.
    """

    UNFRAMED = 0x00
    FRAMED = 0x01


class IsoPhy(IntFlag):
    """PHY preference bitmap. At least one bit must be set."""

    LE_1M = 0x01
    LE_2M = 0x02
    LE_CODED = 0x04


@unique
class ClockAccuracy(IntEnum):
    """`Worst_Case_SCA` -- the peripherals' worst sleep clock accuracy."""

    PPM_251_TO_500 = 0x00
    PPM_151_TO_250 = 0x01
    PPM_101_TO_150 = 0x02
    PPM_76_TO_100 = 0x03
    PPM_51_TO_75 = 0x04
    PPM_31_TO_50 = 0x05
    PPM_21_TO_30 = 0x06
    PPM_0_TO_20 = 0x07


@unique
class DataPathDirection(IntEnum):
    """Direction of an ISO data path, from the controller's point of view."""

    INPUT = 0x00      # host -> controller, i.e. the transmit path
    OUTPUT = 0x01     # controller -> host, i.e. the receive path


class DataPathDirectionMask(IntFlag):
    """`LE_Remove_ISO_Data_Path` takes a bitmap, not a single direction."""

    INPUT = 0x01
    OUTPUT = 0x02
    BOTH = 0x03


@unique
class DataPathId(IntEnum):
    """Well-known `Data_Path_ID` values; 0x01..0xFE are vendor-defined."""

    HCI = 0x00
    DISABLED = 0xFF


@unique
class CodingFormat(IntEnum):
    """`Coding_Format` from the Assigned Numbers codec list."""

    U_LAW = 0x00
    A_LAW = 0x01
    CVSD = 0x02
    TRANSPARENT = 0x03
    LINEAR_PCM = 0x04
    MSBC = 0x05
    LC3 = 0x06
    G_729A = 0x07
    VENDOR_SPECIFIC = 0xFF


@unique
class IsoPayloadType(IntEnum):
    """Payload the ISO test modes generate/expect."""

    ZERO_LENGTH = 0x00
    VARIABLE_LENGTH = 0x01
    MAXIMUM_LENGTH = 0x02


@unique
class HostFeatureBit(IntEnum):
    """Bits `LE_Set_Host_Feature` can toggle (FeatureSet bit numbers)."""

    CONNECTED_ISOCHRONOUS_STREAMS = 32
    CONNECTION_SUBRATING = 38
    CHANNEL_CLASSIFICATION = 40
    ADVERTISING_CODING_SELECTION = 45
    CHANNEL_SOUNDING = 46


#: Reason codes that make sense for terminating a BIG or rejecting a CIS.
TERMINATE_REASON_LOCAL_HOST = 0x16
TERMINATE_REASON_REMOTE_USER = 0x13


def _u24(value: int, name: str) -> bytes:
    if not (0 <= value <= 0xFFFFFF):
        raise ValueError(f"{name} 0x{value:X} does not fit in 3 octets")
    return value.to_bytes(3, "little")


def _check_handle(handle: int, name: str = "connection_handle") -> None:
    if not (0x0000 <= handle <= 0x0EFF):
        raise ValueError(f"Invalid {name}: 0x{handle:04X} (0x0000..0x0EFF)")


def _check_sdu_interval(value: int, name: str) -> None:
    if not (0x0000FF <= value <= 0x0FFFFF):
        raise ValueError(f"{name} {value} us out of range "
                         "(255..1048575 microseconds)")


def _check_phy(value: int, name: str) -> None:
    if not (0x01 <= value <= 0x07):
        raise ValueError(f"{name} 0x{value:02X} must set at least one of "
                         "1M (0x01), 2M (0x02), Coded (0x04)")


def _check_latency(value: int, name: str) -> None:
    if not (0x0005 <= value <= 0x0FA0):
        raise ValueError(f"{name} {value} ms out of range (5..4000 ms)")


# =================================================================== CIG / CIS

class LeSetCigParameters(HciCmdBasePacket):
    """
    LE Set CIG Parameters Command (0x2061).

    `cis_params` is a list of
    `(cis_id, max_sdu_c_to_p, max_sdu_p_to_c, phy_c_to_p, phy_p_to_c,
      rtn_c_to_p, rtn_p_to_c)`.

    The controller answers with the CIS *connection handles* it allocated, in
    the same order -- those are what `LE_Create_CIS` then needs. Re-sending this
    for an existing CIG reconfigures it, but only while none of its CISes are
    established.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_CIG_PARAMS)
    NAME = "LE_Set_CIG_Parameters"

    MAX_CIS = 0x1F

    #: (cis_id, max_sdu_c_to_p, max_sdu_p_to_c, phy_c_to_p, phy_p_to_c,
    #:  rtn_c_to_p, rtn_p_to_c) -- one modest bidirectional stream.
    DEFAULT_CIS = (0x00, 40, 40, int(IsoPhy.LE_2M), int(IsoPhy.LE_2M), 2, 2)

    def __init__(self, cig_id: int = 0x00,
                 sdu_interval_c_to_p: int = 10000,     # 10 ms
                 sdu_interval_p_to_c: int = 10000,
                 worst_case_sca: int = ClockAccuracy.PPM_251_TO_500,
                 packing: int = IsoPacking.SEQUENTIAL,
                 framing: int = IsoFraming.UNFRAMED,
                 max_transport_latency_c_to_p: int = 10,   # ms
                 max_transport_latency_p_to_c: int = 10,
                 cis_params: Sequence[Tuple[int, ...]] = (DEFAULT_CIS,)):
        super().__init__(
            cig_id=cig_id,
            sdu_interval_c_to_p=sdu_interval_c_to_p,
            sdu_interval_p_to_c=sdu_interval_p_to_c,
            worst_case_sca=int(worst_case_sca),
            packing=int(packing),
            framing=int(framing),
            max_transport_latency_c_to_p=max_transport_latency_c_to_p,
            max_transport_latency_p_to_c=max_transport_latency_p_to_c,
            cis_params=[tuple(entry) for entry in cis_params],
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['cig_id'] <= 0xEF):
            raise ValueError(f"cig_id 0x{p['cig_id']:02X} out of range (0x00..0xEF)")
        _check_sdu_interval(p['sdu_interval_c_to_p'], "sdu_interval_c_to_p")
        _check_sdu_interval(p['sdu_interval_p_to_c'], "sdu_interval_p_to_c")
        if not (0x00 <= p['worst_case_sca'] <= 0x07):
            raise ValueError(f"worst_case_sca {p['worst_case_sca']} out of range (0..7)")
        if p['packing'] not in (0x00, 0x01):
            raise ValueError(f"Invalid packing: {p['packing']}")
        if p['framing'] not in (0x00, 0x01):
            raise ValueError(f"Invalid framing: {p['framing']}")
        _check_latency(p['max_transport_latency_c_to_p'],
                       "max_transport_latency_c_to_p")
        _check_latency(p['max_transport_latency_p_to_c'],
                       "max_transport_latency_p_to_c")

        if not (1 <= len(p['cis_params']) <= self.MAX_CIS):
            raise ValueError(f"cis_params holds {len(p['cis_params'])} entries; "
                             f"1..{self.MAX_CIS} allowed")
        seen = set()
        for entry in p['cis_params']:
            if len(entry) != 7:
                raise ValueError(f"each CIS needs 7 fields, got {len(entry)}")
            cis_id, sdu_c, sdu_p, phy_c, phy_p, rtn_c, rtn_p = entry
            if not (0x00 <= cis_id <= 0xEF):
                raise ValueError(f"cis_id 0x{cis_id:02X} out of range (0x00..0xEF)")
            if cis_id in seen:
                raise ValueError(f"duplicate cis_id 0x{cis_id:02X} in the same CIG")
            seen.add(cis_id)
            for sdu, name in ((sdu_c, "max_sdu_c_to_p"), (sdu_p, "max_sdu_p_to_c")):
                if not (0x0000 <= sdu <= 0x0FFF):
                    raise ValueError(f"{name} {sdu} out of range (0..4095)")
            _check_phy(phy_c, "phy_c_to_p")
            _check_phy(phy_p, "phy_p_to_c")
            for rtn, name in ((rtn_c, "rtn_c_to_p"), (rtn_p, "rtn_p_to_c")):
                if not (0x00 <= rtn <= 0xFF):
                    raise ValueError(f"{name} {rtn} out of range (0..255)")
            if sdu_c == 0 and sdu_p == 0:
                raise ValueError(
                    f"CIS 0x{cis_id:02X} has both Max_SDU values 0, so it would "
                    "carry no data in either direction")

    def _serialize_params(self) -> bytes:
        p = self.params
        out = bytearray([p['cig_id']])
        out += _u24(p['sdu_interval_c_to_p'], "sdu_interval_c_to_p")
        out += _u24(p['sdu_interval_p_to_c'], "sdu_interval_p_to_c")
        out += bytes([p['worst_case_sca'], p['packing'], p['framing']])
        out += struct.pack("<HHB", p['max_transport_latency_c_to_p'],
                           p['max_transport_latency_p_to_c'], len(p['cis_params']))
        # One block per CIS, fields interleaved -- not parallel arrays.
        for cis_id, sdu_c, sdu_p, phy_c, phy_p, rtn_c, rtn_p in p['cis_params']:
            out += struct.pack("<BHHBBBB", cis_id, sdu_c, sdu_p,
                               phy_c, phy_p, rtn_c, rtn_p)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetCigParameters":
        if len(data) < 15:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 15")
        cig_id = data[0]
        sdu_c = int.from_bytes(data[1:4], "little")
        sdu_p = int.from_bytes(data[4:7], "little")
        sca, packing, framing = data[7], data[8], data[9]
        latency_c, latency_p, cis_count = struct.unpack_from("<HHB", data, 10)
        needed = 15 + cis_count * 9
        if len(data) < needed:
            raise ValueError(f"Invalid data length: {len(data)}, expected {needed}")
        cis_params = [struct.unpack_from("<BHHBBBB", data, 15 + i * 9)
                      for i in range(cis_count)]
        return cls(cig_id, sdu_c, sdu_p, sca, packing, framing,
                   latency_c, latency_p, cis_params)

    def __str__(self) -> str:
        p = self.params
        return (f"{self.NAME} : 0x{self.OPCODE:04X} (CIG {p['cig_id']}, "
                f"{len(p['cis_params'])} CIS, "
                f"SDU {p['sdu_interval_c_to_p']}/{p['sdu_interval_p_to_c']} us, "
                f"{'framed' if p['framing'] else 'unframed'})")


class LeSetCigParametersTest(HciCmdBasePacket):
    """
    LE Set CIG Parameters Test Command (0x2062).

    The qualification form: the air schedule is given directly rather than
    derived. `cis_params` is a list of
    `(cis_id, nse, max_sdu_c_to_p, max_sdu_p_to_c, max_pdu_c_to_p,
      max_pdu_p_to_c, phy_c_to_p, phy_p_to_c, bn_c_to_p, bn_p_to_c)`.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_CIG_PARAMS_TEST)
    NAME = "LE_Set_CIG_Parameters_Test"

    MAX_CIS = 0x1F

    #: (cis_id, nse, sdu_c, sdu_p, pdu_c, pdu_p, phy_c, phy_p, bn_c, bn_p)
    DEFAULT_CIS = (0x00, 1, 40, 40, 40, 40,
                   int(IsoPhy.LE_2M), int(IsoPhy.LE_2M), 1, 1)

    def __init__(self, cig_id: int = 0x00,
                 sdu_interval_c_to_p: int = 10000,
                 sdu_interval_p_to_c: int = 10000,
                 ft_c_to_p: int = 1,
                 ft_p_to_c: int = 1,
                 iso_interval: int = 8,                # 10 ms in 1.25 ms units
                 worst_case_sca: int = ClockAccuracy.PPM_251_TO_500,
                 packing: int = IsoPacking.SEQUENTIAL,
                 framing: int = IsoFraming.UNFRAMED,
                 cis_params: Sequence[Tuple[int, ...]] = (DEFAULT_CIS,)):
        super().__init__(
            cig_id=cig_id,
            sdu_interval_c_to_p=sdu_interval_c_to_p,
            sdu_interval_p_to_c=sdu_interval_p_to_c,
            ft_c_to_p=ft_c_to_p,
            ft_p_to_c=ft_p_to_c,
            iso_interval=iso_interval,
            worst_case_sca=int(worst_case_sca),
            packing=int(packing),
            framing=int(framing),
            cis_params=[tuple(entry) for entry in cis_params],
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['cig_id'] <= 0xEF):
            raise ValueError(f"cig_id 0x{p['cig_id']:02X} out of range (0x00..0xEF)")
        _check_sdu_interval(p['sdu_interval_c_to_p'], "sdu_interval_c_to_p")
        _check_sdu_interval(p['sdu_interval_p_to_c'], "sdu_interval_p_to_c")
        for ft, name in ((p['ft_c_to_p'], "ft_c_to_p"), (p['ft_p_to_c'], "ft_p_to_c")):
            if not (0x01 <= ft <= 0xFF):
                raise ValueError(f"{name} {ft} out of range (1..255)")
        if not (0x0004 <= p['iso_interval'] <= 0x0C80):
            raise ValueError(f"iso_interval 0x{p['iso_interval']:04X} out of range "
                             "(0x0004..0x0C80, in 1.25 ms units)")
        if not (0x00 <= p['worst_case_sca'] <= 0x07):
            raise ValueError(f"worst_case_sca {p['worst_case_sca']} out of range (0..7)")

        if not (1 <= len(p['cis_params']) <= self.MAX_CIS):
            raise ValueError(f"cis_params holds {len(p['cis_params'])} entries; "
                             f"1..{self.MAX_CIS} allowed")
        for entry in p['cis_params']:
            if len(entry) != 10:
                raise ValueError(f"each CIS needs 10 fields, got {len(entry)}")
            (cis_id, nse, sdu_c, sdu_p, pdu_c, pdu_p,
             phy_c, phy_p, bn_c, bn_p) = entry
            if not (0x00 <= cis_id <= 0xEF):
                raise ValueError(f"cis_id 0x{cis_id:02X} out of range")
            if not (0x01 <= nse <= 0x1F):
                raise ValueError(f"nse {nse} out of range (1..31)")
            for value, name in ((sdu_c, "max_sdu_c_to_p"), (sdu_p, "max_sdu_p_to_c")):
                if not (0x0000 <= value <= 0x0FFF):
                    raise ValueError(f"{name} {value} out of range (0..4095)")
            for value, name in ((pdu_c, "max_pdu_c_to_p"), (pdu_p, "max_pdu_p_to_c")):
                if not (0x0000 <= value <= 0x00FB):
                    raise ValueError(f"{name} {value} out of range (0..251)")
            _check_phy(phy_c, "phy_c_to_p")
            _check_phy(phy_p, "phy_p_to_c")
            for value, name in ((bn_c, "bn_c_to_p"), (bn_p, "bn_p_to_c")):
                if not (0x00 <= value <= 0x0F):
                    raise ValueError(f"{name} {value} out of range (0..15)")

    def _serialize_params(self) -> bytes:
        p = self.params
        out = bytearray([p['cig_id']])
        out += _u24(p['sdu_interval_c_to_p'], "sdu_interval_c_to_p")
        out += _u24(p['sdu_interval_p_to_c'], "sdu_interval_p_to_c")
        out += bytes([p['ft_c_to_p'], p['ft_p_to_c']])
        out += struct.pack("<H", p['iso_interval'])
        out += bytes([p['worst_case_sca'], p['packing'], p['framing'],
                      len(p['cis_params'])])
        for entry in p['cis_params']:
            out += struct.pack("<BBHHHHBBBB", *entry)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetCigParametersTest":
        if len(data) < 15:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 15")
        cig_id = data[0]
        sdu_c = int.from_bytes(data[1:4], "little")
        sdu_p = int.from_bytes(data[4:7], "little")
        ft_c, ft_p = data[7], data[8]
        iso_interval = struct.unpack_from("<H", data, 9)[0]
        sca, packing, framing, cis_count = data[11], data[12], data[13], data[14]
        needed = 15 + cis_count * 14
        if len(data) < needed:
            raise ValueError(f"Invalid data length: {len(data)}, expected {needed}")
        cis_params = [struct.unpack_from("<BBHHHHBBBB", data, 15 + i * 14)
                      for i in range(cis_count)]
        return cls(cig_id, sdu_c, sdu_p, ft_c, ft_p, iso_interval, sca,
                   packing, framing, cis_params)


class LeCreateCis(HciCmdBasePacket):
    """
    LE Create CIS Command (0x2063).

    `cis_connections` pairs each CIS handle from Set CIG Parameters with the ACL
    handle it runs over: `[(cis_handle, acl_handle), ...]`. Central only.

    Answers with Command Status; each stream then reports separately with
    LE CIS Established.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_CIS)
    NAME = "LE_Create_CIS"

    MAX_CIS = 0x1F

    def __init__(self, cis_connections: Sequence[Tuple[int, int]] = ((0x0000, 0x0000),)):
        super().__init__(cis_connections=[tuple(entry) for entry in cis_connections])

    def _validate_params(self) -> None:
        entries = self.params['cis_connections']
        if not (1 <= len(entries) <= self.MAX_CIS):
            raise ValueError(f"cis_connections holds {len(entries)} entries; "
                             f"1..{self.MAX_CIS} allowed")
        for entry in entries:
            if len(entry) != 2:
                raise ValueError("each entry is (cis_handle, acl_handle)")
            _check_handle(entry[0], "cis_handle")
            _check_handle(entry[1], "acl_connection_handle")

    def _serialize_params(self) -> bytes:
        entries = self.params['cis_connections']
        out = bytearray([len(entries)])
        for cis_handle, acl_handle in entries:
            out += struct.pack("<HH", cis_handle, acl_handle)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCreateCis":
        if not data:
            raise ValueError("LE_Create_CIS: empty parameters")
        count = data[0]
        needed = 1 + count * 4
        if len(data) < needed:
            raise ValueError(f"Invalid data length: {len(data)}, expected {needed}")
        return cls([struct.unpack_from("<HH", data, 1 + i * 4) for i in range(count)])


class LeRemoveCig(HciCmdBasePacket):
    """
    LE Remove CIG Command (0x2064).

    Only valid once every CIS in the group is disconnected -- otherwise the
    controller answers Command Disallowed.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_CIG)
    NAME = "LE_Remove_CIG"

    def __init__(self, cig_id: int = 0x00):
        super().__init__(cig_id=cig_id)

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['cig_id'] <= 0xEF):
            raise ValueError(f"cig_id 0x{self.params['cig_id']:02X} out of range")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['cig_id']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeRemoveCig":
        if not data:
            raise ValueError("LE_Remove_CIG: empty parameters")
        return cls(data[0])


class LeAcceptCisRequest(HciCmdBasePacket):
    """
    LE Accept CIS Request Command (0x2065).

    The peripheral's answer to LE CIS Request. The handle is the CIS handle from
    that event, not the ACL handle.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ACCEPT_CIS_REQUEST)
    NAME = "LE_Accept_CIS_Request"

    def __init__(self, connection_handle: int = 0x0000):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeAcceptCisRequest":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


class LeRejectCisRequest(HciCmdBasePacket):
    """LE Reject CIS Request Command (0x2066)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REJECT_CIS_REQUEST)
    NAME = "LE_Reject_CIS_Request"

    def __init__(self, connection_handle: int = 0x0000,
                 reason: int = TERMINATE_REASON_REMOTE_USER):
        super().__init__(connection_handle=connection_handle, reason=reason)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        if not (0x00 <= self.params['reason'] <= 0xFF):
            raise ValueError(f"Invalid reason: {self.params['reason']}")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['connection_handle'],
                           self.params['reason'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeRejectCisRequest":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, reason = struct.unpack_from("<HB", data, 0)
        return cls(handle, reason)


# =================================================================== BIG / BIS

class LeCreateBig(HciCmdBasePacket):
    """
    LE Create BIG Command (0x2067).

    `adv_handle` names an advertising set that already has periodic advertising
    configured and enabled -- the BIGInfo receivers need is carried in that
    periodic train, so without it nothing can ever sync.

    `broadcast_code` is 16 bytes and only used when `encryption` is set.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_BIG)
    NAME = "LE_Create_BIG"

    BROADCAST_CODE_LENGTH = 16

    def __init__(self, big_handle: int = 0x00,
                 adv_handle: int = 0x00,
                 num_bis: int = 1,
                 sdu_interval: int = 10000,            # us
                 max_sdu: int = 40,
                 max_transport_latency: int = 10,      # ms
                 rtn: int = 2,
                 phy: int = IsoPhy.LE_2M,
                 packing: int = IsoPacking.SEQUENTIAL,
                 framing: int = IsoFraming.UNFRAMED,
                 encryption: int = 0,
                 broadcast_code: bytes = b"\x00" * 16):
        super().__init__(
            big_handle=big_handle, adv_handle=adv_handle, num_bis=num_bis,
            sdu_interval=sdu_interval, max_sdu=max_sdu,
            max_transport_latency=max_transport_latency, rtn=rtn, phy=int(phy),
            packing=int(packing), framing=int(framing),
            encryption=int(bool(encryption)),
            broadcast_code=bytes(broadcast_code).ljust(16, b"\x00")[:16],
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['big_handle'] <= 0xEF):
            raise ValueError(f"big_handle 0x{p['big_handle']:02X} out of range")
        if not (0x00 <= p['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{p['adv_handle']:02X} out of range")
        if not (0x01 <= p['num_bis'] <= 0x1F):
            raise ValueError(f"num_bis {p['num_bis']} out of range (1..31)")
        _check_sdu_interval(p['sdu_interval'], "sdu_interval")
        if not (0x0001 <= p['max_sdu'] <= 0x0FFF):
            raise ValueError(f"max_sdu {p['max_sdu']} out of range (1..4095)")
        _check_latency(p['max_transport_latency'], "max_transport_latency")
        if not (0x00 <= p['rtn'] <= 0x1E):
            raise ValueError(f"rtn {p['rtn']} out of range (0..30)")
        _check_phy(p['phy'], "phy")
        if p['packing'] not in (0x00, 0x01):
            raise ValueError(f"Invalid packing: {p['packing']}")
        if p['framing'] not in (0x00, 0x01):
            raise ValueError(f"Invalid framing: {p['framing']}")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([p['big_handle'], p['adv_handle'], p['num_bis']])
                + _u24(p['sdu_interval'], "sdu_interval")
                + struct.pack("<HHBBBBB", p['max_sdu'], p['max_transport_latency'],
                              p['rtn'], p['phy'], p['packing'], p['framing'],
                              p['encryption'])
                + p['broadcast_code'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCreateBig":
        if len(data) < 31:
            raise ValueError(f"Invalid data length: {len(data)}, expected 31")
        big_handle, adv_handle, num_bis = data[0], data[1], data[2]
        sdu_interval = int.from_bytes(data[3:6], "little")
        (max_sdu, latency, rtn, phy, packing,
         framing, encryption) = struct.unpack_from("<HHBBBBB", data, 6)
        return cls(big_handle, adv_handle, num_bis, sdu_interval, max_sdu,
                   latency, rtn, phy, packing, framing, encryption, data[15:31])

    def __str__(self) -> str:
        p = self.params
        return (f"{self.NAME} : 0x{self.OPCODE:04X} (BIG {p['big_handle']} on "
                f"adv set {p['adv_handle']}, {p['num_bis']} BIS, "
                f"{'encrypted' if p['encryption'] else 'clear'})")


class LeCreateBigTest(HciCmdBasePacket):
    """
    LE Create BIG Test Command (0x2068).

    The qualification form of Create BIG: NSE, BN, IRC and PTO are given rather
    than derived from latency and RTN.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CREATE_BIG_TEST)
    NAME = "LE_Create_BIG_Test"

    def __init__(self, big_handle: int = 0x00,
                 adv_handle: int = 0x00,
                 num_bis: int = 1,
                 sdu_interval: int = 10000,
                 iso_interval: int = 8,               # 1.25 ms units
                 nse: int = 1,
                 max_sdu: int = 40,
                 max_pdu: int = 40,
                 phy: int = IsoPhy.LE_2M,
                 packing: int = IsoPacking.SEQUENTIAL,
                 framing: int = IsoFraming.UNFRAMED,
                 bn: int = 1,
                 irc: int = 1,
                 pto: int = 0,
                 encryption: int = 0,
                 broadcast_code: bytes = b"\x00" * 16):
        super().__init__(
            big_handle=big_handle, adv_handle=adv_handle, num_bis=num_bis,
            sdu_interval=sdu_interval, iso_interval=iso_interval, nse=nse,
            max_sdu=max_sdu, max_pdu=max_pdu, phy=int(phy),
            packing=int(packing), framing=int(framing), bn=bn, irc=irc, pto=pto,
            encryption=int(bool(encryption)),
            broadcast_code=bytes(broadcast_code).ljust(16, b"\x00")[:16],
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['big_handle'] <= 0xEF):
            raise ValueError(f"big_handle 0x{p['big_handle']:02X} out of range")
        if not (0x00 <= p['adv_handle'] <= 0xEF):
            raise ValueError(f"adv_handle 0x{p['adv_handle']:02X} out of range")
        if not (0x01 <= p['num_bis'] <= 0x1F):
            raise ValueError(f"num_bis {p['num_bis']} out of range (1..31)")
        _check_sdu_interval(p['sdu_interval'], "sdu_interval")
        if not (0x0004 <= p['iso_interval'] <= 0x0C80):
            raise ValueError(f"iso_interval 0x{p['iso_interval']:04X} out of range "
                             "(0x0004..0x0C80, in 1.25 ms units)")
        if not (0x01 <= p['nse'] <= 0x1F):
            raise ValueError(f"nse {p['nse']} out of range (1..31)")
        if not (0x0001 <= p['max_sdu'] <= 0x0FFF):
            raise ValueError(f"max_sdu {p['max_sdu']} out of range (1..4095)")
        if not (0x0000 <= p['max_pdu'] <= 0x00FB):
            raise ValueError(f"max_pdu {p['max_pdu']} out of range (0..251)")
        _check_phy(p['phy'], "phy")
        if not (0x01 <= p['bn'] <= 0x07):
            raise ValueError(f"bn {p['bn']} out of range (1..7)")
        if not (0x01 <= p['irc'] <= 0x0F):
            raise ValueError(f"irc {p['irc']} out of range (1..15)")
        if not (0x00 <= p['pto'] <= 0x0F):
            raise ValueError(f"pto {p['pto']} out of range (0..15)")
        # The spec ties these together: the bursts have to divide the subevents.
        if p['nse'] % p['bn']:
            raise ValueError(f"nse ({p['nse']}) must be a multiple of bn ({p['bn']})")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([p['big_handle'], p['adv_handle'], p['num_bis']])
                + _u24(p['sdu_interval'], "sdu_interval")
                + struct.pack("<HBHHBBBBBBB", p['iso_interval'], p['nse'],
                              p['max_sdu'], p['max_pdu'], p['phy'], p['packing'],
                              p['framing'], p['bn'], p['irc'], p['pto'],
                              p['encryption'])
                + p['broadcast_code'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeCreateBigTest":
        if len(data) < 36:
            raise ValueError(f"Invalid data length: {len(data)}, expected 36")
        big_handle, adv_handle, num_bis = data[0], data[1], data[2]
        sdu_interval = int.from_bytes(data[3:6], "little")
        (iso_interval, nse, max_sdu, max_pdu, phy, packing, framing,
         bn, irc, pto, encryption) = struct.unpack_from("<HBHHBBBBBBB", data, 6)
        return cls(big_handle, adv_handle, num_bis, sdu_interval, iso_interval,
                   nse, max_sdu, max_pdu, phy, packing, framing, bn, irc, pto,
                   encryption, data[20:36])


class LeTerminateBig(HciCmdBasePacket):
    """LE Terminate BIG Command (0x2069). Transmitter side."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.TERMINATE_BIG)
    NAME = "LE_Terminate_BIG"

    def __init__(self, big_handle: int = 0x00,
                 reason: int = TERMINATE_REASON_LOCAL_HOST):
        super().__init__(big_handle=big_handle, reason=reason)

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['big_handle'] <= 0xEF):
            raise ValueError(f"big_handle 0x{self.params['big_handle']:02X} "
                             "out of range")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['big_handle'], self.params['reason'] & 0xFF])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeTerminateBig":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(data[0], data[1])


class LeBigCreateSync(HciCmdBasePacket):
    """
    LE BIG Create Sync Command (0x206A). Receiver side.

    `sync_handle` comes from LE Periodic Advertising Sync Established -- the BIG
    is found through the periodic train, so that sync has to exist first.
    `bis_indices` selects which streams to receive, numbered from 1.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.BIG_CREATE_SYNC)
    NAME = "LE_BIG_Create_Sync"

    def __init__(self, big_handle: int = 0x00,
                 sync_handle: int = 0x0000,
                 encryption: int = 0,
                 broadcast_code: bytes = b"\x00" * 16,
                 mse: int = 0,                      # 0 = controller decides
                 big_sync_timeout: int = 100,       # 1 s, in 10 ms units
                 bis_indices: Sequence[int] = (1,)):
        super().__init__(
            big_handle=big_handle, sync_handle=sync_handle,
            encryption=int(bool(encryption)),
            broadcast_code=bytes(broadcast_code).ljust(16, b"\x00")[:16],
            mse=mse, big_sync_timeout=big_sync_timeout,
            bis_indices=[int(i) for i in bis_indices],
        )

    def _validate_params(self) -> None:
        p = self.params
        if not (0x00 <= p['big_handle'] <= 0xEF):
            raise ValueError(f"big_handle 0x{p['big_handle']:02X} out of range")
        if not (0x0000 <= p['sync_handle'] <= 0x0EFF):
            raise ValueError(f"Invalid sync_handle: 0x{p['sync_handle']:04X}")
        if not (0x00 <= p['mse'] <= 0x1F):
            raise ValueError(f"mse {p['mse']} out of range (0..31; 0 = controller "
                             "decides)")
        if not (0x000A <= p['big_sync_timeout'] <= 0x4000):
            raise ValueError(f"big_sync_timeout 0x{p['big_sync_timeout']:04X} out "
                             "of range (0x000A..0x4000, in 10 ms units)")
        indices = p['bis_indices']
        if not (1 <= len(indices) <= 0x1F):
            raise ValueError(f"bis_indices holds {len(indices)} entries; 1..31 allowed")
        if len(set(indices)) != len(indices):
            raise ValueError("bis_indices contains duplicates")
        for index in indices:
            if not (0x01 <= index <= 0x1F):
                raise ValueError(f"BIS index {index} out of range (1..31)")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (bytes([p['big_handle']])
                + struct.pack("<H", p['sync_handle'])
                + bytes([p['encryption']])
                + p['broadcast_code']
                + bytes([p['mse']])
                + struct.pack("<H", p['big_sync_timeout'])
                + bytes([len(p['bis_indices'])])
                + bytes(p['bis_indices']))

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeBigCreateSync":
        if len(data) < 25:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 25")
        big_handle = data[0]
        sync_handle = struct.unpack_from("<H", data, 1)[0]
        encryption = data[3]
        broadcast_code = data[4:20]
        mse = data[20]
        timeout = struct.unpack_from("<H", data, 21)[0]
        count = data[23]
        if len(data) < 24 + count:
            raise ValueError(f"Invalid data length: {len(data)}, expected "
                             f"{24 + count}")
        return cls(big_handle, sync_handle, encryption, broadcast_code, mse,
                   timeout, list(data[24:24 + count]))


class LeBigTerminateSync(HciCmdBasePacket):
    """LE BIG Terminate Sync Command (0x206B). Receiver side."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.BIG_TERMINATE_SYNC)
    NAME = "LE_BIG_Terminate_Sync"

    def __init__(self, big_handle: int = 0x00):
        super().__init__(big_handle=big_handle)

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['big_handle'] <= 0xEF):
            raise ValueError(f"big_handle 0x{self.params['big_handle']:02X} "
                             "out of range")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['big_handle']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeBigTerminateSync":
        if not data:
            raise ValueError("LE_BIG_Terminate_Sync: empty parameters")
        return cls(data[0])


# ============================================================== ISO data paths

class LeSetupIsoDataPath(HciCmdBasePacket):
    """
    LE Setup ISO Data Path Command (0x206D).

    Connects one direction of a CIS/BIS to a source or sink. `data_path_id` 0x00
    is the HCI transport itself, which is what you want when the host sends or
    receives the ISO data over this very link; a vendor id routes it to on-chip
    audio instead.

    Each direction is set up separately, and a direction that is not set up
    silently carries nothing -- a common reason a stream "connects" but no audio
    ever flows.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SETUP_ISO_DATA_PATH)
    NAME = "LE_Setup_ISO_Data_Path"

    def __init__(self, connection_handle: int = 0x0000,
                 data_path_direction: int = DataPathDirection.INPUT,
                 data_path_id: int = DataPathId.HCI,
                 coding_format: int = CodingFormat.TRANSPARENT,
                 company_id: int = 0x0000,
                 vendor_codec_id: int = 0x0000,
                 controller_delay: int = 0,          # microseconds
                 codec_configuration: bytes = b''):
        super().__init__(
            connection_handle=connection_handle,
            data_path_direction=int(data_path_direction),
            data_path_id=int(data_path_id),
            coding_format=int(coding_format),
            company_id=company_id,
            vendor_codec_id=vendor_codec_id,
            controller_delay=controller_delay,
            codec_configuration=bytes(codec_configuration),
        )

    def _validate_params(self) -> None:
        p = self.params
        _check_handle(p['connection_handle'])
        if p['data_path_direction'] not in (0x00, 0x01):
            raise ValueError(f"Invalid data_path_direction: "
                             f"{p['data_path_direction']}; 0 = input, 1 = output")
        if not (0x00 <= p['data_path_id'] <= 0xFF):
            raise ValueError(f"Invalid data_path_id: {p['data_path_id']}")
        if not (0 <= p['controller_delay'] <= 0x3D0900):
            raise ValueError(f"controller_delay {p['controller_delay']} us out of "
                             "range (0..4000000 microseconds)")
        if len(p['codec_configuration']) > 0xFF:
            raise ValueError("codec_configuration too long for a one-byte length")
        # A vendor coding format is meaningless without a company to scope it.
        if p['coding_format'] == int(CodingFormat.VENDOR_SPECIFIC) \
                and not p['company_id']:
            raise ValueError("coding_format 0xFF (vendor specific) needs a "
                             "non-zero company_id")

    def _serialize_params(self) -> bytes:
        p = self.params
        return (struct.pack("<HBBB", p['connection_handle'],
                            p['data_path_direction'], p['data_path_id'],
                            p['coding_format'])
                + struct.pack("<HH", p['company_id'], p['vendor_codec_id'])
                + _u24(p['controller_delay'], "controller_delay")
                + bytes([len(p['codec_configuration'])])
                + p['codec_configuration'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetupIsoDataPath":
        if len(data) < 13:
            raise ValueError(f"Invalid data length: {len(data)}, expected >= 13")
        handle, direction, path_id, coding = struct.unpack_from("<HBBB", data, 0)
        company, vendor_codec = struct.unpack_from("<HH", data, 5)
        delay = int.from_bytes(data[9:12], "little")
        config_len = data[12]
        return cls(handle, direction, path_id, coding, company, vendor_codec,
                   delay, data[13:13 + config_len])


class LeRemoveIsoDataPath(HciCmdBasePacket):
    """
    LE Remove ISO Data Path Command (0x206E).

    Note the direction field here is a **bitmap** (bit 0 input, bit 1 output),
    unlike the enum in Setup -- so both directions can go in one command.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_ISO_DATA_PATH)
    NAME = "LE_Remove_ISO_Data_Path"

    def __init__(self, connection_handle: int = 0x0000,
                 data_path_direction: int = DataPathDirectionMask.BOTH):
        super().__init__(connection_handle=connection_handle,
                         data_path_direction=int(data_path_direction))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        direction = self.params['data_path_direction']
        if not (0x01 <= direction <= 0x03):
            raise ValueError(f"data_path_direction 0x{direction:02X} must set at "
                             "least one of input (0x01) / output (0x02)")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['connection_handle'],
                           self.params['data_path_direction'])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeRemoveIsoDataPath":
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, direction = struct.unpack_from("<HB", data, 0)
        return cls(handle, direction)


# =============================================================== ISO test mode

class _IsoTestCommand(HciCmdBasePacket):
    """Shared body for the two ISO test-mode start commands."""

    def __init__(self, connection_handle: int = 0x0000,
                 payload_type: int = IsoPayloadType.MAXIMUM_LENGTH):
        super().__init__(connection_handle=connection_handle,
                         payload_type=int(payload_type))

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])
        if self.params['payload_type'] not in (0x00, 0x01, 0x02):
            raise ValueError(f"Invalid payload_type: {self.params['payload_type']}; "
                             "0 = zero length, 1 = variable, 2 = maximum")

    def _serialize_params(self) -> bytes:
        return struct.pack("<HB", self.params['connection_handle'],
                           self.params['payload_type'])

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected 3")
        handle, payload_type = struct.unpack_from("<HB", data, 0)
        return cls(handle, payload_type)


class LeIsoTransmitTest(_IsoTestCommand):
    """
    LE ISO Transmit Test Command (0x206F).

    The controller generates the test payloads itself, so no ISO data crosses
    HCI while this is running.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_TRANSMIT_TEST)
    NAME = "LE_ISO_Transmit_Test"


class LeIsoReceiveTest(_IsoTestCommand):
    """
    LE ISO Receive Test Command (0x2070).

    The controller checks the received payloads itself and counts them; read the
    tally with LE ISO Read Test Counters.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_RECEIVE_TEST)
    NAME = "LE_ISO_Receive_Test"


class _IsoHandleCommand(HciCmdBasePacket):
    """Shared body for the ISO commands that take only a connection handle."""

    def __init__(self, connection_handle: int = 0x0000):
        super().__init__(connection_handle=connection_handle)

    def _validate_params(self) -> None:
        _check_handle(self.params['connection_handle'])

    def _serialize_params(self) -> bytes:
        return struct.pack("<H", self.params['connection_handle'])

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(struct.unpack_from("<H", data, 0)[0])


class LeIsoReadTestCounters(_IsoHandleCommand):
    """
    LE ISO Read Test Counters Command (0x2071).

    Returns received / missed / failed SDU counts. Only meaningful while a
    receive test is running -- the counters reset when it ends.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_READ_TEST_COUNTERS)
    NAME = "LE_ISO_Read_Test_Counters"


class LeIsoTestEnd(_IsoHandleCommand):
    """LE ISO Test End Command (0x2072). Returns the final counters."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ISO_TEST_END)
    NAME = "LE_ISO_Test_End"


class LeReadIsoTxSync(_IsoHandleCommand):
    """
    LE Read ISO TX Sync Command (0x2060).

    The packet sequence number and transmit timestamp of the most recent SDU --
    what a host uses to align its own audio clock to the controller's.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_ISO_TX_SYNC)
    NAME = "LE_Read_ISO_TX_Sync"


class LeReadIsoLinkQuality(_IsoHandleCommand):
    """
    LE Read ISO Link Quality Command (0x2074).

    Per-stream error counters: CRC failures, unreceived and missed packets.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_ISO_LINK_QUALITY)
    NAME = "LE_Read_ISO_Link_Quality"


class LeRequestPeerSca(_IsoHandleCommand):
    """
    LE Request Peer SCA Command (0x206C).

    Asks the peer for its sleep clock accuracy over an ACL link. Worth doing
    before setting up a CIG, since the CIG takes the *worst case* SCA and
    guessing pessimistically costs airtime.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REQUEST_PEER_SCA)
    NAME = "LE_Request_Peer_SCA"


class LeSetHostFeature(HciCmdBasePacket):
    """
    LE Set Host Feature Command (0x2073).

    Announces a host-side feature to the controller. Bit 32 (Connected
    Isochronous Streams) has to be set before any CIG command is accepted, which
    is why it lives with the ISO commands rather than in `misc`.

    Only accepted while there are no connections.
    """

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.SET_HOST_FEATURE)
    NAME = "LE_Set_Host_Feature"

    def __init__(self, bit_number: int = HostFeatureBit.CONNECTED_ISOCHRONOUS_STREAMS,
                 bit_value: int = 1):
        super().__init__(bit_number=int(bit_number), bit_value=int(bool(bit_value)))

    def _validate_params(self) -> None:
        if not (0x00 <= self.params['bit_number'] <= 0x3F):
            raise ValueError(f"bit_number {self.params['bit_number']} out of range "
                             "(0..63)")

    def _serialize_params(self) -> bytes:
        return bytes([self.params['bit_number'], self.params['bit_value']])

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeSetHostFeature":
        if len(data) < 2:
            raise ValueError(f"Invalid data length: {len(data)}, expected 2")
        return cls(data[0], data[1])

    def __str__(self) -> str:
        p = self.params
        try:
            name = HostFeatureBit(p['bit_number']).name.replace("_", " ").title()
        except ValueError:
            name = f"bit {p['bit_number']}"
        return (f"{self.NAME} : 0x{self.OPCODE:04X} ({name} "
                f"{'on' if p['bit_value'] else 'off'})")


# ------------------------------------------------------------ helper builders

def le_set_cig_parameters(cig_id=0x00, **kwargs):
    return LeSetCigParameters(cig_id, **kwargs)


def le_set_cig_parameters_test(cig_id=0x00, **kwargs):
    return LeSetCigParametersTest(cig_id, **kwargs)


def le_create_cis(cis_connections):
    return LeCreateCis(cis_connections)


def le_remove_cig(cig_id=0x00):
    return LeRemoveCig(cig_id)


def le_accept_cis_request(connection_handle):
    return LeAcceptCisRequest(connection_handle)


def le_reject_cis_request(connection_handle, reason=TERMINATE_REASON_REMOTE_USER):
    return LeRejectCisRequest(connection_handle, reason)


def le_create_big(big_handle=0x00, adv_handle=0x00, **kwargs):
    return LeCreateBig(big_handle, adv_handle, **kwargs)


def le_create_big_test(big_handle=0x00, adv_handle=0x00, **kwargs):
    return LeCreateBigTest(big_handle, adv_handle, **kwargs)


def le_terminate_big(big_handle=0x00, reason=TERMINATE_REASON_LOCAL_HOST):
    return LeTerminateBig(big_handle, reason)


def le_big_create_sync(big_handle, sync_handle, **kwargs):
    return LeBigCreateSync(big_handle, sync_handle, **kwargs)


def le_big_terminate_sync(big_handle=0x00):
    return LeBigTerminateSync(big_handle)


def le_setup_iso_data_path(connection_handle, **kwargs):
    return LeSetupIsoDataPath(connection_handle, **kwargs)


def le_remove_iso_data_path(connection_handle,
                            data_path_direction=DataPathDirectionMask.BOTH):
    return LeRemoveIsoDataPath(connection_handle, data_path_direction)


def le_iso_transmit_test(connection_handle,
                         payload_type=IsoPayloadType.MAXIMUM_LENGTH):
    return LeIsoTransmitTest(connection_handle, payload_type)


def le_iso_receive_test(connection_handle,
                        payload_type=IsoPayloadType.MAXIMUM_LENGTH):
    return LeIsoReceiveTest(connection_handle, payload_type)


def le_iso_read_test_counters(connection_handle):
    return LeIsoReadTestCounters(connection_handle)


def le_iso_test_end(connection_handle):
    return LeIsoTestEnd(connection_handle)


def le_read_iso_tx_sync(connection_handle):
    return LeReadIsoTxSync(connection_handle)


def le_read_iso_link_quality(connection_handle):
    return LeReadIsoLinkQuality(connection_handle)


def le_request_peer_sca(connection_handle):
    return LeRequestPeerSca(connection_handle)


def le_set_host_feature(bit_number=HostFeatureBit.CONNECTED_ISOCHRONOUS_STREAMS,
                        bit_value=1):
    return LeSetHostFeature(bit_number, bit_value)


for _cls in (LeReadIsoTxSync, LeSetCigParameters, LeSetCigParametersTest,
             LeCreateCis, LeRemoveCig, LeAcceptCisRequest, LeRejectCisRequest,
             LeCreateBig, LeCreateBigTest, LeTerminateBig, LeBigCreateSync,
             LeBigTerminateSync, LeRequestPeerSca, LeSetupIsoDataPath,
             LeRemoveIsoDataPath, LeIsoTransmitTest, LeIsoReceiveTest,
             LeIsoReadTestCounters, LeIsoTestEnd, LeSetHostFeature,
             LeReadIsoLinkQuality):
    register_command(_cls)
del _cls


__all__ = [
    'IsoPacking',
    'IsoFraming',
    'IsoPhy',
    'ClockAccuracy',
    'DataPathDirection',
    'DataPathDirectionMask',
    'DataPathId',
    'CodingFormat',
    'IsoPayloadType',
    'HostFeatureBit',
    'TERMINATE_REASON_LOCAL_HOST',
    'TERMINATE_REASON_REMOTE_USER',
    'LeReadIsoTxSync',
    'LeSetCigParameters',
    'LeSetCigParametersTest',
    'LeCreateCis',
    'LeRemoveCig',
    'LeAcceptCisRequest',
    'LeRejectCisRequest',
    'LeCreateBig',
    'LeCreateBigTest',
    'LeTerminateBig',
    'LeBigCreateSync',
    'LeBigTerminateSync',
    'LeRequestPeerSca',
    'LeSetupIsoDataPath',
    'LeRemoveIsoDataPath',
    'LeIsoTransmitTest',
    'LeIsoReceiveTest',
    'LeIsoReadTestCounters',
    'LeIsoTestEnd',
    'LeSetHostFeature',
    'LeReadIsoLinkQuality',
    'le_set_cig_parameters',
    'le_set_cig_parameters_test',
    'le_create_cis',
    'le_remove_cig',
    'le_accept_cis_request',
    'le_reject_cis_request',
    'le_create_big',
    'le_create_big_test',
    'le_terminate_big',
    'le_big_create_sync',
    'le_big_terminate_sync',
    'le_setup_iso_data_path',
    'le_remove_iso_data_path',
    'le_iso_transmit_test',
    'le_iso_receive_test',
    'le_iso_read_test_counters',
    'le_iso_test_end',
    'le_read_iso_tx_sync',
    'le_read_iso_link_quality',
    'le_request_peer_sca',
    'le_set_host_feature',
]
