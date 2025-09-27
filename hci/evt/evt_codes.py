"""
Event codes for HCI events
"""
from enum import IntEnum, unique

# HCI Event Codes
@unique
class HciEventCode(IntEnum):
    INQUIRY_COMPLETE = 0x01
    INQUIRY_RESULT = 0x02
    CONNECTION_COMPLETE = 0x03
    CONNECTION_REQUEST = 0x04
    DISCONNECTION_COMPLETE = 0x05
    AUTHENTICATION_COMPLETE = 0x06
    REMOTE_NAME_REQUEST_COMPLETE = 0x07
    ENCRYPTION_CHANGE = 0x08
    CHANGE_CONNECTION_LINK_KEY_COMPLETE = 0x09
    MASTER_LINK_KEY_COMPLETE = 0x0A
    READ_REMOTE_SUPPORTED_FEATURES_COMPLETE = 0x0B
    READ_REMOTE_VERSION_INFORMATION_COMPLETE = 0x0C
    QOS_SETUP_COMPLETE = 0x0D
    COMMAND_COMPLETE = 0x0E
    COMMAND_STATUS = 0x0F
    HARDWARE_ERROR = 0x10
    FLUSH_OCCURRED = 0x11
    ROLE_CHANGE = 0x12
    NUMBER_OF_COMPLETED_PACKETS = 0x13
    MODE_CHANGE = 0x14
    RETURN_LINK_KEYS = 0x15
    PIN_CODE_REQUEST = 0x16
    LINK_KEY_REQUEST = 0x17
    LINK_KEY_NOTIFICATION = 0x18
    LOOPBACK_COMMAND = 0x19
    DATA_BUFFER_OVERFLOW = 0x1A
    MAX_SLOTS_CHANGE = 0x1B
    READ_CLOCK_OFFSET_COMPLETE = 0x1C
    CONNECTION_PACKET_TYPE_CHANGED = 0x1D
    QOS_VIOLATION = 0x1E
    PAGE_SCAN_REPETITION_MODE_CHANGE = 0x20
    FLOW_SPECIFICATION_COMPLETE = 0x21
    INQUIRY_RESULT_WITH_RSSI = 0x22
    READ_REMOTE_EXTENDED_FEATURES_COMPLETE = 0x23
    SYNCHRONOUS_CONNECTION_COMPLETE = 0x2C
    SYNCHRONOUS_CONNECTION_CHANGED = 0x2D
    SNIFF_SUBRATING = 0x2E
    EXTENDED_INQUIRY_RESULT = 0x2F
    ENCRYPTION_KEY_REFRESH_COMPLETE = 0x30
    IO_CAPABILITY_REQUEST = 0x31
    IO_CAPABILITY_RESPONSE = 0x32
    USER_CONFIRMATION_REQUEST = 0x33
    USER_PASSKEY_REQUEST = 0x34
    REMOTE_OOB_DATA_REQUEST = 0x35
    SIMPLE_PAIRING_COMPLETE = 0x36
    LINK_SUPERVISION_TIMEOUT_CHANGED = 0x38
    ENHANCED_FLUSH_COMPLETE = 0x39
    USER_PASSKEY_NOTIFICATION = 0x3B
    KEYPRESS_NOTIFICATION = 0x3C
    REMOTE_HOST_SUPPORTED_FEATURES_NOTIFICATION = 0x3D
    LE_META_EVENT = 0x3E
    PHYSICAL_LINK_COMPLETE = 0x40
    CHANNEL_SELECTED = 0x41
    DISCONNECTION_PHYSICAL_LINK_COMPLETE = 0x42
    PHYSICAL_LINK_LOSS_EARLY_WARNING = 0x43
    PHYSICAL_LINK_RECOVERY = 0x44
    LOGICAL_LINK_COMPLETE = 0x45
    DISCONNECTION_LOGICAL_LINK_COMPLETE = 0x46
    FLOW_SPEC_MODIFY_COMPLETE = 0x47
    NUMBER_OF_COMPLETED_DATA_BLOCKS = 0x48
    AMP_START_TEST = 0x49
    AMP_TEST_END = 0x4A
    AMP_RECEIVER_REPORT = 0x4B
    SHORT_RANGE_MODE_CHANGE_COMPLETE = 0x4C
    AMP_STATUS_CHANGE = 0x4D
    TRIGGERED_CLOCK_CAPTURE = 0x4E
    SYNCHRONIZATION_TRAIN_COMPLETE = 0x4F
    SYNCHRONIZATION_TRAIN_RECEIVED = 0x50
    CONNECTIONLESS_SLAVE_BROADCAST_RECEIVE = 0x51
    CONNECTIONLESS_SLAVE_BROADCAST_TIMEOUT = 0x52
    TRUNCATED_PAGE_COMPLETE = 0x53
    SLAVE_PAGE_RESPONSE_TIMEOUT = 0x54
    CONNECTIONLESS_SLAVE_BROADCAST_CHANNEL_MAP_CHANGE = 0x55
    INQUIRY_RESPONSE_NOTIFICATION = 0x56
    AUTHENTICATED_PAYLOAD_TIMEOUT_EXPIRED = 0x57
    SAM_STATUS_CHANGE = 0x58
   
