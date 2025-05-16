from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, QMainWindow, QSizePolicy, QHBoxLayout, QLabel
)

from PyQt5.QtGui import (QTextCursor, QIntValidator)

from PyQt5.QtCore import Qt
import time



MAX_LOG_SIZE_LOG_WINDOW = 10 * 1024 * 1024  # 10 MB



class LogWindow(QWidget):
    _instance = None

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
        color = "white"
        if level == "info":
            color = "green"
        elif level == "warning":
            color = "yellow"
        elif level in ("error", "err"):
            color = "red"
        elif level == "debug":
            color = "blue"
        elif level == "critical":
            color = "orange"
        elif level == "exception":
            color = "red"

        # if len(message) > 100:
        #     # Wrap the message to fit within 100 characters per line
        #     words = message.split()
        #     chunks = [" ".join(words[i:i+100]) for i in range(0, len(words), 100)]
        #     wrapped = "\n".join(chunks)
        #     print(wrapped)
        #     message = wrapped
            
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] <span style=\"color:{color};\">[{level.upper()}] {message}</span><br>"
        self.log_text.append(formatted_msg)
        self.enforce_log_size_limit()

    def enforce_log_size_limit(self):
        current_text = self.log_text.toPlainText()
        if len(current_text.encode('utf-8')) > MAX_LOG_SIZE_LOG_WINDOW:
            # Keep only the last 25% of the text
            trimmed = current_text[-MAX_LOG_SIZE_LOG_WINDOW // 4:]
            self.log_text.clear()
            self.log_text.append(trimmed)
            self.log_text.moveCursor(QTextCursor.End)

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
