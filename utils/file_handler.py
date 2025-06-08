"""
Enhanced File Handler Module with Async FileIO Operations
This module provides comprehensive file handling capabilities including:
- Asynchronous FileIO operations with no blocking penalties
- Callback-based event handling
- Both async and blocking API variants
- Global event loop management
- Automatic flushing and cleanup
- Integration with logging systems
"""

import asyncio
import os
import sys
import time
import threading
import weakref
import atexit
from typing import Optional, Callable, Dict, Any, Union, List
from enum import Enum
from datetime import datetime
from dataclasses import dataclass

# Import dependencies

from .async_exec import EventLoopManager
from .asyncio_files import open_async, AsyncTextFile, AsyncBinaryFile
from .Exceptions import *


# Global configuration
_FILE_IO_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
_FILE_IO_MAX_FILES = 5  # Number of files to keep if size exceeds limit

__BASE_DIR = None
_BASE_PATH = None   
_LOG_PATH = None
_LOG_FILE = None


@staticmethod
def __init_base_module():
    """Initialize the base module paths and directories"""
    global __BASE_DIR, _BASE_PATH, _LOG_PATH, _LOG_FILE
    
    print("[FileHandler] Initializing base module...")
    
    # Set the base directory and log path
    _BASE_PATH = __BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _BASE_PATH = os.path.join(os.path.abspath(_BASE_PATH), "app_data")
    _LOG_PATH = os.path.join(_BASE_PATH, "logs")
    
    # Create the log directory if it doesn't exist
    if not os.path.exists(_LOG_PATH):
        os.makedirs(_LOG_PATH, exist_ok=True)
    
    _LOG_FILE = os.path.join(_LOG_PATH, "app.log.txt")  
    if not os.path.isfile(_LOG_FILE):
        with open(_LOG_FILE, 'w') as f:
            f.write(f"{datetime.now()} [FileHandler] APP Started{os.linesep}")


class FileIOEvent(Enum):
    """Events that can trigger callbacks"""
    OPENED = "opened"
    CLOSED = "closed"
    READ = "read"
    WRITE = "write"
    ERROR = "error"
    FLUSH = "flush"
    SEEK = "seek"


class FileIOMode(Enum):
    """File operation modes"""
    READ = "r"
    WRITE = "w"
    APPEND = "a"
    READ_BINARY = "rb"
    WRITE_BINARY = "wb"
    APPEND_BINARY = "ab"
    READ_WRITE = "r+"
    READ_WRITE_BINARY = "r+b"


@dataclass
class FileIOCallbackData:
    """Data structure passed to callbacks"""
    event: FileIOEvent
    data: Any = None
    error: Exception = None
    file_path: str = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class FileInfo:
    """File information data structure"""
    file_name: str
    size: int
    full_path: str
    rel_path: str
    file_type: str
    last_modified: datetime
    
    def __init__(self, file_path: str):
        if not os.path.isfile(file_path):
            raise CustomFileNotFoundError(file_path)

        self.full_path = os.path.abspath(file_path)
        self.rel_path = os.path.relpath(file_path)
        self.file_name = os.path.basename(file_path)
        self.size = os.path.getsize(file_path)
        self.file_type = os.path.splitext(file_path)[1]
        self.last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
    
    @property
    def is_readable(self):
        return os.access(self.full_path, os.R_OK)
    
    @property
    def is_writable(self):
        return os.access(self.full_path, os.W_OK)
    
    @property
    def is_executable(self):
        return os.access(self.full_path, os.X_OK)


