"""
Error codes for HCI events and commands

This module defines the error codes (status values) returned in HCI events.
"""

from enum import IntEnum

class StatusCode(IntEnum):
    """HCI Status Codes / Error Codes"""
    SUCCESS = 0x00
    UNKNOWN_COMMAND = 0x01
    UNKNOWN_CONNECTION_IDENTIFIER = 0x02
    HARDWARE_FAILURE = 0x03
    PAGE_TIMEOUT = 0x04
    AUTHENTICATION_FAILURE = 0x05
    PIN_OR_KEY_MISSING = 0x06
    MEMORY_CAPACITY_EXCEEDED = 0x07
    CONNECTION_TIMEOUT = 0x08
    CONNECTION_LIMIT_EXCEEDED = 0x09
    SYNCHRONOUS_CONNECTION_LIMIT_EXCEEDED = 0x0A
    CONNECTION_ALREADY_EXISTS = 0x0B
    COMMAND_DISALLOWED = 0x0C
    CONNECTION_REJECTED_LIMITED_RESOURCES = 0x0D
    CONNECTION_REJECTED_SECURITY = 0x0E
    CONNECTION_REJECTED_UNACCEPTABLE_BD_ADDR = 0x0F
    CONNECTION_ACCEPT_TIMEOUT_EXCEEDED = 0x10
    UNSUPPORTED_FEATURE_OR_PARAMETER = 0x11
    INVALID_HCI_COMMAND_PARAMETERS = 0x12
    REMOTE_USER_TERMINATED_CONNECTION = 0x13
    REMOTE_DEVICE_TERMINATED_CONNECTION_LOW_RESOURCES = 0x14
    REMOTE_DEVICE_TERMINATED_CONNECTION_POWER_OFF = 0x15
    CONNECTION_TERMINATED_BY_LOCAL_HOST = 0x16
    REPEATED_ATTEMPTS = 0x17
    PAIRING_NOT_ALLOWED = 0x18
    UNKNOWN_LMP_PDU = 0x19
    UNSUPPORTED_REMOTE_FEATURE = 0x1A
    SCO_OFFSET_REJECTED = 0x1B
    SCO_INTERVAL_REJECTED = 0x1C
    SCO_AIR_MODE_REJECTED = 0x1D
    INVALID_LMP_PARAMETERS = 0x1E
    UNSPECIFIED_ERROR = 0x1F
    UNSUPPORTED_LMP_PARAMETER_VALUE = 0x20
    ROLE_CHANGE_NOT_ALLOWED = 0x21
    LMP_RESPONSE_TIMEOUT = 0x22
    LMP_ERROR_TRANSACTION_COLLISION = 0x23
    LMP_PDU_NOT_ALLOWED = 0x24
    ENCRYPTION_MODE_NOT_ACCEPTABLE = 0x25
    LINK_KEY_CANNOT_BE_CHANGED = 0x26
    REQUESTED_QOS_NOT_SUPPORTED = 0x27
    INSTANT_PASSED = 0x28
    PAIRING_WITH_UNIT_KEY_NOT_SUPPORTED = 0x29
    DIFFERENT_TRANSACTION_COLLISION = 0x2A
    RESERVED_1 = 0x2B
    QOS_UNACCEPTABLE_PARAMETER = 0x2C
    QOS_REJECTED = 0x2D
    CHANNEL_CLASSIFICATION_NOT_SUPPORTED = 0x2E
    INSUFFICIENT_SECURITY = 0x2F
    PARAMETER_OUT_OF_MANDATORY_RANGE = 0x30
    RESERVED_2 = 0x31
    ROLE_SWITCH_PENDING = 0x32
    RESERVED_3 = 0x33
    RESERVED_SLOT_VIOLATION = 0x34
    ROLE_SWITCH_FAILED = 0x35
    EXTENDED_INQUIRY_RESPONSE_TOO_LARGE = 0x36
    SECURE_SIMPLE_PAIRING_NOT_SUPPORTED_BY_HOST = 0x37
    HOST_BUSY_PAIRING = 0x38
    CONNECTION_REJECTED_NO_SUITABLE_CHANNEL = 0x39
    CONTROLLER_BUSY = 0x3A
    UNACCEPTABLE_CONNECTION_PARAMETERS = 0x3B
    ADVERTISING_TIMEOUT = 0x3C
    CONNECTION_TERMINATED_MIC_FAILURE = 0x3D
    CONNECTION_FAILED_TO_BE_ESTABLISHED = 0x3E
    MAC_CONNECTION_FAILED = 0x3F
    COARSE_CLOCK_ADJUSTMENT_REJECTED = 0x40
    TYPE0_SUBMAP_NOT_DEFINED = 0x41
    UNKNOWN_ADVERTISING_IDENTIFIER = 0x42
    LIMIT_REACHED = 0x43
    OPERATION_CANCELLED_BY_HOST = 0x44
    PACKET_TOO_LONG = 0x45

