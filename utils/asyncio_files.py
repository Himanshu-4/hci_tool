"""
AsyncioFiles - Asynchronous File I/O Library for Python

This library provides asynchronous file I/O operations built on top of asyncio.
It offers non-blocking file operations suitable for high-performance asyncio applications.
"""

import asyncio

from .Exceptions import *
import os
import io
import functools
from typing import Optional, Union, List, Dict, Any, Callable, AsyncIterator, Tuple, BinaryIO, TextIO
from contextlib import asynccontextmanager

__version__ = "0.1.0"
__all__ = [
    "open_async", "AsyncFile", "AsyncTextFile", "AsyncBinaryFile",
    "read_file", "write_file", "append_to_file", "copy_file",
    "move_file", "delete_file", "create_directory", "directory_exists",
    "file_exists", "list_directory", "get_file_size", "get_file_stats",
    "AsyncFileReader", "AsyncFileWriter", "FileOperation", "scan_directory",
    "FileWatcher"
]


class FileOperation:
    """Helper class to manage file operation callbacks."""
    
    def __init__(self, path: str):
        self.path = path
        self.started = False
        self.completed = False
        self.progress = 0
        self.error = None
        self._callbacks = []
    
    def add_callback(self, callback: Callable) -> None:
        """Add a callback to be executed on operation progress updates."""
        self._callbacks.append(callback)
    
    def update_progress(self, progress: float) -> None:
        """Update operation progress and notify callbacks."""
        self.progress = progress
        for callback in self._callbacks:
            asyncio.create_task(callback(self))
    
    def set_error(self, error: Exception) -> None:
        """Set operation error and notify callbacks."""
        self.error = error
        for callback in self._callbacks:
            asyncio.create_task(callback(self))
    
    def complete(self) -> None:
        """Mark operation as completed and notify callbacks."""
        self.completed = True
        self.progress = 1.0
        for callback in self._callbacks:
            asyncio.create_task(callback(self))

class AsyncFile:
    """Base class for asynchronous file operations."""
    
    def __init__(self, file_obj, path: str, mode: str):
        self._file = file_obj
        self.path = path
        self.mode = mode
        self.closed = False
        self._loop = asyncio.get_event_loop()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def close(self) -> None:
        """Close the file asynchronously."""
        if not self.closed:
            await self._loop.run_in_executor(None, self._file.close)
            self.closed = True
            
    def __repr__(self) -> str:
        status = "closed" if self.closed else "open"
        return f"{self.__class__.__name__}(path='{self.path}', mode='{self.mode}', status='{status}')"

class AsyncTextFile(AsyncFile):
    """Class for asynchronous text file operations."""
    
    def __init__(self, file_obj, path: str, mode: str, encoding: str = "utf-8"):
        super().__init__(file_obj, path, mode)
        self.encoding = encoding
        
    async def read(self, size: Optional[int] = None) -> str:
        """Read up to size characters from the file asynchronously."""
        if size is None:
            return await self._loop.run_in_executor(None, self._file.read)
        return await self._loop.run_in_executor(None, self._file.read, size)
    
    async def readline(self) -> str:
        """Read a single line asynchronously."""
        return await self._loop.run_in_executor(None, self._file.readline)
    
    async def readlines(self) -> List[str]:
        """Read all lines asynchronously."""
        return await self._loop.run_in_executor(None, self._file.readlines)
    
    async def write(self, data: str) -> int:
        """Write string data to the file asynchronously."""
        result = await self._loop.run_in_executor(None, self._file.write, data)
        return result
    
    async def writelines(self, lines: List[str]) -> None:
        """Write a list of strings to the file asynchronously."""
        await self._loop.run_in_executor(None, self._file.writelines, lines)
    
    async def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        """Change stream position asynchronously."""
        return await self._loop.run_in_executor(None, self._file.seek, offset, whence)
    
    async def tell(self) -> int:
        """Return current stream position asynchronously."""
        return await self._loop.run_in_executor(None, self._file.tell)
    
    async def flush(self) -> None:
        """Flush the write buffer asynchronously."""
        await self._loop.run_in_executor(None, self._file.flush)
        
    async def __aiter__(self) -> AsyncIterator[str]:
        """Allow iterating through file lines asynchronously."""
        while True:
            line = await self.readline()
            if not line:
                break
            yield line

