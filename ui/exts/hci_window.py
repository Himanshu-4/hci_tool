from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QMdiSubWindow, 
    QMainWindow, QSizePolicy, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QSpacerItem,
    QCheckBox, QListWidget, QListWidgetItem, QGridLayout
)

from PyQt5.QtGui import (QTextCursor, QIntValidator)

from PyQt5.QtCore import Qt

from ui.hci_ui import HCIControlUI

# from ui.cmds import (cmds)

# from transport.trans_lib import (transport, transport_type)

from utils.Exceptions import *

from .connect_window import ConnectionDialog




class HCIControl(QWidget):
    _connect_window_instance = None
    hci_window_instance = []
    _instance = None
    """
        A singleton class to manage the HCI Control UI and its instances.
        have to see how to manage the create, destroy, and update of the instances.
    """
    
    @classmethod
    def is_inited(cls):
        return False if cls._instance is None else True

    @classmethod
    def is_open(cls):
        """
        Check if the ConnectWindow is open
        """
        return cls._instance is not None and cls._instance.sub_window.isVisible()
    
    @classmethod
    def create_instance(cls, main_window: QMainWindow = None) -> None:
        """
        Create a new instance of ConnectWindow if it doesn't exist
        """
        # if cls._instance is None:
        #     cls._instance = ConnectWindow(main_wind)
        # return cls._instance
        # instance = ConnectionDialog(main_window)
        name = f"ConnectWindow_{len(cls.hci_window_instance)}"
        instance = HCIControlUI(main_window, name)
        instance.register_destroy(lambda: cls.remove_instance(instance))
        cls.hci_window_instance.append(instance)
        print(f"[ConnectWindow] create_instance {instance}")
        
    
    @classmethod
    def get_instance(cls):
        """
        return the singleton instance of ConnectWindow
        """
        return cls._instance
    
    @classmethod
    def remove_instance(cls, instance):
        """
        remove the singleton instance of ConnectWindow
        """
        print(f"[ConnectWindow] remove_instance {instance}")
        if instance in cls.hci_window_instance:
            cls.hci_window_instance.remove(instance)
        del instance
