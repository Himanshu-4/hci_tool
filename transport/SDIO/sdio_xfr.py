"""
    sdio transfer.py
    This module provides functionality for SDIO data transfer.
    It includes:
    - SDIO transfer classes for different transport types (UART, SDIO).
    - Functions for sending and receiving data.
    - Error handling for file operations.
    - Logging for debugging and monitoring.
    - Utility functions for managing SDIO connections.
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
import threading
import time
import asyncio

from utils.logger import LoggerManager as logger
from utils.logger import LogLevel


MAX_DEVICE_COUNT = 10



class sdio_transfer:
    """
    A class to handle SDIO data transfer.
    It provides methods for sending and receiving data over SDIO.
    """
    _instance = None
    _device_instances = {}
    _lock = threading.Lock()

    @classmethod
    def create_instance(cls, device_name) -> 'sdio_transfer':
        """
        Get the singleton instance of the sdio_transfer class for the specified device.
        """
        with cls._lock:
            if cls._instance != None and device_name not in cls._device_instances.keys():
                return sdio_transfer(device_name)
            
            
    def __init__(self, device_name: str):
        """
        Initialize the sdio_transfer class for the specified device.
        """
        if device_name in self._device_instances:
            raise ValueError(f"Device {device_name} is already connected.")
        
        self.device_name = device_name
        self._device_instances[device_name] = self
        self._device_count = len(self._device_instances)
        
        if self._device_count > MAX_DEVICE_COUNT:
            raise ValueError(f"Maximum device count exceeded: {MAX_DEVICE_COUNT}")
        
        print(f"SDIO transfer instance created for device: {device_name}")
        self._is_connected = False
        self._lock = threading.Lock()
        self._timeout = 5  # Default timeout in seconds
        self._clock_speed = 50  # Default clock speed in MHz
        self._instance = self
        
        # @TODO: Uncomment the logger initialization when the logger module is available
        # self._logger = logger.get_logger(__name__, level=LogLevel.DEBUG,
        #                                   log_file=os.path.join(os.getcwd(), "sdio_transfer.log"),
        #                                   log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # self._logger.debug(f"Creating sdio_transfer instance for device: {device_name}")
        # self._logger.debug(f"SDIO transfer instance created for device: {device_name}")
            
    def connect(self):
        """
        Connect to the specified SDIO device.
        """
        # Simulate connection to the device
        print(f"Connected to SDIO device: {self.device_name}")
        return True
    
    def disconnect(self):
        """
        Disconnect from the specified SDIO device.
        """
        # Simulate disconnection from the device
        print(f"Disconnected from SDIO device: {self.device_name}")
        return True
    
    def send(self, data: bytes):
        """
        Send data to the specified SDIO device.
        """
        # Simulate sending data to the device
        print(f"Sending data to SDIO device {self.device_name}: {data}")
        return True
    
    def receive(self):
        """
        Receive data from the specified SDIO device.
        """
        # Simulate receiving data from the device
        data = b"Received data from SDIO device"
        print(f"Receiving data from SDIO device {self.device_name}: {data}")
        return data
    
    def set_sdio_clock_speed(self, speed: int):
        """
        Set the SDIO clock speed for the specified device.
        """
        # Simulate setting the clock speed
        print(f"Setting SDIO clock speed for device {self.device_name} to {speed} MHz")
        return True
    
    def get_sdio_clock_speed(self):
        """
        Get the SDIO clock speed for the specified device.
        """
        # Simulate getting the clock speed
        speed = 50
        print(f"Getting SDIO clock speed for device {self.device_name}: {speed} MHz")
        return speed