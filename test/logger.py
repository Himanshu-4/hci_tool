""""
Updated Logger module with FileIO Integration
This module provides functionality for logging messages to a file and console
with enhanced asynchronous file operations using the FileIO class.
"""

import time, os, logging, sys
from datetime import datetime
import traceback, threading
import logging.handlers as logHandlers
from typing import Union, Optional, Dict, Any
from enum import Enum

# Import the new FileIO components
try:
    from .file_handler import FileIO, FileIOLogger, FileIOEvent, FileIOCallbackData, FileIOMode
except ImportError:
    # Fallback for standalone testing
    from file_handler import FileIO, FileIOLogger, FileIOEvent, FileIOCallbackData, FileIOMode


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    NOTSET = logging.NOTSET


# Map string log levels to logging module levels
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "NOTSET": logging.NOTSET
}

appdata = os.getenv('appdata')
if appdata:
    DEFAULT_LOG_FILE_DIR = os.path.join(appdata, 'Nordic Semiconductor', 'Sniffer', 'logs')
else:
    DEFAULT_LOG_FILE_DIR = "/tmp/logs"

DEFAULT_LOG_FILE_NAME = "log.txt"

logFileName = None
logHandler = None
logHandlerArray = []
logFlusher = None
myMaxBytes = 1000000


class FileIOLogHandler(logging.Handler):
    """
    Custom log handler that uses FileIO for asynchronous logging
    """
    
    def __init__(self, filename: str, mode: str = 'a', encoding: str = 'utf-8', 
                 max_buffer_size: int = 100, auto_flush_interval: float = 5.0):
        super().__init__()
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
        self.max_buffer_size = max_buffer_size
        self.auto_flush_interval = auto_flush_interval
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Initialize FileIO
        file_mode = FileIOMode.APPEND if 'a' in mode else FileIOMode.WRITE
        self.file_io = FileIO(filename, file_mode, encoding=encoding, auto_flush=False)
        
        # Buffer for batching writes
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self._last_flush = time.time()
        
        # Setup FileIO callbacks
        self.file_io.add_callback(FileIOEvent.ERROR, self._on_file_error)
        self.file_io.add_callback(FileIOEvent.WRITE, self._on_write_complete)
        
        # Open the file
        try:
            self.file_io.open_wait(timeout=5.0)
        except Exception as e:
            print(f"Failed to open log file {filename}: {e}")
            raise
        
        # Start auto-flush timer
        self._flush_timer = None
        self._start_flush_timer()
    
    def _on_file_error(self, callback_data: FileIOCallbackData):
        """Handle FileIO errors"""
        error_msg = f"FileIO error in log handler: {callback_data.error}"
        print(error_msg, file=sys.stderr)
        # Could emit to a fallback handler or error tracking system
    
    def _on_write_complete(self, callback_data: FileIOCallbackData):
        """Handle successful writes"""
        # Could add write statistics or metrics here
        pass
    
    def _start_flush_timer(self):
        """Start the auto-flush timer"""
        if self._flush_timer:
            self._flush_timer.cancel()
        
        self._flush_timer = threading.Timer(self.auto_flush_interval, self._auto_flush)
        self._flush_timer.daemon = True
        self._flush_timer.start()
    
    def _auto_flush(self):
        """Automatically flush the buffer periodically"""
        current_time = time.time()
        with self._buffer_lock:
            if self._buffer and (current_time - self._last_flush) >= self.auto_flush_interval:
                self._flush_buffer()
        
        # Restart the timer
        self._start_flush_timer()
    
    def emit(self, record):
        """Emit a log record"""
        try:
            msg = self.format(record)
            
            with self._buffer_lock:
                self._buffer.append(msg + '\n')
                
                # Flush if buffer is getting full or if it's an error/critical message
                should_flush = (
                    len(self._buffer) >= self.max_buffer_size or
                    record.levelno >= logging.ERROR or
                    (time.time() - self._last_flush) >= self.auto_flush_interval
                )
                
                if should_flush:
                    self._flush_buffer()
                    
        except Exception as e:
            self.handleError(record)
    
    def _flush_buffer(self):
        """Flush the internal buffer to file"""
        if not self._buffer:
            return
        
        try:
            buffer_content = ''.join(self._buffer)
            self._buffer.clear()
            self._last_flush = time.time()
            
            # Write asynchronously (non-blocking)
            self.file_io.write(buffer_content)
            
        except Exception as e:
            print(f"Error flushing log buffer: {e}", file=sys.stderr)
    
    def flush(self):
        """Flush any pending log records"""
        with self._buffer_lock:
            self._flush_buffer()
        
        # Wait for FileIO to complete the flush
        try:
            self.file_io.flush_wait(timeout=5.0)
        except Exception as e:
            print(f"Error flushing FileIO: {e}", file=sys.stderr)
    
    def close(self):
        """Close the handler"""
        # Cancel the flush timer
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None
        
        # Flush any remaining buffer
        self.flush()
        
        # Close the FileIO
        try:
            self.file_io.close_wait(timeout=5.0)
        except Exception as e:
            print(f"Error closing FileIO: {e}", file=sys.stderr)
        
        super().close()


