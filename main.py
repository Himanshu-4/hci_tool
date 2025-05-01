from utils import Utils
from transport import Transport
from hci import HCI
from ui import UI
import sys



if __name__ == "__main__":

    # initialize core components
    utils = Utils()
    transport = Transport()
    hci = HCI()
    ui_app = UI(hci, transport, utils)
    # initialize the UI
    ui_app.initUI()
    # use a system‐wide executor to launch the UI renderer
    # bind ui_app.run to sys.exec
    sys.exec = ui_app.run

    # invoke the UI via sys.exec()
    sys.exec()
