

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QLabel, QCheckBox, QComboBox, QSizePolicy)


class A2DPTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A2DP Test")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIconText("A2DP Test")
        self.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: lightblue;")
        
        