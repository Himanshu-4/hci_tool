
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



