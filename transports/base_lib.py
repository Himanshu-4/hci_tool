from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
from enum import StrEnum, Enum

class ConnectionStatus(StrEnum):    
    """Enumeration for connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    ERROR = "error"
    

class TransportState(Enum):
    """Transport state"""
    INITIALIZED = 0
    DISCONNECTED = 1
    CONNECTED = 2
    ERROR = 3

class TransportEvent(Enum):
    """Transport event"""
    READ = 0
    WRITE = 1
    CONNECT = 2
    DISCONNECT = 3
    ERROR = 4
    FLOW_CONTROL_UPDATE = 5

class TransportInterface(ABC):
    """Abstract base class for all transport interfaces"""
    
    def __init__(self):
        self.status = ConnectionStatus.DISCONNECTED
        self.config = {}
        self.callbacks = {
            TransportEvent.READ: [],
            TransportEvent.WRITE: [],
            TransportEvent.CONNECT: [],
            TransportEvent.DISCONNECT: [],
            TransportEvent.ERROR: []
        }
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection with the configured parameters
        Returns True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close the connection
        Returns True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the transport interface with given parameters
        Args:
            config: Dictionary containing configuration parameters
        Returns True if configuration is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def read(self, size: int = -1) -> Optional[bytes]:
        """
        Read data from the transport interface
        Args:
            size: Number of bytes to read (-1 for all available)
        Returns bytes data or None if error/no data
        """
        pass
    
    @abstractmethod
    def write(self, data: bytes) -> bool:
        """
        Write data to the transport interface
        Args:
            data: Bytes to write
        Returns True if successful, False otherwise
        """
        pass
    
    def add_callback(self, event_type: str, callback: Callable):
        """
        Add a callback function for specific events
        Args:
            event_type: Type of event ('read', 'write', 'connect', 'disconnect')
            callback: Function to call when event occurs
        """
        if event_type in self.callbacks.keys():
            self.callbacks[event_type].append(callback)
        else:
            raise ValueError(f"Invalid event type: {event_type}")
    
    def remove_callback(self, event_type: str, callback: Callable):
        """
        Remove a callback function
        Args:
            event_type: Type of event
            callback: Function to remove
        """
        if event_type in self.callbacks.keys() and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
    
    def _trigger_callbacks(self, event_type: str, *args, **kwargs):
        """
        Trigger all callbacks for a specific event type
        Args:
            event_type: Type of event
            *args, **kwargs: Arguments to pass to callback functions
        """
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Callback error in {event_type}: {e}")
    
    def get_status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self.status
    
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.status == ConnectionStatus.CONNECTED
    
    @property
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.__dict__

class TransportError(Exception):
    """Custom exception for transport-related errors"""
    pass

class ConfigurationError(TransportError):
    """Exception for configuration-related errors"""
    pass

class ConnectionError(TransportError):
    """Exception for connection-related errors"""
    pass