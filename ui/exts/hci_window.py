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

from transports.transport import Transport

from utils.Exceptions import *

from .connect_window import ConnectionDialog


# @todo method to log window need to shift to logger only 
from ui.exts.log_window import LogWindow
from hci.cmd.cmd_parser import hci_cmd_parse_from_bytes



class HCIControl(QWidget):
    """
        A singleton class to manage the HCI Control UI and its instances.
        have to see how to manage the create, destroy, and update of the instances.
    """
    _connect_window_instance = None
    hci_window_instance : list[HCIControlUI] = []
    _instance = None
    _main_window = None
    _transport = None
    
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
        cls.create_connect_window(main_window)
        
    @classmethod
    def create_connect_window(cls, main_window: QMainWindow = None) -> None:
        """
        Create a new instance of ConnectWindow if it doesn't exist
        """
        # no need to handle this as user cant touch anything while connect window is open
        # if cls._connect_window_instance is not None and cls._connect_window_instance.isVisible():
        #     cls._connect_window_instance.raise_()
        #     cls._connect_window_instance.activateWindow()
        #     return
        
        # create a new instance of ConnectionDialog
        cls._main_window = main_window
        cls._connect_window_instance = ConnectionDialog(main_window)
        cls._connect_window_instance.connection_done_signal.connect(HCIControl.create_new_instance)
        cls._connect_window_instance.show()

    @classmethod
    def check_transport_exists(cls, transport: Transport) -> bool:
        """
        Check if the transport instance already exists
        """
        if transport is None:
            return False
        for instance in cls.hci_window_instance:
            if instance.transport == transport:
                return True
        return False
    
    @classmethod
    def get_HCIControlUI(cls, transport: Transport) -> HCIControlUI:
        """
        Get the HCIControlUI instance for the given transport
        """
        if transport is None:
            raise ValueError("Transport must be provided to get HCIControlUI instance.")
        
        for instance in cls.hci_window_instance:
            if instance.transport == transport:
                return instance
        
        raise ValueError(f"No HCIControlUI instance found for transport: {transport.name}")
    
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


    @staticmethod
    def create_new_instance(transport: Transport):
        """ 
        Create a new instance of HCIControlUI with the provided transport
        """
        def log_window(data : bytes) -> None:
            try:
                print(f"[ConnectWindow] log_window {data}")
                LogWindow.info(f"{transport.name}->" + str(hci_cmd_parse_from_bytes(data)))
            except Exception as e:
                LogWindow.error(f"Error parsing HCI command: {e}")
                import traceback
                print(traceback.format_exc())
            
        print(f"[ConnectWindow] create_new_instance {transport} name {transport.name}")
        if HCIControl._main_window is None:
            raise ValueError("Main window must be set before creating a new instance.")
        if transport is None:
            raise ValueError("Transport must be provided to create a new instance.")
        # Ensure the main window is set before creating an instance
        name = transport.name
        
        if HCIControl.check_transport_exists(transport):
            # if the instance already exists, just raise the window
            HCIControl.get_HCIControlUI(transport).show_window()
        else :
        # add the read callback to print the data
            transport.add_callback('write',lambda data : (log_window(data),transport.read(200)))
            instance = HCIControlUI(HCIControl._main_window, transport, name)
            instance.register_destroy(lambda: HCIControl.remove_instance(instance))
            HCIControl.hci_window_instance.append(instance)
            print(f"[ConnectWindow] create_instance {instance}")
        
        HCIControl._main_window = None  # Reset main window after creating instance
        HCIControl._connect_window_instance = None  # Reset connect window after creating instance

