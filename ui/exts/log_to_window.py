"""
Enhanced Log to Window Handler
This module provides an improved handler for logging to the GUI window
with better integration and configuration support.
"""

import logging
import threading
import time
from typing import Optional, List, Dict, Any, Callable
from queue import Queue, Empty
from datetime import datetime
import weakref

# Import the LogWindow class (from your log_window module)
from ui.exts.log_window import LogWindow


class LogToWindowHandler(logging.Handler):
    """
    Enhanced handler for logging to a GUI window
    
    Features:
    - Thread-safe logging to GUI
    - Buffering for performance
    - Rate limiting to prevent GUI flooding
    - Automatic cleanup on window close
    - Color coding by log level
    - Filtering capabilities
    """
    
    # Class-level registry of all handlers
    _handlers: weakref.WeakSet = weakref.WeakSet()
    
    def __init__(self, module_name: str,
                 max_buffer_size: int = 100,
                 flush_interval: float = 0.1,
                 rate_limit: int = 100,  # Max messages per second
                 enable_colors: bool = True,
                 timestamp_format: Optional[str] = None):
        """
        Initialize the log window handler
        
        Args:
            module_name: Name of the module for identification
            max_buffer_size: Maximum number of messages to buffer
            flush_interval: Interval for flushing buffer to GUI
            rate_limit: Maximum messages per second to prevent flooding
            enable_colors: Whether to enable color coding
            timestamp_format: Custom timestamp format
        """
        super().__init__()
        
        self.module_name = module_name
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval
        self.rate_limit = rate_limit
        self.enable_colors = enable_colors
        self.timestamp_format = timestamp_format or "%H:%M:%S.%f"[:-3]
        
        # Message buffer
        self._buffer: Queue[Dict[str, Any]] = Queue(maxsize=max_buffer_size)
        self._buffer_lock = threading.Lock()
        
        # Rate limiting
        self._rate_limiter = RateLimiter(rate_limit)
        
        # Statistics
        self._stats = {
            'messages_logged': 0,
            'messages_displayed': 0,
            'messages_dropped': 0,
            'flushes': 0
        }
        
        # Flusher thread
        self._flusher_thread: Optional[threading.Thread] = None
        self._stop_flusher = threading.Event()
        self._start_flusher_thread()
        
        # Register this handler
        LogToWindowHandler._handlers.add(self)
        
        # Color map for log levels
        self.color_map = {
            logging.DEBUG: "blue",
            logging.INFO: "green",
            logging.WARNING: "orange",
            logging.ERROR: "red",
            logging.CRITICAL: "darkred"
        }
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a record to the log window
        
        Args:
            record: LogRecord to emit
        """
        try:
            # Check if window is available
            if not LogWindow.is_inited():
                return
            
            # Rate limiting check
            if not self._rate_limiter.allow():
                self._stats['messages_dropped'] += 1
                return
            
            # Format the record
            msg = self.format(record)
            
            # Create message data
            message_data = {
                'timestamp': datetime.now(),
                'level': record.levelno,
                'level_name': record.levelname,
                'module': self.module_name,
                'message': msg,
                'color': self.color_map.get(record.levelno, "black") if self.enable_colors else None,
                'record': record
            }
            
            # Add to buffer
            try:
                self._buffer.put_nowait(message_data)
                self._stats['messages_logged'] += 1
            except:
                # Buffer full, drop oldest message
                try:
                    self._buffer.get_nowait()
                    self._buffer.put_nowait(message_data)
                    self._stats['messages_dropped'] += 1
                except:
                    pass
                    
        except Exception:
            self.handleError(record)
    
    def _start_flusher_thread(self):
        """Start the background flusher thread"""
        self._flusher_thread = threading.Thread(
            target=self._flusher_worker,
            name=f"LogWindowHandler-{self.module_name}",
            daemon=True
        )
        self._flusher_thread.start()
    
    def _flusher_worker(self):
        """Background worker for flushing messages to GUI"""
        while not self._stop_flusher.is_set():
            try:
                # Wait for interval or stop signal
                if self._stop_flusher.wait(self.flush_interval):
                    break
                
                # Flush messages
                self._flush_messages()
                
            except Exception as e:
                print(f"[LogToWindowHandler] Flusher error: {e}")
    
    def _flush_messages(self):
        """Flush buffered messages to the GUI"""
        if not LogWindow.is_inited():
            return
        
        messages = []
        
        # Collect all buffered messages
        while not self._buffer.empty() and len(messages) < 50:  # Batch limit
            try:
                messages.append(self._buffer.get_nowait())
            except Empty:
                break
        
        if not messages:
            return
        
        # Send to GUI
        try:
            log_window = LogWindow.get_instance()
            if log_window and hasattr(log_window, 'append_log_batch'):
                # Batch append if available
                log_window.append_log_batch(messages)
            else:
                # Individual append
                for msg_data in messages:
                    self._append_to_window(msg_data)
            
            self._stats['messages_displayed'] += len(messages)
            self._stats['flushes'] += 1
            
        except Exception as e:
            print(f"[LogToWindowHandler] Error flushing to window: {e}")
    
    def _append_to_window(self, msg_data: Dict[str, Any]):
        """Append a single message to the log window"""
        try:
            log_window = LogWindow.get_instance()
            if not log_window:
                return
            
            # Format timestamp
            timestamp = msg_data['timestamp'].strftime(self.timestamp_format)
            
            # Format message with module name
            formatted_msg = f"[{self.module_name}] {msg_data['message']}"
            
            # Append to window
            log_window.append_log(formatted_msg, msg_data['level_name'])
            
        except Exception as e:
            print(f"[LogToWindowHandler] Error appending message: {e}")
    
    def flush(self):
        """Flush the handler"""
        self._flush_messages()
    
    def close(self):
        """Close the handler"""
        # Stop flusher thread
        self._stop_flusher.set()
        if self._flusher_thread and self._flusher_thread.is_alive():
            self._flusher_thread.join(timeout=1.0)
        
        # Final flush
        self.flush()
        
        # Remove from registry
        LogToWindowHandler._handlers.discard(self)
        
        # Print statistics
        print(f"[LogToWindowHandler-{self.module_name}] Stats: {self._stats}")
        
        super().close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get handler statistics"""
        return self._stats.copy()
    
    def reset_statistics(self):
        """Reset handler statistics"""
        for key in self._stats:
            self._stats[key] = 0
    
    @classmethod
    def flush_all_handlers(cls):
        """Flush all registered window handlers"""
        for handler in cls._handlers:
            try:
                handler.flush()
            except:
                pass
    
    @classmethod
    def close_all_handlers(cls):
        """Close all registered window handlers"""
        handlers = list(cls._handlers)
        for handler in handlers:
            try:
                handler.close()
            except:
                pass


