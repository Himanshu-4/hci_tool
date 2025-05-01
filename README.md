
# HCI Tool README

## Overview
This HCI tool provides command line and UI interface  for Bluetooth Host commands and events interfce . One common use case is creating an LE connection and obtaining detailed packet information, testing throughput, testing controller functionality, etc.

## Example Usage

```python

# Create a connection using the HCI command with appropriate parameters.
pkt = hci.cmd.le_cmds.le_create_connection(params)
trasnp.send_cmd(pkt.data)
# Print the complete packet information.
print(pkt)

# Access the data contained in the packet.
pkt.data
```

## Instructions
1. Ensure required dependencies are installed.
2. Modify `params` with valid connection settings.
3. Run the script in a Python environment.
4. Use the output for debugging or further processing.

For further details, consult the project's documentation.