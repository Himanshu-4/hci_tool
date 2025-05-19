
# HCI Tool README

## Overview
This HCI tool provides command line and UI interface  for Bluetooth Host commands and events interfce . One common use case is creating an LE connection and obtaining detailed packet information, testing throughput, testing controller functionality like A2DP, sco, HID, throughput etc.

## Example Usage

```python
import hci.cmd as hci_cmd

# Create an LE Set Advertising Parameters command
cmd = hci_cmd.le_cmds.le_set_adv_params(
    adv_interval_min=0x0020,
    adv_interval_max=0x0040,
    adv_type=hci_cmd.le_cmds.AdvertisingType.ADV_IND
)

# Convert to bytes for sending to a device
bytes_data = cmd.to_bytes()

trasnp.send_cmd(bytes_data)
# Print the complete packet information.
print(pkt)

rsp = transp.w4_rsp(timeout)

# Access the data contained in the packet.
rsp.data
```

## Instructions
1. Ensure required dependencies are installed.
2. Modify `params` with valid connection settings.
3. Run the script in a Python environment.
4. Use the output for debugging or further processing.

For further details, consult the project's documentation.



@todo

-------------- main in hci library 
----> evt handler have different codes like LE_META event and they have subcode after that 
----> status complete event should be handled in all the status complete and command complete event

1. async file handler, run this handler in event loop, file handler should have minmal latency in fileIO and be very responsive
2. event loop library of  creating new event loop and handle async codes, handle callbacks, stop, close, destroy evt loop with destroy callbacks of all task are running on the event loop
3. async transport layer that will handle the serial api or other transport api in async manner to make ui responsive 
4. async logger library the library will be used to handle the modules logging 
5. app.conf file for handling the app related configuration and that also we can enable, disable, configure logger objects of other module
6. creating a throughput_test.py, HID, A2DP, SCO, tests
7. checking if all the module logging on terminal, files are proper


===================== application run time analysis is pending, what impact it put on system in terms on memory and CPU utilistation