# Dictionary mapping status codes to descriptions
STATUS_CODE_DESCRIPTIONS = {
    StatusCode.SUCCESS: "Success",
    StatusCode.UNKNOWN_COMMAND: "Unknown HCI Command",
    StatusCode.UNKNOWN_CONNECTION_IDENTIFIER: "Unknown Connection Identifier",
    StatusCode.HARDWARE_FAILURE: "Hardware Failure",
    StatusCode.PAGE_TIMEOUT: "Page Timeout",
    StatusCode.AUTHENTICATION_FAILURE: "Authentication Failure",
    StatusCode.PIN_OR_KEY_MISSING: "PIN or Key Missing",
    StatusCode.MEMORY_CAPACITY_EXCEEDED: "Memory Capacity Exceeded",
    StatusCode.CONNECTION_TIMEOUT: "Connection Timeout",
    StatusCode.CONNECTION_LIMIT_EXCEEDED: "Connection Limit Exceeded",
    StatusCode.SYNCHRONOUS_CONNECTION_LIMIT_EXCEEDED: "Synchronous Connection Limit Exceeded",
    StatusCode.CONNECTION_ALREADY_EXISTS: "Connection Already Exists",
    StatusCode.COMMAND_DISALLOWED: "Command Disallowed",
    StatusCode.CONNECTION_REJECTED_LIMITED_RESOURCES: "Connection Rejected due to Limited Resources",
    StatusCode.CONNECTION_REJECTED_SECURITY: "Connection Rejected due to Security Reasons",
    StatusCode.CONNECTION_REJECTED_UNACCEPTABLE_BD_ADDR: "Connection Rejected due to Unacceptable BD_ADDR",
    StatusCode.CONNECTION_ACCEPT_TIMEOUT_EXCEEDED: "Connection Accept Timeout Exceeded",
    StatusCode.UNSUPPORTED_FEATURE_OR_PARAMETER: "Unsupported Feature or Parameter Value",
    StatusCode.INVALID_HCI_COMMAND_PARAMETERS: "Invalid HCI Command Parameters",
    StatusCode.REMOTE_USER_TERMINATED_CONNECTION: "Remote User Terminated Connection",
    StatusCode.REMOTE_DEVICE_TERMINATED_CONNECTION_LOW_RESOURCES: "Remote Device Terminated Connection due to Low Resources",
    StatusCode.REMOTE_DEVICE_TERMINATED_CONNECTION_POWER_OFF: "Remote Device Terminated Connection due to Power Off",
    StatusCode.CONNECTION_TERMINATED_BY_LOCAL_HOST: "Connection Terminated by Local Host",
    StatusCode.REPEATED_ATTEMPTS: "Repeated Attempts",
    StatusCode.PAIRING_NOT_ALLOWED: "Pairing Not Allowed",
    StatusCode.UNKNOWN_LMP_PDU: "Unknown LMP PDU",
    StatusCode.UNSUPPORTED_REMOTE_FEATURE: "Unsupported Remote Feature / LMP Feature",
    StatusCode.SCO_OFFSET_REJECTED: "SCO Offset Rejected",
    StatusCode.SCO_INTERVAL_REJECTED: "SCO Interval Rejected",
    StatusCode.SCO_AIR_MODE_REJECTED: "SCO Air Mode Rejected",
    StatusCode.INVALID_LMP_PARAMETERS: "Invalid LMP Parameters / LL Parameters",
    StatusCode.UNSPECIFIED_ERROR: "Unspecified Error",
    StatusCode.UNSUPPORTED_LMP_PARAMETER_VALUE: "Unsupported LMP Parameter Value / LL Parameter Value",
    StatusCode.ROLE_CHANGE_NOT_ALLOWED: "Role Change Not Allowed",
    StatusCode.LMP_RESPONSE_TIMEOUT: "LMP Response Timeout / LL Response Timeout",
    StatusCode.LMP_ERROR_TRANSACTION_COLLISION: "LMP Error Transaction Collision / LL Procedure Collision",
    StatusCode.LMP_PDU_NOT_ALLOWED: "LMP PDU Not Allowed",
    StatusCode.ENCRYPTION_MODE_NOT_ACCEPTABLE: "Encryption Mode Not Acceptable",
    StatusCode.LINK_KEY_CANNOT_BE_CHANGED: "Link Key cannot be Changed",
    StatusCode.REQUESTED_QOS_NOT_SUPPORTED: "Requested QoS Not Supported",
    StatusCode.INSTANT_PASSED: "Instant Passed",
    StatusCode.PAIRING_WITH_UNIT_KEY_NOT_SUPPORTED: "Pairing with Unit Key Not Supported",
    StatusCode.DIFFERENT_TRANSACTION_COLLISION: "Different Transaction Collision",
    StatusCode.RESERVED_1: "Reserved",
    StatusCode.QOS_UNACCEPTABLE_PARAMETER: "QoS Unacceptable Parameter",
    StatusCode.QOS_REJECTED: "QoS Rejected",
    StatusCode.CHANNEL_CLASSIFICATION_NOT_SUPPORTED: "Channel Classification Not Supported",
    StatusCode.INSUFFICIENT_SECURITY: "Insufficient Security",
    StatusCode.PARAMETER_OUT_OF_MANDATORY_RANGE: "Parameter Out Of Mandatory Range",
    StatusCode.RESERVED_2: "Reserved",
    StatusCode.ROLE_SWITCH_PENDING: "Role Switch Pending",
    StatusCode.RESERVED_3: "Reserved",
    StatusCode.RESERVED_SLOT_VIOLATION: "Reserved Slot Violation",
    StatusCode.ROLE_SWITCH_FAILED: "Role Switch Failed",
    StatusCode.EXTENDED_INQUIRY_RESPONSE_TOO_LARGE: "Extended Inquiry Response Too Large",
    StatusCode.SECURE_SIMPLE_PAIRING_NOT_SUPPORTED_BY_HOST: "Secure Simple Pairing Not Supported By Host",
    StatusCode.HOST_BUSY_PAIRING: "Host Busy - Pairing",
    StatusCode.CONNECTION_REJECTED_NO_SUITABLE_CHANNEL: "Connection Rejected due to No Suitable Channel Found",
    StatusCode.CONTROLLER_BUSY: "Controller Busy",
    StatusCode.UNACCEPTABLE_CONNECTION_PARAMETERS: "Unacceptable Connection Parameters",
    StatusCode.ADVERTISING_TIMEOUT: "Advertising Timeout",
    StatusCode.CONNECTION_TERMINATED_MIC_FAILURE: "Connection Terminated due to MIC Failure",
    StatusCode.CONNECTION_FAILED_TO_BE_ESTABLISHED: "Connection Failed to be Established",
    StatusCode.MAC_CONNECTION_FAILED: "MAC Connection Failed",
    StatusCode.COARSE_CLOCK_ADJUSTMENT_REJECTED: "Coarse Clock Adjustment Rejected but Will Try to Adjust Using Clock Dragging",
    StatusCode.TYPE0_SUBMAP_NOT_DEFINED: "Type0 Submap Not Defined",
    StatusCode.UNKNOWN_ADVERTISING_IDENTIFIER: "Unknown Advertising Identifier",
    StatusCode.LIMIT_REACHED: "Limit Reached",
    StatusCode.OPERATION_CANCELLED_BY_HOST: "Operation Cancelled by Host",
    StatusCode.PACKET_TOO_LONG: "Packet Too Long",
}

def get_status_description(status_code: int) -> str:
    """
    Get the description for a status code
    
    Args:
        status_code: Status code value
        
    Returns:
        Description of the status code or "Unknown Status Code" if not found
    """
    if status_code in STATUS_CODE_DESCRIPTIONS:
        return STATUS_CODE_DESCRIPTIONS[status_code]
    
    return f"Unknown Status Code (0x{status_code:02X})"

# Export constants
__all__ = [
    'StatusCode',
    'STATUS_CODE_DESCRIPTIONS',
    'get_status_description',
]