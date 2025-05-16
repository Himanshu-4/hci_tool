from enum import IntEnum

# define this enum for data type
    
class hci_msg_type(IntEnum):
    H4_TYPE_COMMAND = 1
    H4_TYPE_ACL = 2
    H4_TYPE_SCO = 3
    H4_TYPE_EVENT = 4