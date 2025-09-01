""""
Updated Logger module with FileIO Integration
This module provides functionality for logging messages to a file and console
with enhanced asynchronous file operations using the FileIO class.
"""

# import time, os, logging, sys
# from datetime import datetime
# import traceback, threading
# import logging.handlers as logHandlers
# from typing import Union, Optional, Dict, Any
# from enum import Enum

# import the GuiLogHandler

# # Import the new FileIO components
# from .file_handler import FileIO, FileIOEvent, FileIOCallbackData, FileIOMode
# # Remove the problematic import to avoid circular dependency
# # from ui.exts.log_to_window import LogToWindowHandler, setup_log_to_window

# class LogLevel(Enum):
#     DEBUG = logging.DEBUG
#     INFO = logging.INFO
#     WARNING = logging.WARNING
#     ERROR = logging.ERROR
#     CRITICAL = logging.CRITICAL
#     NOTSET = logging.NOTSET


# # Map string log levels to logging module levels
# log_level_map = {
#     "DEBUG": logging.DEBUG,
#     "INFO": logging.INFO,
#     "WARNING": logging.WARNING,
#     "ERROR": logging.ERROR,
#     "CRITICAL": logging.CRITICAL,
#     "NOTSET": logging.NOTSET
# }


# ##########################################################################################
# # Custom logging filter to enable/disable logging for specific modules
# ##########################################################################################

# class CustomLogFilter(logging.Filter):
#     def __init__(self, module_name, enabled=True):
#         super().__init__(name=module_name)
#         self.module_name = module_name
#         self.enabled = enabled

#     def filter(self, record):
#         return self.enabled


# class LoggerManager:
#     """Enhanced logger manager with FileIO support"""
#     _loggers : Dict[str, Dict[str, Any]] = {}
#     _lock = threading.Lock()
#     APP_LOG_FILE = "app.log"

#     @classmethod
#     def get_logger(cls, module_name, level: Union[str, LogLevel] = LogLevel.DEBUG, *,
#                    to_console=True, to_file=True, to_log_window=False,
#                    description=True, prepend="", append="",
#                    log_file=None, enable=True, use_fileio=True,
#                    max_buffer_size=50, auto_flush_interval=2.0):

#         with cls._lock:
#             if module_name in cls._loggers:
#                 return cls._loggers[module_name]["logger"]

#             logger = logging.getLogger(module_name)
            
#             # Set the logger level
#             if isinstance(level, str):
#                 level = log_level_map.get(level.upper(), logging.DEBUG)
#             elif isinstance(level, LogLevel):
#                 level = level.value
            
#             logger.setLevel(level)
#             logger.propagate = False  # avoid double logging

#             formatter = cls._get_formatter(description, prepend, append)
#             module_log_file = log_file or cls.APP_LOG_FILE

#             if to_console:
#                 ch = logging.StreamHandler(sys.stdout)
#                 ch.setFormatter(formatter)
#                 logger.addHandler(ch)

#             if to_file:
#                 try:
#                     # Create directory if needed
#                     log_dir = os.path.dirname(module_log_file)
#                     if log_dir and not os.path.exists(log_dir):
#                         os.makedirs(log_dir, exist_ok=True)
                    
#                     if use_fileio:
#                         # Use the new FileIO-based handler
#                         fh = FileIOLogHandler(
#                             module_log_file,
#                             mode='a',
#                             max_buffer_size=max_buffer_size,
#                             auto_flush_interval=auto_flush_interval
#                         )
#                     else:
#                         # Use traditional file handler
#                         fh = logging.FileHandler(module_log_file, mode='a')
                    
#                     fh.setFormatter(formatter)
#                     logger.addHandler(fh)
                    
#                 except Exception as e:
#                     print(f"Failed to create file handler for {module_name}: {e}")
#                     # Continue without file logging

#             # Optional: Hook for GUI log window
#             if to_log_window:
#                 try:
#                     from ui.exts.log_window_async import GuiLogHandler
#                     gh = GuiLogHandler(module_name)
#                     gh.setFormatter(formatter)
#                     logger.addHandler(gh)
#                 except ImportError:
#                     print("GUI log handler not available")

