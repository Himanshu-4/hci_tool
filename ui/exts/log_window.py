from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, QMainWindow, QSizePolicy, QHBoxLayout, QLabel
)

from PyQt5.QtGui import (QTextCursor, QIntValidator)

from PyQt5.QtCore import Qt
import time


MAX_LOG_SIZE_LOG_WINDOW = 10 * 1024 * 1024  # 10 MB



class LogWindow(QWidget):
    _instance = None
    _color_map = {
        'DEBUG': "blue",
        'INFO': "green",
        'WARNING': "yellow",
        'ERROR': "red",
        'CRITICAL': "orange",
        'NOTSET': "white"
    }

    @classmethod
    def is_inited(cls):
        return False if cls._instance is None else True

    @classmethod
    def is_open(cls):
        """
        Check if the log window is open
        """
        return cls._instance is not None and cls._instance.sub_window.isVisible()
    
    @classmethod
    def create_instance(cls, main_wind: QMainWindow = None) -> "LogWindow":
        """
        Create a new instance of LogWindow if it doesn't exist
        """
        if cls._instance is None:
            cls._instance = LogWindow(main_wind)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "LogWindow":
        """
        return the singleton instance of LogWindow
        """
        return cls._instance

    def __init__(self, main_wind: QMainWindow = None):
        print("[LogWindow].__init__")
        if LogWindow._instance is not None:
            raise Exception("Only one instance of LogWindow is allowed")
        super().__init__()

        LogWindow._instance = self
        self.main_wind: QMainWindow = main_wind

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas; font-size: 12px;")
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)  # Disable line wrapping
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.log_text.setMaximumSize(800, 400)  # Set maximum size
        
        # layout = QHBoxLayout()
        # layout.addWidget(self.log_text)
        # # # enable layout expanding in all directions
        # # # layout.setStretch(2, 1)

        # # # bottom_layout.addWidget(self.clear_btn)
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.setLayout(layout)

        # create a new subwindow
        self.sub_window = QMdiSubWindow()
        self.sub_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sub_window.setWindowTitle("Log Window")
        self.sub_window.setWindowIconText("Log Window")  # Set window icon text
        self.sub_window.setWidget(self.log_text)  # Set the widget to be the log window
        self.sub_window.setWindowIconText("Log Window")  # Set window icon text
        self.sub_window.setWindowFlags(Qt.Window)  # Set window flags to make it a top-level window
        self.sub_window.setWindowModality(Qt.ApplicationModal)  # Set window modality to application modal
        # sizing the subwindow
        self.sub_window.resize(800, 400)
        self.sub_window.setMinimumSize(400, 200)  # Set minimum size
        self.sub_window.setAttribute(Qt.WA_DeleteOnClose, True)  # Enable deletion on close
        self.sub_window.destroyed.connect(lambda subwindow: (setattr(self, 'sub_window', None), self._on_subwindow_closed()))

        # show the subwindow in the main window's MDI area
        self.sub_window.raise_()  # Bring the subwindow to the front
        self.sub_window.activateWindow()  # Activate the subwindow
        self.sub_window.setFocus()  # Set focus to the subwindow
        
        self.main_wind.mdi_area.addSubWindow(self.sub_window)
        self.sub_window.show()
        
        self.info("Log window created.")
        self.error("Log window created.")
        self.debug("Log window created.")
        self.warning("Log window created.")
        self.critical("Log window created.")
        self.exception("Log window created.")
        self.text("Log window created.")


    def _on_subwindow_closed(self):
        """
        Called when the QMdiSubWindow is destroyed—
        cleans up the LogWindow singleton and widget.
        """
        if self.log_text is not None:
            self.log_text.deleteLater()
            self.log_text = None
        LogWindow._instance = None
        if self.sub_window is not None:
            self.sub_window.close()
            self.sub_window.deleteLater()
            self.sub_window = None
        # Reset the singleton instance
        LogWindow._instance = None
        # if hasattr(self, 'deleteLater'):
        #     self.deleteLater()
        print("[LogWindow] subwindow closed, instance reset.")

    def __del__(self):    
        if LogWindow._instance is not None:
            self._on_subwindow_closed()
        # clean up in base class
        if hasattr(super(), '__del__'):
            super().__del__()
        print("[LogWindow].__del__")
        
    def closeEvent(self, event):
        """
        Override the close event to handle the window closing.
        """
        self.__del__()
        event.accept()
        
    def append_log(self, message: str, level: str = "INFO"):
        """Append a log message to the log window."""
        # wrap message after 500 characters
        level = level.lower()
        color = self._color_map.get(level, "white")

        # if len(message) > 100:
        #     # Wrap the message to fit within 100 characters per line
        #     words = message.split()
        #     chunks = [" ".join(words[i:i+100]) for i in range(0, len(words), 100)]
        #     wrapped = "\n".join(chunks)
        #     print(wrapped)
        #     message = wrapped
            
        timestamp = time.strftime("%H:%M:%S")
        # Replace \n, \r, \n\r with <br> for HTML formatting
        message = message.replace("\r\n", "<br>").replace("\r", "<br>").replace("\r", "<br>")
        message = message.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")  # Replace tabs with spaces for HTML
        message = message.replace(" ", "&nbsp;")  # Replace spaces with non-breaking spaces for HTML
        # Format the message with timestamp and color
        formatted_msg = f"[{timestamp}] <span style=\"color:{color};\">[{level.upper()}] {message}</span>"
        self.log_text.append(formatted_msg)
        self.enforce_log_size_limit()

    def enforce_log_size_limit(self):
        current_text = self.log_text.toPlainText()
        if len(current_text.encode('utf-8')) > MAX_LOG_SIZE_LOG_WINDOW:
            # Keep only the last 25% of the text
            trimmed = current_text[-MAX_LOG_SIZE_LOG_WINDOW // 4:]
            self.log_text.clear()
            self.log_text.append(trimmed)
            # make sure the cursor is at the end of the text
            self.log_text.moveCursor(QTextCursor.End)
            # make sure the cursor is visible
            self.log_text.ensureCursorVisible()

    def clear_log(self):
        self.log_text.clear()

    @classmethod
    def get_log_window(cls) -> QTextEdit:
        if cls._instance is not None:
            return cls._instance.log_text
        return None
    
    @classmethod
    def text(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "TEXT")
    
    @classmethod
    def error(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "ERROR")

    @classmethod
    def info(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "INFO")

    @classmethod
    def debug(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "DEBUG")

    @classmethod
    def warning(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "WARNING")

    @classmethod
    def critical(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "CRITICAL")
    
    @classmethod
    def exception(cls, message: str):
        if not LogWindow.is_inited():
            return
        cls.get_instance().append_log(message, "EXCEPTION")
        

### Static Methods

@staticmethod
def ClearLogWindow():
    log_window = LogWindow.get_instance()
    if log_window is not None:
        log_window.clear_log()
    
@staticmethod
def logToWindow(module_name: str, message: str):
    log_window = LogWindow.get_instance()
    if log_window is not None:
        log_window.append_log(f"{module_name}: {message}")
    # log_window.show()
    # log_window.raise_()
    # log_window.activateWindow()
    # log_window.setFocus()
    # log_window.show()



def test_log_window():
    log_window = LogWindow.get_instance()
    log_window.show()
    log_window.append_log("This is a test message.")
    log_window.append_log("This is another test message.")
    log_window.append_log("This is a test message with a long text to check the size limit." * 10)




# class EnhancedLogWindow(LogWindow):
#     """
#     Enhanced LogWindow with batch operations and better performance
    
#     This extends the existing LogWindow class with additional features
#     """
    
#     def __init__(self, main_wind=None):
#         super().__init__(main_wind)
        
#         # Batch operation support
#         self._batch_timer = None
#         self._pending_messages = []
#         self._batch_lock = threading.Lock()
    
#     def append_log_batch(self, messages: List[Dict[str, Any]]):
#         """
#         Append multiple log messages in a batch for better performance
        
#         Args:
#             messages: List of message dictionaries
#         """
#         with self._batch_lock:
#             self._pending_messages.extend(messages)
            
#             # Schedule batch update
#             if not self._batch_timer:
#                 from PyQt5.QtCore import QTimer
#                 self._batch_timer = QTimer()
#                 self._batch_timer.timeout.connect(self._process_batch)
#                 self._batch_timer.start(50)  # 50ms batch interval
    
#     def _process_batch(self):
#         """Process pending messages in batch"""
#         with self._batch_lock:
#             if not self._pending_messages:
#                 return
            
#             messages = self._pending_messages[:100]  # Process up to 100 at a time
#             self._pending_messages = self._pending_messages[100:]
        
#         # Process messages
#         for msg_data in messages:
#             timestamp = msg_data['timestamp'].strftime("%H:%M:%S")
#             level = msg_data['level_name']
#             message = msg_data['message']
#             color = msg_data.get('color', 'white')
            
#             # Format and append
#             formatted_msg = f"[{timestamp}] <span style=\"color:{color};\">[{level}] {message}</span>"
#             self.log_text.append(formatted_msg)
        
#         # Ensure size limit
#         self.enforce_log_size_limit()
        
#         # Stop timer if no more messages
#         with self._batch_lock:
#             if not self._pending_messages and self._batch_timer:
#                 self._batch_timer.stop()
#                 self._batch_timer = None
    
#     def set_filter(self, filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None):
#         """
#         Set a filter function for messages
        
#         Args:
#             filter_func: Function that returns True to display message
#         """
#         self._filter_func = filter_func
    
#     def clear_with_pattern(self, pattern: str):
#         """
#         Clear messages matching a pattern
        
#         Args:
#             pattern: Regex pattern to match messages
#         """
#         import re
#         current_html = self.log_text.toHtml()
#         lines = current_html.split('<br>')
#         filtered_lines = [line for line in lines if not re.search(pattern, line)]
#         self.log_text.setHtml('<br>'.join(filtered_lines))