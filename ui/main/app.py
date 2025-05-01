import sys

from PyQt5.QtCore import (Qt)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMdiArea, QMdiSubWindow,
    QLabel, QWidget, QVBoxLayout, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QGridLayout, QSpacerItem,
    QCheckBox, QListWidget, QSizePolicy, QListWidgetItem
)

# from ..exts import (a2dp_test, diagnostic, hci_control, hid_test,
#                           le_iso_test, sco_test, throughput_test, firmware_download,
#                           config_chip, log_window, util_screen)

from ..exts.a2dp_test import *
# from ..exts.diagnostic import Diagnostic
# from ..exts.hci_control import HCIControl
# from ..exts.hid_test import HIDTest
# from ..exts.le_iso_test import LEISOTEST
# from ..exts.sco_test import SCOTest
# from ..exts.throughput_test import ThroughputTest
# from ..exts.firmware_download import FirmwareDownload
# from ..exts.config_chip import ConfigChip
# from ..exts.log_window import LogWindow
# from ..exts.util_screen import UtilScreen

from utils import ( logger, version, )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Blue Tool")
        self.setWindowIconText("Blue Tool")
        self.setGeometry(100, 100, 800, 600)

        # MDI Area
        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Menu Bar
        self.menu_bar = self.menuBar()

        # Menus
        self.create_menu("File", ["New", "Open log", "Save log"])
        self.create_menu("Edit", [ "Copy", "Find", "Find Next", "Find Previous", "save app log" ])
        self.create_menu("View", ["Zoom In", "Zoom Out", "Log Window", "clear log"])
        self.create_menu("Tools", ["HCI", "Diagnostics", "Throughput Test", "SCO Test", "LE ISO Test", "HID Test", "A2DP Test", "Firmware Download", "config chip"])
        self.create_menu("Window", ["Close All", "exit"])
        self.create_menu("Help", ["About","Paths" ,"Documentation"])

    def create_menu(self, menu_name, actions):
        menu = self.menu_bar.addMenu(menu_name)
        for action_name in actions:
            action = QAction(action_name, self)
            action.triggered.connect(lambda checked, name=action_name: self.open_child_window(name))
            menu.addAction(action)

    def open_child_window(self, title):
        sub = QMdiSubWindow()
        sub.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close
        sub.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if title == "HCI":
            sub.setWidget(StartChildWindow(title))
        else:
            sub.setWidget(ChildWindow(title))
        sub.setWindowTitle(title)
        self.mdi_area.addSubWindow(sub)
        sub.show()


class ChildWindow(QWidget):
    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        layout = QVBoxLayout()
        label = QLabel(f"This is the {title} window.")
        layout.addWidget(label)
        self.setLayout(layout)
        self.setStyleSheet("background-color: lightblue;")  # Set background color
        self.setWindowIconText(title)  # Set window icon text
        self.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close



class StartChildWindow(QWidget):
    def __init__(self, title):
        super().__init__()
        self.setMinimumSize(200, 600)
        layout = QVBoxLayout()

        # Toggle boxes
        self.toggle1 = QCheckBox("Enable Feature A")
        self.toggle2 = QCheckBox("Enable Feature B")
        layout.addWidget(self.toggle1)
        layout.addWidget(self.toggle2)

        # List with 8 items
        self.combo_box = QComboBox()
        for i in range(1, 9):
            self.combo_box.addItem(f"Option {i}")
        layout.addWidget(self.combo_box)

        # Label display area
        self.label_area = QLabel("Select an item to display its info here.")
        self.label_area.setWordWrap(True)
        layout.addWidget(self.label_area)

        # Connect signal
        self.combo_box.currentTextChanged.connect(lambda text: self.label_area.setText(f"Details for {text} displayed below."))

        self.setLayout(layout)
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.setStyleSheet("background-color: lightblue;")  # Set background color
        self.setWindowIconText(title)  # Set window icon text
        self.setAttribute(Qt.WA_DeleteOnClose)  # Enable deletion on close


    def on_item_selected(self, current, previous):
        if current:
            self.label_area.setText(f"Details for {current.text()} displayed below.")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())