""""
Logger module for Nordic Semiconductor Sniffer
This module provides functionality for logging messages to a file and console.
It includes:
- Custom loggers for different modules
- Log rotation and file handling
- Custom log filters to enable/disable logging for specific modules
- GUI log handler for displaying logs in a GUI window
- Example usage of the logger
- Test function to demonstrate logger functionality
- Custom exceptions for file handling
"""


import time, os, logging, sys
from datetime import datetime
import traceback, threading
import logging.handlers as logHandlers


#create a Union to hold the log_levels and mapped that to loggign levels
from typing import Union
from enum import Enum

class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    NOTSET = logging.NOTSET
    # Add more log levels as needed

# Map string log levels to logging module levels
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "NOTSET": logging.NOTSET
}
# Map logging module levels to string log levels



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


def setLogFileName(log_file_path):
    global logFileName
    logFileName = os.path.abspath(log_file_path)


# Ensure that the directory we are writing the log file to exists.
# Create our logfile, and write the timestamp in the first line.
def initLogger():
    try:
        global logFileName
        if logFileName is None:
            logFileName = os.path.join(DEFAULT_LOG_FILE_DIR, DEFAULT_LOG_FILE_NAME)

        # First, make sure that the directory exists
        if not os.path.isdir(os.path.dirname(logFileName)):
            os.makedirs(os.path.dirname(logFileName))

        # If the file does not exist, create it, and save the timestamp
        if not os.path.isfile(logFileName):
            with open(logFileName, "w") as f:
                f.write(str(time.time()) + str(os.linesep))

        global logFlusher
        global logHandlerArray

        logHandler = MyRotatingFileHandler(logFileName, mode='a', maxBytes=myMaxBytes, backupCount=3)
        logFormatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%d-%b-%Y %H:%M:%S (%z)')
        logHandler.setFormatter(logFormatter)
        logger = logging.getLogger()
        logger.addHandler(logHandler)
        logger.setLevel(logging.INFO)
        logFlusher = LogFlusher(logHandler)
        logHandlerArray.append(logHandler)
    except:
        print("LOGGING FAILED")
        print(traceback.format_exc())
        raise


def shutdownLogger():
    if logFlusher is not None:
        logFlusher.stop()
    logging.shutdown()


# Clear the log (typically after it has been sent on email)
def clearLog():
    try:
        logHandler.doRollover()
    except:
        print("LOGGING FAILED")
        raise "failing to clear log"


# Returns the timestamp residing on the first line of the logfile. Used for checking the time of creation
def getTimestamp():
    try:
        with open(logFileName, "r") as f:
            f.seek(0)
            return f.readline()
    except:
        print("LOGGING FAILED")


def addTimestamp():
    try:
        with open(logFileName, "a") as f:
            f.write(str(time.time()) + os.linesep)
    except:
        print("LOGGING FAILED")


# Returns the entire content of the logfile. Used when sending emails
def readAll():
    try:
        text = ""
        with open(logFileName, "r") as f:
            text = f.read()
        return text
    except:
        print("LOGGING FAILED")


def addLogHandler(logHandler):
    global logHandlerArray
    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    logHandlerArray.append(logHandler)

def removeLogHandler(logHandler):
    global logHandlerArray
    logger = logging.getLogger()
    logger.removeHandler(logHandler)
    logHandlerArray.remove(logHandler)


class MyRotatingFileHandler(logHandlers.RotatingFileHandler):
    def doRollover(self):
        try:
            logHandlers.RotatingFileHandler.doRollover(self)
            addTimestamp()
            self.maxBytes = myMaxBytes
        except:
            # There have been permissions issues with the log files.
            self.maxBytes += int(myMaxBytes / 2)


class LogFlusher(threading.Thread):
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
        self.handler.flush()
        os.fsync(self.handler.stream.fileno())

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
    _loggers = {}
    _lock = threading.Lock()
    APP_LOG_FILE = "app.log"

    @classmethod
    def get_logger(cls, module_name, level : Union[str, LogLevel] =  LogLevel.DEBUG, *,
                   to_console=True, to_file=True, to_log_window=False,
                   description=True, prepend="", append="",
                   log_file=None, enable=True):

        with cls._lock:
            if module_name in cls._loggers:
                return cls._loggers[module_name]["logger"]

            logger = logging.getLogger(module_name)
            # Set the logger level
            if isinstance(level, str):
                level = log_level_map.get(level.upper(), logging.DEBUG)
            logger.setLevel(level)
            logger.propagate = False  # avoid double logging

            formatter = cls._get_formatter(description, prepend, append)
            module_log_file = log_file or cls.APP_LOG_FILE

            if to_console:
                ch = logging.StreamHandler(sys.stdout)
                ch.setFormatter(formatter)
                logger.addHandler(ch)

            if to_file:
                os.makedirs(os.path.dirname(module_log_file), exist_ok=True) if os.path.dirname(module_log_file) else None
                fh = logging.FileHandler(module_log_file, mode='a')
                fh.setFormatter(formatter)
                logger.addHandler(fh)

            # Optional: Hook for GUI log window
            if to_log_window:
                from ui.exts.log_window import GuiLogHandler
                gh = GuiLogHandler(module_name)
                gh.setFormatter(formatter)
                logger.addHandler(gh)

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
        if module_name in cls._loggers:
            cls._loggers[module_name]["filter"].enabled = True

    @classmethod
    def disable_module(cls, module_name):
        if module_name in cls._loggers:
            cls._loggers[module_name]["filter"].enabled = False

    @staticmethod
    def _get_formatter(include_desc, prepend, append):
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
    
    
    
    


from logging import Handler

class GuiLogHandler(Handler):
    def __init__(self, module_name):
        super().__init__()
        self.module_name = module_name

    def emit(self, record):
        msg = self.format(record)
        # Here, send to log_window (like signal or queue)
        from ui.exts.log_window import log_to_window
        log_to_window(self.module_name, msg)
        
        
    
    

def test_logger():
        # Example usage
    
    log = LoggerManager.get_logger(
        "A2DP",
        level=logging.DEBUG,
        to_console=True,
        to_file=True,
        to_log_window=False,
        description=True,
        prepend="[A2DP]",
        append="",
        log_file="logs/a2dp.log"
    )

    log.info("A2DP initialized")
    log.error("A2DP error")


    LoggerManager.disable_module("A2DP")
    LoggerManager.enable_module("A2DP")

    logger = LoggerManager.get_logger("example_module", level=logging.DEBUG)
    logger.info("This is an info message.")
    logger.debug("This is a debug message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
    logger.exception("This is an exception message.")
    logger.info("This is an info message with a timestamp.")
    logger.info("This is an info message with a timestamp.", extra={"timestamp": datetime.now()})
    
    try:
        1 / 0
    except Exception as e:
        log.error("Exception occurred", exc_info=True)
        
    
if __name__ == "__main__":
    test_logger()