# LE Meta Event Subevent Codes
@unique
class LeMetaEventSubCode(IntEnum):
    CONNECTION_COMPLETE = 0x01
    ADVERTISING_REPORT = 0x02
    CONNECTION_UPDATE_COMPLETE = 0x03
    READ_REMOTE_FEATURES_COMPLETE = 0x04
    LONG_TERM_KEY_REQUEST = 0x05
    REMOTE_CONNECTION_PARAMETER_REQUEST = 0x06
    DATA_LENGTH_CHANGE = 0x07
    READ_LOCAL_P256_PUBLIC_KEY_COMPLETE = 0x08
    GENERATE_DHKEY_COMPLETE = 0x09
    ENHANCED_CONNECTION_COMPLETE = 0x0A
    DIRECTED_ADVERTISING_REPORT = 0x0B
    PHY_UPDATE_COMPLETE = 0x0C
    EXTENDED_ADVERTISING_REPORT = 0x0D
    PERIODIC_ADVERTISING_SYNC_ESTABLISHED = 0x0E
    PERIODIC_ADVERTISING_REPORT = 0x0F
    PERIODIC_ADVERTISING_SYNC_LOST = 0x10
    SCAN_TIMEOUT = 0x11
    ADVERTISING_SET_TERMINATED = 0x12
    SCAN_REQUEST_RECEIVED = 0x13
    CHANNEL_SELECTION_ALGORITHM = 0x14
    CONNECTIONLESS_IQ_REPORT = 0x15
    CONNECTION_IQ_REPORT = 0x16
    CTE_REQUEST_FAILED = 0x17
    PERIODIC_ADVERTISING_SYNC_TRANSFER_RECEIVED = 0x18
    CIS_ESTABLISHED = 0x19
    CIS_REQUEST = 0x1A
    CREATE_BIG_COMPLETE = 0x1B
    TERMINATE_BIG_COMPLETE = 0x1C
    BIG_SYNC_ESTABLISHED = 0x1D
    BIG_SYNC_LOST = 0x1E
    REQUEST_PEER_SCA_COMPLETE = 0x1F
    PATH_LOSS_THRESHOLD = 0x20
    TRANSMIT_POWER_REPORTING = 0x21
    BIG_INFO_ADVERTISING_REPORT = 0x22
    SUBRATE_CHANGE = 0x23


