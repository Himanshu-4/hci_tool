"""
    uart transfer.py
    This module provides functionality for uart data transfer.
    It includes:
    - UART transfer classes for different transport types (UART, SDIO).
    - Functions for sending and receiving data.
    - Error handling for file operations.
    - Logging for debugging and monitoring.
    - Utility functions for managing UART connections.
    - Custom exceptions for error handling.

    - [specific functionality, e.g., data validation, etc.]
    - [specific functionality, e.g., data processing, etc.]
    - [specific functionality, e.g., data formatting, etc.]
    - [specific functionality, e.g., data conversion, etc.]
    - [specific functionality, e.g., data encryption, etc.]
    - [specific functionality, e.g., data decryption, etc.]
    - [specific functionality, e.g., data compression, etc.]
    - [specific functionality, e.g., data decompression, etc.]      
    
    
"""

import os
import serial
import serial.tools.list_ports

import threading
import time
import asyncio

from utils.logger import LoggerManager as logger
from utils.logger import LogLevel

from ..base_lib import TransportInterface, ConnectionStatus, TransportError, ConfigurationError, ConnectionError, TransportState, TransportEvent

# MAX_DEVICE_COUNT = 10

# class uart_transfer:
#     """
#     A class to handle UART data transfer.
#     It provides methods for sending and receiving data over UART.
#     """
#     _instance = None
#     _device_instances = {}
#     _lock = threading.Lock()

#     @classmethod
#     def create_instance(cls, device_name) -> 'uart_transfer':
#         """
#         create the singleton instance of the uart_transfer class for the specified device.
#         """
#         with cls._lock:
#             if cls._instance != None and device_name not in cls._device_instances.keys():
#                 return uart_transfer(device_name)
            
#     @classmethod
#     def get_instance(cls, device_name : str) -> 'uart_transfer':
#         """
#         Get the singleton instance of the uart_transfer class for the specified device.
#         """
#         return cls._instance
    
    
#     def __init__(self, device_name):
#         self.device_name = device_name
#         self.serial_port = None
#         self.is_connected = False
#         self._device_instances[device_name] = self
#         self._instance = self
#         # self._logger = logger.get_logger(__name__, level=LogLevel.DEBUG,
#         #                                   log_file=os.path.join(os.path.dirname(__file__), "uart_transfer.log"))
        
#         # self._logger.debug(f"Creating uart_transfer instance for device: {device_name}")
        
        
        
#     def connect(self, baudrate=115200, timeout=1):
#         """
#         Connect to the UART device.
#         :param baudrate: Baud rate for the UART connection.
#         :param timeout: Timeout for the UART connection.
#         :return: True if connected, False otherwise.
#         """
#         # if self.is_connected:
#         #     self._logger.warning(f"Already connected to {self.device_name}")
#         #     return True
        
#         # try:
#         #     self.serial_port = serial.Serial(self.device_name, baudrate=baudrate, timeout=timeout)
#         #     self.is_connected = True
            
#         #     # self._logger.info(f"Connected to {self.device_name} at {baudrate} baud.")
#         #     return True
#         # except serial.SerialException as e:
#         #     # self._logger.error(f"Failed to connect to {self.device_name}: {e}")
#         #     return False
#         print(f"Connecting to {self.device_name} at {baudrate} baud...")
        
        
#     def disconnect(self):
#         """
#         Disconnect from the UART device.
#         :return: True if disconnected, False otherwise.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return False
        
#         # try:
#         #     self.serial_port.close()
#         #     self.is_connected = False
#         #     self._logger.info(f"Disconnected from {self.device_name}.")
#         #     return True
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to disconnect from {self.device_name}: {e}")
#         #     return False
#         print(f"Disconnecting from {self.device_name}...")
        
#     def send(self, data: bytes):
#         """
#         Send data to the UART device.
#         :param data: Data to be sent.
#         :return: True if data is sent successfully, False otherwise.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return False
        
#         # try:
#         #     self.serial_port.write(data)
#         #     self._logger.info(f"Sent data to {self.device_name}: {data}")
#         #     return True
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to send data to {self.device_name}: {e}")
#         #     return False
#         print(f"Sending data to {self.device_name}: {data}")
        
        
#     def receive(self, size: int = 1024):
#         """
#         Receive data from the UART device.
#         :param size: Number of bytes to read.
#         :return: Received data.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return None
        
#         # try:
#         #     data = self.serial_port.read(size)
#         #     self._logger.info(f"Received data from {self.device_name}: {data}")
#         #     return data
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to receive data from {self.device_name}: {e}")
#         #     return None
#         print(f"Receiving data from {self.device_name}...")
        
#     def set_timeout(self, timeout: int):
#         """
#         Set the timeout for the UART connection.
#         :param timeout: Timeout in seconds.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return False
        
#         # try:
#         #     self.serial_port.timeout = timeout
#         #     self._logger.info(f"Set timeout for {self.device_name} to {timeout} seconds.")
#         #     return True
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to set timeout for {self.device_name}: {e}")
#         #     return False
#         print(f"Setting timeout for {self.device_name} to {timeout} seconds...")
        
        
#     def get_timeout(self):
#         """
#         Get the timeout for the UART connection.
#         :return: Timeout in seconds.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return None
        
