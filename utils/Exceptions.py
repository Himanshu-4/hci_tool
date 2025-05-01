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

from logger import logger.terminal as log


class CustomException(Exception):
    """
    Base class for all custom exceptions in the application.
    """
    pass

class FileNotFoundError(CustomException):
    """
    Exception raised when a file is not found.

    Attributes:
        filename -- name of the file that was not found
    """

    def __init__(self, filename):
        self.filename = filename
        super().__init__(f"File '{filename}' not found.")
        
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