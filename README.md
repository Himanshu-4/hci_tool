
# HCI Tool README

## Overview
This HCI tool provides commands for Bluetooth LE operations. One common use case is creating an LE connection and obtaining detailed packet information.

## Example Usage

```python
# Create a connection using the HCI command with appropriate parameters.
pkt = hci.cmd.le_cmds.le_create_connection(params)

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