# Dictionary of event codes to names
HCI_EVENT_CODE_TO_NAME = {
    HciEventCode.INQUIRY_COMPLETE: "Inquiry_Complete",
    HciEventCode.INQUIRY_RESULT: "Inquiry_Result",
    HciEventCode.CONNECTION_COMPLETE: "Connection_Complete",
    HciEventCode.CONNECTION_REQUEST: "Connection_Request",
    HciEventCode.DISCONNECTION_COMPLETE: "Disconnection_Complete",
    HciEventCode.AUTHENTICATION_COMPLETE: "Authentication_Complete",
    HciEventCode.REMOTE_NAME_REQUEST_COMPLETE: "Remote_Name_Request_Complete",
    HciEventCode.ENCRYPTION_CHANGE: "Encryption_Change",
    HciEventCode.CHANGE_CONNECTION_LINK_KEY_COMPLETE: "Change_Connection_Link_Key_Complete",
    HciEventCode.MASTER_LINK_KEY_COMPLETE: "Master_Link_Key_Complete",
    HciEventCode.READ_REMOTE_SUPPORTED_FEATURES_COMPLETE: "Read_Remote_Supported_Features_Complete",
    HciEventCode.READ_REMOTE_VERSION_INFORMATION_COMPLETE: "Read_Remote_Version_Information_Complete",
    HciEventCode.QOS_SETUP_COMPLETE: "QoS_Setup_Complete",
    HciEventCode.COMMAND_COMPLETE: "Command_Complete",
    HciEventCode.COMMAND_STATUS: "Command_Status",
    HciEventCode.HARDWARE_ERROR: "Hardware_Error",
    HciEventCode.FLUSH_OCCURRED: "Flush_Occurred",
    HciEventCode.ROLE_CHANGE: "Role_Change",
    HciEventCode.NUMBER_OF_COMPLETED_PACKETS: "Number_Of_Completed_Packets",
    HciEventCode.MODE_CHANGE: "Mode_Change",
    HciEventCode.RETURN_LINK_KEYS: "Return_Link_Keys",
    HciEventCode.PIN_CODE_REQUEST: "PIN_Code_Request",
    HciEventCode.LINK_KEY_REQUEST: "Link_Key_Request",
    HciEventCode.LINK_KEY_NOTIFICATION: "Link_Key_Notification",
    HciEventCode.LOOPBACK_COMMAND: "Loopback_Command",
    HciEventCode.DATA_BUFFER_OVERFLOW: "Data_Buffer_Overflow",
    HciEventCode.MAX_SLOTS_CHANGE: "Max_Slots_Change",
    HciEventCode.READ_CLOCK_OFFSET_COMPLETE: "Read_Clock_Offset_Complete",
    HciEventCode.CONNECTION_PACKET_TYPE_CHANGED: "Connection_Packet_Type_Changed",
    HciEventCode.QOS_VIOLATION: "QoS_Violation",
    HciEventCode.PAGE_SCAN_REPETITION_MODE_CHANGE: "Page_Scan_Repetition_Mode_Change",
    HciEventCode.FLOW_SPECIFICATION_COMPLETE: "Flow_Specification_Complete",
    HciEventCode.INQUIRY_RESULT_WITH_RSSI: "Inquiry_Result_With_RSSI",
    HciEventCode.READ_REMOTE_EXTENDED_FEATURES_COMPLETE: "Read_Remote_Extended_Features_Complete",
    HciEventCode.SYNCHRONOUS_CONNECTION_COMPLETE: "Synchronous_Connection_Complete",
    HciEventCode.SYNCHRONOUS_CONNECTION_CHANGED: "Synchronous_Connection_Changed",
    HciEventCode.SNIFF_SUBRATING: "Sniff_Subrating",
    HciEventCode.EXTENDED_INQUIRY_RESULT: "Extended_Inquiry_Result",
    HciEventCode.ENCRYPTION_KEY_REFRESH_COMPLETE: "Encryption_Key_Refresh_Complete",
    HciEventCode.IO_CAPABILITY_REQUEST: "IO_Capability_Request",
    HciEventCode.IO_CAPABILITY_RESPONSE: "IO_Capability_Response",
    HciEventCode.USER_CONFIRMATION_REQUEST: "User_Confirmation_Request",
    HciEventCode.USER_PASSKEY_REQUEST: "User_Passkey_Request",
    HciEventCode.REMOTE_OOB_DATA_REQUEST: "Remote_OOB_Data_Request",
    HciEventCode.SIMPLE_PAIRING_COMPLETE: "Simple_Pairing_Complete",
    HciEventCode.LINK_SUPERVISION_TIMEOUT_CHANGED: "Link_Supervision_Timeout_Changed",
    HciEventCode.ENHANCED_FLUSH_COMPLETE: "Enhanced_Flush_Complete",
    HciEventCode.USER_PASSKEY_NOTIFICATION: "User_Passkey_Notification",
    HciEventCode.KEYPRESS_NOTIFICATION: "Keypress_Notification",
    HciEventCode.REMOTE_HOST_SUPPORTED_FEATURES_NOTIFICATION: "Remote_Host_Supported_Features_Notification",
    HciEventCode.LE_META_EVENT: "LE_Meta_Event",
    HciEventCode.PHYSICAL_LINK_COMPLETE: "Physical_Link_Complete",
    HciEventCode.CHANNEL_SELECTED: "Channel_Selected",
    HciEventCode.DISCONNECTION_PHYSICAL_LINK_COMPLETE: "Disconnection_Physical_Link_Complete",
    HciEventCode.PHYSICAL_LINK_LOSS_EARLY_WARNING: "Physical_Link_Loss_Early_Warning",
    HciEventCode.PHYSICAL_LINK_RECOVERY: "Physical_Link_Recovery",
    HciEventCode.LOGICAL_LINK_COMPLETE: "Logical_Link_Complete",
    HciEventCode.DISCONNECTION_LOGICAL_LINK_COMPLETE: "Disconnection_Logical_Link_Complete",
    HciEventCode.FLOW_SPEC_MODIFY_COMPLETE: "Flow_Spec_Modify_Complete",
    HciEventCode.NUMBER_OF_COMPLETED_DATA_BLOCKS: "Number_Of_Completed_Data_Blocks",
    HciEventCode.AMP_START_TEST: "AMP_Start_Test",
    HciEventCode.AMP_TEST_END: "AMP_Test_End",
    HciEventCode.AMP_RECEIVER_REPORT: "AMP_Receiver_Report",
    HciEventCode.SHORT_RANGE_MODE_CHANGE_COMPLETE: "Short_Range_Mode_Change_Complete",
    HciEventCode.AMP_STATUS_CHANGE: "AMP_Status_Change",
    HciEventCode.TRIGGERED_CLOCK_CAPTURE: "Triggered_Clock_Capture",
    HciEventCode.SYNCHRONIZATION_TRAIN_COMPLETE: "Synchronization_Train_Complete",
    HciEventCode.SYNCHRONIZATION_TRAIN_RECEIVED: "Synchronization_Train_Received",
    HciEventCode.CONNECTIONLESS_SLAVE_BROADCAST_RECEIVE: "Connectionless_Slave_Broadcast_Receive",
    HciEventCode.CONNECTIONLESS_SLAVE_BROADCAST_TIMEOUT: "Connectionless_Slave_Broadcast_Timeout",
    HciEventCode.TRUNCATED_PAGE_COMPLETE: "Truncated_Page_Complete",
    HciEventCode.SLAVE_PAGE_RESPONSE_TIMEOUT: "Slave_Page_Response_Timeout",
    HciEventCode.CONNECTIONLESS_SLAVE_BROADCAST_CHANNEL_MAP_CHANGE: "Connectionless_Slave_Broadcast_Channel_Map_Change",
    HciEventCode.INQUIRY_RESPONSE_NOTIFICATION: "Inquiry_Response_Notification",
    HciEventCode.AUTHENTICATED_PAYLOAD_TIMEOUT_EXPIRED: "Authenticated_Payload_Timeout_Expired",
    HciEventCode.SAM_STATUS_CHANGE: "SAM_Status_Change",
}

