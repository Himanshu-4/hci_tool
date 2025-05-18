"""
Example usage of the HCI library - Event-driven approach

This example demonstrates an event-driven approach to using the HCI library.
It shows how to set up a packet handler and process incoming events from a Bluetooth controller.
"""

import hci
import hci.cmd as hci_cmd
import hci.evt as hci_evt
from hci.cmd.le_cmd import AdvertisingType, AddressType
from hci.evt.error_codes import StatusCode
import time
import queue
import threading

# Simulated transport layer
class FakeHciTransport:
    def __init__(self):
        self.recv_queue = queue.Queue()
        self.packet_handler = None
        self.running = False
        self.thread = None
    
    def open(self):
        """Open the transport layer"""
        self.running = True
        self.thread = threading.Thread(target=self._process_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def close(self):
        """Close the transport layer"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def send(self, data):
        """Send data to the controller"""
        # Simulate sending to controller
        print(f">>> Sending: {data.hex()}")
        
        # For demonstration, simulate a response based on the command
        if len(data) >= 3:  # Ensure we have a complete command
            packet_type = data[0]
            if packet_type == hci.HciPacketType.COMMAND:
                opcode = (data[2] << 8) | data[1]  # Little-endian opcode
                
                # Simulate Command Complete event
                if opcode == hci_cmd.controller_baseband.Reset.OPCODE:
                    # Handle Reset command with Command Complete event
                    self._simulate_response_reset()
                elif opcode == hci_cmd.le_cmds.LeSetAdvParams.OPCODE:
                    # Handle LE Set Advertising Parameters command with Command Complete event
                    self._simulate_response_le_set_adv_params()
                elif opcode == hci_cmd.le_cmds.LeSetAdvData.OPCODE:
                    # Handle LE Set Advertising Data command with Command Complete event
                    self._simulate_response_le_set_adv_data()
                elif opcode == hci_cmd.le_cmds.LeSetScanEnable.OPCODE:
                    # Handle LE Set Scan Enable command with Command Complete event
                    self._simulate_response_le_set_scan_enable()
                    # If scan is enabled, simulate some advertising reports
                    if data[4] == 0x01:  # Check scan_enable parameter
                        threading.Timer(0.5, self._simulate_le_adv_report).start()
    
    def register_packet_handler(self, handler):
        """Register a packet handler function"""
        self.packet_handler = handler
    
    def _process_loop(self):
        """Process incoming data"""
        while self.running:
            try:
                data = self.recv_queue.get(timeout=0.1)
                if self.packet_handler:
                    self.packet_handler(data)
            except queue.Empty:
                pass
    
    def _queue_event(self, event_data):
        """Queue an event for processing"""
        self.recv_queue.put(bytes([hci.HciPacketType.EVENT]) + event_data)
    
    def _simulate_response_reset(self):
        """Simulate response to Reset command"""
        # Create Command Complete event for Reset
        event = hci_evt.common_events.CommandCompleteEvent(
            num_hci_command_packets=1,
            command_opcode=hci_cmd.controller_baseband.Reset.OPCODE,
            return_parameters=bytes([StatusCode.SUCCESS])
        )
        self._queue_event(event.to_bytes())
    
    def _simulate_response_le_set_adv_params(self):
        """Simulate response to LE Set Advertising Parameters command"""
        # Create Command Complete event for LE Set Advertising Parameters
        event = hci_evt.common_events.CommandCompleteEvent(
            num_hci_command_packets=1,
            command_opcode=hci_cmd.le_cmds.LeSetAdvParams.OPCODE,
            return_parameters=bytes([StatusCode.SUCCESS])
        )
        self._queue_event(event.to_bytes())
    
    def _simulate_response_le_set_adv_data(self):
        """Simulate response to LE Set Advertising Data command"""
        # Create Command Complete event for LE Set Advertising Data
        event = hci_evt.common_events.CommandCompleteEvent(
            num_hci_command_packets=1,
            command_opcode=hci_cmd.le_cmds.LeSetAdvData.OPCODE,
            return_parameters=bytes([StatusCode.SUCCESS])
        )
        self._queue_event(event.to_bytes())
    
    def _simulate_response_le_set_scan_enable(self):
        """Simulate response to LE Set Scan Enable command"""
        # Create Command Complete event for LE Set Scan Enable
        event = hci_evt.common_events.CommandCompleteEvent(
            num_hci_command_packets=1,
            command_opcode=hci_cmd.le_cmds.LeSetScanEnable.OPCODE,
            return_parameters=bytes([StatusCode.SUCCESS])
        )
        self._queue_event(event.to_bytes())
    
    def _simulate_le_adv_report(self):
        """Simulate LE Advertising Report event"""
        # Create fake advertising data
        adv_data = bytes([
            0x02, 0x01, 0x06,  # Flags: LE General Discoverable Mode, BR/EDR Not Supported
            0x07, 0x09, 0x53, 0x69, 0x6D, 0x44, 0x65, 0x76  # Complete Local Name: "SimDev"
        ])
        
        # Create LE Advertising Report event
        event = hci_evt.le_events.LeAdvertisingReportEvent(
            num_reports=1,
            event_type=hci_evt.le_events.LeAdvertisingReportEvent.EventType.ADV_IND,
            address_type=AddressType.PUBLIC,
            address=bytes.fromhex("112233445566"),  # Example address
            data_length=len(adv_data),
            data=adv_data,
            rssi=-70
        )
        self._queue_event(event.to_bytes())
        
        # Simulate another report after a delay if still scanning
        if self.running:
            threading.Timer(2.0, self._simulate_le_adv_report).start()

class HciEventHandler:
    """Event handler for HCI events"""
    
    def __init__(self, transport):
        """Initialize with transport layer"""
        self.transport = transport
        self.devices = {}  # Dictionary to store discovered devices
    
    def handle_packet(self, data):
        """Handle incoming HCI packet"""
        if not data:
            return
        
        packet_type = data[0]
        packet_data = data[1:]
        
        if packet_type == hci.HciPacketType.EVENT:
            self._handle_event(packet_data)
    
    def _handle_event(self, event_data):
        """Handle HCI event"""
        if len(event_data) < 2:
            print("Invalid event data")
            return
        
        event_code = event_data[0]
        event = hci.evt.hci_evt_parse_from_bytes(event_data)
        
        if event is None:
            print(f"Unknown event with code: 0x{event_code:02X}")
            return
        
        print(f"<<< Received event: {event.NAME}")
        
        # Handle specific events
        if isinstance(event, hci_evt.common_events.CommandCompleteEvent):
            self._handle_command_complete(event)
        elif isinstance(event, hci_evt.common_events.CommandStatusEvent):
            self._handle_command_status(event)
        elif isinstance(event, hci_evt.common_events.LEMetaEvent):
            self._handle_le_meta_event(event)
        elif isinstance(event, hci_evt.link_control_events.DisconnectionCompleteEvent):
            self._handle_disconnection_complete(event)
    
    def _handle_command_complete(self, event):
        """Handle Command Complete event"""
        command_opcode = event.params['command_opcode']
        status = event.params['return_parameters'][0] if event.params['return_parameters'] else None
        
        print(f"  Command Complete for opcode 0x{command_opcode:04X}, status: {status if status is not None else 'unknown'}")
        
        # Handle specific commands
        if command_opcode == hci_cmd.controller_baseband.Reset.OPCODE:
            print("  Reset complete!")
            # After reset, set up advertising parameters
            self._set_advertising_parameters()
        elif command_opcode == hci_cmd.le_cmds.LeSetAdvParams.OPCODE:
            print("  Advertising parameters set!")
            # After setting parameters, set advertising data
            self._set_advertising_data()
        elif command_opcode == hci_cmd.le_cmds.LeSetAdvData.OPCODE:
            print("  Advertising data set!")
            # Start scanning for devices
            self._start_scanning()
    
    def _handle_command_status(self, event):
        """Handle Command Status event"""
        command_opcode = event.params['command_opcode']
        status = event.params['status']
        
        print(f"  Command Status for opcode 0x{command_opcode:04X}, status: {status}")
    
    def _handle_le_meta_event(self, event):
        """Handle LE Meta Event"""
        subevent_code = event.params['subevent_code']
        
        if subevent_code == hci_evt.evt_codes.LeMetaEventSubCode.ADVERTISING_REPORT:
            self._handle_le_advertising_report(event)
        elif subevent_code == hci_evt.evt_codes.LeMetaEventSubCode.CONNECTION_COMPLETE:
            self._handle_le_connection_complete(event)
    
    def _handle_le_advertising_report(self, event):
        """Handle LE Advertising Report event"""
        # Convert to the specific event class
        adv_report = hci_evt.le_events.LeAdvertisingReportEvent(
            num_reports=event.params['num_reports'],
            event_type=event.params['event_type'],
            address_type=event.params['address_type'],
            address=event.params['address'],
            data_length=event.params['data_length'],
            data=event.params['data'],
            rssi=event.params['rssi']
        )
        
        # Process the discovered device
        addr = adv_report.params['address'].hex()
        addr_type = adv_report.params['address_type']
        rssi = adv_report.params['rssi']
        data = adv_report.params['data']
        
        # Parse device name from advertising data if available
        name = None
        i = 0
        while i < len(data):
            length = data[i]
            if i + 1 + length <= len(data):
                ad_type = data[i + 1]
                if ad_type == 0x09:  # Complete Local Name
                    name = data[i + 2:i + 1 + length].decode('utf-8', errors='replace')
                    break
            i += 1 + length
        
        # Store or update device
        if addr not in self.devices:
            self.devices[addr] = {'addr_type': addr_type, 'rssi': rssi, 'name': name}
            print(f"  New device: {addr} ({name if name else 'Unknown'}), RSSI: {rssi}")
        else:
            self.devices[addr]['rssi'] = rssi
            if name and self.devices[addr]['name'] != name:
                self.devices[addr]['name'] = name
                print(f"  Updated device: {addr} ({name}), RSSI: {rssi}")
    
    def _handle_le_connection_complete(self, event):
        """Handle LE Connection Complete event"""
        print(f"  Connection complete, handle: 0x{event.params['connection_handle']:04X}")
    
    def _handle_disconnection_complete(self, event):
        """Handle Disconnection Complete event"""
        print(f"  Disconnection complete, handle: 0x{event.params['connection_handle']:04X}")
    
    def _set_advertising_parameters(self):
        """Set advertising parameters"""
        cmd = hci_cmd.le_cmds.le_set_adv_params(
            adv_interval_min=0x0020,  # 20ms
            adv_interval_max=0x0040,  # 40ms
            adv_type=AdvertisingType.ADV_IND,
            own_addr_type=AddressType.PUBLIC,
            adv_channel_map=0x07  # All channels
        )
        
        packet = bytes([hci.HciPacketType.COMMAND]) + cmd.to_bytes()
        self.transport.send(packet)
    
    def _set_advertising_data(self):
        """Set advertising data"""
        adv_data = bytes([
            0x02, 0x01, 0x06,  # Flags: LE General Discoverable Mode, BR/EDR Not Supported
            0x07, 0x09, 0x54, 0x65, 0x73, 0x74, 0x44, 0x65, 0x76  # Complete Local Name: "TestDev"
        ])
        
        cmd = hci_cmd.le_cmds.le_set_adv_data(data=adv_data)
        packet = bytes([hci.HciPacketType.COMMAND]) + cmd.to_bytes()
        self.transport.send(packet)
    
    def _start_scanning(self):
        """Start scanning for devices"""
        cmd = hci_cmd.le_cmds.le_set_scan_enable(
            scan_enable=True,
            filter_duplicates=True
        )
        packet = bytes([hci.HciPacketType.COMMAND]) + cmd.to_bytes()
        self.transport.send(packet)
        print("Starting scan for devices...")
    
    def initialize(self):
        """Initialize the controller"""
        # Send Reset command
        cmd = hci_cmd.controller_baseband.reset()
        packet = bytes([hci.HciPacketType.COMMAND]) + cmd.to_bytes()
        self.transport.send(packet)
        print("Initializing HCI controller...")

def main():
    # Create transport and event handler
    transport = FakeHciTransport()
    handler = HciEventHandler(transport)
    
    # Register packet handler
    transport.register_packet_handler(handler.handle_packet)
    
    # Open transport
    if not transport.open():
        print("Failed to open transport")
        return
    
    # Initialize controller
    handler.initialize()
    
    try:
        # Run for 10 seconds
        print("Running HCI example (Ctrl+C to exit)...")
        time.sleep(10)
        
        # Print discovered devices
        print("\nDiscovered devices:")
        for addr, device in handler.devices.items():
            print(f"  {addr}: {device['name'] if device['name'] else 'Unknown'}, RSSI: {device['rssi']}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Close transport
        transport.close()

if __name__ == "__main__":
    main()