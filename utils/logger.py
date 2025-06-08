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

# import the GuiLogHandler
from ui.exts.log_window import GuiLogHandler

# Import the new FileIO components
from .file_handler import FileIO, FileIOLogger, FileIOEvent, FileIOCallbackData, FileIOMode

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


logFileName = None
logHandler = None
logHandlerArray = []
logFlusher = None
myMaxBytes = 1000000





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