class EnhancedRotatingFileHandler(FileIOLogHandler):
    """
    Rotating file handler using FileIO with size-based rotation
    """
    
    def __init__(self, filename: str, mode: str = 'a', maxBytes: int = 0, 
                 backupCount: int = 0, encoding: str = 'utf-8', **kwargs):
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        self._rotation_lock = threading.Lock()
        
        super().__init__(filename, mode, encoding, **kwargs)
    
    def _should_rollover(self) -> bool:
        """Check if we should perform a rollover"""
        if self.maxBytes <= 0:
            return False
        
        try:
            # Check file size
            if os.path.exists(self.filename):
                return os.path.getsize(self.filename) >= self.maxBytes
        except (OSError, ValueError):
            pass
        
        return False
    
    def _do_rollover(self):
        """Perform the file rollover"""
        with self._rotation_lock:
            if not self._should_rollover():
                return
            
            try:
                # Close current file
                self.file_io.close_wait()
                
                # Rotate files
                for i in range(self.backupCount - 1, 0, -1):
                    src_file = f"{self.filename}.{i}"
                    dst_file = f"{self.filename}.{i + 1}"
                    
                    if os.path.exists(src_file):
                        if os.path.exists(dst_file):
                            os.remove(dst_file)
                        os.rename(src_file, dst_file)
                
                # Move current file to .1
                if os.path.exists(self.filename):
                    dst_file = f"{self.filename}.1"
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    os.rename(self.filename, dst_file)
                
                # Reopen the file
                self.file_io = FileIO(self.filename, FileIOMode.WRITE, encoding=self.encoding)
                self.file_io.add_callback(FileIOEvent.ERROR, self._on_file_error)
                self.file_io.add_callback(FileIOEvent.WRITE, self._on_write_complete)
                self.file_io.open_wait()
                
            except Exception as e:
                print(f"Error during log rotation: {e}", file=sys.stderr)
    
    def emit(self, record):
        """Emit a log record with rotation check"""
        # Check if we need to rotate before writing
        if self._should_rollover():
            self._do_rollover()
        
        super().emit(record)


def setLogFileName(log_file_path):
    global logFileName
    logFileName = os.path.abspath(log_file_path)


def initLogger():
    """Initialize the logger with FileIO support"""
    try:
        global logFileName, logHandler, logHandlerArray, logFlusher
        
        if logFileName is None:
            logFileName = os.path.join(DEFAULT_LOG_FILE_DIR, DEFAULT_LOG_FILE_NAME)

        # Create directory if it doesn't exist
        if not os.path.isdir(os.path.dirname(logFileName)):
            os.makedirs(os.path.dirname(logFileName))

        # If the file does not exist, create it with timestamp
        if not os.path.isfile(logFileName):
            with open(logFileName, "w") as f:
                f.write(str(time.time()) + str(os.linesep))

        # Use the new FileIO-based rotating handler
        logHandler = EnhancedRotatingFileHandler(
            logFileName, 
            mode='a', 
            maxBytes=myMaxBytes, 
            backupCount=3,
            max_buffer_size=50,
            auto_flush_interval=2.0
        )
        
        logFormatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s', 
            datefmt='%d-%b-%Y %H:%M:%S (%z)'
        )
        logHandler.setFormatter(logFormatter)
        
        logger = logging.getLogger()
        logger.addHandler(logHandler)
        logger.setLevel(logging.INFO)
        
        logHandlerArray.append(logHandler)
        
        # Note: logFlusher is now handled internally by FileIO
        print("Logger initialized with FileIO support")
        
    except Exception as e:
        print(f"LOGGING INITIALIZATION FAILED: {e}")
        print(traceback.format_exc())
        raise