class RateLimiter:
    """Simple rate limiter for preventing GUI flooding"""
    
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


class EnhancedLogWindow(LogWindow):
    """
    Enhanced LogWindow with batch operations and better performance
    
    This extends the existing LogWindow class with additional features
    """
    
    def __init__(self, main_wind=None):
        super().__init__(main_wind)
        
        # Batch operation support
        self._batch_timer = None
        self._pending_messages = []
        self._batch_lock = threading.Lock()
    
    def append_log_batch(self, messages: List[Dict[str, Any]]):
        """
        Append multiple log messages in a batch for better performance
        
        Args:
            messages: List of message dictionaries
        """
        with self._batch_lock:
            self._pending_messages.extend(messages)
            
            # Schedule batch update
            if not self._batch_timer:
                from PyQt5.QtCore import QTimer
                self._batch_timer = QTimer()
                self._batch_timer.timeout.connect(self._process_batch)
                self._batch_timer.start(50)  # 50ms batch interval
    
    def _process_batch(self):
        """Process pending messages in batch"""
        with self._batch_lock:
            if not self._pending_messages:
                return
            
            messages = self._pending_messages[:100]  # Process up to 100 at a time
            self._pending_messages = self._pending_messages[100:]
        
        # Process messages
        for msg_data in messages:
            timestamp = msg_data['timestamp'].strftime("%H:%M:%S")
            level = msg_data['level_name']
            message = msg_data['message']
            color = msg_data.get('color', 'white')
            
            # Format and append
            formatted_msg = f"[{timestamp}] <span style=\"color:{color};\">[{level}] {message}</span>"
            self.log_text.append(formatted_msg)
        
        # Ensure size limit
        self.enforce_log_size_limit()
        
        # Stop timer if no more messages
        with self._batch_lock:
            if not self._pending_messages and self._batch_timer:
                self._batch_timer.stop()
                self._batch_timer = None
    
    def set_filter(self, filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None):
        """
        Set a filter function for messages
        
        Args:
            filter_func: Function that returns True to display message
        """
        self._filter_func = filter_func
    
    def clear_with_pattern(self, pattern: str):
        """
        Clear messages matching a pattern
        
        Args:
            pattern: Regex pattern to match messages
        """
        import re
        current_html = self.log_text.toHtml()
        lines = current_html.split('<br>')
        filtered_lines = [line for line in lines if not re.search(pattern, line)]
        self.log_text.setHtml('<br>'.join(filtered_lines))