# Dictionary of LE Meta Event Subcodes to names
LE_META_EVENT_SUBCODE_TO_NAME = {
    LeMetaEventSubCode.CONNECTION_COMPLETE: "LE_Connection_Complete",
    LeMetaEventSubCode.ADVERTISING_REPORT: "LE_Advertising_Report",
    LeMetaEventSubCode.CONNECTION_UPDATE_COMPLETE: "LE_Connection_Update_Complete",
    LeMetaEventSubCode.READ_REMOTE_FEATURES_COMPLETE: "LE_Read_Remote_Features_Complete",
    LeMetaEventSubCode.LONG_TERM_KEY_REQUEST: "LE_Long_Term_Key_Request",
    LeMetaEventSubCode.REMOTE_CONNECTION_PARAMETER_REQUEST: "LE_Remote_Connection_Parameter_Request",
    LeMetaEventSubCode.DATA_LENGTH_CHANGE: "LE_Data_Length_Change",
    LeMetaEventSubCode.READ_LOCAL_P256_PUBLIC_KEY_COMPLETE: "LE_Read_Local_P-256_Public_Key_Complete",
    LeMetaEventSubCode.GENERATE_DHKEY_COMPLETE: "LE_Generate_DHKey_Complete",
    LeMetaEventSubCode.ENHANCED_CONNECTION_COMPLETE: "LE_Enhanced_Connection_Complete",
    LeMetaEventSubCode.DIRECTED_ADVERTISING_REPORT: "LE_Directed_Advertising_Report",
    LeMetaEventSubCode.PHY_UPDATE_COMPLETE: "LE_PHY_Update_Complete",
    LeMetaEventSubCode.EXTENDED_ADVERTISING_REPORT: "LE_Extended_Advertising_Report",
    LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_ESTABLISHED: "LE_Periodic_Advertising_Sync_Established",
    LeMetaEventSubCode.PERIODIC_ADVERTISING_REPORT: "LE_Periodic_Advertising_Report",
    LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_LOST: "LE_Periodic_Advertising_Sync_Lost",
    LeMetaEventSubCode.SCAN_TIMEOUT: "LE_Scan_Timeout",
    LeMetaEventSubCode.ADVERTISING_SET_TERMINATED: "LE_Advertising_Set_Terminated",
    LeMetaEventSubCode.SCAN_REQUEST_RECEIVED: "LE_Scan_Request_Received",
    LeMetaEventSubCode.CHANNEL_SELECTION_ALGORITHM: "LE_Channel_Selection_Algorithm",
    LeMetaEventSubCode.CONNECTIONLESS_IQ_REPORT: "LE_Connectionless_IQ_Report",
    LeMetaEventSubCode.CONNECTION_IQ_REPORT: "LE_Connection_IQ_Report",
    LeMetaEventSubCode.CTE_REQUEST_FAILED: "LE_CTE_Request_Failed",
    LeMetaEventSubCode.PERIODIC_ADVERTISING_SYNC_TRANSFER_RECEIVED: "LE_Periodic_Advertising_Sync_Transfer_Received",
    LeMetaEventSubCode.CIS_ESTABLISHED: "LE_CIS_Established",
    LeMetaEventSubCode.CIS_REQUEST: "LE_CIS_Request",
    LeMetaEventSubCode.CREATE_BIG_COMPLETE: "LE_Create_BIG_Complete",
    LeMetaEventSubCode.TERMINATE_BIG_COMPLETE: "LE_Terminate_BIG_Complete",
    LeMetaEventSubCode.BIG_SYNC_ESTABLISHED: "LE_BIG_Sync_Established",
    LeMetaEventSubCode.BIG_SYNC_LOST: "LE_BIG_Sync_Lost",
    LeMetaEventSubCode.REQUEST_PEER_SCA_COMPLETE: "LE_Request_Peer_SCA_Complete",
    LeMetaEventSubCode.PATH_LOSS_THRESHOLD: "LE_Path_Loss_Threshold",
    LeMetaEventSubCode.TRANSMIT_POWER_REPORTING: "LE_Transmit_Power_Reporting",
    LeMetaEventSubCode.BIG_INFO_ADVERTISING_REPORT: "LE_BIG_Info_Advertising_Report",
    LeMetaEventSubCode.SUBRATE_CHANGE: "LE_Subrate_Change",
}

# Export constants
__all__ = [
    'HciEventCode',
    'LeMetaEventSubCode',
    'CommandCompleteReturnParamLen',
    'HCI_EVENT_CODE_TO_NAME',
    'LE_META_EVENT_SUBCODE_TO_NAME',
]