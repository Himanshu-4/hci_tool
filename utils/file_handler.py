"""
Module: file_handler.py
Description:
    this module provides functionality for handling file operations, including
    reading, writing, and processing files. It is designed to be used in
    applications that require file manipulation and data processing.
    The module includes functions for:
    - Reading data from files
    - Writing data to files
    - Processing file contents
    - Handling file-related exceptions
    - Logging file operations
    - [any other specific functionality]
    The module is designed to be easy to use and integrate into existing
    applications. It provides a set of functions and classes that can be
    imported and used directly in your code. The module also includes
    exception handling to ensure that errors are managed gracefully.
    The module is intended for developers who need to perform file operations
    in their applications. It is suitable for use in a variety of contexts,
    including data processing, file management, and application development.


Usage:
    Import this module to access its functions and classes:
        from <module_name> import <function_or_class>
    Use the provided functions to perform file operations:
        data = read_file("example.txt")
        write_file("output.txt", data)
        process_file("input.txt", "output.txt")
    Handle exceptions using the provided custom exception classes:
        try:
            data = read_file("example.txt")
        except FileNotFoundError as e:
            print(f"Error: {e}")
        except InvalidInputError as e:
            print(f"Error: {e}")
    [any other usage examples]
"""


import utils.Exceptions as cstm_exceptions
import asyncio
import os, sys, time
import threading
from typing import Callable, Optional, Dict
from datetime import datetime

from dataclasses import dataclass
from typing import Union, Literal

_FILE_IO_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
_FILE_IO_MAX_FILES = 5  # Number of files to keep if size exceeds limit

__BASE_DIR = None
_BASE_PATH = None   
_LOG_PATH = None
_LOG_FILE = None



@staticmethod
def __init_base_module():
    """
    Initialize the base module.
    This function sets up the necessary environment for the module to function correctly.
    It includes setting up paths, creating directories, and ensuring that the necessary
    files are present.
    """
    global __BASE_DIR
    global _BASE_PATH
    global _LOG_PATH
    global _LOG_FILE
    global _FILE_IO_MAX_SIZE

    print("[FileHandler] Initializing base module...")
    # Set the base directory and log path & also create the log directory if it doesn't exist
    _BASE_PATH =  __BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) ## 2 times is used to remove the utils directory also
    _BASE_PATH = os.path.join(os.path.abspath(_BASE_PATH), "app_data")
    _LOG_PATH = os.path.join(_BASE_PATH, "logs")
    
    # Create the log directory & file if it doesn't exist
    if not os.path.exists(_LOG_PATH):
        os.makedirs(_LOG_PATH, exist_ok=True)
    _LOG_FILE = os.path.join(_LOG_PATH, "app.log.txt")  
    if not os.path.isfile(_LOG_FILE):
        with open(_LOG_FILE, 'w') as f:
            pass
    if not os.access(_LOG_FILE, os.W_OK | os.R_OK):
        raise cstm_exceptions.CustomFileNotFoundError(_LOG_FILE)
    
    #write the time stamp in the first line
    with open(_LOG_FILE, "w") as f:
        f.write(str(datetime.fromtimestamp(time.time())) + "   [FileHandler] APP Started  "+str(os.linesep))

########################################################################
# File Handler Class
########################################################################
# This class provides asynchronous file handling capabilities.
    