#             # Add filter for enabling/disabling
#             log_filter = CustomLogFilter(module_name, enable)
#             logger.addFilter(log_filter)

#             cls._loggers[module_name] = {
#                 "logger": logger,
#                 "filter": log_filter
#             }
#             return logger

#     @classmethod
#     def enable_module(cls, module_name):
#         """Enable logging for a specific module"""
#         if module_name in cls._loggers:
#             cls._loggers[module_name]["filter"].enabled = True

#     @classmethod
#     def disable_module(cls, module_name):
#         """Disable logging for a specific module"""
#         if module_name in cls._loggers:
#             cls._loggers[module_name]["filter"].enabled = False

#     @classmethod
#     def flush_all(cls):
#         """Flush all loggers"""
#         for logger_info in cls._loggers.values():
#             logger = logger_info["logger"]
#             for handler in logger.handlers:
#                 if hasattr(handler, 'flush'):
#                     handler.flush()

#     @classmethod
#     def shutdown_all(cls):
#         """Shutdown all loggers"""
#         cls.flush_all()
        
#         for logger_info in cls._loggers.values():
#             logger = logger_info["logger"]
#             for handler in logger.handlers[:]:  # Copy list to avoid modification during iteration
#                 if hasattr(handler, 'close'):
#                     handler.close()
#                 logger.removeHandler(handler)
        
#         cls._loggers.clear()

#     @staticmethod
#     def _get_formatter(include_desc, prepend, append):
#         """Create a formatter with the specified options"""
#         parts = []
#         if prepend:
#             parts.append(prepend)
#         if include_desc:
#             parts.append("[%(asctime)s] [%(threadName)s] [%(module)s:%(lineno)d]")
#         parts.append("%(message)s")
#         if append:
#             parts.append(append)
#         fmt = ' '.join(parts)
#         return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")



# def test_logger():
#     """Test the enhanced logger functionality"""
#     print("Testing enhanced logger with FileIO...")
    
#     # Test basic logger
#     log = LoggerManager.get_logger(
#         "TestModule",
#         level=logging.DEBUG,
#         to_console=True,
#         to_file=True,
#         log_file="logs/test_module.log",
#         prepend="[TEST]",
#         use_fileio=True,
#         max_buffer_size=10,
#         auto_flush_interval=1.0
#     )

#     log.info("Logger initialized with FileIO")
#     log.debug("This is a debug message")
#     log.warning("This is a warning message")
#     log.error("This is an error message")
#     log.critical("This is a critical message")

#     # Test exception logging
#     try:
#         1 / 0
#     except Exception:
#         log.exception("Exception occurred")

#     # Test module enable/disable
#     LoggerManager.disable_module("TestModule")
#     log.info("This message should not appear")
    
#     LoggerManager.enable_module("TestModule")
#     log.info("Module re-enabled")

#     # Test rapid logging to trigger buffer flush
#     for i in range(20):
#         log.info(f"Rapid log message {i}")

#     # Wait a bit for async operations
#     import time
#     time.sleep(2)

#     # Flush and shutdown
#     LoggerManager.flush_all()
#     time.sleep(1)
#     LoggerManager.shutdown_all()
    
#     print("Logger test completed")


# if __name__ == "__main__":
#     test_logger()
    
    
"""
Enhanced Logger Module with YAML Configuration Support
This module provides a comprehensive logging system with:
- YAML-based configuration with inheritance
- Multiple handler types (console, file, window)
- Dynamic configuration reloading
- Module-specific configurations
"""

import copy
import logging
import os
import sys
import threading
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import weakref
import atexit

import signal

# Import custom components
from .yaml_cfg_parser import Parser as YAMLConfigParser
from .file_log_handler import FileIOLogHandler, AsyncRotatingFileHandler
# import the log window handler
from ui.exts.log_window_async import   log_window_handler
# Remove the problematic import to avoid circular dependency
from .file_handler import init_module as init_fileio_module