class AsyncBinaryFile(AsyncFile):
    """Class for asynchronous binary file operations."""
    
    def __init__(self, file_obj, path: str, mode: str):
        super().__init__(file_obj, path, mode)
        
    async def read(self, size: Optional[int] = None) -> bytes:
        """Read up to size bytes from the file asynchronously."""
        if size is None:
            return await self._loop.run_in_executor(None, self._file.read)
        return await self._loop.run_in_executor(None, self._file.read, size)
    
    async def read_exact(self, size: int) -> bytes:
        """Read exactly size bytes, raising EOFError if not enough data."""
        data = await self.read(size)
        if len(data) < size:
            raise EOFError(f"End of file reached before reading {size} bytes")
        return data
        
    async def readinto(self, b: bytearray) -> int:
        """Read bytes into a pre-allocated bytearray asynchronously."""
        return await self._loop.run_in_executor(None, self._file.readinto, b)
    
    async def write(self, data: bytes) -> int:
        """Write binary data to the file asynchronously."""
        return await self._loop.run_in_executor(None, self._file.write, data)
    
    async def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        """Change stream position asynchronously."""
        return await self._loop.run_in_executor(None, self._file.seek, offset, whence)
    
    async def tell(self) -> int:
        """Return current stream position asynchronously."""
        return await self._loop.run_in_executor(None, self._file.tell)
    
    async def flush(self) -> None:
        """Flush the write buffer asynchronously."""
        await self._loop.run_in_executor(None, self._file.flush)

class AsyncFileReader:
    """High-level reader for asynchronous file operations."""
    
    def __init__(self, path: str, chunk_size: int = 4096, binary: bool = False, encoding: str = "utf-8"):
        self.path = path
        self.chunk_size = chunk_size
        self.binary = binary
        self.encoding = encoding
        
    async def read_chunks(self) -> AsyncIterator[Union[str, bytes]]:
        """Read file in chunks asynchronously."""
        mode = "rb" if self.binary else "r"
        kwargs = {} if self.binary else {"encoding": self.encoding}
        
        async with open_async(self.path, mode, **kwargs) as file:
            while True:
                chunk = await file.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
                
    async def read_lines(self) -> AsyncIterator[str]:
        """Read file line by line asynchronously."""
        if self.binary:
            raise ValueError("Cannot read lines in binary mode")
            
        async with open_async(self.path, "r", encoding=self.encoding) as file:
            async for line in file:
                yield line
                
    async def read_all(self) -> Union[str, bytes]:
        """Read entire file asynchronously."""
        mode = "rb" if self.binary else "r"
        kwargs = {} if self.binary else {"encoding": self.encoding}
        
        async with open_async(self.path, mode, **kwargs) as file:
            return await file.read()

class AsyncFileWriter:
    """High-level writer for asynchronous file operations."""
    
    def __init__(self, path: str, binary: bool = False, encoding: str = "utf-8", append: bool = False):
        self.path = path
        self.binary = binary
        self.encoding = encoding
        self.append = append
        
    async def write(self, data: Union[str, bytes]) -> int:
        """Write data to file asynchronously."""
        mode = "ab" if self.append else "wb" if self.binary else "a" if self.append else "w"
        kwargs = {} if self.binary else {"encoding": self.encoding}
        
        async with open_async(self.path, mode, **kwargs) as file:
            return await file.write(data)
            
    async def write_lines(self, lines: List[Union[str, bytes]]) -> None:
        """Write lines to file asynchronously."""
        mode = "ab" if self.append else "wb" if self.binary else "a" if self.append else "w"
        kwargs = {} if self.binary else {"encoding": self.encoding}
        
        async with open_async(self.path, mode, **kwargs) as file:
            if self.binary:
                for line in lines:
                    await file.write(line)
            else:
                await file.writelines(lines)

