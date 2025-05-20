"""
HCI SubWindow Module

This module defines an MDI subwindow class that can be used in the HCI tool UI.
It provides a container for HCI-related UI components and handles window management.
"""

from PyQt5.QtWidgets import QMdiSubWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent

class HciSubWindow(QMdiSubWindow):
    """
    A customized MDI subwindow for the HCI tool.
    
    This class provides a standardized container for HCI UI components, with consistent
    window behavior, styling, and lifecycle management.
    """
    
    # Signal emitted when the window is closed
    closed = pyqtSignal(str)  # Emits the window title
    
    def __init__(self, widget: QWidget = None, window_title: str = "", parent=None):
        """
        Initialize the HCI SubWindow.
        
        Args:
            widget: The main widget to display in the subwindow
            window_title: The title for the window
            parent: The parent widget
        """
        super().__init__(parent)
        
        # Save the title for reference
        self.window_title = window_title
        
        # Set window properties
        self.setWindowTitle(window_title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        self.windowIconText(window_title)  # Set window icon text
        
        # Configure the layout if a widget is provided
        if widget:
            self.setWidget(widget)
        
        # Default size
        self.resize(600, 400)
    
    def closeEvent(self, event: QCloseEvent):
        """
        Handle the window close event.
        
        Args:
            event: The close event
        """
        # Emit the closed signal with the window title
        self.closed.emit(self.window_title)
        
        # Call the parent class closeEvent
        super().closeEvent(event)
    
    def maximize(self):
        """
        Maximize the subwindow.
        """
        self.setWindowState(Qt.WindowMaximized)
    
    def restore(self):
        """
        Restore the window to its normal state.
        """
        self.setWindowState(Qt.WindowNoState)
    
    def center_in_parent(self):
        """
        Center the window within its parent MDI area.
        """
        if self.parentWidget():
            parent_rect = self.parentWidget().rect()
            self_rect = self.rect()
            
            x = (parent_rect.width() - self_rect.width()) // 2
            y = (parent_rect.height() - self_rect.height()) // 2
            
            self.move(x, y)