####==============================================================
# import the cleanup modules 
##=================================================================
from ui.exts.log_window_async import LogToWindowHandler
from .file_handler import cleanup_module as file_handler_cleanup_module
    
    
class EnhancedLogManager:
    """
    Enhanced logger manager with YAML configuration support
    """
    
    
    # Singleton instance
    _instance: Optional['EnhancedLogManager'] = None
    _lock = threading.Lock()
    
    # Class variables
    _loggers: Dict[str, logging.Logger] = {}
    _configs: Dict[str, Dict[str, Any]] = {}
    _handlers: Dict[str, logging.Handler] = {}
    _config_parser: Optional[YAMLConfigParser] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super(EnhancedLogManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
    
    def _initialize(self):
        """Initialize the logger manager"""
        self._initialized = True
        print("[EnhancedLogManager] Initing module")
        try:
            # Init the config parser module to use here 
            if not self._config_parser:
                self._config_parser = YAMLConfigParser()
                
            ### init the module global methods
            init_fileio_module()
            
        except Exception as e:
            print(f"[EnhancedLogManager] Warning: Could not initialize file handler: {e}")
            raise 
        
        # also register if interrupt comes to stop the application 

        def _handle_sigint(signum, frame):
            print("[EnhancedLogManager] SIGINT received, shutting down...")
            self.shutdown()
            sys.exit(0)

        # Register SIGINT handler (Ctrl+C)
        signal.signal(signal.SIGINT, _handle_sigint)
        signal.signal(signal.SIGTERM, _handle_sigint)
        # Register cleanup
        atexit.register(self.shutdown)
    
    
    def shutdown(self):
        """Shutdown all loggers and handlers"""
        print("[EnhancedLogManager] Shutting down...")
        
        # Flush all handlers
        for handler in self._handlers.values():
            try:
                if hasattr(handler, 'flush'):
                    handler.flush()
            except:
                pass
        
        # Close all handlers
        for handler in self._handlers.values():
            try:
                if hasattr(handler, 'close'):
                    handler.close()
            except:
                pass
            
        ## ===================shutdown the handlers top level module ==============================
        # cleanup the log window handler
        LogToWindowHandler.cleanup_module()
        # cleanup the file handler module
        file_handler_cleanup_module()

        # Clear
        self._loggers.clear()
        self._handlers.clear()
        self._configs.clear()
        
        print("[EnhancedLogManager] Shutdown complete")

    ##########################################################################################
    # YAML Configuration
    ##########################################################################################
    
    def configure_from_yaml(self, config_file: Union[str, Path], 
                           base_dir: Optional[str] = None):
        """
        Configure logging from a YAML file
        
        Args:
            config_file: Path to the YAML configuration file
            base_dir: Base directory for resolving relative paths
        """
        if not self._config_parser:
            self._config_parser = YAMLConfigParser(base_dir)
        
        # Load main configuration
        main_config = self._config_parser.load_config(config_file)
        
        # Apply global settings
        if 'global' in main_config:
            self._apply_global_settings(main_config['global'])
        
        # Store the configuration as main config
        self._configs['_main'] = main_config
    
    def _apply_global_settings(self, global_config: Dict[str, Any]):
        """Apply global logging settings"""
        # Set global log directory
        if 'log_dir' in global_config:
            os.environ['LOG_DIR'] = global_config['log_dir']
        
        # Set root logger level
        if 'root_level' in global_config:
            logging.getLogger().setLevel(
                getattr(logging, global_config['root_level'].upper())
            )

    ####============================ logger configurations based on YAML ==========================================
    def _get_logger_config_from_main(self, logger_name: str) -> Dict[str, Any]:
        """Get logger configuration from main config"""
        main_config = self._configs.get('_main', {})
        
        # Start with defaults
        config = main_config.get('default_logger', {}).copy()
        
        # Check for specific logger config
        loggers_config = main_config.get('loggers', {})
        if logger_name in loggers_config:
            specific_config = loggers_config[logger_name]
            config = self._merge_configs(config, specific_config)
        else:
            # Check patterns
            for pattern, pattern_config in loggers_config.items():
                if self._matches_pattern(logger_name, pattern):
                    config = self._merge_configs(config, pattern_config)
        
        return config
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a logger name matches a pattern"""
        import re
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f'^{regex_pattern}$', name))
    
    def _merge_configs(self, base: Dict[str, Any], 
                      override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configurations"""
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
            Get default logger configuration
            default only support console handler
        """
        return {
            'level': 'INFO',
            'handlers': {
                'console': {
                    'enabled': True,
                    'level': 'INFO'
                }
            },
            'format': '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            'propagate': False
        }
        
    ##########################################################################################
    # Logger Management
    ##########################################################################################
    
    def get_logger(self, name: str, 
                   config_file: Optional[Union[str, Path]] = None,
                   source_file: Optional[str] = None,
                   **kwargs) -> logging.Logger:
        """
        Get or create a logger with YAML configuration
        
        Args:
            name: Logger name
            config_file: Optional specific config file for this logger
            source_file: Source file path (from __file__)
            **kwargs: Additional configuration overrides
            
        Returns:
            Configured logger instance
        """
        with self._lock:
            # Check if logger already exists
            if name in self._loggers:
                return self._loggers[name]
            
            # Get configuration
            if config_file:
                config = self._config_parser.get_logger_config(name, config_file)
            elif '_main' in self._configs:
                config = self._get_logger_config_from_main(name)
            else:
                # Use defaults
                config = self._get_default_config()
            
            # Merge with kwargs
            config = self._merge_configs(config, kwargs)
            
            # Create logger
            logger = self._create_logger(name, config, source_file)
            
            # Store
            self._loggers[name] = logger
            self._configs[name] = config
            
            return logger
    
    
    def _create_logger(self, name: str, config: Dict[str, Any], 
                      source_file: Optional[str] = None) -> logging.Logger:
        """Create and configure a logger"""
        logger = logging.getLogger(name)
        
        # Set level as INT number based on the level string
        level = getattr(logging, config.get('level', 'INFO').upper())
        logger.setLevel(level)
        
        # Set propagate to false as not traverse to the parent
        logger.propagate = config.get('propagate', False)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = self._create_formatter(config, name)
        
        # Add handlers
        handlers_config : Dict[str, Any] = config.get('handlers', {})
        for handler_type, handler_config in handlers_config.items():
            if handler_config.get('enabled', False):
                # create and add handler to the logger
                handler = self._create_handler(
                    handler_type, handler_config, name, formatter, source_file
                )
                if handler:
                    logger.addHandler(handler)
        
        # Add filters
        filters_config : List[Dict[str, Any]] = config.get('filters', [])
        for filter_config in filters_config:
            filter_obj = self._create_filter(filter_config)
            if filter_obj:
                logger.addFilter(filter_obj)
        
        return logger
    
    def _create_formatter(self, config: Dict[str, Any], 
                         logger_name: str) -> logging.Formatter:
        """Create a log formatter if not given then raise error"""
        format_str : str = config.get('format')

        # raise error if not format
        if not format_str:
            raise ValueError("Log format is not specified")

        # Replace placeholders
        format_str = format_str.replace('%(logger_name)s', logger_name)
        
        date_format = config.get('date_format', '%Y-%m-%d %H:%M:%S')
        
        return logging.Formatter(format_str, date_format)
    
    
    def _create_filter(self, filter_config: Dict[str, Any]) -> Optional[logging.Filter]:
        """Create a filter based on configuration"""
        filter_type = filter_config.get('type', 'basic')
        
        if filter_type == 'module':
            # Module name filter
            class ModuleFilter(logging.Filter):
                def __init__(self, module_name, enabled):
                    self.module_name = module_name
                    self.enabled = enabled
                
                def filter(self, record : logging.LogRecord) -> bool:
                    return self.enabled and record.name.startswith(self.module_name)
            
            return ModuleFilter(
                filter_config.get('name', ''),
                filter_config.get('enabled', False)
            )
        
        return None
    
    def reload_config(self, logger_name: Optional[str] = None):
        """
        Reload configuration for a logger or all loggers
        note: This is no use right now ****
        Args:
            logger_name: Specific logger to reload, or None for all
        """
        with self._lock:
            if logger_name:
                if logger_name in self._loggers:
                    # Remove and recreate
                    del self._loggers[logger_name]
                    config = self._configs.get(logger_name, {})
                    self._create_logger(logger_name, config)
            else:
                # Reload all
                for name in list(self._loggers.keys()):
                    self.reload_config(name)
                    
    ##########################################################################################
    # Handler Management
    ##########################################################################################
    
    def _create_handler(self, handler_type: str, 
                       handler_config: Dict[str, Any],
                       logger_name: str,
                       formatter: logging.Formatter,
                       source_file: Optional[str] = None) -> Optional[logging.Handler]:
        """Create a handler based on type and configuration"""
        handler = None
        
        try:
            if handler_type == 'console':
                handler = self._create_console_handler(handler_config)
            
            elif handler_type == 'file':
                handler = self._create_file_handler(
                    handler_config, logger_name, source_file
                )
            
            elif handler_type == 'log_window':
                handler = self._create_window_handler(handler_config, logger_name)
            
            elif handler_type == 'syslog':
                # we should not use this handler type, it is not supported
                # handler = self._create_syslog_handler(handler_config)
                pass
            
            else:
                raise ValueError(f"[EnhancedLogManager] Unknown handler type: {handler_type}")
            
            # Set level
            level = getattr(logging, 
                            handler_config.get('level', 'INFO').upper())
            handler.setLevel(level)
            
            # Set formatter
            if 'format' in handler_config:
                custom_formatter = logging.Formatter(
                    handler_config['format'],
                    handler_config.get('date_format', '%Y-%m-%d %H:%M:%S')
                )
                handler.setFormatter(custom_formatter)
            else:
                handler.setFormatter(formatter)
            
            # Store handler
            handler_key = f"{logger_name}_{handler_type}"
            self._handlers[handler_key] = handler
        
        except Exception as e:
            print(f"[EnhancedLogManager] Error creating {handler_type} handler: {e}")
        
        return handler
    
    def _create_console_handler(self, config: Dict[str, Any]) -> logging.Handler:
        """Create a console handler"""
        stream = sys.stderr if config.get('stream', 'stdout') == 'stderr' else sys.stdout
        return logging.StreamHandler(stream)
    
    def _create_file_handler(self, config: Dict[str, Any], 
                           logger_name: str,
                           source_file: Optional[str] = None) -> logging.Handler:
        """Create a file handler with optional FileIO support"""
        # Determine filename
        filename = config.get('filename', f"{logger_name}.log")
        
        # Expand environment variables
        filename = os.path.expandvars(filename)
        
        # If relative, make it relative to source file or log dir
        if not os.path.isabs(filename):
            if source_file and 'log_dir' not in os.environ:
                filename = os.path.join(os.path.dirname(source_file), filename)
            elif 'LOG_DIR' in os.environ:
                filename = os.path.join(os.environ['LOG_DIR'], filename)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Determine handler type
        use_fileio = config.get('use_fileio', True)
        max_size = config.get('max_size', 10 * 1024 * 1024)  # 10MB default
        backup_count = config.get('backup_count', 5)
        
        if use_fileio:
            return FileIOLogHandler(
                filename=filename,
                mode=config.get('mode', 'a'),
                max_bytes=max_size,
                backup_count=backup_count,
                encoding=config.get('encoding', 'utf-8'),
                max_buffer_size=config.get('buffer_size', 100),
                auto_flush_interval=config.get('flush_interval', 2.0),
                use_async=config.get('async', True)
            )
        else:
            # Use standard rotating file handler
            from logging.handlers import RotatingFileHandler
            return RotatingFileHandler(
                filename=filename,
                mode=config.get('mode', 'a'),
                maxBytes=max_size,
                backupCount=backup_count,
                encoding=config.get('encoding', 'utf-8')
            )
    
    def _create_window_handler(self, config: Dict[str, Any], 
                             logger_name: str) -> logging.Handler:
        """Create a window handler"""
        return log_window_handler(
            module_name=logger_name,
            max_buffer_size=config.get('buffer_size', 100),
            flush_interval=config.get('flush_interval', 0.1),
            rate_limit=config.get('rate_limit', 100),
            enable_colors=config.get('colors', True),
            timestamp_format=config.get('timestamp_format')
        )

    def _create_syslog_handler(self, config: Dict[str, Any]) -> logging.Handler:
        """Create a syslog handler"""
        from logging.handlers import SysLogHandler
        
        address = config.get('address', '/dev/log')
        if ':' in str(address):
            # Network address
            host, port = address.split(':')
            address = (host, int(port))
        
        facility = getattr(SysLogHandler, 
                         f"LOG_{config.get('facility', 'USER').upper()}")
        
        return SysLogHandler(address=address, facility=facility)
    
    ##########################################################################################
    
    
    def set_level(self, logger_name: str, level: Union[str, int]):
        """
        Set the level for a logger
        
        Args:
            logger_name: Logger name
            level: New level
        """
        if logger_name in self._loggers:
            if isinstance(level, str):
                level = getattr(logging, level.upper())
            self._loggers[logger_name].setLevel(level)
    
    def enable_handler(self, logger_name: str, handler_type: str):
        """Enable a handler for a logger"""
        # Implementation depends on handler tracking
        pass
    
    def disable_handler(self, logger_name: str, handler_type: str):
        """Disable a handler for a logger"""
        # Implementation depends on handler tracking
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all loggers and handlers"""
        stats = {
            'loggers': list(self._loggers.keys()),
            'handlers': {}
        }
        
        for handler_key, handler in self._handlers.items():
            if hasattr(handler, 'get_statistics'):
                stats['handlers'][handler_key] = handler.get_statistics()
        
        return stats
    


# Convenience functions
_manager = EnhancedLogManager()

def configure_logging(config_file: Union[str, Path], base_dir: Optional[str] = None):
    """Configure logging from YAML file"""
    _manager.configure_from_yaml(config_file, base_dir)

def get_logger(name: str, **kwargs) -> logging.Logger:
    """Get a configured logger"""
    return _manager.get_logger(name, **kwargs)

def reload_config(logger_name: Optional[str] = None):
    """Reload logger configuration"""
    _manager.reload_config(logger_name)

def get_logging_statistics() -> Dict[str, Any]:
    """Get logging statistics"""
    return _manager.get_statistics()

def shutdown_logging():
    """Shutdown logging system"""
    _manager.shutdown()



##########################################################################################
# Example usage
##########################################################################################

##########################################################################################
#create a test that creates multiple threads and test log functionality 


def test_log_to_window_thread(i):
    logger = get_logger(f"TestModule{i}", level='INFO')
    logger.info(f"This is an info message {i}")
    logger.warning(f"This is a warning message {i}")
    logger.error(f"This is an error message {i}")
    logger.debug(f"This is a debug message {i}")
    logger.critical(f"This is a critical message {i}")

def test_multiple_logger_threads():
    print("test_multiple_logger_threads")
    threads = []
    for i in range(10):
        thread = threading.Thread(target=test_log_to_window_thread, args=(i,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

# Example usage
if __name__ == "__main__":
    # Example configuration
    import tempfile
    
    # Create example config
    config = """
            global:
            log_dir: ./logs
            root_level: DEBUG

            default_logger:
            level: INFO
            handlers:
                console:
                enabled: true
                level: INFO
                file:
                enabled: true
                level: DEBUG
                filename: ${LOG_DIR}/${logger_name}.log
                max_size: 10485760
                backup_count: 3
                use_fileio: true

            loggers:
            A2DP_logger:
                level: DEBUG
                handlers:
                console:
                    enabled: false
                file:
                    filename: ${LOG_DIR}/a2dp.log
                log_window:
                    enabled: true
                    rate_limit: 50
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(config)
        config_file = f.name
    
    # Configure logging
    configure_logging(config_file)
    
    # Get logger
    logger = get_logger("A2DP_logger")
    
    # Log messages
    logger.info("Test info message")
    logger.debug("Test debug message")
    logger.error("Test error message")
    
    # Get statistics
    print("Statistics:", get_logging_statistics())
    
    # Cleanup
    import time
    time.sleep(1)
    shutdown_logging()
    os.unlink(config_file)