def shutdownLogger():
    """Shutdown the logger and cleanup FileIO resources"""
    global logHandler, logHandlerArray
    
    try:
        # Flush all handlers
        for handler in logHandlerArray:
            if hasattr(handler, 'flush'):
                handler.flush()
            if hasattr(handler, 'close'):
                handler.close()
        
        logging.shutdown()
        
        # Clear the handler array
        logHandlerArray.clear()
        
        print("Logger shutdown completed")
        
    except Exception as e:
        print(f"Error during logger shutdown: {e}")


def clearLog():
    """Clear the log (perform rollover)"""
    try:
        if logHandler and hasattr(logHandler, '_do_rollover'):
            logHandler._do_rollover()
        elif logHandler and hasattr(logHandler, 'doRollover'):
            logHandler.doRollover()
    except Exception as e:
        print(f"LOGGING FAILED during clear: {e}")
        raise


def getTimestamp():
    """Returns the timestamp from the first line of the logfile"""
    try:
        with open(logFileName, "r") as f:
            f.seek(0)
            return f.readline()
    except Exception as e:
        print(f"LOGGING FAILED during timestamp read: {e}")


def addTimestamp():
    """Add a timestamp to the log file"""
    try:
        with open(logFileName, "a") as f:
            f.write(str(time.time()) + os.linesep)
    except Exception as e:
        print(f"LOGGING FAILED during timestamp add: {e}")


def readAll():
    """Returns the entire content of the logfile"""
    try:
        with open(logFileName, "r") as f:
            return f.read()
    except Exception as e:
        print(f"LOGGING FAILED during read all: {e}")


def addLogHandler(handler):
    """Add a log handler"""
    global logHandlerArray
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logHandlerArray.append(handler)


def removeLogHandler(handler):
    """Remove a log handler"""
    global logHandlerArray
    logger = logging.getLogger()
    logger.removeHandler(handler)
    if handler in logHandlerArray:
        logHandlerArray.remove(handler)


class MyRotatingFileHandler(logHandlers.RotatingFileHandler):
    """Legacy rotating file handler (kept for compatibility)"""
    def doRollover(self):
        try:
            logHandlers.RotatingFileHandler.doRollover(self)
            addTimestamp()
            self.maxBytes = myMaxBytes
        except:
            # There have been permissions issues with the log files.
            self.maxBytes += int(myMaxBytes / 2)


class LogFlusher(threading.Thread):
    """Legacy log flusher (kept for compatibility)"""
    def __init__(self, logHandler):
        threading.Thread.__init__(self)
        self.daemon = True
        self.handler = logHandler
        self.exit = threading.Event()
        self.start()

    def run(self):
        while True:
            if self.exit.wait(10):
                try:
                    self.doFlush()
                except AttributeError as e:
                    print(e)
                break
            self.doFlush()

    def doFlush(self):
        if hasattr(self.handler, 'flush'):
            self.handler.flush()
            if hasattr(self.handler, 'stream') and hasattr(self.handler.stream, 'fileno'):
                try:
                    os.fsync(self.handler.stream.fileno())
                except (AttributeError, OSError):
                    pass

    def stop(self):
        self.exit.set()


##########################################################################################
# Custom logging filter to enable/disable logging for specific modules
##########################################################################################

class CustomLogFilter(logging.Filter):
    def __init__(self, module_name, enabled=True):
        super().__init__(name=module_name)
        self.module_name = module_name
        self.enabled = enabled

    def filter(self, record):
        return self.enabled


