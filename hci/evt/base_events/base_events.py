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
        status_desc = get_status_description(self.params['status'])
        return (f"Command_Status: "
                f"Opcode=0x{self.params['opcode']:04X}, \r\n"
                f"NumPackets={self.params['num_hci_command_packets']}, \r\n"
                f"Status={status_desc} (0x{self.params['status']:02X}), \r\n" )



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
    def from_bytes(cls, data: bytes) -> 'CommandCompleteEvent':
        """Create Command Complete Event from parameter bytes (excluding header)"""
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected 4 bytes")
        
        num_hci_command_packets, opcode, status = struct.unpack("<BHB", data[:4])
        return cls(num_hci_command_packets, opcode, status)
    
    @classmethod
    def get_basic_event_data(cls, data: bytes) -> tuple[int, int, int, bytes]:
        """Get basic event data from bytes"""
        if len(data) < 4:
            raise ValueError(f"Invalid data length: {len(data)}, expected at least 4 bytes")
        
        num_hci_command_packets, opcode, status = struct.unpack("<BHB", data[:4])
        return num_hci_command_packets, opcode, status, data[4:]
    

    def __str__(self) -> str:
        """String representation of the command complete event"""
        status_desc = get_status_description(self.params['status']) if self.params.get('status') is not None else "Unknown"
        name = getattr(self.__class__, 'NAME', OPCODE_TO_NAME.get(self.params['opcode'], 'UNKNOWN'))
        return (f"Command_Complete: 0x{(self.EVENT_CODE or 0xFF):02X} \r\n"
                f"{name}->0x{self.params['opcode']:04X}, \r\n"
                f"NumPackets={self.params['num_hci_command_packets']}, \r\n"
                f"Status={status_desc} (0x{self.params['status']:02X}), \r\n")
        


register_event(CommandStatusEvent)

# we should not register the as multiple flavours are there of it
# register_event(CommandCompleteEvent)