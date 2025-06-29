"""
Enhanced Log to Window Module
Thread-safe logging to Qt GUI window using Qt's signal-slot mechanism
"""

import logging
import threading
import time
from typing import Optional, List, Dict, Any
from queue import Queue, Empty
from datetime import datetime
import weakref

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt5.QtWidgets import QApplication


# Import your existing LogWindow class
from ui.exts.log_window import LogWindow
from dataclasses import dataclass


@dataclass  
class LogMessage:
    """Data class for log messages"""
    level: int
    level_name: str
    module: str
    message: str
    color: Optional[str] = None
    record: Optional[logging.LogRecord] = None
    timestamp: datetime = None

    def __post_init__(self):
        self.timestamp = datetime.now()

class RateLimiter:
    """Thread-safe rate limiter for preventing GUI flooding"""
    
    def __init__(self, max_per_second: int):
        self.max_per_second = max_per_second
        self.window_size = 1.0  # 1 second window
        self.requests = []
        self.lock = threading.Lock()
    
    def allow(self) -> bool:
        """Check if a request is allowed"""
        if self.max_per_second <= 0:
            return True
        
        with self.lock:
            now = time.time()
            # Remove old requests outside the window
            self.requests = [t for t in self.requests if now - t < self.window_size]
            
            if len(self.requests) < self.max_per_second:
                self.requests.append(now)
                return True
            return False


class LogWindowBridge(QObject):
    """
    Qt Bridge for thread-safe logging to GUI
    This class runs on the main thread and receives signals from worker threads
    """
    
    # Signals for thread-safe communication
    log_message_signal = pyqtSignal(object)  # Single message
    log_batch_signal = pyqtSignal(list)      # Batch of messages
    
    def __init__(self):
        super().__init__()
        
        # Connect signals to slots
        self.log_message_signal.connect(self._handle_single_message)
        self.log_batch_signal.connect(self._handle_batch_messages)
    
    def _handle_single_message(self, log_msg: LogMessage):
        """Handle a single log message (runs on main thread)"""
        if not LogWindow.is_inited():
            return
            
        try:
            log_window = LogWindow.get_instance()
            if log_window:
                formatted_msg = f"[{log_msg.module}] {log_msg.message}"
                log_window.append_log(formatted_msg, log_msg.level_name)
        except Exception as e:
            print(f"[LogWindowBridge] Error handling message: {e}")
    
    def _handle_batch_messages(self, messages: List[LogMessage]):
        """Handle batch of log messages (runs on main thread)"""
        if not LogWindow.is_inited():
            return
            
        try:
            log_window = LogWindow.get_instance()
            if not log_window:
                return
                
            # Process batch efficiently
            for log_msg in messages:
                formatted_msg = f"[{log_msg.module}] {log_msg.message}"
                log_window.append_log(formatted_msg, log_msg.level_name)
                
        except Exception as e:
            print(f"[LogWindowBridge] Error handling batch: {e}")


class LogProcessor(QThread):
    """
    Background thread for processing log messages
    Uses Qt's QThread for better integration with Qt event system
    """
    
    def __init__(self, bridge: LogWindowBridge, flush_interval: float = 0.1, 
                 batch_size: int = 50):
        super().__init__()
        self.bridge = bridge
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        
        # Message queue
        self.message_queue: Queue[LogMessage] = Queue()
        self.running = False
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'batches_sent': 0,
            'messages_dropped': 0
        }
    
    def add_message(self, log_msg: LogMessage):
        """Add a message to the processing queue"""
        try:
            self.message_queue.put_nowait(log_msg)
        except:
            # Queue full, drop message
            self.stats['messages_dropped'] += 1
    
    def run(self):
        """Main processing loop (runs in background thread)"""
        self.running = True
        
        while self.running:
            try:
                messages = []
                
                # Collect messages for batch processing
                end_time = time.time() + self.flush_interval
                
                while len(messages) < self.batch_size and time.time() < end_time:
                    try:
                        # Wait for message with timeout
                        remaining_time = max(0.001, end_time - time.time())
                        msg = self.message_queue.get(timeout=remaining_time)
                        messages.append(msg)
                        # self.message_queue.task_done() # no need to do this
                        
                    except Empty:
                        break
                
                # Send messages to GUI thread if we have any
                if messages:
                    if len(messages) == 1:
                        # Single message - use single signal
                        self.bridge.log_message_signal.emit(messages[0])
                    else:
                        # Multiple messages - use batch signal
                        self.bridge.log_batch_signal.emit(messages)
                    
                    self.stats['messages_processed'] += len(messages)
                    self.stats['batches_sent'] += 1
                
                # Small sleep to prevent busy waiting
                else:
                    self.msleep(10)  # QThread's msleep method
                    
            except Exception as e:
                print(f"[LogProcessor] Error in processing loop: {e}")
    
    def stop(self):
        """Stop the processing thread"""
        self.running = False
        self.wait(1000)  # Wait up to 1 second for thread to finish
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()