class LoggerManager:
    """Enhanced logger manager with FileIO support"""
    _loggers = {}
    _lock = threading.Lock()
    APP_LOG_FILE = "app.log"

    @classmethod
    def get_logger(cls, module_name, level: Union[str, LogLevel] = LogLevel.DEBUG, *,
                   to_console=True, to_file=True, to_log_window=False,
                   description=True, prepend="", append="",
                   log_file=None, enable=True, use_fileio=True,
                   max_buffer_size=50, auto_flush_interval=2.0):

        with cls._lock:
            if module_name in cls._loggers:
                return cls._loggers[module_name]["logger"]

            logger = logging.getLogger(module_name)
            
            # Set the logger level
            if isinstance(level, str):
                level = log_level_map.get(level.upper(), logging.DEBUG)
            elif isinstance(level, LogLevel):
                level = level.value
            
            logger.setLevel(level)
            logger.propagate = False  # avoid double logging

            formatter = cls._get_formatter(description, prepend, append)
            module_log_file = log_file or cls.APP_LOG_FILE

            if to_console:
                ch = logging.StreamHandler(sys.stdout)
                ch.setFormatter(formatter)
                logger.addHandler(ch)

            if to_file:
                try:
                    # Create directory if needed
                    log_dir = os.path.dirname(module_log_file)
                    if log_dir and not os.path.exists(log_dir):
                        os.makedirs(log_dir, exist_ok=True)
                    
                    if use_fileio:
                        # Use the new FileIO-based handler
                        fh = FileIOLogHandler(
                            module_log_file,
                            mode='a',
                            max_buffer_size=max_buffer_size,
                            auto_flush_interval=auto_flush_interval
                        )
                    else:
                        # Use traditional file handler
                        fh = logging.FileHandler(module_log_file, mode='a')
                    
                    fh.setFormatter(formatter)
                    logger.addHandler(fh)
                    
                except Exception as e:
                    print(f"Failed to create file handler for {module_name}: {e}")
                    # Continue without file logging

            # Optional: Hook for GUI log window
            if to_log_window:
                try:
                    from ui.exts.log_window import GuiLogHandler
                    gh = GuiLogHandler(module_name)
                    gh.setFormatter(formatter)
                    logger.addHandler(gh)
                except ImportError:
                    print("GUI log handler not available")

            # Add filter for enabling/disabling
            log_filter = CustomLogFilter(module_name, enable)
            logger.addFilter(log_filter)

            cls._loggers[module_name] = {
                "logger": logger,
                "filter": log_filter
            }
            return logger

    @classmethod
    def enable_module(cls, module_name):
        """Enable logging for a specific module"""
        if module_name in cls._loggers:
            cls._loggers[module_name]["filter"].enabled = True

    @classmethod
    def disable_module(cls, module_name):
        """Disable logging for a specific module"""
        if module_name in cls._loggers:
            cls._loggers[module_name]["filter"].enabled = False

    @classmethod
    def flush_all(cls):
        """Flush all loggers"""
        for logger_info in cls._loggers.values():
            logger = logger_info["logger"]
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()

    @classmethod
    def shutdown_all(cls):
        """Shutdown all loggers"""
        cls.flush_all()
        
        for logger_info in cls._loggers.values():
            logger = logger_info["logger"]
            for handler in logger.handlers[:]:  # Copy list to avoid modification during iteration
                if hasattr(handler, 'close'):
                    handler.close()
                logger.removeHandler(handler)
        
        cls._loggers.clear()

    @staticmethod
    def _get_formatter(include_desc, prepend, append):
        """Create a formatter with the specified options"""
        parts = []
        if prepend:
            parts.append(prepend)
        if include_desc:
            parts.append("[%(asctime)s] [%(threadName)s] [%(module)s:%(lineno)d]")
        parts.append("%(message)s")
        if append:
            parts.append(append)
        fmt = ' '.join(parts)
        return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")