#         # try:
#         #     timeout = self.serial_port.timeout
#         #     self._logger.info(f"Timeout for {self.device_name} is {timeout} seconds.")
#         #     return timeout
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to get timeout for {self.device_name}: {e}")
#         #     return None
#         print(f"Getting timeout for {self.device_name}...")
        
#     def set_baudrate(self, baudrate: int):
#         """
#         Set the baud rate for the UART connection.
#         :param baudrate: Baud rate.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return False
        
#         # try:
#         #     self.serial_port.baudrate = baudrate
#         #     self._logger.info(f"Set baud rate for {self.device_name} to {baudrate}.")
#         #     return True
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to set baud rate for {self.device_name}: {e}")
#         #     return False
#         print(f"Setting baud rate for {self.device_name} to {baudrate}...")
#         self.baudrate = baudrate
        
#     def get_baudrate(self):
#         """
#         Get the baud rate for the UART connection.
#         :return: Baud rate.
#         """
#         # if not self.is_connected:
#         #     self._logger.warning(f"Not connected to {self.device_name}")
#         #     return None
        
#         # try:
#         #     baudrate = self.serial_port.baudrate
#         #     self._logger.info(f"Baud rate for {self.device_name} is {baudrate}.")
#         #     return baudrate
#         # except serial.SerialException as e:
#         #     self._logger.error(f"Failed to get baud rate for {self.device_name}: {e}")
#         #     return None
#         print(f"Getting baud rate for {self.device_name}...")
#         return self.baudrate
    


import serial
import serial.tools.list_ports
import threading
import time
from typing import Dict, Any, Optional
from ..base_lib import TransportInterface, ConnectionStatus, TransportError, ConfigurationError, ConnectionError

from dataclasses import dataclass

@dataclass
class UARTConfig:
    # port
    port: str
    # baudrate
    baudrate: int
    # bytesize
    bytesize: int
    # parity
    parity: int
    # stopbits
    stopbits: int
    # timeout
    timeout: int
    # flow control
    enable_flow_control: bool
    xonxoff: bool
    rtscts: bool
    dsrdtr: bool
    flow_control_threshold: int
    flow_control_window: int
    flow_control_window_size: int
    flow_control_window_size_max: int
    flow_control_window_size_min: int
    # queue size
    max_queue_size: int
    read_buffer_size: int

    def __init__(self, **kwargs):
        self.port = kwargs.get('port', None)
        self.baudrate = kwargs.get('baudrate', None)
        self.bytesize = kwargs.get('bytesize', None)
        self.parity = kwargs.get('parity', None)
        self.stopbits = kwargs.get('stopbits', None)
        self.timeout = kwargs.get('timeout', None)
        self.xonxoff = kwargs.get('xonxoff', None)
        self.rtscts = kwargs.get('rtscts', None)
    
    def __post_init__(self):
        # set default values if not provided
        # baudrate
        if self.baudrate is None:
            self.baudrate = 115200
        # bytesize
        if self.bytesize is None:
            self.bytesize = serial.EIGHTBITS
        # parity
        if self.parity is None:
            self.parity = serial.PARITY_NONE
        # stopbits
        if self.stopbits is None:
            self.stopbits = serial.STOPBITS_ONE
        # timeout
        if self.timeout is None:
            self.timeout = 1
        # xonxoff
        if self.xonxoff is None:
            self.xonxoff = False
        # rtscts
        if self.rtscts is None:
            self.rtscts = False
        # dsrdtr
        if self.dsrdtr is None:
            self.dsrdtr = False
        # max_queue_size
        if self.max_queue_size is None: 
            self.max_queue_size = 1000
        # read_buffer_size
        if self.read_buffer_size is None:
            self.read_buffer_size = 4096
        # enable_flow_control
        if self.enable_flow_control is None:
            self.enable_flow_control = True
        # flow_control_threshold
        if self.flow_control_threshold is None:
            self.flow_control_threshold = 1000
        # flow_control_window
        if self.flow_control_window is None:
            self.flow_control_window = 1000
        # flow_control_window_size
        if self.flow_control_window_size is None:
            self.flow_control_window_size = 1000
        # flow_control_window_size_max
        if self.flow_control_window_size_max is None:
            self.flow_control_window_size_max = 1000
        # flow_control_window_size_min  
        if self.flow_control_window_size_min is None:
            self.flow_control_window_size_min = 1000