@asynccontextmanager
async def open_async(
    path: str, 
    mode: str = "r", 
    buffering: int = -1, 
    encoding: Optional[str] = None, 
    errors: Optional[str] = None, 
    newline: Optional[str] = None, 
    closefd: bool = True
) -> AsyncIterator[Union[AsyncTextFile, AsyncBinaryFile]]:
    """
    Open a file asynchronously, returning an async file object.
    
    Args:
        path: Path to the file
        mode: Mode in which the file is opened
        buffering: Buffering policy
        encoding: Text encoding
        errors: How encoding errors are handled
        newline: Newline character handling
        closefd: Whether to close the file descriptor
        
    Returns:
        Either AsyncTextFile or AsyncBinaryFile depending on mode
        
    Raises:
        FileNotFoundError: If file doesn't exist in read mode
        PermissionError: If file can't be accessed with requested permissions
    """
    loop = asyncio.get_event_loop()
    
    try:
        # Use run_in_executor to perform blocking file open in a separate thread
        file_obj = await loop.run_in_executor(
            None,
            functools.partial(
                open,
                path,
                mode=mode,
                buffering=buffering,
                encoding=encoding,
                errors=errors,
                newline=newline,
                closefd=closefd
            )
        )
        
        # Return the appropriate async file class
        if "b" in mode:
            async_file = AsyncBinaryFile(file_obj, path, mode)
        else:
            async_file = AsyncTextFile(file_obj, path, mode, encoding=encoding or "utf-8")
            
        try:
            yield async_file
        finally:
            await async_file.close()
            
    except Exception as e:
        # Map standard exceptions to our custom ones
        if isinstance(e, io.UnsupportedOperation):
            raise CustomFileException(f"Unsupported file operation: {str(e)}")
        elif isinstance(e, os.error):
            if e.errno == os.errno.ENOENT:  # No such file or directory
                raise FileNotFoundError(f"File not found: {path}")
            elif e.errno == os.errno.EACCES:  # Permission denied
                raise PermissionError(f"Permission denied: {path}")
            elif e.errno == os.errno.EEXIST:  # File exists
                raise FileExistsError(f"File already exists: {path}")
            else:
                raise CustomFileException(f"File operation error: {str(e)}")
        else:
            raise CustomFileException(f"Unknown error: {str(e)}")

async def read_file(path: str, binary: bool = False, encoding: str = "utf-8") -> Union[str, bytes]:
    """
    Read entire file contents asynchronously.
    
    Args:
        path: Path to the file
        binary: Whether to read in binary mode
        encoding: Text encoding if not binary
        
    Returns:
        File contents as string or bytes
    """
    mode = "rb" if binary else "r"
    kwargs = {} if binary else {"encoding": encoding}
    
    async with open_async(path, mode, **kwargs) as file:
        return await file.read()

async def write_file(
    path: str, 
    data: Union[str, bytes], 
    binary: bool = False, 
    encoding: str = "utf-8",
    create_dirs: bool = False
) -> None:
    """
    Write data to a file asynchronously.
    
    Args:
        path: Path to the file
        data: Content to write (string or bytes)
        binary: Whether to write in binary mode
        encoding: Text encoding if not binary
        create_dirs: Create parent directories if they don't exist
    """
    if create_dirs:
        directory = os.path.dirname(path)
        if directory and not await directory_exists(directory):
            await create_directory(directory, parents=True)
    
    mode = "wb" if binary else "w"
    kwargs = {} if binary else {"encoding": encoding}
    
    async with open_async(path, mode, **kwargs) as file:
        await file.write(data)

async def append_to_file(
    path: str, 
    data: Union[str, bytes], 
    binary: bool = False, 
    encoding: str = "utf-8"
) -> None:
    """
    Append data to a file asynchronously.
    
    Args:
        path: Path to the file
        data: Content to append (string or bytes)
        binary: Whether to write in binary mode
        encoding: Text encoding if not binary
    """
    mode = "ab" if binary else "a"
    kwargs = {} if binary else {"encoding": encoding}
    
    async with open_async(path, mode, **kwargs) as file:
        await file.write(data)

async def copy_file(
    src_path: str, 
    dest_path: str, 
    buffer_size: int = 65536,
    callback: Optional[Callable[[float], Any]] = None
) -> None:
    """
    Copy a file asynchronously with progress reporting.
    
    Args:
        src_path: Source file path
        dest_path: Destination file path
        buffer_size: Size of the buffer for copying
        callback: Optional callback function for progress reporting
    
    Raises:
        FileNotFoundError: If source file doesn't exist
        FileExistsError: If destination file exists and overwrite is False
    """
    loop = asyncio.get_event_loop()
    
    # Get file size for progress tracking
    file_size = await get_file_size(src_path)
    copied = 0
    
    # Create a file operation object for tracking
    operation = FileOperation(dest_path)
    operation.started = True
    
    if callback:
        operation.add_callback(callback)
    
    try:
        async with open_async(src_path, "rb") as src:
            async with open_async(dest_path, "wb") as dest:
                while True:
                    chunk = await src.read(buffer_size)
                    if not chunk:
                        break
                    
                    await dest.write(chunk)
                    copied += len(chunk)
                    
                    if callback and file_size > 0:
                        operation.update_progress(copied / file_size)
                        
        operation.complete()
    except Exception as e:
        operation.set_error(e)
        raise