class GuiLogHandler(logging.Handler):
    """GUI log handler (kept for compatibility)"""
    def __init__(self, module_name):
        super().__init__()
        self.module_name = module_name

    def emit(self, record):
        msg = self.format(record)
        try:
            from ui.exts.log_window import log_to_window
            log_to_window(self.module_name, msg)
        except ImportError:
            pass  # GUI not available


def test_logger():
    """Test the enhanced logger functionality"""
    print("Testing enhanced logger with FileIO...")
    
    # Test basic logger
    log = LoggerManager.get_logger(
        "TestModule",
        level=logging.DEBUG,
        to_console=True,
        to_file=True,
        log_file="logs/test_module.log",
        prepend="[TEST]",
        use_fileio=True,
        max_buffer_size=10,
        auto_flush_interval=1.0
    )

    log.info("Logger initialized with FileIO")
    log.debug("This is a debug message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.critical("This is a critical message")

    # Test exception logging
    try:
        1 / 0
    except Exception:
        log.exception("Exception occurred")

    # Test module enable/disable
    LoggerManager.disable_module("TestModule")
    log.info("This message should not appear")
    
    LoggerManager.enable_module("TestModule")
    log.info("Module re-enabled")

    # Test rapid logging to trigger buffer flush
    for i in range(20):
        log.info(f"Rapid log message {i}")

    # Wait a bit for async operations
    import time
    time.sleep(2)

    # Flush and shutdown
    LoggerManager.flush_all()
    time.sleep(1)
    LoggerManager.shutdown_all()
    
    print("Logger test completed")


if __name__ == "__main__":
    test_logger()
    
    
    
    
    
    
    
class FileIOLogHandler(logging.Handler):
    """
    Custom log handler that uses FileIO for asynchronous logging
    """
    
    def __init__(self, filename: str, mode: str = 'a', encoding: str = 'utf-8', 
                 max_buffer_size: int = 100, auto_flush_interval: float = 5.0):
        super().__init__()
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
        self.max_buffer_size = max_buffer_size
        self.auto_flush_interval = auto_flush_interval
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Initialize FileIO
        file_mode = FileIOMode.APPEND if 'a' in mode else FileIOMode.WRITE
        self.file_io = FileIO(filename, file_mode, encoding=encoding, auto_flush=False)
        
        # Buffer for batching writes
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self._last_flush = time.time()
        
        # Setup FileIO callbacks
        self.file_io.add_callback(FileIOEvent.ERROR, self._on_file_error)
        self.file_io.add_callback(FileIOEvent.WRITE, self._on_write_complete)
        
        # Open the file
        try:
            self.file_io.open_wait(timeout=5.0)
        except Exception as e:
            print(f"Failed to open log file {filename}: {e}")
            raise
        
        # Start auto-flush timer
        self._flush_timer = None
        self._start_flush_timer()
    
    def _on_file_error(self, callback_data: FileIOCallbackData):
        """Handle FileIO errors"""
        error_msg = f"FileIO error in log handler: {callback_data.error}"
        print(error_msg, file=sys.stderr)
        # Could emit to a fallback handler or error tracking system
    
    def _on_write_complete(self, callback_data: FileIOCallbackData):
        """Handle successful writes"""
        # Could add write statistics or metrics here
        pass
    
    def _start_flush_timer(self):
        """Start the auto-flush timer"""
        if self._flush_timer:
            self._flush_timer.cancel()
        
        self._flush_timer = threading.Timer(self.auto_flush_interval, self._auto_flush)
        self._flush_timer.daemon = True
        self._flush_timer.start()
    
    def _auto_flush(self):
        """Automatically flush the buffer periodically"""
        current_time = time.time()
        with self._buffer_lock:
            if self._buffer and (current_time - self._last_flush) >= self.auto_flush_interval:
                self._flush_buffer()
        
        # Restart the timer
        self._start_flush_timer()
    
    def emit(self, record):
        """Emit a log record"""
        try:
            msg = self.format(record)
            
            with self._buffer_lock:
                self._buffer.append(msg + '\n')
                
                # Flush if buffer is getting full or if it's an error/critical message
                should_flush = (
                    len(self._buffer) >= self.max_buffer_size or
                    record.levelno >= logging.ERROR or
                    (time.time() - self._last_flush) >= self.auto_flush_interval
                )
                
                if should_flush:
                    self._flush_buffer()
                    
        except Exception as e:
            self.handleError(record)
    
    def _flush_buffer(self):
        """Flush the internal buffer to file"""
        if not self._buffer:
            return
        
        try:
            buffer_content = ''.join(self._buffer)
            self._buffer.clear()
            self._last_flush = time.time()
            
            # Write asynchronously (non-blocking)
            self.file_io.write(buffer_content)
            
        except Exception as e:
            print(f"Error flushing log buffer: {e}", file=sys.stderr)
    
    def flush(self):
        """Flush any pending log records"""
        with self._buffer_lock:
            self._flush_buffer()
        
        # Wait for FileIO to complete the flush
        try:
            self.file_io.flush_wait(timeout=5.0)
        except Exception as e:
            print(f"Error flushing FileIO: {e}", file=sys.stderr)
    
    def close(self):
        """Close the handler"""
        # Cancel the flush timer
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None
        
        # Flush any remaining buffer
        self.flush()
        
        # Close the FileIO
        try:
            self.file_io.close_wait(timeout=5.0)
        except Exception as e:
            print(f"Error closing FileIO: {e}", file=sys.stderr)
        
        super().close()


class EnhancedRotatingFileHandler(FileIOLogHandler):
    """
    Rotating file handler using FileIO with size-based rotation
    """
    
    def __init__(self, filename: str, mode: str = 'a', maxBytes: int = 0, 
                 backupCount: int = 0, encoding: str = 'utf-8', **kwargs):
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        self._rotation_lock = threading.Lock()
        
        super().__init__(filename, mode, encoding, **kwargs)
    
    def _should_rollover(self) -> bool:
        """Check if we should perform a rollover"""
        if self.maxBytes <= 0:
            return False
        
        try:
            # Check file size
            if os.path.exists(self.filename):
                return os.path.getsize(self.filename) >= self.maxBytes
        except (OSError, ValueError):
            pass
        
        return False
    
    def _do_rollover(self):
        """Perform the file rollover"""
        with self._rotation_lock:
            if not self._should_rollover():
                return
            
            try:
                # Close current file
                self.file_io.close_wait()
                
                # Rotate files
                for i in range(self.backupCount - 1, 0, -1):
                    src_file = f"{self.filename}.{i}"
                    dst_file = f"{self.filename}.{i + 1}"
                    
                    if os.path.exists(src_file):
                        if os.path.exists(dst_file):
                            os.remove(dst_file)
                        os.rename(src_file, dst_file)
                
                # Move current file to .1
                if os.path.exists(self.filename):
                    dst_file = f"{self.filename}.1"
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    os.rename(self.filename, dst_file)
                
                # Reopen the file
                self.file_io = FileIO(self.filename, FileIOMode.WRITE, encoding=self.encoding)
                self.file_io.add_callback(FileIOEvent.ERROR, self._on_file_error)
                self.file_io.add_callback(FileIOEvent.WRITE, self._on_write_complete)
                self.file_io.open_wait()
                
            except Exception as e:
                print(f"Error during log rotation: {e}", file=sys.stderr)
    
    def emit(self, record):
        """Emit a log record with rotation check"""
        # Check if we need to rotate before writing
        if self._should_rollover():
            self._do_rollover()
        
        super().emit(record)


def setLogFileName(log_file_path):
    global logFileName
    logFileName = os.path.abspath(log_file_path)


def initLogger():
    """Initialize the logger with FileIO support"""
    try:
        global logFileName, logHandler, logHandlerArray, logFlusher
        
        if logFileName is None:
            logFileName = os.path.join(DEFAULT_LOG_FILE_DIR, DEFAULT_LOG_FILE_NAME)

        # Create directory if it doesn't exist
        if not os.path.isdir(os.path.dirname(logFileName)):
            os.makedirs(os.path.dirname(logFileName))

        # If the file does not exist, create it with timestamp
        if not os.path.isfile(logFileName):
            with open(logFileName, "w") as f:
                f.write(str(time.time()) + str(os.linesep))

        # Use the new FileIO-based rotating handler
        logHandler = EnhancedRotatingFileHandler(
            logFileName, 
            mode='a', 
            maxBytes=myMaxBytes, 
            backupCount=3,
            max_buffer_size=50,
            auto_flush_interval=2.0
        )
        
        logFormatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s', 
            datefmt='%d-%b-%Y %H:%M:%S (%z)'
        )
        logHandler.setFormatter(logFormatter)
        
        logger = logging.getLogger()
        logger.addHandler(logHandler)
        logger.setLevel(logging.INFO)
        
        logHandlerArray.append(logHandler)
        
        # Note: logFlusher is now handled internally by FileIO
        print("Logger initialized with FileIO support")
        
    except Exception as e:
        print(f"LOGGING INITIALIZATION FAILED: {e}")
        print(traceback.format_exc())
        raise