class FileIO:
    """
    High-performance asynchronous FileIO class with callback support.
    
    Features:
    - Non-blocking file operations
    - Callback-based event handling
    - Both async and blocking API variants
    - Automatic flushing on destruction
    - Global event loop management
    - Error handling with custom exceptions
    """
    
    # Global event loop manager for all FileIO instances
    _global_manager: Optional[EventLoopManager] = None
    _instances: weakref.WeakSet = weakref.WeakSet()
    _lock = threading.Lock()
    _initialized = False
    
    @classmethod
    def _ensure_global_manager(cls):
        """Ensure the global event loop manager is initialized"""
        with cls._lock:
            if not cls._initialized:
                cls._global_manager = EventLoopManager("FileIO_Manager")
                cls._global_manager.start()
                cls._initialized = True
                
                print("[FileIO] Global event loop manager initialized")
                
                # Register cleanup handlers
                atexit.register(cls._cleanup_all)
                if hasattr(cls._global_manager, 'add_task_destroy_callback'):
                    cls._global_manager.add_task_destroy_callback(cls._flush_all_instances)
                
    @classmethod
    def _cleanup_all(cls):
        """Cleanup all FileIO instances and the global manager"""
        print("[FileIO] Cleaning up all FileIO instances")
        
        # Flush all instances
        instances = list(cls._instances)
        for instance in instances:
            try:
                if not instance._closed:
                    instance.close_wait()
            except Exception as e:
                print(f"[FileIO] Error closing instance {instance._file_path}: {e}")
        
        # Destroy the global manager
        if cls._global_manager:
            cls._global_manager.destroy()
            cls._global_manager = None
            cls._initialized = False
            
    @classmethod
    def _flush_all_instances(cls):
        """Flush all FileIO instances (called before manager shutdown)"""
        print("[FileIO] Flushing all FileIO instances before manager shutdown")
            
        async def flush_all():
            instances = list(cls._instances)
            tasks = []
            for instance in instances:
                if not instance._closed and instance._file:
                    tasks.append(instance._async_flush())
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        if cls._global_manager and hasattr(cls._global_manager, 'is_running') and cls._global_manager.is_running:
            try:
                cls._global_manager.run_and_wait(flush_all(), timeout=10)
            except Exception as e:
                print(f"[FileIO] Error flushing instances: {e}")

    def __init__(self, file_path: str, mode: Union[str, FileIOMode] = FileIOMode.READ, 
                 encoding: str = "utf-8", buffering: int = -1, auto_flush: bool = False):
        """
        Initialize FileIO instance
        
        Args:
            file_path: Path to the file
            mode: File opening mode
            encoding: Text encoding for text files
            buffering: Buffering policy
            auto_flush: Whether to auto-flush after each write
        """
        self._ensure_global_manager()
        
        self._file_path = os.path.abspath(file_path)
        self._mode = mode.value if isinstance(mode, FileIOMode) else mode
        self._encoding = encoding
        self._buffering = buffering
        self._auto_flush = auto_flush
        
        # State management
        self._file: Optional[Union[AsyncTextFile, AsyncBinaryFile]] = None
        self._closed = True
        self._callbacks: Dict[FileIOEvent, List[Callable[[FileIOCallbackData], None]]] = {
            event: [] for event in FileIOEvent
        }
        
        # Register this instance
        self._instances.add(self)
        
        print(f"[FileIO] Instance created for {self._file_path} with mode {self._mode}")

    def __del__(self):
        """Destructor - ensure file is closed and flushed"""
        if not self._closed:
            try:
                self.close_wait()
            except Exception as e:
                print(f"[FileIO] Error closing in destructor: {e}")

    def add_callback(self, event: FileIOEvent, callback: Callable[[FileIOCallbackData], None]):
        """Add a callback for a specific event"""
        self._callbacks[event].append(callback)
        
    def remove_callback(self, event: FileIOEvent, callback: Callable[[FileIOCallbackData], None]):
        """Remove a callback for a specific event"""
        if callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            
    def _trigger_callbacks(self, event: FileIOEvent, data: Any = None, error: Exception = None):
        """Trigger all callbacks for an event"""
        if not self._callbacks[event]:
            return
            
        callback_data = FileIOCallbackData(event, data, error, self._file_path)
        
        for callback in self._callbacks[event]:
            try:
                callback(callback_data)
            except Exception as e:
                print(f"[FileIO] Error in callback for event {event}: {e}")

    async def _async_open(self):
        """Asynchronously open the file"""
        try:
            # Create a simple async file opener if open_async is not available
            if 'open_async' in globals():
                self._file = await open_async(
                    self._file_path, 
                    self._mode, 
                    buffering=self._buffering,
                    encoding=self._encoding if 'b' not in self._mode else None
                ).__aenter__()
            else:
                # Fallback to synchronous opening in executor
                loop = asyncio.get_event_loop()
                file_obj = await loop.run_in_executor(
                    None, 
                    open, 
                    self._file_path, 
                    self._mode,
                    self._buffering,
                    self._encoding if 'b' not in self._mode else None
                )
                self._file = file_obj
                
            self._closed = False
            self._trigger_callbacks(FileIOEvent.OPENED, self._file_path)
            print(f"[FileIO] File opened: {self._file_path}")
        except Exception as e:
            self._trigger_callbacks(FileIOEvent.ERROR, error=e)
            print(f"[FileIO] Error opening file {self._file_path}: {e}")
            raise

    async def _async_close(self):
        """Asynchronously close the file"""
        if self._closed or not self._file:
            return
            
        try:
            if hasattr(self._file, 'close'):
                if asyncio.iscoroutinefunction(self._file.close):
                    await self._file.close()
                else:
                    self._file.close()
            else:
                self._file.close()
                
            self._closed = True
            self._trigger_callbacks(FileIOEvent.CLOSED, self._file_path)
            print(f"[FileIO] File closed: {self._file_path}")
        except Exception as e:
            self._trigger_callbacks(FileIOEvent.ERROR, error=e)
            print(f"[FileIO] Error closing file {self._file_path}: {e}")
            raise

    async def _async_read(self, size: Optional[int] = None) -> Union[str, bytes]:
        """Asynchronously read from the file"""
        if self._closed or not self._file:
            raise CustomFileException(self._file_path, "File is not open")
            
        try:
            if hasattr(self._file, 'read') and asyncio.iscoroutinefunction(self._file.read):
                data = await self._file.read(size)
            else:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, self._file.read, size)
                
            self._trigger_callbacks(FileIOEvent.READ, data)
            print(f"[FileIO] Read {len(data)} characters/bytes from {self._file_path}")
            return data
        except Exception as e:
            self._trigger_callbacks(FileIOEvent.ERROR, error=e)
            print(f"[FileIO] Error reading from file {self._file_path}: {e}")
            raise

    async def _async_write(self, data: Union[str, bytes]) -> int:
        """Asynchronously write to the file"""
        if self._closed or not self._file:
            raise CustomFileException(self._file_path, "File is not open")
            
        try:
            if hasattr(self._file, 'write') and asyncio.iscoroutinefunction(self._file.write):
                bytes_written = await self._file.write(data)
                if self._auto_flush and hasattr(self._file, 'flush'):
                    await self._file.flush()
            else:
                loop = asyncio.get_event_loop()
                bytes_written = await loop.run_in_executor(None, self._file.write, data)
                if self._auto_flush:
                    await loop.run_in_executor(None, self._file.flush)
                    
            self._trigger_callbacks(FileIOEvent.WRITE, bytes_written)
            print(f"[FileIO] Wrote {bytes_written} characters/bytes to {self._file_path}")
            return bytes_written
        except Exception as e:
            self._trigger_callbacks(FileIOEvent.ERROR, error=e)
            print(f"[FileIO] Error writing to file {self._file_path}: {e}")
            raise

    async def _async_flush(self):
        """Asynchronously flush the file"""
        if self._closed or not self._file:
            return
            
        try:
            if hasattr(self._file, 'flush'):
                if asyncio.iscoroutinefunction(self._file.flush):
                    await self._file.flush()
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._file.flush)
                    
            self._trigger_callbacks(FileIOEvent.FLUSH)
            print(f"[FileIO] Flushed file: {self._file_path}")
        except Exception as e:
            self._trigger_callbacks(FileIOEvent.ERROR, error=e)
            print(f"[FileIO] Error flushing file {self._file_path}: {e}")
            raise

    async def _async_seek(self, offset: int, whence: int = 0) -> int:
        """Asynchronously seek in the file"""
        if self._closed or not self._file:
            raise CustomFileException(self._file_path, "File is not open")
            
        try:
            if hasattr(self._file, 'seek') and asyncio.iscoroutinefunction(self._file.seek):
                position = await self._file.seek(offset, whence)
            else:
                loop = asyncio.get_event_loop()
                position = await loop.run_in_executor(None, self._file.seek, offset, whence)
                
            self._trigger_callbacks(FileIOEvent.SEEK, position)
            print(f"[FileIO] Seeked to position {position} in {self._file_path}")
            return position
        except Exception as e:
            self._trigger_callbacks(FileIOEvent.ERROR, error=e)
            print(f"[FileIO] Error seeking in file {self._file_path}: {e}")
            raise

    # Non-blocking async methods
    def open(self, callback: Optional[Callable[[FileIOCallbackData], None]] = None):
        """Open the file asynchronously (non-blocking)"""
        if callback:
            self.add_callback(FileIOEvent.OPENED, callback)
            self.add_callback(FileIOEvent.ERROR, callback)
        return self._global_manager.add_task(self._async_open())

    def close(self, callback: Optional[Callable[[FileIOCallbackData], None]] = None):
        """Close the file asynchronously (non-blocking)"""
        if callback:
            self.add_callback(FileIOEvent.CLOSED, callback)
            self.add_callback(FileIOEvent.ERROR, callback)
        return self._global_manager.add_task(self._async_close())

    def read(self, size: Optional[int] = None, callback: Optional[Callable[[FileIOCallbackData], None]] = None):
        """Read from the file asynchronously (non-blocking)"""
        if callback:
            self.add_callback(FileIOEvent.READ, callback)
            self.add_callback(FileIOEvent.ERROR, callback)
        return self._global_manager.add_task(self._async_read(size))

    def write(self, data: Union[str, bytes], callback: Optional[Callable[[FileIOCallbackData], None]] = None):
        """Write to the file asynchronously (non-blocking)"""
        if callback:
            self.add_callback(FileIOEvent.WRITE, callback)
            self.add_callback(FileIOEvent.ERROR, callback)
        return self._global_manager.add_task(self._async_write(data))

    def flush(self, callback: Optional[Callable[[FileIOCallbackData], None]] = None):
        """Flush the file asynchronously (non-blocking)"""
        if callback:
            self.add_callback(FileIOEvent.FLUSH, callback)
            self.add_callback(FileIOEvent.ERROR, callback)
        return self._global_manager.add_task(self._async_flush())

    def seek(self, offset: int, whence: int = 0, callback: Optional[Callable[[FileIOCallbackData], None]] = None):
        """Seek in the file asynchronously (non-blocking)"""
        if callback:
            self.add_callback(FileIOEvent.SEEK, callback)
            self.add_callback(FileIOEvent.ERROR, callback)
        return self._global_manager.add_task(self._async_seek(offset, whence))

    # Blocking wait methods
    def open_wait(self, timeout: Optional[float] = None):
        """Open the file and wait for completion (blocking)"""
        return self._global_manager.run_and_wait(self._async_open(), timeout)

    def close_wait(self, timeout: Optional[float] = None):
        """Close the file and wait for completion (blocking)"""
        return self._global_manager.run_and_wait(self._async_close(), timeout)

    def read_wait(self, size: Optional[int] = None, timeout: Optional[float] = None) -> Union[str, bytes]:
        """Read from the file and wait for completion (blocking)"""
        return self._global_manager.run_and_wait(self._async_read(size), timeout)

    def write_wait(self, data: Union[str, bytes], timeout: Optional[float] = None) -> int:
        """Write to the file and wait for completion (blocking)"""
        return self._global_manager.run_and_wait(self._async_write(data), timeout)

    def flush_wait(self, timeout: Optional[float] = None):
        """Flush the file and wait for completion (blocking)"""
        return self._global_manager.run_and_wait(self._async_flush(), timeout)

    def seek_wait(self, offset: int, whence: int = 0, timeout: Optional[float] = None) -> int:
        """Seek in the file and wait for completion (blocking)"""
        return self._global_manager.run_and_wait(self._async_seek(offset, whence), timeout)

    # Context manager support
    def __enter__(self):
        self.open_wait()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_wait()

    # Properties
    @property
    def is_open(self) -> bool:
        """Check if the file is open"""
        return not self._closed and self._file is not None

    @property
    def file_path(self) -> str:
        """Get the file path"""
        return self._file_path

    @property
    def mode(self) -> str:
        """Get the file mode"""
        return self._mode

    @property
    def encoding(self) -> str:
        """Get the file encoding"""
        return self._encoding


