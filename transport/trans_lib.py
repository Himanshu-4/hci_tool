
from transport.uart.uart_xfr import uart_transfer
from transport.SDIO.sdio_xfr import sdio_transfer
from transport.usb.usb_xfr import usb_transfer

import threading
import time

from utils.logger import LoggerManager as logger
from utils.logger import LogLevel

# define the maximum number of devices that can be connected
MAX_DEVICE_COUNT = 40


class TransportLibrary(uart_transfer, sdio_transfer, usb_transfer):
    """
    A class to handle different transport types (UART and SDIO) for data transfer.
    It provides a unified interface for sending and dereceiving data, as well as managing
    connection settings such as timeouts, baud rates, and SDIO speeds.
    """
    def __init__(self, transport_type : str, **kwargs):
        self.transport_type = transport_type
        self.transport = None

        if transport_type == 'UART':
            # init the UART transport base class
            uart_transfer().__init__(**kwargs)
        elif transport_type == 'SDIO':
            sdio_transfer().__init__(**kwargs)
        elif transport_type == 'USB':
            usb_transfer().__init__(**kwargs)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

    def send(self, data):
        if self.transport_type == 'UART':
            uart_transfer.send(self, data)
        elif self.transport_type == 'SDIO':
            sdio_transfer.send(self, data)
        elif self.transport_type == 'USB':
            usb_transfer.send(self, data)
        else:
            raise ValueError(f"Unsupported transport type: {self.transport_type}")


    def receive(self):
        return self.receive()
    
    def connect(self):
        return self.connect()
    
    def disconnect(self):
        return self.disconnect()
    
    @property
    def is_connected(self):
        return self.is_connected()
    
    def set_timeout(self, timeout):
        return self.set_timeout(timeout)
    
    def get_timeout(self):
        return self.get_timeout()
    
    def set_baudrate(self, baudrate):
        if self.transport_type != 'UART':
            raise ValueError("Baudrate can only be set for UART transport.")
        return self.set_baudrate(baudrate)
    
    def get_baudrate(self):
        if self.transport_type != 'UART':
            raise ValueError("Baudrate can only be retrieved for UART transport.")
        return self.get_baudrate()
    
    def set_sdio_speed(self, speed):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO speed can only be set for SDIO transport.")
        return self.set_sdio_speed(speed)
    
    def get_sdio_speed(self):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO speed can only be retrieved for SDIO transport.")
        return self.get_sdio_speed()
    
    def set_sdio_mode(self, mode):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO mode can only be set for SDIO transport.")
        return self.set_sdio_mode(mode)
    
    def get_sdio_mode(self):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO mode can only be retrieved for SDIO transport.")
        return self.get_sdio_mode()
    
    def set_sdio_bus_width(self, width):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO bus width can only be set for SDIO transport.")
        return self.set_sdio_bus_width(width)
    
    def get_sdio_bus_width(self):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO bus width can only be retrieved for SDIO transport.")
        return self.get_sdio_bus_width()
    
    def set_sdio_clock_speed(self, speed):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO clock speed can only be set for SDIO transport.")
        return self.set_sdio_clock_speed(speed)
    
    def get_sdio_clock_speed(self):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO clock speed can only be retrieved for SDIO transport.")
        return self.get_sdio_clock_speed()
    
    def set_sdio_timeout(self, timeout):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO timeout can only be set for SDIO transport.")
        return self.set_sdio_timeout(timeout)
    
    def get_sdio_timeout(self):
        if self.transport_type != 'SDIO':
            raise ValueError("SDIO timeout can only be retrieved for SDIO transport.")
        return self.get_sdio_timeout()



class Transport:
    """
    A class to handle different transport types (UART, SDIO, USB) for data transfer.
    It provides methods for sending and receiving data over the specified transport type.
    """
    _instance = None
    _lock = threading.Lock()
    _device_instances = {}
    _device_count = 0

    def __init__(self, transport_type: str, **kwargs):
        self.transport_type = transport_type
        self.transport = None

        if transport_type == 'UART':
            self.transport = uart_transfer(**kwargs)
        elif transport_type == 'SDIO':
            self.transport = sdio_transfer(**kwargs)
        elif transport_type == 'USB':
            self.transport = usb_transfer(**kwargs)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

 
    @property
    def is_connected(self):
        return self.transport.is_connected
    
    def set_timeout(self, timeout):
        return self.transport.set_timeout(timeout)
    
    def get_timeout(self):
        return self.transport.get_timeout()