def shutdownLogger():
    """Shutdown the logger and cleanup FileIO resources"""
    global logHandler, logHandlerArray
    
    try:
        # Flush all handlers
        for handler in logHandlerArray:
            if hasattr(handler, 'flush'):
                handler.flush()
            if hasattr(handler, 'close'):
                handler.close()
        
        logging.shutdown()
        
        # Clear the handler array
        logHandlerArray.clear()
        
        print("Logger shutdown completed")
        
    except Exception as e:
        print(f"Error during logger shutdown: {e}")


def clearLog():
    """Clear the log (perform rollover)"""
    try:
        if logHandler and hasattr(logHandler, '_do_rollover'):
            logHandler._do_rollover()
        elif logHandler and hasattr(logHandler, 'doRollover'):
            logHandler.doRollover()
    except Exception as e:
        print(f"LOGGING FAILED during clear: {e}")
        raise


def getTimestamp():
    """Returns the timestamp from the first line of the logfile"""
    try:
        with open(logFileName, "r") as f:
            f.seek(0)
            return f.readline()
    except Exception as e:
        print(f"LOGGING FAILED during timestamp read: {e}")


def addTimestamp():
    """Add a timestamp to the log file"""
    try:
        with open(logFileName, "a") as f:
            f.write(str(time.time()) + os.linesep)
    except Exception as e:
        print(f"LOGGING FAILED during timestamp add: {e}")


