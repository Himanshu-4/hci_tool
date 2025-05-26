from typing import Dict, Any, Optional
from .base_lib import TransportInterface, ConnectionStatus, TransportError
from .UART.uart import UARTTransport
from .SDIO.sdio import SDIOTransport
from .USB.usb import USBTransport


class Transport:
    """Main transport class that manages different transport interfaces"""
    
    def __init__(self, name: str = "DefaultTransport"):
        self.name = name
        self.interface_type = None
        self.transport_instance = None
        
        # Available transport interfaces
        self.available_interfaces = {
            'UART': UARTTransport,
            'SDIO': SDIOTransport,
            'USB': USBTransport
        }
    
    def select_interface(self, interface_type: str) -> bool:
        """
        Select and initialize transport interface
        Args:
            interface_type: Type of interface ('UART', 'SDIO', 'USB')
        Returns True if interface is available and selected
        """
        try:
            if interface_type not in self.available_interfaces:
                raise TransportError(f"Interface '{interface_type}' not available. "
                                   f"Available interfaces: {list(self.available_interfaces.keys())}")
            
            # Disconnect current interface if connected
            if self.transport_instance and self.transport_instance.is_connected():
                self.transport_instance.disconnect()
            
            # Create new interface instance
            interface_class = self.available_interfaces[interface_type]
            self.transport_instance = interface_class()
            self.interface_type = interface_type
            
            return True
            
        except Exception as e:
            raise TransportError(f"Failed to select interface: {str(e)}")
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the selected transport interface
        Args:
            config: Configuration parameters dictionary
        Returns True if configuration successful
        """
        if not self.transport_instance:
            raise TransportError("No interface selected. Call select_interface() first.")
        
        return self.transport_instance.configure(config)
    
    def connect(self) -> bool:
        """
        Establish connection using the selected and configured interface
        Returns True if connection successful
        """
        if not self.transport_instance:
            raise TransportError("No interface selected. Call select_interface() first.")
        
        return self.transport_instance.connect()
    
    def disconnect(self) -> bool:
        """
        Close the connection
        Returns True if disconnection successful
        """
        if not self.transport_instance:
            return True
        
        return self.transport_instance.disconnect()
    
    def read(self, size: int = -1) -> Optional[bytes]:
        """
        Read data from the transport interface
        Args:
            size: Number of bytes to read (-1 for all available)
        Returns bytes data or None if no data/error
        """
        if not self.transport_instance:
            raise TransportError("No interface selected.")
        
        return self.transport_instance.read(size)
    
    def write(self, data: bytes) -> bool:
        """
        Write data to the transport interface
        Args:
            data: Bytes to write
        Returns True if write successful
        """
        if not self.transport_instance:
            raise TransportError("No interface selected.")
        
        return self.transport_instance.write(data)
    
    def add_callback(self, event_type: str, callback):
        """
        Add callback function for transport events
        Args:
            event_type: Type of event ('read', 'write', 'connect', 'disconnect')
            callback: Function to call when event occurs
        """
        if not self.transport_instance:
            raise TransportError("No interface selected.")
        
        self.transport_instance.add_callback(event_type, callback)
    
    def remove_callback(self, event_type: str, callback):
        """
        Remove callback function
        Args:
            event_type: Type of event
            callback: Function to remove
        """
        if not self.transport_instance:
            raise TransportError("No interface selected.")
        
        self.transport_instance.remove_callback(event_type, callback)
    
    def get_status(self) -> ConnectionStatus:
        """Get current connection status"""
        if not self.transport_instance:
            return ConnectionStatus.DISCONNECTED
        
        return self.transport_instance.get_status()
    
    def is_connected(self) -> bool:
        """Check if currently connected"""
        if not self.transport_instance:
            return False
        
        return self.transport_instance.is_connected()
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        if not self.transport_instance:
            return {}
        
        return self.transport_instance.get_config()
    
    def get_interface_type(self) -> Optional[str]:
        """Get currently selected interface type"""
        return self.interface_type
    
    def get_available_interfaces(self) -> list:
        """Get list of available transport interfaces"""
        return list(self.available_interfaces.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get transport statistics"""
        stats = {
            'interface_type': self.interface_type,
            'status': self.get_status().value if self.transport_instance else 'not_selected'
        }
        
        if self.transport_instance and hasattr(self.transport_instance, 'get_stats'):
            stats.update(self.transport_instance.get_stats())
        
        return stats

# Convenience functions for direct interface access
def create_uart_transport() -> UARTTransport:
    """Create a UART transport instance directly"""
    return UARTTransport()

def create_sdio_transport() -> SDIOTransport:
    """Create an SDIO transport instance directly"""
    return SDIOTransport()

def create_usb_transport() -> USBTransport:
    """Create a USB transport instance directly"""
    return USBTransport()