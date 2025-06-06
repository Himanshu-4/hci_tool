"""
Exceptions.py

This module provides functionality for [brief description of the module's purpose].
It includes:
- used to define custom exceptions for the application
- [specific functionality, e.g., error handling, logging, etc.]
- [specific functionality, e.g., data validation, etc.]
- handle exceptions in a consistent manner across the application


Each function and class includes detailed docstrings describing parameters,
return values, exceptions raised, and usage examples.
"""

import sys
import traceback

class CustomException(Exception):
    """
    Base class for all custom exceptions in the application.
    """
    def __init__(self, message):
        super().__init__(f"Exception: {message}")
        # sys.exit(1)


####################################################################################################
## Custom Exceptions for File Handling
####################################################################################################

class CustomFileException(CustomException):
    """
    Base class for all file-related exceptions.

    Attributes:
        filename -- name of the file that caused the error
        message -- explanation of the error
    """

    def __init__(self, filename, message="An error occurred with the file."):
        self.filename = filename
        self.message = message
        super().__init__(f"{message} File: {filename}")

class CustomFileNotFoundError(CustomFileException):
    """
    Exception raised when a file is not found.

    Attributes:
        filename -- name of the file that was not found
    """

    def __init__(self, filename):
        self.filename = filename
        self.message = "File not found."
        super().__init__(filename, self.message)
    
class FileAlreadyExistsError(CustomFileException):
    """
    Exception raised when a file already exists.

    Attributes:
        filename -- name of the file that already exists
        message -- explanation of the error
    """

    def __init__(self, filename, message="File already exists."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)
     
class FileReadError(CustomFileException):
    """
    Exception raised when a file cannot be read.

    Attributes:
        filename -- name of the file that could not be read
        message -- explanation of the error
    """

    def __init__(self, filename, message="File could not be read."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)
        
class FileWriteError(CustomFileException):
    """
    Exception raised when a file cannot be written.

    Attributes:
        filename -- name of the file that could not be written
        message -- explanation of the error
    """

    def __init__(self, filename, message="File could not be written."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)

class FileProcessingError(CustomFileException):
    """
    Exception raised when a file cannot be processed.

    Attributes:
        filename -- name of the file that could not be processed
        message -- explanation of the error
    """

    def __init__(self, filename, message="File could not be processed."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)

class InvalidFileFormatError(CustomFileException):
    """
    Exception raised for invalid file format.

    Attributes:
        filename -- name of the file with invalid format
        message -- explanation of the error
    """

    def __init__(self, filename, message="Invalid file format."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)
        
class PermissionDeniedError(CustomFileException):
    """
    Exception raised when permission is denied for a file operation.

    Attributes:
        filename -- name of the file for which permission was denied
        message -- explanation of the error
    """

    def __init__(self, filename, message="Permission denied."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)
        
class FileEncodingError(CustomFileException):
    """
    Exception raised for encoding errors in file operations.

    Attributes:
        filename -- name of the file with encoding issues
        message -- explanation of the error
    """

    def __init__(self, filename, message="File encoding error."):
        self.filename = filename
        self.message = message
        super().__init__(filename, message)
####################################################################################################
## Custom Exceptions for Input Handling
####################################################################################################
        
        
class InvalidInputError(CustomException):
    """
    Exception raised for invalid input.

    Attributes:
        input_value -- the invalid input value
        message -- explanation of the error
    """

    def __init__(self, input_value, message="Invalid input provided."):
        self.input_value = input_value
        self.message = message
        super().__init__(f"{message} Input: {input_value}")
        
class InputOutOfRangeError(InvalidInputError):
    """
    Exception raised when input is out of the expected range.

    Attributes:
        input_value -- the out-of-range input value
        min_value -- minimum acceptable value
        max_value -- maximum acceptable value
        message -- explanation of the error
    """

    def __init__(self, input_value, min_value, max_value):
        self.input_value = input_value
        self.min_value = min_value
        self.max_value = max_value
        self.message = f"Input {input_value} is out of range ({min_value}, {max_value})."
        super().__init__(input_value, self.message)
        
