"""
LE Filter Accept List commands (the list formerly called the White List).

    0x200F  LE_Read_Filter_Accept_List_Size
    0x2010  LE_Clear_Filter_Accept_List
    0x2011  LE_Add_Device_To_Filter_Accept_List
    0x2012  LE_Remove_Device_From_Filter_Accept_List

Every scan/advertise/initiate filter policy in the tool refers to this list, so
without a way to populate it the "Filter Accept List only" options do nothing but
make the controller ignore everything.

The controller rejects all three modifying commands with Command Disallowed
while the list is in use -- that is, while advertising, scanning or initiating
with a policy that reads it. Stop those first.
"""

from __future__ import annotations

from enum import IntEnum, unique
from typing import Union

from .. import register_command
from ..cmd_base_packet import HciCmdBasePacket
from ..cmd_opcodes import LEControllerOCF, OGF, create_opcode
from .advertisement import _coerce_addr


@unique
class FilterAcceptListAddressType(IntEnum):
    """`Address_Type` for the add/remove commands."""

    PUBLIC = 0x00
    RANDOM = 0x01
    #: Anonymous advertisers have no address; 0xFF is the only way to match them
    #: and the Address field is then ignored.
    ANONYMOUS = 0xFF


class LeReadFilterAcceptListSize(HciCmdBasePacket):
    """LE Read Filter Accept List Size Command (0x200F)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.READ_WHITE_LIST_SIZE)
    NAME = "LE_Read_Filter_Accept_List_Size"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeReadFilterAcceptListSize":
        return cls()


class LeClearFilterAcceptList(HciCmdBasePacket):
    """LE Clear Filter Accept List Command (0x2010)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.CLEAR_WHITE_LIST)
    NAME = "LE_Clear_Filter_Accept_List"

    def __init__(self):
        super().__init__()

    def _serialize_params(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls, data: bytes) -> "LeClearFilterAcceptList":
        return cls()


class _FilterAcceptListEntry(HciCmdBasePacket):
    """Shared body for add (0x2011) and remove (0x2012): same two fields."""

    def __init__(self, address: Union[bytes, str] = b"\x00" * 6,
                 address_type: int = FilterAcceptListAddressType.PUBLIC):
        super().__init__(address_type=int(address_type),
                         address=_coerce_addr(address))

    def _validate_params(self) -> None:
        addr_type = self.params['address_type']
        if addr_type not in (0x00, 0x01, 0xFF):
            raise ValueError(
                f"Invalid address_type: 0x{addr_type:02X}; expected 0x00 (public), "
                "0x01 (random) or 0xFF (anonymous)")

    def _serialize_params(self) -> bytes:
        return (bytes([self.params['address_type']])
                + bytes(reversed(self.params['address'])))

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < 7:
            raise ValueError(f"Invalid data length: {len(data)}, expected 7")
        return cls(bytes(reversed(data[1:7])), data[0])


class LeAddDeviceToFilterAcceptList(_FilterAcceptListEntry):
    """LE Add Device To Filter Accept List Command (0x2011)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.ADD_DEVICE_TO_WHITE_LIST)
    NAME = "LE_Add_Device_To_Filter_Accept_List"


class LeRemoveDeviceFromFilterAcceptList(_FilterAcceptListEntry):
    """LE Remove Device From Filter Accept List Command (0x2012)."""

    OPCODE = create_opcode(OGF.LE, LEControllerOCF.REMOVE_DEVICE_FROM_WHITE_LIST)
    NAME = "LE_Remove_Device_From_Filter_Accept_List"


# ------------------------------------------------------------ helper builders

def le_read_filter_accept_list_size() -> LeReadFilterAcceptListSize:
    return LeReadFilterAcceptListSize()


def le_clear_filter_accept_list() -> LeClearFilterAcceptList:
    return LeClearFilterAcceptList()


def le_add_device_to_filter_accept_list(address, address_type=0x00):
    return LeAddDeviceToFilterAcceptList(address, address_type)


def le_remove_device_from_filter_accept_list(address, address_type=0x00):
    return LeRemoveDeviceFromFilterAcceptList(address, address_type)


for _cls in (LeReadFilterAcceptListSize, LeClearFilterAcceptList,
             LeAddDeviceToFilterAcceptList, LeRemoveDeviceFromFilterAcceptList):
    register_command(_cls)
del _cls


__all__ = [
    'FilterAcceptListAddressType',
    'LeReadFilterAcceptListSize',
    'LeClearFilterAcceptList',
    'LeAddDeviceToFilterAcceptList',
    'LeRemoveDeviceFromFilterAcceptList',
    'le_read_filter_accept_list_size',
    'le_clear_filter_accept_list',
    'le_add_device_to_filter_accept_list',
    'le_remove_device_from_filter_accept_list',
]