class AsyncFileHandler(FileInfo):
    """
    Enhanced asynchronous file handler with buffering and rotation capabilities.
    Provides high-level operations built on top of FileIO.
    """
    
    def __init__(self, file_path: str, *, max_size_bytes: int = _FILE_IO_MAX_SIZE, 
                 max_files_limit: int = _FILE_IO_MAX_FILES, auto_flush: bool = True,
                 buffer_size: int = 1000):
        """
        Initialize the AsyncFileHandler
        
        Args:
            file_path: Path to the file
            max_size_bytes: Maximum size before rotation
            max_files_limit: Number of rotated files to keep
            auto_flush: Whether to auto-flush writes
            buffer_size: Maximum number of items in write buffer
        """
        # Ensure directory exists
        file_dir = os.path.dirname(file_path)
        if file_dir and not os.path.exists(file_dir):
            os.makedirs(file_dir, exist_ok=True)
        
        # Create file if it doesn't exist
        if not os.path.isfile(file_path):
            with open(file_path, 'w') as f:
                pass
        
        # Initialize FileInfo
        super().__init__(file_path)
        
        # Configuration
        self.max_size_bytes = max_size_bytes
        self.max_files_limit = max_files_limit
        self.auto_flush = auto_flush
        self.buffer_size = buffer_size
        
        # Create FileIO instance
        self._file_io = FileIO(file_path, FileIOMode.APPEND, auto_flush=auto_flush)
        
        # Write buffer
        self._write_buffer: List[str] = []
        self._buffer_lock = threading.Lock()
        
        # Callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'error': [],
            'write': [],
            'flush': [],
            'rotate': []
        }
        
        # Setup FileIO callbacks
        self._file_io.add_callback(FileIOEvent.ERROR, self._on_fileio_error)
        self._file_io.add_callback(FileIOEvent.WRITE, self._on_fileio_write)
        
        # Open the file
        self._file_io.open_wait()
        
        print(f"[AsyncFileHandler] Initialized for {file_path}")

    def _on_fileio_error(self, callback_data: FileIOCallbackData):
        """Handle FileIO errors"""
        for callback in self._callbacks['error']:
            try:
                callback(callback_data.error)
            except Exception as e:
                print(f"[AsyncFileHandler] Error in error callback: {e}")

    def _on_fileio_write(self, callback_data: FileIOCallbackData):
        """Handle successful FileIO writes"""
        for callback in self._callbacks['write']:
            try:
                callback(callback_data.data)
            except Exception as e:
                print(f"[AsyncFileHandler] Error in write callback: {e}")

    def add_callback(self, callback_type: str, callback: Callable):
        """Add a callback for events"""
        if callback_type in self._callbacks:
            self._callbacks[callback_type].append(callback)

    def remove_callback(self, callback_type: str, callback: Callable):
        """Remove a callback"""
        if callback_type in self._callbacks and callback in self._callbacks[callback_type]:
            self._callbacks[callback_type].remove(callback)

    def write(self, data: str):
        """Write data asynchronously (non-blocking)"""
        with self._buffer_lock:
            self._write_buffer.append(data)
            
            # Auto-flush if buffer is full
            if len(self._write_buffer) >= self.buffer_size:
                self._flush_buffer()

    def _flush_buffer(self):
        """Flush the internal buffer to FileIO"""
        if not self._write_buffer:
            return
        
        # Check if rotation is needed
        if self._should_rotate():
            self._rotate_files()
        
        # Combine buffer contents
        buffer_content = '\n'.join(self._write_buffer) + '\n'
        self._write_buffer.clear()
        
        # Write via FileIO (non-blocking)
        self._file_io.write(buffer_content)

    def _should_rotate(self) -> bool:
        """Check if file rotation is needed"""
        try:
            return os.path.getsize(self.full_path) >= self.max_size_bytes
        except (OSError, ValueError):
            return False

    def _rotate_files(self):
        """Perform file rotation"""
        try:
            # Close current file
            self._file_io.close_wait()
            
            # Find the highest existing file number
            highest_num = 0
            for i in range(1, self.max_files_limit + 1):
                if os.path.exists(f"{self.full_path}.{i}"):
                    highest_num = i
            
            # Create new file with next number
            new_file_num = highest_num + 1
            new_file_path = f"{self.full_path}.{new_file_num}"
            
            # Create new FileIO instance for the new file
            self._file_io = FileIO(new_file_path, FileIOMode.WRITE, auto_flush=self.auto_flush)
            self._file_io.add_callback(FileIOEvent.ERROR, self._on_fileio_error)
            self._file_io.add_callback(FileIOEvent.WRITE, self._on_fileio_write)
            self._file_io.open_wait()
            
            # Update the full path to point to the new file
            self.full_path = new_file_path
            
            # Trigger rotation callbacks
            for callback in self._callbacks['rotate']:
                try:
                    callback(self.full_path)
                except Exception as e:
                    print(f"[AsyncFileHandler] Error in rotate callback: {e}")
                    
            print(f"[AsyncFileHandler] Created new file {self.full_path}")
            
        except Exception as e:
            print(f"[AsyncFileHandler] Error during rotation: {e}")

    def flush(self):
        """Flush pending writes (non-blocking)"""
        with self._buffer_lock:
            self._flush_buffer()
        
        # Trigger flush callbacks
        for callback in self._callbacks['flush']:
            try:
                callback()
            except Exception as e:
                print(f"[AsyncFileHandler] Error in flush callback: {e}")

    def flush_wait(self, timeout: Optional[float] = None):
        """Flush pending writes and wait for completion (blocking)"""
        self.flush()
        self._file_io.flush_wait(timeout)

    def read_data(self, lines: int = 1, bytes_: int = 0, 
                  callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """Read data from the file"""
        try:
            if bytes_ > 0:
                data = self._file_io.read_wait(bytes_)
            else:
                # Read specific number of lines
                all_data = self._file_io.read_wait()
                lines_list = all_data.split('\n')
                data = '\n'.join(lines_list[:lines])
            
            if callback:
                callback(data)
            return data
        except Exception as e:
            print(f"[AsyncFileHandler] Read error: {e}")
            return None

    def close(self):
        """Close the file handler"""
        self.flush_wait()
        self._file_io.close_wait()

    def __del__(self):
        """Destructor"""
        try:
            self.close()
        except:
            pass


class FileIOLogger:
    """
    Enhanced logger that uses FileIO for asynchronous logging
    """
    
    def __init__(self, log_file: str, level: str = "INFO", max_buffer_size: int = 1000):
        self._file_io = FileIO(log_file, FileIOMode.APPEND, auto_flush=False)
        self._buffer: List[str] = []
        self._buffer_lock = threading.Lock()
        self._max_buffer_size = max_buffer_size
        
        # Open the file
        self._file_io.open_wait()
        
        # Setup callbacks
        self._file_io.add_callback(FileIOEvent.ERROR, self._on_error)
        self._file_io.add_callback(FileIOEvent.WRITE, self._on_write_complete)

    def _on_error(self, callback_data: FileIOCallbackData):
        """Handle FileIO errors"""
        print(f"FileIOLogger error: {callback_data.error}")

    def _on_write_complete(self, callback_data: FileIOCallbackData):
        """Handle successful writes"""
        pass  # Could add metrics or notifications here

    def log(self, message: str, level: str = "INFO"):
        """Log a message asynchronously"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        
        with self._buffer_lock:
            self._buffer.append(formatted_message)
            
            # Flush buffer if it's getting full
            if len(self._buffer) >= self._max_buffer_size:
                self._flush_buffer()

    def _flush_buffer(self):
        """Flush the internal buffer to file"""
        if not self._buffer:
            return
            
        buffer_content = '\n'.join(self._buffer) + '\n'
        self._buffer.clear()
        
        # Write asynchronously
        self._file_io.write(buffer_content)

    def flush(self):
        """Flush any remaining buffer content"""
        with self._buffer_lock:
            self._flush_buffer()
        self._file_io.flush_wait()

    def close(self):
        """Close the logger"""
        self.flush()
        self._file_io.close_wait()

    def __del__(self):
        """Destructor"""
        try:
            self.close()
        except:
            pass


########################################################################
# Global File Handler Management
########################################################################

_file_handlers: Dict[str, AsyncFileHandler] = {}
_global_lock = threading.Lock()
_module_initialized = False


def init():
    """Initialize the file handler module"""
    global _module_initialized
    
    if _module_initialized:
        return
    
    try:
        __init_base_module()
        _module_initialized = True
        print("[FileHandler] Module initialized")
    except Exception as e:
        print(f"[FileHandler] Error initializing module: {e}")
        raise


def register_file(name: str, path: str, **kwargs) -> AsyncFileHandler:
    """Register a file handler"""
    if not _module_initialized:
        init()
    
    with _global_lock:
        if name in _file_handlers:
            return _file_handlers[name]
        
        handler = AsyncFileHandler(path, **kwargs)
        _file_handlers[name] = handler
        return handler


def get_handler(name: str) -> Optional[AsyncFileHandler]:
    """Get a registered file handler"""
    return _file_handlers.get(name)


def write_to_file(name: str, data: str):
    """Write data to a registered file handler"""
    handler = get_handler(name)
    if handler:
        handler.write(data)
    else:
        raise ValueError(f"Handler '{name}' not found")


def flush_all():
    """Flush all registered handlers"""
    for handler in _file_handlers.values():
        handler.flush()


def close_all():
    """Close all registered handlers"""
    for handler in _file_handlers.values():
        handler.close()
    _file_handlers.clear()


def cleanup():
    """Cleanup the file handler module"""
    global _module_initialized
    
    print("[FileHandler] Cleaning up...")
    close_all()
    FileIO._cleanup_all()
    _module_initialized = False
    print("[FileHandler] Cleanup completed")


# Register cleanup on module exit
atexit.register(cleanup)


########################################################################
# Example usage and testing
########################################################################

def test_file_handler():
    """Test the file handler functionality"""
    print("Testing FileHandler module...")
    
    def on_write(data):
        print(f"Write callback: {data} bytes written")
    
    def on_error(error):
        print(f"Error callback: {error}")
    
    def on_flush():
        print("Flush callback triggered")
    
    # Initialize module
    init()
    
    # Test FileIO directly
    print("\n--- Testing FileIO ---")
    file_io = FileIO("test_fileio.txt", FileIOMode.WRITE)
    file_io.add_callback(FileIOEvent.WRITE, lambda cb: print(f"FileIO write: {cb.data}"))
    file_io.add_callback(FileIOEvent.ERROR, lambda cb: print(f"FileIO error: {cb.error}"))
    
    with file_io:
        file_io.write_wait("Hello FileIO!\n")
        file_io.write_wait("This is a test.\n")
    
    # Test AsyncFileHandler
    print("\n--- Testing AsyncFileHandler ---")
    handler = register_file("test_handler", "test_handler.txt", buffer_size=5)
    handler.add_callback('write', on_write)
    handler.add_callback('error', on_error)
    handler.add_callback('flush', on_flush)
    
    # Write some data
    for i in range(10):
        handler.write(f"Test message {i}")
    
    # Flush and wait
    handler.flush_wait()
    
    # Test FileIOLogger
    print("\n--- Testing FileIOLogger ---")
    logger = FileIOLogger("test_logger.txt")
    
    for i in range(5):
        logger.log(f"Logger test message {i}", "INFO")
    
    logger.close()
    
    # Cleanup
    time.sleep(1)  # Give async operations time to complete
    cleanup()
    
    print("FileHandler test completed!")


if __name__ == "__main__":
    test_file_handler()