import sys
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit, QLabel, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal

# Basic HCI Decoder
def decode_hci_event(data):
    if data[0] == 0x04:  # HCI Event Packet
        event_code = data[1]
        length = data[2]
        return f"HCI Event: Code=0x{event_code:02X}, Length={length}, Data={data[3:3+length].hex()}"
    return f"Unknown Packet: {data.hex()}"

def decode_hci_command(data):
    if data[0] == 0x01:  # HCI Command Packet
        opcode = data[1] | (data[2] << 8)
        length = data[3]
        return f"HCI Command: Opcode=0x{opcode:04X}, Length={length}, Data={data[4:4+length].hex()}"
    return f"Unknown Packet: {data.hex()}"

# Serial Thread
class SerialReaderThread(QThread):
    data_received = pyqtSignal(bytes)

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.running = True

    def run(self):
        while self.running:
            if self.serial_port.in_waiting:
                data = self.serial_port.read(self.serial_port.in_waiting)
                self.data_received.emit(data)

    def stop(self):
        self.running = False
        self.wait()

# GUI App
class BTControllerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BT Controller Command Tool")
        self.setGeometry(200, 200, 600, 400)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.port_selector = QComboBox()
        self.refresh_ports()
        self.layout.addWidget(QLabel("Select COM Port"))
        self.layout.addWidget(self.port_selector)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        self.layout.addWidget(self.connect_button)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter HCI Command in hex (e.g., 01030C00)")
        self.layout.addWidget(self.command_input)

        self.send_button = QPushButton("Send Command")
        self.send_button.clicked.connect(self.send_command)
        self.layout.addWidget(self.send_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)

        self.serial_port = None
        self.reader_thread = None

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_selector.clear()
        for port in ports:
            self.port_selector.addItem(port.device)

    def connect_serial(self):
        port_name = self.port_selector.currentText()
        try:
            self.serial_port = serial.Serial(port_name, baudrate=115200, timeout=0.1)
            self.reader_thread = SerialReaderThread(self.serial_port)
            self.reader_thread.data_received.connect(self.handle_data)
            self.reader_thread.start()
            self.log_output.append(f"[INFO] Connected to {port_name}")
        except Exception as e:
            self.log_output.append(f"[ERROR] Could not open port: {e}")

    def send_command(self):
        hex_input = self.command_input.text()
        try:
            data = bytes.fromhex(hex_input)
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(data)
                decoded = decode_hci_command(data)
                self.log_output.append(f">>> {decoded}")
            else:
                self.log_output.append("[ERROR] Serial port not connected")
        except ValueError:
            self.log_output.append("[ERROR] Invalid hex input")

    def handle_data(self, data):
        decoded = decode_hci_event(data)
        self.log_output.append(f"<<< {decoded}")

    def closeEvent(self, event):
        if self.reader_thread:
            self.reader_thread.stop()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BTControllerApp()
    window.show()
    sys.exit(app.exec_())