@dataclass
class FileInfo:
    file_name: str
    size: int
    full_path: str
    rel_path: str
    file_type: str
    last_modified: datetime
    
    def __init__(self, file_path: str):
        """
        Initialize the FileInfo object.
        :param file_path: Path to the file.
        """
        if not os.path.isfile(file_path):
            raise cstm_exceptions.CustomFileNotFoundError(file_path)

        self.rel_path = os.path.relpath(self.file_path)
        self.full_path = os.path.abspath(self.file_path)
        self.file_path = os.path.abspath(self.file_path)
        self.file_name = os.path.basename(self.file_path)
        self.size = os.path.getsize(self.file_path)
        self.file_type = os.path.splitext(self.file_path)[1]
        self.last_modified = datetime.fromtimestamp(os.path.getmtime(self.file_path))
    
    
    @property
    def file_size(self):
        """
        Get the size of the file.
        :return: Size of the file in bytes.
        """
        return os.path.getsize(self.file_path)

    @property
    def is_file_present(self):
        """
        Check if the file is present.
        :return: True if the file is present, False otherwise.
        """
        return os.path.isfile(self.file_path)
    
    @property
    def is_file_empty(self):
        """
        Check if the file is empty.
        :return: True if the file is empty, False otherwise.
        """
        return os.path.getsize(self.file_path) == 0
   
    @property
    def is_file_readable(self):
        """
        Check if the file is readable.
        :return: True if the file is readable, False otherwise.
        """
        return os.access(self.file_path, os.R_OK)
    
    @property   
    def is_file_writable(self):
        """
        Check if the file is writable.
        :return: True if the file is writable, False otherwise.
        """
        return os.access(self.file_path, os.W_OK)
    
    @property
    def is_file_executable(self):
        """
        Check if the file is executable.
        :return: True if the file is executable, False otherwise.
        """
        return os.access(self.file_path, os.X_OK)
    
    def __hash__(self):
        """
        Hash function for the FileInfo object.
        :return: Hash value of the object.
        """
        return hash((self.file_name, self.size, self.file_path, self.file_type, self.last_modified))
    
    def __str__(self):
        """
        String representation of the FileInfo object.
        :return: String representation of the object.
        """
        return f"FileInfo({self.file_name}, size={self.size}, last_modified={self.last_modified})"
    
    def __repr__(self):
        """
        String representation of the FileInfo object.
        :return: String representation of the object.
        """
        return f"FileInfo({self.file_name}, size={self.size}, last_modified={self.last_modified})"
    
    def __eq__(self, other):
        """
        Equality operator for the FileInfo object.
        :param other: Other object to compare with.
        :return: True if the objects are equal, False otherwise.
        """
        if not isinstance(other, FileInfo):
            return NotImplemented
        return self.file_name == other.file_name and self.size == other.size and self.last_modified == other.last_modified
    
    def __ne__(self, other):
        """
        Inequality operator for the FileInfo object.
        :param other: Other object to compare with.
        :return: True if the objects are not equal, False otherwise.
        """
        if not isinstance(other, FileInfo):
            return NotImplemented
        return not self.__eq__(other)
    
    def __lt__(self, other):    
        if not isinstance(other, FileInfo):
            return NotImplemented
        return self.size < other.size
    def __le__(self, other):
        if not isinstance(other, FileInfo):
            return NotImplemented
        return self.size <= other.size
    def __gt__(self, other):
        if not isinstance(other, FileInfo):
            return NotImplemented
        return self.size > other.size
    def __ge__(self, other):
        if not isinstance(other, FileInfo):
            return NotImplemented
        return self.size >= other.size

        