class LogToWindowHandler(logging.Handler):
    """
    Enhanced logging handler that uses Qt's signal-slot mechanism
    for thread-safe GUI updates
    """
    
    # Shared components (singleton pattern)
    _bridge: Optional[LogWindowBridge] = None
    _processor: Optional[LogProcessor] = None
    _handlers: weakref.WeakSet = weakref.WeakSet()
    _lock = threading.Lock()
    # Color mapping
    _color_map = {
            logging.DEBUG: "blue",
            logging.INFO: "green", 
            logging.WARNING: "orange",
            logging.ERROR: "red",
            logging.CRITICAL: "darkred"
        }
        
    def __init__(self, module_name: str,
                 rate_limit: int = 100,
                 enable_colors: bool = True,
                 max_queue_size: int = 1000):
        """
        Initialize the log handler
        
        Args:
            module_name: Name of the module for identification
            rate_limit: Maximum messages per second
            enable_colors: Whether to enable color coding
            max_queue_size: Maximum queue size before dropping messages
        """
        super().__init__()
        
        self.module_name = module_name
        self.enable_colors = enable_colors
        
        # Rate limiting
        self._rate_limiter = RateLimiter(rate_limit)
        
        # Initialize shared components
        self._ensure_shared_components()
        
        # Register this handler
        LogToWindowHandler._handlers.add(self)
        
    
    @classmethod
    def _ensure_shared_components(cls):
        """Ensure shared components are initialized (thread-safe)"""
        with cls._lock:
            if cls._bridge is None:
                # Check if we're in a Qt application
                app = QApplication.instance()
                if app is None:
                    raise RuntimeError("LogToWindowHandler requires a Qt application")
                
                # Create bridge (must be on main thread)
                cls._bridge = LogWindowBridge()
                
                # Create and start processor thread
                cls._processor = LogProcessor(cls._bridge)
                cls._processor.start()
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record"""
        try:
            # Check if window is available
            if not LogWindow.is_inited():
                return
            
            # Rate limiting
            if not self._rate_limiter.allow():
                return
            
            # Format the record
            msg = self.format(record)
            
            # Create log message object
            log_msg = LogMessage(
                level=record.levelno,
                level_name=record.levelname,
                module=self.module_name,
                message=msg,
                color=self._color_map.get(record.levelno) if self.enable_colors else None
            )
            
            # Send to processor
            if self._processor:
                self._processor.add_message(log_msg)
                
        except Exception:
            self.handleError(record)
    
    def flush(self):
        """Flush any pending messages"""
        # Qt handles this automatically through the event system
        pass
    
    def close(self):
        """Close the handler"""
        # Remove from registry
        LogToWindowHandler._handlers.discard(self)
        
        # If this was the last handler, cleanup shared components
        with self._lock:
            if not self._handlers and self._processor:
                self._processor.stop()
                self._processor = None
                self._bridge = None
        
        super().close()
    
    @classmethod
    def get_shared_stats(cls) -> Dict[str, Any]:
        """Get statistics from the shared processor"""
        if cls._processor:
            return cls._processor.get_stats()
        return {}
    
    @classmethod
    def cleanup_all(cls):
        """Cleanup all shared components"""
        with cls._lock:
            if cls._processor:
                cls._processor.stop()
                cls._processor = None
            cls._bridge = None
            
            # Close all handlers
            handlers = list(cls._handlers)
            for handler in handlers:
                try:
                    handler.close()
                except:
                    pass


# Convenience function for easy setup
def setup_log_to_window(module_name: str, logger: Optional[logging.Logger] = None,
                       level: int = logging.INFO, **kwargs) -> LogToWindowHandler:
    """
    Convenience function to set up logging to window
    
    Args:
        module_name: Name of the module
        logger: Logger instance (if None, uses root logger)
        level: Logging level
        **kwargs: Additional arguments for LogToWindowHandler
    
    Returns:
        The created handler
    """
    if logger is None:
        logger = logging.getLogger()
    
    handler = LogToWindowHandler(module_name, **kwargs)
    handler.setLevel(level)
    
    # Set a formatter if none exists
    if not handler.formatter:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return handler


# Example usage and testing
def test_log_to_window():
    """Test function for the log to window system"""
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    # Create Qt application if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create main window (placeholder)
    main_window = QMainWindow()
    
    # Create log window
    log_window = LogWindow.create_instance(main_window)
    
    # Set up logging
    logger = logging.getLogger("TestModule")
    handler = setup_log_to_window("TestModule", logger, logging.DEBUG)
    
    # Test logging
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.debug("This is a debug message")
    logger.critical("This is a critical message")
    
    # Test rapid logging
    for i in range(10):
        logger.info(f"Rapid message {i}")
    
    print("Log handler statistics:", LogToWindowHandler.get_shared_stats())
    
    # Cleanup
    LogToWindowHandler.cleanup_all()


if __name__ == "__main__":
    test_log_to_window()