async def move_file(
    src_path: str, 
    dest_path: str,
    callback: Optional[Callable[[float], Any]] = None
) -> None:
    """
    Move a file asynchronously.
    
    Args:
        src_path: Source file path
        dest_path: Destination file path
        callback: Optional callback function for progress reporting
    """
    loop = asyncio.get_event_loop()
    
    # Check if files are on the same filesystem
    # If yes, we can use os.rename which is atomic
    # If no, we need to copy and delete
    
    try:
        # Try rename first (fast path)
        await loop.run_in_executor(None, os.rename, src_path, dest_path)
        if callback:
            operation = FileOperation(dest_path)
            operation.started = True
            operation.complete()
            await callback(operation)
    except OSError:
        # If rename fails (e.g., cross-device link), fallback to copy + delete
        await copy_file(src_path, dest_path, callback=callback)
        await delete_file(src_path)

async def delete_file(path: str) -> None:
    """
    Delete a file asynchronously.
    
    Args:
        path: Path to the file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file can't be deleted due to permissions
    """
    loop = asyncio.get_event_loop()
    
    try:
        await loop.run_in_executor(None, os.unlink, path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except PermissionError:
        raise PermissionError(f"Permission denied when deleting: {path}")

async def create_directory(path: str, mode: int = 0o777, parents: bool = False) -> None:
    """
    Create a directory asynchronously.
    
    Args:
        path: Directory path
        mode: Directory permissions
        parents: Create parent directories if they don't exist
        
    Raises:
        FileExistsError: If directory already exists and parents is False
    """
    loop = asyncio.get_event_loop()
    
    try:
        if parents:
            await loop.run_in_executor(None, os.makedirs, path, mode)
        else:
            await loop.run_in_executor(None, os.mkdir, path, mode)
    except FileExistsError:
        if not parents:
            raise FileExistsError(f"Directory already exists: {path}")

async def directory_exists(path: str) -> bool:
    """
    Check if a directory exists asynchronously.
    
    Args:
        path: Directory path
        
    Returns:
        True if directory exists, False otherwise
    """
    loop = asyncio.get_event_loop()
    
    return await loop.run_in_executor(None, os.path.isdir, path)

async def file_exists(path: str) -> bool:
    """
    Check if a file exists asynchronously.
    
    Args:
        path: File path
        
    Returns:
        True if file exists, False otherwise
    """
    loop = asyncio.get_event_loop()
    
    return await loop.run_in_executor(None, os.path.isfile, path)

async def list_directory(path: str, pattern: Optional[str] = None) -> List[str]:
    """
    List directory contents asynchronously.
    
    Args:
        path: Directory path
        pattern: Optional glob pattern to filter results
        
    Returns:
        List of file/directory names in the directory
    """
    import fnmatch
    loop = asyncio.get_event_loop()
    
    try:
        contents = await loop.run_in_executor(None, os.listdir, path)
        
        if pattern:
            contents = [item for item in contents if fnmatch.fnmatch(item, pattern)]
            
        return contents
    except FileNotFoundError:
        raise FileNotFoundError(f"Directory not found: {path}")
    except PermissionError:
        raise PermissionError(f"Permission denied when listing directory: {path}")

async def get_file_size(path: str) -> int:
    """
    Get file size asynchronously.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    loop = asyncio.get_event_loop()
    
    try:
        return await loop.run_in_executor(None, os.path.getsize, path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")

async def get_file_stats(path: str) -> os.stat_result:
    """
    Get file or directory stats asynchronously.
    
    Args:
        path: File or directory path
        
    Returns:
        os.stat_result object
        
    Raises:
        FileNotFoundError: If path doesn't exist
    """
    loop = asyncio.get_event_loop()
    
    try:
        return await loop.run_in_executor(None, os.stat, path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Path not found: {path}")

async def scan_directory(
    directory: str, 
    recursive: bool = False, 
    include_files: bool = True,
    include_dirs: bool = True,
    pattern: Optional[str] = None
) -> List[str]:
    """
    Scan a directory asynchronously.
    
    Args:
        directory: Directory path
        recursive: Whether to scan subdirectories
        include_files: Whether to include files in results
        include_dirs: Whether to include directories in results
        pattern: Optional glob pattern to filter results
        
    Returns:
        List of file/directory paths
    """
    import fnmatch
    loop = asyncio.get_event_loop()
    results = []
    
    try:
        items = await list_directory(directory)
        
        for item in items:
            item_path = os.path.join(directory, item)
            is_dir = await loop.run_in_executor(None, os.path.isdir, item_path)
            
            # Check if the item matches the pattern
            if pattern and not fnmatch.fnmatch(item, pattern):
                pass  # Skip if pattern doesn't match
            elif is_dir and include_dirs:
                results.append(item_path)
            elif not is_dir and include_files:
                results.append(item_path)
                
            # Recurse into subdirectories if requested
            if is_dir and recursive:
                sub_items = await scan_directory(
                    item_path, 
                    recursive=True,
                    include_files=include_files,
                    include_dirs=include_dirs,
                    pattern=pattern
                )
                results.extend(sub_items)
                
        return results
    except FileNotFoundError:
        raise FileNotFoundError(f"Directory not found: {directory}")
    except PermissionError:
        raise PermissionError(f"Permission denied when scanning directory: {directory}")

class FileWatcher:
    """
    Watch a file or directory for changes.
    
    This is a simple polling-based implementation. For production use,
    consider using a native file system watcher like watchdog.
    """
    
    def __init__(
        self, 
        path: str, 
        recursive: bool = False, 
        poll_interval: float = 1.0,
        watch_pattern: Optional[str] = None
    ):
        self.path = path
        self.recursive = recursive
        self.poll_interval = poll_interval
        self.watch_pattern = watch_pattern
        self._running = False
        self._file_mtimes: Dict[str, float] = {}
        self._callbacks: List[Callable[[str, str], Any]] = []
        self._task = None
        
    def add_callback(self, callback: Callable[[str, str], Any]) -> None:
        """
        Add a callback to be called when a file changes.
        
        Callback will receive (file_path, event_type) where event_type
        is one of: 'created', 'modified', 'deleted'
        """
        self._callbacks.append(callback)
        
    async def start(self) -> None:
        """Start watching for file changes."""
        if self._running:
            return
            
        self._running = True
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._watch_loop())
        
    async def _watch_loop(self) -> None:
        """Internal loop that watches for file changes."""
        # Initialize file state
        await self._scan_files()
        
        while self._running:
            await asyncio.sleep(self.poll_interval)
            await self._check_for_changes()
    
    async def _scan_files(self) -> None:
        """Scan all files and store their modification times."""
        is_dir = await directory_exists(self.path)
        
        if is_dir:
            if self.recursive:
                files = await scan_directory(
                    self.path, 
                    recursive=True,
                    include_dirs=False,
                    pattern=self.watch_pattern
                )
            else:
                files = [
                    os.path.join(self.path, f) 
                    for f in await list_directory(self.path, pattern=self.watch_pattern)
                    if await file_exists(os.path.join(self.path, f))
                ]
        else:
            files = [self.path]
            
        for file_path in files:
            try:
                stats = await get_file_stats(file_path)
                self._file_mtimes[file_path] = stats.st_mtime
            except (FileNotFoundError, PermissionError):
                pass
    
    async def _check_for_changes(self) -> None:
        """Check for file changes and trigger callbacks."""
        # Get current files
        is_dir = await directory_exists(self.path)
        
        current_files = []
        if is_dir:
            if self.recursive:
                current_files = await scan_directory(
                    self.path, 
                    recursive=True,
                    include_dirs=False,
                    pattern=self.watch_pattern
                )
            else:
                current_files = [
                    os.path.join(self.path, f) 
                    for f in await list_directory(self.path, pattern=self.watch_pattern)
                    if await file_exists(os.path.join(self.path, f))
                ]
        elif await file_exists(self.path):
            current_files = [self.path]
            
        # Check for new or modified files
        for file_path in current_files:
            try:
                stats = await get_file_stats(file_path)
                
                if file_path not in self._file_mtimes:
                    # New file
                    self._file_mtimes[file_path] = stats.st_mtime
                    await self._trigger_callbacks(file_path, 'created')
                elif stats.st_mtime > self._file_mtimes[file_path]:
                    # Modified file
                    self._file_mtimes[file_path] = stats.st_mtime
                    await self._trigger_callbacks(file_path, 'modified')
            except (FileNotFoundError, PermissionError):
                pass
                
        # Check for deleted files
        deleted_files = [
            file_path for file_path in self._file_mtimes
            if file_path not in current_files
        ]
        
        for file_path in deleted_files:
            await self._trigger_callbacks(file_path, 'deleted')
            del self._file_mtimes[file_path]
    
    async def _trigger_callbacks(self, file_path: str, event_type: str) -> None:
        """Trigger all registered callbacks."""
        for callback in self._callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(file_path, event_type)
            else:
                callback(file_path, event_type)
                
    async def stop(self) -> None:
        """Stop watching for file changes."""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None