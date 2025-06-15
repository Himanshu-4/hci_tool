"""
FileIO-based Log Handler for the Logger Module
This module provides a high-performance asynchronous file handler for logging
using the FileIO class with buffering and rotation capabilities.
"""

import logging
import os
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from queue import Queue, Empty
import atexit

# Import FileIO components (these would be from your file_handler module)
from .file_handler import FileIO, FileIOMode, FileIOEvent, FileIOCallbackData


class FileIOLogHandler(logging.Handler):
    """
    Asynchronous file handler for logging using FileIO
    
    Features:
    - Non-blocking writes using FileIO
    - Automatic file rotation
    - Buffering with configurable flush intervals
    - Thread-safe operations
    - Graceful shutdown handling
    """
    
    def __init__(self, filename: str, mode: str = 'a',
                 max_bytes: int = 10*1024*1024,  # 10MB
                 backup_count: int = 5,
                 encoding: str = 'utf-8',
                 max_buffer_size: int = 100,
                 auto_flush_interval: float = 2.0,
                 use_async: bool = True):
        """
        Initialize the FileIO log handler
        
        Args:
            filename: Path to the log file
            mode: File opening mode ('a' for append, 'w' for write)
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep
            encoding: File encoding
            max_buffer_size: Maximum number of log records to buffer
            auto_flush_interval: Interval for automatic buffer flushing
            use_async: Whether to use async FileIO operations
        """
        super().__init__()
        
        self.filename = filename
        self.mode = mode
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.encoding = encoding
        self.max_buffer_size = max_buffer_size
        self.auto_flush_interval = auto_flush_interval
        self.use_async = use_async
        
        # Create directory if needed
        log_dir = os.path.dirname(filename)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Initialize FileIO
        self._file_io: Optional[FileIO] = None
        self._init_file_io()
        
        # Buffer management
        self._buffer: List[str] = []
        self._buffer_lock = threading.Lock()
        self._last_flush_time = time.time()
        
        # Background flusher thread
        self._flusher_thread: Optional[threading.Thread] = None
        self._stop_flusher = threading.Event()
        self._start_flusher_thread()
        
        # Register cleanup
        atexit.register(self.close)
        
        # Statistics
        self._stats = {
            'messages_logged': 0,
            'bytes_written': 0,
            'flushes': 0,
            'rotations': 0,
            'errors': 0
        }
    
    def _init_file_io(self):
        """Initialize or reinitialize the FileIO instance"""
        try:
            # Create file if it doesn't exist
            if not os.path.exists(self.filename):
                with open(self.filename, 'w'):
                    pass
            
            # Close existing FileIO if any
            if self._file_io and self._file_io.is_open:
                self._file_io.close_wait()
            
            # Determine FileIO mode
            file_mode = FileIOMode.APPEND if self.mode == 'a' else FileIOMode.WRITE
            
            # Create new FileIO instance
            self._file_io = FileIO(
                self.filename,
                mode=file_mode,
                encoding=self.encoding,
                auto_flush=False  # We'll manage flushing
            )
            
            # Set up callbacks
            self._file_io.add_callback(FileIOEvent.ERROR, self._on_file_error)
            self._file_io.add_callback(FileIOEvent.WRITE, self._on_write_complete)
            
            # Open the file
            if self.use_async:
                self._file_io.open()
            else:
                self._file_io.open_wait()
                
        except Exception as e:
            self.handleError(logging.LogRecord(
                name="FileIOLogHandler",
                level=logging.ERROR,
                pathname=__file__,
                lineno=0,
                msg=f"Failed to initialize FileIO: {e}",
                args=(),
                exc_info=None
            ))
    
    def _on_file_error(self, callback_data: FileIOCallbackData):
        """Handle FileIO errors"""
        self._stats['errors'] += 1
        print(f"[FileIOLogHandler] FileIO error: {callback_data.error}")
    
    def _on_write_complete(self, callback_data: FileIOCallbackData):
        """Handle successful writes"""
        if callback_data.data:
            self._stats['bytes_written'] += callback_data.data
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a record to the file
        
        Args:
            record: LogRecord to emit
        """
        try:
            msg = self.format(record)
            
            with self._buffer_lock:
                self._buffer.append(msg)
                self._stats['messages_logged'] += 1
                
                # Check if we should flush
                should_flush = (
                    len(self._buffer) >= self.max_buffer_size or
                    (time.time() - self._last_flush_time) >= self.auto_flush_interval
                )
                
                if should_flush:
                    self._flush_buffer()
                    
        except Exception:
            self.handleError(record)
    
    def _flush_buffer(self):
        """Flush the internal buffer to file"""
        if not self._buffer:
            return
        
        try:
            # Check if rotation is needed
            if self._should_rotate():
                self._rotate()
            
            # Prepare data
            data = '\n'.join(self._buffer) + '\n'
            self._buffer.clear()
            
            # Write to file
            if self._file_io and self._file_io.is_open:
                if self.use_async:
                    self._file_io.write(data)
                else:
                    self._file_io.write_wait(data)
                
                self._stats['flushes'] += 1
                self._last_flush_time = time.time()
            else:
                # Re-add to buffer if file is not ready
                self._buffer.append(data.rstrip('\n'))
                
        except Exception as e:
            print(f"[FileIOLogHandler] Error flushing buffer: {e}")
            self._stats['errors'] += 1
    
    def _should_rotate(self) -> bool:
        """Check if file rotation is needed"""
        try:
            if self.max_bytes <= 0:
                return False
            
            # Get current file size
            if os.path.exists(self.filename):
                return os.path.getsize(self.filename) >= self.max_bytes
            return False
            
        except (OSError, ValueError):
            return False
    
    def _rotate(self):
        """Perform file rotation"""
        try:
            # Close current file
            if self._file_io:
                self._file_io.close_wait()
            
            # Perform rotation
            for i in range(self.backup_count - 1, 0, -1):
                old_name = f"{self.filename}.{i}"
                new_name = f"{self.filename}.{i + 1}"
                if os.path.exists(old_name):
                    if os.path.exists(new_name):
                        os.remove(new_name)
                    os.rename(old_name, new_name)
            
            # Rename current file to .1
            if os.path.exists(self.filename):
                backup_name = f"{self.filename}.1"
                if os.path.exists(backup_name):
                    os.remove(backup_name)
                os.rename(self.filename, backup_name)
            
            # Reinitialize FileIO with new file
            self._init_file_io()
            self._stats['rotations'] += 1
            
            print(f"[FileIOLogHandler] Rotated log file: {self.filename}")
            
        except Exception as e:
            print(f"[FileIOLogHandler] Error during rotation: {e}")
            self._stats['errors'] += 1
    
    def _start_flusher_thread(self):
        """Start the background flusher thread"""
        if self.auto_flush_interval > 0:
            self._flusher_thread = threading.Thread(
                target=self._flusher_worker,
                name="FileIOLogHandler-Flusher",
                daemon=True
            )
            self._flusher_thread.start()
    
    def _flusher_worker(self):
        """Background worker for periodic flushing"""
        while not self._stop_flusher.is_set():
            try:
                # Wait for interval or stop signal
                if self._stop_flusher.wait(self.auto_flush_interval):
                    break
                
                # Flush buffer
                with self._buffer_lock:
                    if self._buffer:
                        self._flush_buffer()
                        
            except Exception as e:
                print(f"[FileIOLogHandler] Flusher error: {e}")
    
    def flush(self):
        """Flush the handler"""
        with self._buffer_lock:
            self._flush_buffer()
        
        if self._file_io and self._file_io.is_open:
            self._file_io.flush_wait()
    
    def close(self):
        """Close the handler"""
        # Stop flusher thread
        self._stop_flusher.set()
        if self._flusher_thread and self._flusher_thread.is_alive():
            self._flusher_thread.join(timeout=2.0)
        
        # Final flush
        self.flush()
        
        # Close FileIO
        if self._file_io:
            self._file_io.close_wait()
            self._file_io = None
        
        # Print statistics
        print(f"[FileIOLogHandler] Closing - Stats: {self._stats}")
        
        super().close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get handler statistics"""
        return self._stats.copy()
    
    def reset_statistics(self):
        """Reset handler statistics"""
        for key in self._stats:
            self._stats[key] = 0


class AsyncRotatingFileHandler(FileIOLogHandler):
    """
    Convenience class that mimics RotatingFileHandler interface
    but uses FileIO for async operations
    """
    
    def __init__(self, filename: str, mode: str = 'a',
                 maxBytes: int = 10*1024*1024,
                 backupCount: int = 5,
                 encoding: str = 'utf-8',
                 delay: bool = False):
        """
        Initialize with RotatingFileHandler-compatible parameters
        
        Args:
            filename: Path to the log file
            mode: File mode
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: If True, file opening is deferred until first emit
        """
        # Convert parameters to FileIOLogHandler format
        super().__init__(
            filename=filename,
            mode=mode,
            max_bytes=maxBytes,
            backup_count=backupCount,
            encoding=encoding,
            use_async=True
        )
        
        # Handle delayed opening
        if delay:
            if self._file_io:
                self._file_io.close_wait()
                self._file_io = None
    
    def shouldRollover(self, record: logging.LogRecord) -> bool:
        """
        Check if rollover should occur
        
        Args:
            record: LogRecord to check
            
        Returns:
            True if rollover should occur
        """
        return self._should_rotate()
    
    def doRollover(self):
        """Perform rollover"""
        self._rotate()
        
        
        
# ================================
# 
# ================================


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