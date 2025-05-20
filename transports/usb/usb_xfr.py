"""
Usb transfer module
This module provides functionality for USB data transfer.
It includes:
- USB transfer classes for different transport types (UART, SDIO).
- Functions for sending and receiving data.
- Error handling for file operations.
- Logging for debugging and monitoring.
- Utility functions for managing USB connections.
- Custom exceptions for error handling.
- [specific functionality, e.g., data validation, etc.]
- [specific functionality, e.g., data processing, etc.]
- [specific functionality, e.g., data formatting, etc.]
- [specific functionality, e.g., data conversion, etc.]
- [specific functionality, e.g., data encryption, etc.]
- [specific functionality, e.g., data decryption, etc.]
- [specific functionality, e.g., data compression, etc.]
- [specific functionality, e.g., data decompression, etc.]
#         filename -- name of the file that already exists

"""


MAX_DEVICE_COUNT = 10


from utils.logger import LoggerManager as logger
from utils.logger import LogLevel
import threading

import asyncio
import time

class usb_transfer:
    """
    A class to handle USB data transfer.
    It provides methods for sending and receiving data over USB.
    """
    _instance = None
    _lock = threading.Lock()

    
    @classmethod
    def create_instance(cls, device_name) -> 'usb_transfer':
        """
        Get the singleton instance of the usb_transfer class for the specified device.
        """
        with cls._lock:
            if cls._instance != None and device_name not in cls._device_instances.keys():
                return usb_transfer(device_name)
            
    
    @classmethod
    def get_device_instance(cls, device_name) -> 'usb_transfer':
        """
        Get the instance of the usb_transfer class for the specified device.
        """
        with cls._lock:
            if device_name in cls._device_instances:
                return cls._device_instances[device_name]
            else:
                raise ValueError(f"No instance found for device: {device_name}")        


    def __init__(self, device_name, timeout=1):
        self.device_name = device_name
        self._inteface_str = None
        self.timeout = timeout
        self._is_connected = False
        self._lock = threading.Lock()
        usb_transfer._device_instances[device_name] = self
        # self._logger = logger.get_logger(__name__, level=LogLevel.DEBUG,
        #                                  to_console=True, to_file=True,
        #                                  description=True, prepend="USB Transfer: ",
        #                                  append="", log_file=None, enable=True)
        # self._logger.debug(f"USB transfer instance created for device: {device_name}")
        # self._logger.debug(f"Baudrate: , Timeout: {timeout}")


    def connect(self):
        """
        Connect to the USB device.
        """
        with self._lock:
            if self._is_connected:
                raise ValueError(f"Already connected to device: {self.device_name}")
            
            # Simulate connection process
            time.sleep(1)
            self._is_connected = True
            print(f"Connected to USB device: {self.device_name}")
            
    def disconnect(self):
        """
        Disconnect from the USB device.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            # Simulate disconnection process
            time.sleep(1)
            self._is_connected = False
            print(f"Disconnected from USB device: {self.device_name}")
            
    def send(self, data: bytes):
        """
        Send data to the USB device.
        :param data: Data to be sent.
        :return: True if data is sent successfully, False otherwise.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            # Simulate sending data
            time.sleep(1)
            print(f"Sent data to USB device: {self.device_name}")
            return True
        
    def receive(self):
        """
        Receive data from the USB device.
        :return: Received data.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            # Simulate receiving data
            time.sleep(1)
            data = b"Received data from USB device"
            print(f"Received data from USB device: {self.device_name}")
            return data
        
    def set_timeout(self, timeout: int):
        """
        Set the timeout for the USB device.
        :param timeout: Timeout in seconds.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            self.timeout = timeout
            print(f"Set timeout for USB device {self.device_name} to {timeout} seconds")
        return True
    
    def get_timeout(self):
        """
        Get the timeout for the USB device.
        :return: Timeout in seconds.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            print(f"Get timeout for USB device {self.device_name}: {self.timeout} seconds")
            return self.timeout
        
    def set_interface_string(self, interface_str: str):
        """
        Set the interface string for the USB device.
        :param interface_str: Interface string.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            self._inteface_str = interface_str
            print(f"Set interface string for USB device {self.device_name} to {interface_str}")
        return True
    
    def get_interface_string(self):
        """
        Get the interface string for the USB device.
        :return: Interface string.
        """
        with self._lock:
            if not self._is_connected:
                raise ValueError(f"Not connected to device: {self.device_name}")
            
            print(f"Get interface string for USB device {self.device_name}: {self._inteface_str}")
            return self._inteface_str
        