class UARTTransport(TransportInterface):
    """UART transport implementation using pyserial"""
    
    def __init__(self):
        super().__init__()
        self.serial_connection = None
        self.read_thread = None
        self.stop_reading = False
        self.read_buffer = bytearray()
        self.buffer_lock = threading.Lock()
        
        # Default configuration
        self.default_config = UARTConfig(
            port=None,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure UART parameters
        Args:
            config: Dictionary with UART configuration parameters
        Returns True if configuration is valid
        """
        try:
            # Validate required parameters
            if 'port' not in config or not config['port']:
                raise ConfigurationError("Port parameter is required")
            
            # Validate port exists
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
            if config['port'] not in available_ports:
                raise ConfigurationError(f"Port {config['port']} not found. Available ports: {available_ports}")
            
            # Merge with defaults
            self.config = UARTConfig(**config)
            
            # Validate baudrate
            valid_baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
            if self.config.baudrate not in valid_baudrates:
                raise ConfigurationError(f"Invalid baudrate: {self.config.baudrate}")
            
            return True
            
        except Exception as e:
            raise ConfigurationError(f"UART configuration error: {str(e)}")
    
    @property
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.__dict__
    
    def connect(self) -> bool:
        """
        Establish UART connection
        Returns True if connection successful
        """
        try:
            if self.is_connected():
                return True
            
            if not self.config.port:
                raise ConnectionError("No port configured")
            
            self.status = ConnectionStatus.CONNECTING
            
            # Create serial connection
            self.serial_connection = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout,
                # xonxoff=self.config['xonxoff'],
                # rtscts=self.config['rtscts'],
                # dsrdtr=self.config['dsrdtr']
            )
            # Test connection
            if not self.serial_connection.is_open:
                self.serial_connection.open()
            
            # Start read thread
            # self._start_read_thread()
            
            self.status = ConnectionStatus.CONNECTED
            self._trigger_callbacks(TransportEvent.CONNECT, self)
            
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.serial_connection = None
            raise ConnectionError(f"UART connection failed: {str(e)}")
    
    def disconnect(self) -> bool:
        """
        Close UART connection
        Returns True if successful
        """
        try:
            if not self.is_connected():
                return True
            
            # Stop read thread
            self._stop_read_thread()
            
            # Close serial connection
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            self.serial_connection = None
            self.status = ConnectionStatus.DISCONNECTED
            
            # Clear read buffer
            with self.buffer_lock:
                self.read_buffer.clear()
            
            self._trigger_callbacks(TransportEvent.DISCONNECT, self)
            
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            raise ConnectionError(f"UART disconnect failed: {str(e)}")
    
    def read(self, size: int = -1, max_wait : int = 1) -> Optional[bytes]:
        """
        Read data from UART
        Args:
            size: Number of bytes to read (-1 for all available)
        Returns bytes data or None if no data/error
        """
        # try:
        #     if not self.is_connected():
        #         return None
            
        #     with self.buffer_lock:
        #         if not self.read_buffer:
        #             return None
                
        #         if size == -1 or size >= len(self.read_buffer):
        #             # Return all available data
        #             data = bytes(self.read_buffer)
        #             self.read_buffer.clear()
        #         else:
        #             # Return requested amount
        #             data = bytes(self.read_buffer[:size])
        #             del self.read_buffer[:size]
                
        #         if data:
        #             self._trigger_callbacks('read', data)
                
        #         return data
                
        # except Exception as e:
        #     raise TransportError(f"UART read error: {str(e)}")
        start_time = time.time()
        while (time.time() - start_time) < max_wait:
            # Check if there's data available
            if self.serial_connection.in_waiting > 0:
                # Read packet type
                pkt_type = self.serial_connection.read(1)
                
                if len(pkt_type) == 0:
                    continue
                
                if pkt_type[0] == 0x04:
                    # Read event code
                    evt_code = self.serial_connection.read(1)
                    if len(evt_code) == 0:
                        continue
                    
                    # Read parameter length
                    param_len = self.serial_connection.read(1)
                    if len(param_len) == 0:
                        continue
                    
                    # Read parameters
                    if param_len[0] > 0:
                        params = self.serial_connection.read(param_len[0])
                        if len(params) < param_len[0]:
                            continue
                    else:
                        params = b''
                    
                    # Construct full packet
                    packet = pkt_type + evt_code + param_len + params
                    
                    print(f"Received: {packet}")
                    
                    # Parse event
                    event = {
                        'event_code': evt_code[0],
                        'parameters': params
                    }
                    self._trigger_callbacks(TransportEvent.READ, packet)
                    return b''
                else:
                    # Discard other packet types for now
                    print(f"Received non-event packet type: {pkt_type[0]}")
                    continue
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
        
        print("No event received within timeout")
        return None

    def write(self, data: bytes) -> bool:
        """
        Write data to UART
        Args:
            data: Bytes to write
        Returns True if successful
        """
        try:
            if not self.is_connected():
                return False
            
            if not isinstance(data, (bytes, bytearray)):
                raise ValueError("Data must be bytes or bytearray")
            
            bytes_written = self.serial_connection.write(data)
            success = bytes_written == len(data)
            
            if success:
                self._trigger_callbacks(TransportEvent.WRITE, data)
            
            return success
            
        except Exception as e:
            raise TransportError(f"UART write error: {str(e)}")
    
    def _start_read_thread(self):
        """Start the background read thread"""
        self.stop_reading = False
        self.read_thread = threading.Thread(target=self._read_worker, daemon=True)
        self.read_thread.start()
    
    def _stop_read_thread(self):
        """Stop the background read thread"""
        self.stop_reading = True
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
    
    def _read_worker(self):
        """Background thread worker for reading data"""
        while not self.stop_reading and self.serial_connection and self.serial_connection.is_open:
            try:
                # Check if data is available
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    if data:
                        with self.buffer_lock:
                            self.read_buffer.extend(data)
                
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                print(f"Read thread error: {e}")
                break
    
    def get_available_ports(self) -> list:
        """Get list of available COM ports"""
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
    
    def flush_input(self):
        """Flush input buffer"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.reset_input_buffer()
            with self.buffer_lock:
                self.read_buffer.clear()
    
    def flush_output(self):
        """Flush output buffer"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.reset_output_buffer()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = {
            'port': self.config.port,
            'baudrate': self.config.baudrate,
            'status': self.status.value,
            'buffer_size': len(self.read_buffer) if hasattr(self, 'read_buffer') else 0
        }
        
        if self.serial_connection:
            stats.update({
                'is_open': self.serial_connection.is_open,
                'in_waiting': self.serial_connection.in_waiting if self.serial_connection.is_open else 0,
                'out_waiting': self.serial_connection.out_waiting if self.serial_connection.is_open else 0
            })
        
        return stats
    
    
"""
Async UART Library with HCI Flow Control
This module provides an asynchronous UART transport layer with HCI packet flow control
"""

import asyncio
import serial
from .uart_async import open_serial_connection
import serial.tools.list_ports
from serial.serialutil import SerialException
import threading
import time
import struct
from typing import Dict, Any, Optional, Callable, Union, List, Tuple
from dataclasses import dataclass
from enum import IntEnum, auto
import weakref
from functools import wraps
import logging
from collections import deque
import inspect

# Setup logger
logger = logging.getLogger(__name__)

# HCI Packet Types
class HCIPacketType(IntEnum):
    COMMAND = 0x01
    ACL_DATA = 0x02
    SYNC_DATA = 0x03
    EVENT = 0x04
    ISO_DATA = 0x05

# HCI Event Codes
class HCIEventCode(IntEnum):
    COMMAND_COMPLETE = 0x0E
    COMMAND_STATUS = 0x0F
    NUMBER_OF_COMPLETED_PACKETS = 0x13
    LE_META_EVENT = 0x3E

@dataclass
class HCIPacket:
    """Represents an HCI packet"""
    packet_type: HCIPacketType
    data: bytes
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class FlowControlState:
    """Tracks flow control state for HCI"""
    num_hci_command_packets: int = 1
    num_acl_data_packets: int = 0
    pending_commands: int = 0
    pending_acl: int = 0
    
    @property
    def can_send_command(self) -> bool:
        return self.num_hci_command_packets > self.pending_commands
    
    @property
    def can_send_acl(self) -> bool:
        return self.num_acl_data_packets > self.pending_acl

class HCIPacketParser:
    """Parser for HCI packets with flow control extraction"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.current_packet_type = None
        self.expected_length = 0
        
    def add_data(self, data: bytes) -> List[HCIPacket]:
        """Add data to parser and return complete packets"""
        self.buffer.extend(data)
        packets = []
        
        while self.buffer:
            if self.current_packet_type is None:
                # Need at least 1 byte for packet type
                if len(self.buffer) < 1:
                    break
                    
                packet_type = self.buffer[0]
                if packet_type not in [t.value for t in HCIPacketType]:
                    # Invalid packet type, skip byte
                    logger.warning(f"Invalid HCI packet type: 0x{packet_type:02X}")
                    self.buffer.pop(0)
                    continue
                    
                self.current_packet_type = HCIPacketType(packet_type)
                self.buffer.pop(0)
            
            # Parse based on packet type
            packet = self._parse_packet()
            if packet:
                packets.append(packet)
                self.current_packet_type = None
                self.expected_length = 0
            else:
                # Not enough data yet
                break
                
        return packets
    
    def _parse_packet(self) -> Optional[HCIPacket]:
        """Parse a single packet based on current type"""
        if self.current_packet_type == HCIPacketType.COMMAND:
            # Command: OpCode (2) + Length (1) + Parameters
            if len(self.buffer) < 3:
                return None
            length = self.buffer[2]
            if len(self.buffer) < 3 + length:
                return None
            data = bytes(self.buffer[:3 + length])
            del self.buffer[:3 + length]
            return HCIPacket(self.current_packet_type, data)
            
        elif self.current_packet_type == HCIPacketType.ACL_DATA:
            # ACL: Handle (2) + Length (2) + Data
            if len(self.buffer) < 4:
                return None
            length = struct.unpack('<H', self.buffer[2:4])[0]
            if len(self.buffer) < 4 + length:
                return None
            data = bytes(self.buffer[:4 + length])
            del self.buffer[:4 + length]
            return HCIPacket(self.current_packet_type, data)
            
        elif self.current_packet_type == HCIPacketType.EVENT:
            # Event: Event Code (1) + Length (1) + Parameters
            if len(self.buffer) < 2:
                return None
            length = self.buffer[1]
            if len(self.buffer) < 2 + length:
                return None
            data = bytes(self.buffer[:2 + length])
            del self.buffer[:2 + length]
            return HCIPacket(self.current_packet_type, data)
            
        elif self.current_packet_type == HCIPacketType.SYNC_DATA:
            # Sync: Handle (2) + Length (1) + Data
            if len(self.buffer) < 3:
                return None
            length = self.buffer[2]
            if len(self.buffer) < 3 + length:
                return None
            data = bytes(self.buffer[:3 + length])
            del self.buffer[:3 + length]
            return HCIPacket(self.current_packet_type, data)
            
        elif self.current_packet_type == HCIPacketType.ISO_DATA:
            # ISO: Handle (2) + Length (2) + Data
            if len(self.buffer) < 4:
                return None
            length = struct.unpack('<H', self.buffer[2:4])[0] & 0x3FFF
            if len(self.buffer) < 4 + length:
                return None
            data = bytes(self.buffer[:4 + length])
            del self.buffer[:4 + length]
            return HCIPacket(self.current_packet_type, data)
            
        return None
    
    @staticmethod
    def extract_flow_control_info(packet: HCIPacket) -> Optional[Dict[str, Any]]:
        """Extract flow control information from HCI packets"""
        if packet.packet_type != HCIPacketType.EVENT:
            return None
            
        event_code = packet.data[0]
        
        if event_code == HCIEventCode.COMMAND_COMPLETE:
            # Command Complete: EventCode(1) + Length(1) + NumHCICommands(1) + OpCode(2) + ReturnParams
            if len(packet.data) >= 3:
                num_hci_commands = packet.data[2]
                return {'num_hci_command_packets': num_hci_commands}
                
        elif event_code == HCIEventCode.COMMAND_STATUS:
            # Command Status: EventCode(1) + Length(1) + Status(1) + NumHCICommands(1) + OpCode(2)
            if len(packet.data) >= 4:
                num_hci_commands = packet.data[3]
                return {'num_hci_command_packets': num_hci_commands}
                
        elif event_code == HCIEventCode.NUMBER_OF_COMPLETED_PACKETS:
            # Number of Completed Packets event
            if len(packet.data) >= 3:
                num_handles = packet.data[2]
                if len(packet.data) >= 3 + (num_handles * 4):
                    total_completed = 0
                    for i in range(num_handles):
                        offset = 3 + (i * 4)
                        # handle = struct.unpack('<H', packet.data[offset:offset+2])[0]
                        num_completed = struct.unpack('<H', packet.data[offset+2:offset+4])[0]
                        total_completed += num_completed
                    return {'num_completed_acl_packets': total_completed}
                    
        return None

class AsyncUARTPort:
    """Async UART port with HCI flow control"""
    
    def __init__(self, port_id: str, port_url: str, baudrate: int = 115200,
                 enable_flow_control: bool = True, max_queue_size: int = 1000,
                 read_buffer_size: int = 4096, **serial_kwargs):
        self.port_id = port_id
        self.port_url = port_url
        self.baudrate = baudrate
        self.serial_kwargs = serial_kwargs
        self.enable_flow_control = enable_flow_control
        self.max_queue_size = max_queue_size
        self.read_buffer_size = read_buffer_size
        
        # Connection state
        self._reader = None
        self._writer = None
        self._read_task = None
        self._write_task = None
        self._connection_lock = asyncio.Lock()
        self.is_connected = False
        self._disconnect_requested = asyncio.Event()
        
        # Queues
        self.rx_queue = asyncio.Queue(maxsize=max_queue_size)  # Received packets
        self.tx_queue = asyncio.Queue(maxsize=max_queue_size)  # Packets to transmit
        
        # HCI Parser and Flow Control
        self.hci_parser = HCIPacketParser()
        self.flow_control = FlowControlState()
        self._flow_control_lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'flow_control_blocks': 0
        }
        
        # Callbacks
        self._callbacks = {
            'on_connect': [],
            'on_disconnect': [],
            'on_packet_received': [],
            'on_packet_sent': [],
            'on_error': [],
            'on_flow_control_update': []
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add callback for specific event"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
        else:
            raise ValueError(f"Unknown event: {event}")
    
    def remove_callback(self, event: str, callback: Callable):
        """Remove callback for specific event"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    async def _trigger_callback(self, event: str, *args, **kwargs):
        """Trigger callbacks for an event"""
        for callback in self._callbacks.get(event, []):
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    # Run sync callbacks in executor to avoid blocking
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, callback, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")
    
    async def connect(self) -> bool:
        """Connect to UART port"""
        async with self._connection_lock:
            if self.is_connected:
                logger.info(f"[{self.port_id}] Already connected")
                return True
            
            logger.info(f"[{self.port_id}] Connecting to {self.port_url} at {self.baudrate} baud")
            
            try:
                self._reader, self._writer = await open_serial_connection(
                    url=self.port_url,
                    baudrate=self.baudrate,
                    **self.serial_kwargs
                )
                
                self.is_connected = True
                self._disconnect_requested.clear()
                
                # Reset state
                self.hci_parser = HCIPacketParser()
                self.flow_control = FlowControlState()
                self.stats = {k: 0 for k in self.stats}
                
                # Start worker tasks
                self._read_task = asyncio.create_task(self._read_worker())
                self._write_task = asyncio.create_task(self._write_worker())
                
                logger.info(f"[{self.port_id}] Connected successfully")
                await self._trigger_callback(TransportEvent.CONNECT, self.port_id, True, "Connected")
                
                return True
                
            except Exception as e:
                logger.error(f"[{self.port_id}] Connection failed: {e}")
                self.is_connected = False
                await self._trigger_callback(TransportEvent.CONNECT, self.port_id, False, str(e))
                return False
    
    async def disconnect(self, reason: str = "User requested") -> bool:
        """Disconnect from UART port"""
        async with self._connection_lock:
            if not self.is_connected:
                logger.info(f"[{self.port_id}] Already disconnected")
                return True
            
            logger.info(f"[{self.port_id}] Disconnecting: {reason}")
            self._disconnect_requested.set()
            
            # Signal write task to stop
            await self.tx_queue.put(None)
            
            # Wait for tasks to complete
            tasks = []
            if self._read_task:
                tasks.append(self._read_task)
            if self._write_task:
                tasks.append(self._write_task)
            
            if tasks:
                done, pending = await asyncio.wait(tasks, timeout=2.0)
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self._read_task = None
            self._write_task = None
            
            # Close serial connection
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception as e:
                    logger.error(f"[{self.port_id}] Error closing writer: {e}")
                finally:
                    self._writer = None
            
            self._reader = None
            self.is_connected = False
            
            # Clear queues
            while not self.rx_queue.empty():
                try:
                    self.rx_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            while not self.tx_queue.empty():
                try:
                    self.tx_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info(f"[{self.port_id}] Disconnected")
            await self._trigger_callback(TransportEvent.DISCONNECT, self.port_id, reason)
            
            return True
    
    async def _read_worker(self):
        """Background worker for reading data"""
        logger.info(f"[{self.port_id}] Read worker started")
        
        try:
            while not self._disconnect_requested.is_set() and self._reader:
                try:
                    # Read available data
                    data = await asyncio.wait_for(
                        self._reader.read(self.read_buffer_size),
                        timeout=0.1
                    )
                    
                    if not data:
                        logger.warning(f"[{self.port_id}] EOF received")
                        self._disconnect_requested.set()
                        break
                    
                    self.stats['bytes_received'] += len(data)
                    
                    # Parse HCI packets
                    packets = self.hci_parser.add_data(data)
                    
                    for packet in packets:
                        self.stats['packets_received'] += 1
                        
                        # Extract flow control info
                        if self.enable_flow_control:
                            flow_info = HCIPacketParser.extract_flow_control_info(packet)
                            if flow_info:
                                await self._update_flow_control(flow_info)
                        
                        # Add to receive queue
                        try:
                            self.rx_queue.put_nowait(packet)
                            await self._trigger_callback(TransportEvent.READ, self.port_id, packet)
                        except asyncio.QueueFull:
                            logger.warning(f"[{self.port_id}] RX queue full, dropping packet")
                            self.stats['errors'] += 1
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"[{self.port_id}] Read error: {e}")
                    self.stats['errors'] += 1
                    await self._trigger_callback(TransportEvent.ERROR, self.port_id, 'read', str(e))
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"[{self.port_id}] Read worker cancelled")
        finally:
            logger.info(f"[{self.port_id}] Read worker stopped")
            if self._disconnect_requested.is_set() and self.is_connected:
                asyncio.create_task(self.disconnect("Read error"))
    
    async def _write_worker(self):
        """Background worker for writing data with flow control"""
        logger.info(f"[{self.port_id}] Write worker started")
        
        try:
            while True:
                try:
                    # Wait for packet to send
                    packet = await asyncio.wait_for(self.tx_queue.get(), timeout=0.1)
                    
                    if packet is None:  # Shutdown signal
                        break
                    
                    if not self.is_connected or not self._writer:
                        logger.error(f"[{self.port_id}] Cannot write: not connected")
                        await self._trigger_callback(TransportEvent.WRITE, self.port_id, packet, False, "Not connected")
                        continue
                    
                    # Check flow control
                    if self.enable_flow_control:
                        can_send = await self._check_flow_control(packet)
                        if not can_send:
                            # Put packet back and wait
                            await self.tx_queue.put(packet)
                            self.stats['flow_control_blocks'] += 1
                            await asyncio.sleep(0.01)
                            continue
                    
                    # Send packet
                    packet_bytes = bytes([packet.packet_type.value]) + packet.data
                    self._writer.write(packet_bytes)
                    await self._writer.drain()
                    
                    self.stats['packets_sent'] += 1
                    self.stats['bytes_sent'] += len(packet_bytes)
                    
                    # Update flow control counters
                    if self.enable_flow_control:
                        await self._update_flow_control_on_send(packet)
                    
                    await self._trigger_callback(TransportEvent.WRITE, self.port_id, packet, True, None)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"[{self.port_id}] Write error: {e}")
                    self.stats['errors'] += 1
                    await self._trigger_callback(TransportEvent.ERROR, self.port_id, 'write', str(e))
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"[{self.port_id}] Write worker cancelled")
        finally:
            logger.info(f"[{self.port_id}] Write worker stopped")
            if self._disconnect_requested.is_set() and self.is_connected:
                asyncio.create_task(self.disconnect("Write error"))
    
    async def _check_flow_control(self, packet: HCIPacket) -> bool:
        """Check if packet can be sent according to flow control"""
        async with self._flow_control_lock:
            if packet.packet_type == HCIPacketType.COMMAND:
                return self.flow_control.can_send_command
            elif packet.packet_type == HCIPacketType.ACL_DATA:
                return self.flow_control.can_send_acl
            else:
                # No flow control for other packet types
                return True
    
    async def _update_flow_control_on_send(self, packet: HCIPacket):
        """Update flow control counters when sending packet"""
        async with self._flow_control_lock:
            if packet.packet_type == HCIPacketType.COMMAND:
                self.flow_control.pending_commands += 1
            elif packet.packet_type == HCIPacketType.ACL_DATA:
                self.flow_control.pending_acl += 1
    
    async def _update_flow_control(self, flow_info: Dict[str, Any]):
        """Update flow control state from received packets"""
        async with self._flow_control_lock:
            if 'num_hci_command_packets' in flow_info:
                self.flow_control.num_hci_command_packets = flow_info['num_hci_command_packets']
                self.flow_control.pending_commands = max(0, self.flow_control.pending_commands - 1)
                
            if 'num_completed_acl_packets' in flow_info:
                completed = flow_info['num_completed_acl_packets']
                self.flow_control.pending_acl = max(0, self.flow_control.pending_acl - completed)
                # Simple assumption: controller can handle many ACL packets
                self.flow_control.num_acl_data_packets = 10
            
            await self._trigger_callback(TransportEvent.FLOW_CONTROL_UPDATE, self.port_id, self.flow_control)
    
    async def send_packet(self, packet: HCIPacket) -> bool:
        """Send an HCI packet"""
        if not self.is_connected:
            return False
        
        try:
            self.tx_queue.put_nowait(packet)
            return True
        except asyncio.QueueFull:
            logger.warning(f"[{self.port_id}] TX queue full")
            return False
    
    async def send_command(self, opcode: int, parameters: bytes = b'') -> bool:
        """Send an HCI command packet"""
        # Construct command packet
        data = struct.pack('<HB', opcode, len(parameters)) + parameters
        packet = HCIPacket(HCIPacketType.COMMAND, data)
        return await self.send_packet(packet)
    
    async def send_acl_data(self, handle: int, pb_flag: int, bc_flag: int, data: bytes) -> bool:
        """Send an ACL data packet"""
        # Construct ACL header
        handle_flags = (bc_flag << 14) | (pb_flag << 12) | (handle & 0x0FFF)
        header = struct.pack('<HH', handle_flags, len(data))
        packet = HCIPacket(HCIPacketType.ACL_DATA, header + data)
        return await self.send_packet(packet)
    
    async def receive_packet(self, timeout: Optional[float] = None) -> Optional[HCIPacket]:
        """Receive a packet from the RX queue"""
        try:
            if timeout is None:
                return await self.rx_queue.get()
            else:
                return await asyncio.wait_for(self.rx_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None
        except asyncio.QueueEmpty:
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get port status and statistics"""
        return {
            'port_id': self.port_id,
            'port_url': self.port_url,
            'baudrate': self.baudrate,
            'is_connected': self.is_connected,
            'rx_queue_size': self.rx_queue.qsize(),
            'tx_queue_size': self.tx_queue.qsize(),
            'flow_control': {
                'num_hci_commands': self.flow_control.num_hci_command_packets,
                'pending_commands': self.flow_control.pending_commands,
                'num_acl_packets': self.flow_control.num_acl_data_packets,
                'pending_acl': self.flow_control.pending_acl
            },
            'stats': self.stats.copy()
        }

class AsyncUARTManager:
    """Manager for multiple async UART ports"""
    
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._loop = loop
        self._ports: Dict[str, AsyncUARTPort] = {}
        self._lock = asyncio.Lock()
        
        # If no loop provided, we'll manage our own
        self._managed_loop = loop is None
        self._loop_thread = None
        
        if self._managed_loop:
            self._loop = asyncio.new_event_loop()
            self._start_event_loop()
    
    def _start_event_loop(self):
        """Start the event loop in a background thread"""
        def run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()
        
        # Wait for loop to start
        while not self._loop.is_running():
            time.sleep(0.01)
    
    def stop(self):
        """Stop the manager and all ports"""
        if self._managed_loop and self._loop:
            # Disconnect all ports
            future = asyncio.run_coroutine_threadsafe(self._disconnect_all(), self._loop)
            future.result(timeout=5.0)
            
            # Stop the loop
            self._loop.call_soon_threadsafe(self._loop.stop)
            
            if self._loop_thread:
                self._loop_thread.join(timeout=5.0)
    
    async def _disconnect_all(self):
        """Disconnect all ports"""
        tasks = []
        for port in self._ports.values():
            if port.is_connected:
                tasks.append(port.disconnect("Manager shutdown"))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def add_port(self, port_id: str, port_url: str, baudrate: int = 115200,
                 enable_flow_control: bool = True, **kwargs) -> AsyncUARTPort:
        """Add a new UART port"""
        if port_id in self._ports:
            raise ValueError(f"Port {port_id} already exists")
        
        port = AsyncUARTPort(port_id, port_url, baudrate, enable_flow_control, **kwargs)
        self._ports[port_id] = port
        return port
    
    def get_port(self, port_id: str) -> Optional[AsyncUARTPort]:
        """Get a port by ID"""
        return self._ports.get(port_id)
    
    def remove_port(self, port_id: str):
        """Remove a port"""
        if port_id in self._ports:
            port = self._ports[port_id]
            if port.is_connected:
                future = asyncio.run_coroutine_threadsafe(
                    port.disconnect("Port removed"),
                    self._loop
                )
                future.result(timeout=2.0)
            del self._ports[port_id]
    
    def connect_port(self, port_id: str) -> asyncio.Future:
        """Connect a port (returns future)"""
        port = self._ports.get(port_id)
        if not port:
            raise ValueError(f"Port {port_id} not found")
        
        return asyncio.run_coroutine_threadsafe(port.connect(), self._loop)
    
    def disconnect_port(self, port_id: str, reason: str = "User requested") -> asyncio.Future:
        """Disconnect a port (returns future)"""
        port = self._ports.get(port_id)
        if not port:
            raise ValueError(f"Port {port_id} not found")
        
        return asyncio.run_coroutine_threadsafe(port.disconnect(reason), self._loop)
    
    def send_packet(self, port_id: str, packet: HCIPacket) -> asyncio.Future:
        """Send a packet to a port (returns future)"""
        port = self._ports.get(port_id)
        if not port:
            raise ValueError(f"Port {port_id} not found")
        
        return asyncio.run_coroutine_threadsafe(port.send_packet(packet), self._loop)
    
    def get_available_ports(self) -> List[Tuple[str, str]]:
        """Get list of available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all ports"""
        return {port_id: port.get_status() for port_id, port in self._ports.items()}

# Example usage
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create manager
    manager = AsyncUARTManager()
    
    # List available ports
    available_ports = manager.get_available_ports()
    print("Available ports:")
    for device, description in available_ports:
        print(f"  {device}: {description}")
    
    if not available_ports:
        print("No serial ports found!")
        sys.exit(1)
    
    # Use first available port
    port_url = available_ports[0][0]
    
    # Add port with flow control enabled
    port = manager.add_port("HCI_Port", port_url, baudrate=115200, enable_flow_control=True)
    
    # Setup callbacks
    def on_connect(port_id, success, message):
        print(f"[CALLBACK] Connect: {port_id}, Success: {success}, Message: {message}")
    
    def on_disconnect(port_id, reason):
        print(f"[CALLBACK] Disconnect: {port_id}, Reason: {reason}")
    
    def on_packet_received(port_id, packet):
        print(f"[CALLBACK] Packet received on {port_id}: Type={packet.packet_type.name}, Length={len(packet.data)}")
    
    def on_flow_control_update(port_id, flow_state):
        print(f"[CALLBACK] Flow control update on {port_id}: Commands={flow_state.num_hci_command_packets}, ACL={flow_state.num_acl_data_packets}")
    
    port.add_callback('on_connect', on_connect)
    port.add_callback('on_disconnect', on_disconnect)
    port.add_callback('on_packet_received', on_packet_received)
    port.add_callback('on_flow_control_update', on_flow_control_update)
    
    # Connect
    print(f"Connecting to {port_url}...")
    connect_future = manager.connect_port("HCI_Port")
    
    try:
        # Wait for connection
        success = connect_future.result(timeout=5.0)
        if not success:
            print("Failed to connect!")
            sys.exit(1)
        
        print("Connected! Sending HCI Reset command...")
        
        # Send HCI Reset command (OGF=0x03, OCF=0x03, OpCode=0x0C03)
        reset_packet = HCIPacket(HCIPacketType.COMMAND, b'\x03\x0C\x00')
        send_future = manager.send_packet("HCI_Port", reset_packet)
        send_future.result(timeout=1.0)
        
        # Run for a while to see packets
        print("Listening for packets... Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
                status = port.get_status()
                print(f"Status: RX Queue={status['rx_queue_size']}, TX Queue={status['tx_queue_size']}, "
                      f"Flow Control: Cmds={status['flow_control']['num_hci_commands']}")
        except KeyboardInterrupt:
            print("\nStopping...")
        
    finally:
        # Disconnect
        print("Disconnecting...")
        disconnect_future = manager.disconnect_port("HCI_Port")
        disconnect_future.result(timeout=5.0)
        
        # Stop manager
        manager.stop()
        print("Done!")