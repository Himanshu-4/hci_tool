"""
    tranport_layer.py
    This module provides functionality for transport layer operations.
    It includes:
    handling all the transport layer operations of different transport types (UART, SDIO).
    It includes:
    - Transport layer classes for different transport types (UART, SDIO).
    - Functions for sending and receiving data.
    - Error handling for file operations.
    - Logging for debugging and monitoring.
    - Utility functions for managing transport connections.
    - calling the handler functions of the transport layer.
    
    
    
"""

import asyncio
import threading

from transport.uart.uart_xfr import uart_transfer
from transport.SDIO.sdio_xfr import sdio_transfer
from transport.usb.usb_xfr import usb_transfer

from utils.logger import LoggerManager as logger
from utils.logger import LogLevel

from trans_lib import Transport


class TransportLayer:
    """
    A class to handle different transport types (UART, SDIO, USB) for data transfer.
    It provides a unified interface for sending and receiving data, as well as managing
    connection settings such as timeouts, baud rates, and SDIO speeds.
    """
    _instance = None
    _lock = threading.Lock()
    
    
    @classmethod
    def get_instance(cls, transport_type: str, **kwargs) -> 'TransportLayer':
        """
        Get the singleton instance of the TransportLayer class for the specified transport type.
        """
        return cls._instance
        
    def create_instance(cls, transport_type: str, **kwargs) -> 'TransportLayer':
        """
        crearte the singleton instance of the TransportLayer class for the specified transport type.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = TransportLayer(transport_type, **kwargs)
            return cls._instance
        

    
    def __init__(self, transport_type: str, **kwargs):
        self.transport_type = transport_type
        self.transport = None

        if transport_type == 'UART':
            self.transport = uart_transfer.create_instance(**kwargs)
        elif transport_type == 'SDIO':
            self.transport = sdio_transfer.create_instance(**kwargs)
        elif transport_type == 'USB':
            self.transport = usb_transfer.create_instance(**kwargs)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
        
        
        # self._logger = logger.get_logger(__name__, level=LogLevel.DEBUG,
        #                                   to_console=True, to_file=True,
        #                                   description=True, prepend="Transport Layer: ",
        #                                   append="", log_file=None, enable=True)
        # self._logger.debug(f"Transport layer instance created for transport type: {transport_type}")
        # self._logger.debug(f"Transport layer instance created for transport type: {transport_type}")
        
        
        
        def __del__(self):
            """
            Destructor to clean up the transport layer instance.
            """
            if self.transport:
                self.transport.disconnect()
                self.transport = None
                TransportLayer._instance = None
                self._logger.debug(f"Transport layer instance destroyed for transport type: {self.transport_type}")
                
        
        def worker_thread(self):
            """
            Worker thread to handle transport layer operations.
            """
            while True:
                # Perform transport layer operations here
                pass
                # Check for exit condition
                if self._exit_event.is_set():
                    break
            self._logger.debug("Worker thread exiting.")
            self._exit_event.set()
            self._worker_thread.join()
            self._logger.debug("Worker thread joined.")
            self._logger.debug("Worker thread started.")