def readAll():
    """Returns the entire content of the logfile"""
    try:
        with open(logFileName, "r") as f:
            return f.read()
    except Exception as e:
        print(f"LOGGING FAILED during read all: {e}")


def addLogHandler(handler):
    """Add a log handler"""
    global logHandlerArray
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logHandlerArray.append(handler)


def removeLogHandler(handler):
    """Remove a log handler"""
    global logHandlerArray
    logger = logging.getLogger()
    logger.removeHandler(handler)
    if handler in logHandlerArray:
        logHandlerArray.remove(handler)


class MyRotatingFileHandler(logHandlers.RotatingFileHandler):
    """Legacy rotating file handler (kept for compatibility)"""
    def doRollover(self):
        try:
            logHandlers.RotatingFileHandler.doRollover(self)
            addTimestamp()
            self.maxBytes = myMaxBytes
        except:
            # There have been permissions issues with the log files.
            self.maxBytes += int(myMaxBytes / 2)


class LogFlusher(threading.Thread):
    """Legacy log flusher (kept for compatibility)"""
    def __init__(self, logHandler):
        threading.Thread.__init__(self)
        self.daemon = True
        self.handler = logHandler
        self.exit = threading.Event()
        self.start()

    def run(self):
        while True:
            if self.exit.wait(10):
                try:
                    self.doFlush()
                except AttributeError as e:
                    print(e)
                break
            self.doFlush()

    def doFlush(self):
        if hasattr(self.handler, 'flush'):
            self.handler.flush()
            if hasattr(self.handler, 'stream') and hasattr(self.handler.stream, 'fileno'):
                try:
                    os.fsync(self.handler.stream.fileno())
                except (AttributeError, OSError):
                    pass

    def stop(self):
        self.exit.set()