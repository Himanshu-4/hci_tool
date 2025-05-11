import sys

from PyQt5.QtCore import (Qt)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMdiArea, QMdiSubWindow,
    QLabel, QWidget, QVBoxLayout, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QGridLayout, QSpacerItem,
    QCheckBox, QListWidget, QSizePolicy, QListWidgetItem
)

import os
from collections import namedtuple

from ui.exts import (a2dp_test, diagnostic, hci_control, hid_test,
                          le_iso_test, sco_test, throughput_test, firmware_download,
                          config_chip, log_window, util_screen)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Blue Tool")
        self.setWindowIconText("Blue Tool")
        self.setGeometry(100, 100, 1000, 800)

        # Set the minimum size
        self.setMinimumSize(800, 600)
        # Set the maximum size
        # self.setMaximumSize(1600, 1200)
        # MDI Area
        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)

        # Menu Bar
        self.menu_bar = self.menuBar()

        # Menus
        self.create_menu("File", ["New", "Open log", "Save log"])
        self.create_menu("Edit", [ "Copy", "Find", "Find Next", "Find Previous", "save app log" ])
        self.create_menu("View", ["Zoom In", "Zoom Out", "Log Window", "clear log"])
        self.create_menu("Tools", ["HCI", "Diagnostics", "Throughput Test", "SCO Test", "LE ISO Test", "HID Test", "A2DP Test", "Firmware Download", "util screen"])
        self.create_menu("setting", ["Close All", "app setting", "config chip"])
        self.create_menu("Help", ["about","Paths" ,"Documentation"])
        
        # bind the quit action to the close event
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        self.menu_bar.addAction(quit_action)
        # Add actions to the menu bar

    def create_menu(self, menu_name, actions : list[str]):
        menu = self.menu_bar.addMenu(menu_name)
        for action_name in actions:
            action = QAction(action_name, self)
            action.triggered.connect(lambda checked, name=action_name: self.open_child_window(name))
            menu.addAction(action)

    def open_child_window(self, title : str)->None:
        """
        Open a child window based on the title.
        If the title is not found in the mapping, a default child window is opened.
        """
        # Define a simple struct‐like mapping
        ChildFactory = namedtuple('ChildFactory', ['module', 'cls_name'])
        # Define a mapping of titles to child window classes
        WINDOW_MAP = {
            "HCI":           ChildFactory(module=hci_control,    cls_name="HCIControl"),
            "Diagnostics":  ChildFactory(module=diagnostic,     cls_name="DiagnosticWindow"),
            "Throughput Test": ChildFactory(module=throughput_test, cls_name="ThroughputWindow"),
            "SCO Test":     ChildFactory(module=sco_test,        cls_name="ScoTestWindow"),
            "LE ISO Test":  ChildFactory(module=le_iso_test,     cls_name="LeIsoTestWindow"),
            "HID Test":     ChildFactory(module=hid_test,        cls_name="HidTestWindow"),
            "A2DP Test":    ChildFactory(module=a2dp_test,       cls_name="A2dpTestWindow"),
            "Firmware Download": ChildFactory(module=firmware_download, cls_name="FirmwareDownloadWindow"),
            "config chip":  ChildFactory(module=config_chip,     cls_name="ConfigChipWindow"),
            "Log Window":   ChildFactory(module=log_window,      cls_name="LogWindow"),
            "util screen":  ChildFactory(module=util_screen,     cls_name="UtilScreenWindow"),
        }
        # Define a mapping of titles to utility functions
        methodFactory = namedtuple('ChildFactory', ['module', 'func_name'])
        # also create a utility function map that maps the action name to the function
        UTILITY_MAP = {
            "app setting": methodFactory(module=util_screen, func_name="AppSettingWindow"),
            "Paths":       methodFactory(module=util_screen, func_name="PathsWindow"),
            "Documentation": methodFactory(module=util_screen, func_name="DocumentationWindow"),
            "about":       methodFactory(module=util_screen, func_name="AboutWindow"),
            "clear log":   methodFactory(module=log_window, func_name="ClearLogWindow"),
        }
        
        # --- inside MainWindow.open_child_window ---
        if title in WINDOW_MAP:
            info = WINDOW_MAP[title]
            # dynamically fetch the class from the module
            try:
                cls = getattr(info.module, info.cls_name) ## info.module.__dict__[info.cls_name]
                #invoke the create_instance method of the class
                instance_method = getattr(cls, "create_instance")
                instance_method(self)
            except Exception as e:
                print(f"Error loading {title}: {e}")
                # Optionally, you can log the error or handle it as needed
                # For example, you could write to a log file or display a message box
        elif title in UTILITY_MAP:
            info = UTILITY_MAP[title]
            # dynamically fetch the class from the module
            func = getattr(info.module, info.func_name) ## info.module.__dict__[info.cls_name]   
            func()
        else:
            # Fallback to a default child window if the title is not found
            pass
         


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




def start_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # Check if the script is being run directly
    try:
        start_app()
    except Exception as e:
        print(f"An error occurred: {e}")
        # Optionally, you can log the error or handle it as needed
        # For example, you could write to a log file or display a message box