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


MAX_DEVICE_COUNT = 10

class uart_transfer:
    """
    A class to handle UART data transfer.
    It provides methods for sending and receiving data over UART.
    """
    _instance = None
    _device_instances = {}
    _lock = threading.Lock()

    @classmethod
    def create_instance(cls, device_name) -> 'uart_transfer':
        """
        create the singleton instance of the uart_transfer class for the specified device.
        """
        with cls._lock:
            if cls._instance != None and device_name not in cls._device_instances.keys():
                return uart_transfer(device_name)
            
    @classmethod
    def get_instance(cls, device_name : str) -> 'uart_transfer':
        """
        Get the singleton instance of the uart_transfer class for the specified device.
        """
        return cls._instance
    
    
    def __init__(self, device_name):
        self.device_name = device_name
        self.serial_port = None
        self.is_connected = False
        self._device_instances[device_name] = self
        self._instance = self
        # self._logger = logger.get_logger(__name__, level=LogLevel.DEBUG,
        #                                   log_file=os.path.join(os.path.dirname(__file__), "uart_transfer.log"))
        
        # self._logger.debug(f"Creating uart_transfer instance for device: {device_name}")
        
        
        
    def connect(self, baudrate=115200, timeout=1):
        """
        Connect to the UART device.
        :param baudrate: Baud rate for the UART connection.
        :param timeout: Timeout for the UART connection.
        :return: True if connected, False otherwise.
        """
        # if self.is_connected:
        #     self._logger.warning(f"Already connected to {self.device_name}")
        #     return True
        
        # try:
        #     self.serial_port = serial.Serial(self.device_name, baudrate=baudrate, timeout=timeout)
        #     self.is_connected = True
            
        #     # self._logger.info(f"Connected to {self.device_name} at {baudrate} baud.")
        #     return True
        # except serial.SerialException as e:
        #     # self._logger.error(f"Failed to connect to {self.device_name}: {e}")
        #     return False
        print(f"Connecting to {self.device_name} at {baudrate} baud...")
        
        
    def disconnect(self):
        """
        Disconnect from the UART device.
        :return: True if disconnected, False otherwise.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return False
        
        # try:
        #     self.serial_port.close()
        #     self.is_connected = False
        #     self._logger.info(f"Disconnected from {self.device_name}.")
        #     return True
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to disconnect from {self.device_name}: {e}")
        #     return False
        print(f"Disconnecting from {self.device_name}...")
        
    def send(self, data: bytes):
        """
        Send data to the UART device.
        :param data: Data to be sent.
        :return: True if data is sent successfully, False otherwise.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return False
        
        # try:
        #     self.serial_port.write(data)
        #     self._logger.info(f"Sent data to {self.device_name}: {data}")
        #     return True
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to send data to {self.device_name}: {e}")
        #     return False
        print(f"Sending data to {self.device_name}: {data}")
        
        
    def receive(self, size: int = 1024):
        """
        Receive data from the UART device.
        :param size: Number of bytes to read.
        :return: Received data.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return None
        
        # try:
        #     data = self.serial_port.read(size)
        #     self._logger.info(f"Received data from {self.device_name}: {data}")
        #     return data
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to receive data from {self.device_name}: {e}")
        #     return None
        print(f"Receiving data from {self.device_name}...")
        
    def set_timeout(self, timeout: int):
        """
        Set the timeout for the UART connection.
        :param timeout: Timeout in seconds.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return False
        
        # try:
        #     self.serial_port.timeout = timeout
        #     self._logger.info(f"Set timeout for {self.device_name} to {timeout} seconds.")
        #     return True
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to set timeout for {self.device_name}: {e}")
        #     return False
        print(f"Setting timeout for {self.device_name} to {timeout} seconds...")
        
        
    def get_timeout(self):
        """
        Get the timeout for the UART connection.
        :return: Timeout in seconds.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return None
        
        # try:
        #     timeout = self.serial_port.timeout
        #     self._logger.info(f"Timeout for {self.device_name} is {timeout} seconds.")
        #     return timeout
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to get timeout for {self.device_name}: {e}")
        #     return None
        print(f"Getting timeout for {self.device_name}...")
        
    def set_baudrate(self, baudrate: int):
        """
        Set the baud rate for the UART connection.
        :param baudrate: Baud rate.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return False
        
        # try:
        #     self.serial_port.baudrate = baudrate
        #     self._logger.info(f"Set baud rate for {self.device_name} to {baudrate}.")
        #     return True
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to set baud rate for {self.device_name}: {e}")
        #     return False
        print(f"Setting baud rate for {self.device_name} to {baudrate}...")
        self.baudrate = baudrate
        
    def get_baudrate(self):
        """
        Get the baud rate for the UART connection.
        :return: Baud rate.
        """
        # if not self.is_connected:
        #     self._logger.warning(f"Not connected to {self.device_name}")
        #     return None
        
        # try:
        #     baudrate = self.serial_port.baudrate
        #     self._logger.info(f"Baud rate for {self.device_name} is {baudrate}.")
        #     return baudrate
        # except serial.SerialException as e:
        #     self._logger.error(f"Failed to get baud rate for {self.device_name}: {e}")
        #     return None
        print(f"Getting baud rate for {self.device_name}...")
        return self.baudrate
    