class AsyncFileHandler(FileInfo):
    """
    Asynchronous file handler for writing and reading files.
    This class provides methods for writing data to a file, rotating the file
    when it exceeds a certain size, and reading data from the file.
    It uses asyncio for non-blocking I/O operations.
    Attributes:
        file_path (str): Path to the log file.
        max_size_bytes (int): Maximum size of the log file before rotation.
        max_rotations (int): Number of rotated files to keep.
        
    _write_queue (asyncio.Queue): Queue for writing data to the file.
    _shutdown_event (asyncio.Event): Event for shutting down the handler.
    _loop (asyncio.AbstractEventLoop): Event loop for asynchronous operations.
    _writer_task (asyncio.Task): Task for the write worker.
    _lock (asyncio.Lock): Lock for synchronizing access to the file.
    """
    
    CallbackType = Union[Literal["error"], Literal["done"], Literal["ready"], Literal["data"], Literal["close"]]

    CALLBACK_TYPE: CallbackType = "ready"
    
    def __init__(self, file_path: str, *,max_size_bytes: int = _FILE_IO_MAX_SIZE, max_files_limit: int = _FILE_IO_MAX_FILES):
        """
        Initialize the AsyncFileHandler.
        :param file_path: Path to the log file.
        :param max_size_bytes: Maximum size of the log file before rotation.
        :param max_rotations: Number of rotated files to keep.
        """
        self.file_path = os.path.relpath(_LOG_PATH,file_path)
        if not os.path.exists(os.path.dirname(self.file_path)):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.isfile(self.file_path):
            with open(self.file_path, 'w') as f:
                pass
        if not os.access(self.file_path, os.W_OK, os.R_OK):
            raise cstm_exceptions.CustomFileNotFoundError(self.file_path)
        
        # Initialize the base class
        super().__init__(self, self.file_path)
        
        self.max_size_bytes = max_size_bytes
        self.max_files_limit = max_files_limit
        #create reader and writer queues
        self._write_queue = asyncio.Queue()
        self._read_queue = asyncio.Queue()
        
        self._shutdown_event = asyncio.Event()
        # module loop will be created in the main thread
        # self._loop = asyncio.get_event_loop()
        # self._writer_task = self._loop.create_task(self._write_worker())
        self._enable = True
        self._lock = asyncio.Lock()
        self._callback : dict[AsyncFileHandler.CallbackType, callable[[str], None]] = {}
        self._callback_enabled = False
        self._callback_type = AsyncFileHandler.CALLBACK_TYPE

    def __del__(self):
        """Destructor to ensure proper cleanup."""
        if self._writer_task and not self._writer_task.done():
            self._shutdown_event.set()
            # self._loop.run_until_complete(self._writer_task)
        if self._write_queue:
            del self._write_queue
        if self._read_queue:
            del self._read_queue
        if self._shutdown_event:
            self._shutdown_event = None
        if self._callback:
            self._callback = None
            
        if self._lock:
            self._lock = None
        if self._loop:
            self._loop = None
        print(f"[AsyncFileHandler] Closed file handler for {self.file_path}")
        # Ensure the event loop is closed
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
            print(f"[AsyncFileHandler] Event loop closed for {self.file_path}")
        else:
            print(f"[AsyncFileHandler] Event loop already closed for {self.file_path}")
        print(f"[AsyncFileHandler] File handler for {self.file_path} destroyed")
        # Ensure the file is closed
        if hasattr(self, 'file'):
            self.file.close()
            print(f"[AsyncFileHandler] File {self.file_path} closed")
        else:
            print(f"[AsyncFileHandler] File {self.file_path} already closed or not opened")
        # Ensure the file handler is removed from the global handlers
        if self.file_path in _file_handlers:
            del _file_handlers[self.file_path]
            print(f"[AsyncFileHandler] File handler for {self.file_path} removed from global handlers")
        else:
            print(f"[AsyncFileHandler] File handler for {self.file_path} not found in global handlers")
        # Ensure the file handler is removed from the global handlers
        if self.file_path in _file_handlers:
            del _file_handlers[self.file_path]
            print(f"[AsyncFileHandler] File handler for {self.file_path} removed from global handlers")
        else:
            print(f"[AsyncFileHandler] File handler for {self.file_path} not found in global handlers")
        # Ensure the file handler is removed from the global handlers
        if self.file_path in _file_handlers:
            pass
        
    
    
    def info(self) -> FileInfo:
        """Get file information."""
        return FileInfo(self.file_path)

    def enable_callback(self):
        """Enable a callback function to be called on write."""
        self._callback_enabled = True
        
    def disable_callback(self):
        """Disable the callback function."""
        self._callback_enabled = False
        
    def set_callback(self, call_type : CallbackType, callback: Callable[[str], None]):
        """Set the callback function to be called on write."""
        self._callback[call_type] = callback
        
    def get_callback(self, call_type: CallbackType) -> Optional[Callable[[str], None]]:
        """Get the callback function for the specified type."""
        return self._callback.get(call_type, None)

    def remove_callback(self, call_type: CallbackType):
        """Remove the callback function for the specified type."""
        del self._callback[call_type]

        
    @property
    def set_max_size(self, size: int):
        """Set the maximum size of the log file."""
        self.max_size_bytes = size
    
    @property
    def get_max_size(self) -> int:
        """Get the maximum size of the log file."""
        return self.max_size_bytes
    
    @property
    def enabled(self) -> bool:
        """Check if the file handler is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Set the file handler enabled state."""
        self._enabled = value
        
    def write(self, data: str):
        """Public method to enqueue data for writing (non-blocking)."""
        if not self._enabled:
            return
        self._write_queue.put_nowait(data)

    async def _write_worker(self):
        while not self._shutdown_event.is_set() or not self._write_queue.empty():
            try:
                data = await self._write_queue.get()
                await self._rotate_if_needed()
                async with aiofiles.open(self.file_path, 'a') as f:
                    await f.write(data + '\n')
                self._write_queue.task_done()
            except Exception as e:
                print(f"[AsyncFileHandler] Write error: {e}")

    async def _create_new_file_if_exceeds(self):
        try:
            if not os.path.exists(self.file_path):
                return
            if os.path.getsize(self.file_path) < self.max_size_bytes:
                return
            # Rotate files
            for i in reversed(range(1, self.max_rotations)):
                src = f"{self.file_path}.{i}"
                dst = f"{self.file_path}.{i + 1}"
                if os.path.exists(src):
                    os.rename(src, dst)
            os.rename(self.file_path, f"{self.file_path}.1")
        except Exception as e:
            print(f"[AsyncFileHandler] Rotation error: {e}")

    async def request_data(self, *, lines: int = 1, bytes_: int = 0,
                           callback: Optional[Callable[[str], None]] = None):
        try:
            async with aiofiles.open(self.file_path, 'r') as f:
                if bytes_:
                    data = await f.read(bytes_)
                else:
                    data = ''.join([await f.readline() for _ in range(lines)])
            if callback:
                callback(data)
            return data
        except Exception as e:
            print(f"[AsyncFileHandler] Read error: {e}")
            return None

    def request_data_wait(self, *, lines: int = 1, bytes_: int = 0) -> Optional[str]:
        """Blocking read wrapper for sync code."""
        result = None
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _read():
            nonlocal result
            result = await self.request_data(lines=lines, bytes_=bytes_)
        loop.run_until_complete(_read())
        loop.close()
        return result

    async def flush(self):
        """Flush the write queue."""
        await self._write_queue.join()

    async def close(self):
        """Graceful shutdown."""
        self._shutdown_event.set()
        await self.flush()
        await self._writer_task
        
    def request_data(name: str, *, lines: int = 1, bytes_: int = 0,
                   callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        if not _enabled:
            raise RuntimeError("File handler not initialized")

        handler = get_handler(name)
        if handler is None:
            raise ValueError(f"Handler '{name}' not found")

        return handler.request_data_wait(lines=lines, bytes_=bytes_, callback=callback)


    def request_data_async(name: str, *, lines: int = 1, bytes_: int = 0,
                            callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        if not _enabled:
            raise RuntimeError("File handler not initialized")
        handler = get_handler(name)
        if handler is None:
            raise ValueError(f"Handler '{name}' not found")
        return handler.request_data(lines=lines, bytes_=bytes_, callback=callback)      
            

 
    

########################################################################
# File Handler module 
########################################################################
# This module provides functionality for enabling file operations, including
# reading, writing, and processing files. It is designed to be used in
# applications that require file manipulation and data processing.


_file_loop = None
_loop_thread = None
_enabled = False
_file_handlers: Dict[str, AsyncFileHandler] = {}
_shutdown_event = threading.Event()


def init():
    """Initialize the file handler module."""
    global _file_loop, _loop_thread, _enabled

    if _enabled:
        return
    
    try:
        # Initialize the base module
        __init_base_module()
    except Exception as e:
        print(f"[FileHandler] Error initializing base module: {e}")
        raise
        
    # Create the event loop & start the thread
    _shutdown_event.clear()
    _file_handlers.clear()
    _file_loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(target=_run_loop, daemon=True)
    _loop_thread.start()
    _enabled = True
    print("[FileHandler] Initialized")

def _run_loop():
    asyncio.set_event_loop(_file_loop)
    _file_loop.run_until_complete(_service_loop())

async def _service_loop():
    while not _shutdown_event.is_set():
        await asyncio.sleep(0.1)  # Polling interval
        for handler in _file_handlers.values():
            # @TODO: Add any periodic tasks for each handler
            # For example, you can check if the file size exceeds the limit
            # and perform rotation if needed.
            # await handler._rotate_if_needed()
            # Or you can flush the write queue periodically
            # await handler.flush()
            # Or you can perform any other periodic tasks
            # For example, you can check if the file size exceeds the limit
            # and perform rotation if needed.
            # await handler._rotate_if_needed()
            await handler.flush()


def enable():
    if not _enabled:
        init()

def is_enabled() -> bool:
    return _enabled

def disable():
    global _enabled
    _enabled = False
    print("[FileHandler] Disabled")

def stop():
    disable()

def register_file(name: str, path: str):
    if not _enabled:
        raise RuntimeError("File handler not initialized")

    def create_handler():
        return AsyncFileHandler(path)

    future = asyncio.run_coroutine_threadsafe(_register(name, create_handler), _file_loop)
    return future.result()

async def _register(name: str, creator):
    handler = creator()
    _file_handlers[name] = handler
    return handler

def get_handler(name: str) -> Optional[AsyncFileHandler]:
    return _file_handlers.get(name, None)

def delete():
    global _file_loop
    print("[FileHandler] Shutting down...")
    _shutdown_event.set()

    async def _shutdown_all():
        for handler in _file_handlers.values():
            await handler.close()
        _file_handlers.clear()

    if _file_loop and _file_loop.is_running():
        asyncio.run_coroutine_threadsafe(_shutdown_all(), _file_loop).result()
        _file_loop.call_soon_threadsafe(_file_loop.stop)
        _loop_thread.join()
        print("[FileHandler] Event loop terminated.")

def flush_all():
    """Flush all registered handlers."""
    if not _enabled:
        return

    futures = []
    for handler in _file_handlers.values():
        future = asyncio.run_coroutine_threadsafe(handler.flush(), _file_loop)
        futures.append(future)

    for f in futures:
        f.result()



########################################################################
# Example usage of AsyncFileHandler
########################################################################

       

# Example usage of AsyncFileHandler
def test_file_handler():
    init()
    # async def main():
    #     handler = AsyncFileHandler("logs/app.log")
    #     handler.set,a
    #     # Log some data
    #     for i in range(5):
    #         handler.write(f"Log entry {i}")

    #     await asyncio.sleep(0.5)
    #     await handler.flush()

    #     # Read some data
    #     await handler.request_data(lines=2, callback=lambda data: print("Async read:\n", data))

    #     # Shutdown properly
    #     await handler.close()

    # asyncio.run(main())
    
if __name__ == "__main__":
    # Test the file handler
    test_file_handler()
    # Clean up
    delete()
    # Stop the event loop
    stop()
    # Disable the file handler
    disable()
