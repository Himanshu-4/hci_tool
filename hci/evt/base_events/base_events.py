from ..evt_base_packet import HciEvtBasePacket
from ...cmd.cmd_opcodes import StatusOCF,OGF,OPCODE_TO_NAME

from ..error_codes import StatusCode, get_status_description
from ..evt_codes import HciEventCode
from .. import register_event
import struct
from typing import Union, ClassVar, Optional

class CommandStatusEvent(HciEvtBasePacket):
    """Command Status Event"""
    EVENT_CODE =  HciEventCode.COMMAND_STATUS # Command Status Event Code
    NAME = "Command_Status"
    
    def __init__(self, status: Union[int, StatusCode], num_hci_command_packets: int, opcode: int):
        if isinstance(status, StatusCode):
            status = status.value
        
        super().__init__(
            status=status,
            num_hci_command_packets=num_hci_command_packets,
            opcode=opcode
        )
    
    def _serialize_params(self) -> bytes:
        return struct.pack("<BBH",
                          self.params['status'],
                          self.params['num_hci_command_packets'],
                          self.params['opcode'])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'CommandStatusEvent':
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4 bytes")
        
        status, num_packets, opcode = struct.unpack("<BBH", data[:4])
        return cls(status, num_packets, opcode)
    
    def __str__(self) -> str:
        opcode = self.params['opcode']
        name = OPCODE_TO_NAME.get(opcode, f"Opcode_0x{opcode:04X}")
        status = self.params['status']
        return (f"Command_Status: {name} (0x{opcode:04X}), "
                f"NumPackets={self.params['num_hci_command_packets']}, "
                f"Status={get_status_description(status)} (0x{status:02X})")



class CommandCompleteEvent(HciEvtBasePacket):
    """Command Status Event
    This event is sent by the controller to the host when a command has been completed.
    It contains the number of HCI command packets that were sent to the controller, the command opcode,
    and the status of the command execution.
    so this class only know status and opcode, the rest is not known
    """
    EVENT_CODE =  HciEventCode.COMMAND_COMPLETE # Command Status Event Code
    NAME : ClassVar[str]
    OPCODE : ClassVar[int]
    
    def __init__(self, num_hci_command_packets: int, opcode: int, status: Optional[Union[int, StatusCode]] = None, **kwargs):
        """
        Initialize Command Complete Event
        Args:
            num_hci_command_packets: Number of HCI command packets
            opcode: Command opcode (2 bytes)
            status: Status code (1 byte), can be an integer or StatusCode enum
        """
        if not isinstance(num_hci_command_packets, int) or num_hci_command_packets < 0:
            raise ValueError(f"Invalid num_hci_command_packets: {num_hci_command_packets}, must be a non-negative integer")
        if isinstance(status, StatusCode):
            status = status.value
        # call the base class constructor
        super().__init__(
            num_hci_command_packets=num_hci_command_packets,
            opcode=opcode,
            status = status,
            **kwargs
        )
    
    def _serialize_params(self) -> bytes:
        return struct.pack("<BHB",
                          self.params['num_hci_command_packets'],
                          self.params['opcode'],
                            self.params['status'] if self.params.get('status') is not None else 0x00
                          )
    
    def _validate_params(self) -> None:
       pass  # No specific validation needed for this event
   
    @classmethod
    def from_bytes(cls, data: bytes, sub_event_code: Optional[int] = None) -> 'CommandCompleteEvent':
        """
        Create Command Complete Event from parameter bytes (header excluded).

        Anything past the status byte is command-specific and is kept verbatim in
        `return_params` -- callers that know the opcode (e.g. Read_BD_ADDR) can
        decode it; everyone else can still log it.
        """
        if len(data) < 3:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 3 bytes")

        num_hci_command_packets, opcode = struct.unpack("<BH", data[:3])
        status = data[3] if len(data) > 3 else None
        return cls(num_hci_command_packets, opcode, status,
                   return_params=bytes(data[4:]))
    
    @classmethod
    def get_basic_event_data(cls, data: bytes) -> tuple[int, int, int, bytes]:
        """Get basic event data from bytes"""
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 4 bytes")
        
        num_hci_command_packets, opcode, status = struct.unpack("<BHB", data[:4])
        return num_hci_command_packets, opcode, status, data[4:]
    

    def __str__(self) -> str:
        """String representation of the command complete event"""
        opcode = self.params.get('opcode', 0)
        # A per-opcode subclass carries a meaningful NAME; the generic fallback
        # does not, so resolve from the opcode table in that case.
        name = getattr(self.__class__, 'NAME', None)
        if not name or name in ("Unknown_Event", "Command_Complete"):
            name = OPCODE_TO_NAME.get(opcode, f"Opcode_0x{opcode:04X}")
        status = self.params.get('status')

        text = (f"Command_Complete: {name} (0x{opcode:04X}), "
                f"NumPackets={self.params.get('num_hci_command_packets')}")
        if status is not None:
            text += f", Status={get_status_description(status)} (0x{status:02X})"
        extra = self.params.get('return_params')
        if extra:
            text += f", ReturnParams={extra.hex(' ')}"
        return text
        


register_event(CommandStatusEvent)

# Registered as the *fallback* decoder for event code 0x0E. Per-opcode flavours
# (ReadBdAddrComplete and friends) live in `_cmd_complete_evt_registery` and win
# the lookup; this one catches every other opcode so a plain
# "status only" Command Complete still parses instead of raising.
register_event(CommandCompleteEvent)