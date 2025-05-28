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
        self.default_config = {
            'port': None,
            'baudrate': 115200,
            'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE,
            'stopbits': serial.STOPBITS_ONE,
            'timeout': 1,
            'xonxoff': False,
            'rtscts': False,
            'dsrdtr': False
        }
    
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
            self.config = self.default_config.copy()
            self.config.update(config)
            
            # Validate baudrate
            valid_baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
            if self.config['baudrate'] not in valid_baudrates:
                raise ConfigurationError(f"Invalid baudrate: {self.config['baudrate']}")
            
            return True
            
        except Exception as e:
            raise ConfigurationError(f"UART configuration error: {str(e)}")
    
    def connect(self) -> bool:
        """
        Establish UART connection
        Returns True if connection successful
        """
        try:
            if self.is_connected():
                return True
            
            if not self.config.get('port'):
                raise ConnectionError("No port configured")
            
            self.status = ConnectionStatus.CONNECTING
            
            # Create serial connection
            self.serial_connection = serial.Serial(
                port=self.config['port'],
                baudrate=self.config['baudrate'],
                bytesize=self.config['bytesize'],
                parity=self.config['parity'],
                stopbits=self.config['stopbits'],
                timeout=self.config['timeout'],
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
            self._trigger_callbacks('connect', self)
            
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
            
            self._trigger_callbacks('disconnect', self)
            
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
                    self._trigger_callbacks('read', packet)
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
                self._trigger_callbacks('write', data)
            
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
            'port': self.config.get('port', 'Unknown'),
            'baudrate': self.config.get('baudrate', 0),
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