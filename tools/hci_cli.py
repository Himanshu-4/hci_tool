#!/usr/bin/env python3
"""
Headless driver for the HCI tool.

Runs the POC flows without the GUI, which makes bring-up against real hardware
far quicker to iterate on -- and lets the whole stack be exercised against the
virtual controller with no dongle attached.

Examples::

    # against a real controller
    python tools/hci_cli.py --port /dev/tty.usbserial-1 --baud 115200 scan
    python tools/hci_cli.py --port /dev/tty.usbserial-1 advertise --name "My Dev"
    python tools/hci_cli.py --port /dev/tty.usbserial-1 connect AA:BB:CC:11:22:33
    python tools/hci_cli.py --port /dev/tty.usbserial-1 inquiry --duration 8

    # against the built-in emulated controller
    python tools/hci_cli.py --virtual scan
    python tools/hci_cli.py --virtual ports
"""

from __future__ import annotations

import argparse
import os
import sys
import time

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)
sys._BASE_PATH = BASE_PATH
sys._APP_DATA_PATH = os.path.join(BASE_PATH, "app_data")
sys._APP_CONFIG_PATH = "syscfg.yml"

from hci.session import HciSession, procedures                    # noqa: E402
from hci.session.session import EVT_ERROR, EVT_PACKET, CommandError  # noqa: E402
from transports import Transport, UARTTransport                   # noqa: E402


def log(message: str) -> None:
    print(f"  {message}", flush=True)


def build_transport(args) -> Transport:
    transport = Transport.get_instance("cli")
    if args.virtual:
        transport.select_interface("VIRTUAL")
        transport.configure({"latency": 0.002})
        print("Using the emulated virtual controller (no hardware).")
    else:
        if not args.port:
            raise SystemExit("--port is required (or use --virtual)")
        transport.select_interface("UART")
        transport.configure({
            "port": args.port,
            "baudrate": args.baud,
            "rtscts": args.rtscts,
        })
        print(f"Opening {args.port} at {args.baud} baud "
              f"(rtscts={'on' if args.rtscts else 'off'})...")
    transport.connect()
    return transport


def attach_tracing(session: HciSession, level: str) -> None:
    if level == "none":
        return

    def _on_packet(raw: bytes, event) -> None:
        if level == "hex":
            print(f"    < {raw.hex(' ')}", flush=True)
        else:
            print(f"    < {event}", flush=True)

    session.on(EVT_PACKET, _on_packet)
    session.on(EVT_ERROR, lambda msg: print(f"    ! {msg}", flush=True))


def cmd_ports(_args) -> int:
    ports = UARTTransport.list_ports()
    if not ports:
        print("No serial ports found.")
        return 1
    print(f"{len(ports)} serial port(s):")
    for device, description in ports:
        print(f"  {device}\t{description}")
    return 0


def cmd_info(session: HciSession, _args) -> int:
    for key, value in session.status_summary().items():
        print(f"  {key:20} {value}")
    return 0


def cmd_scan(session: HciSession, args) -> int:
    devices = procedures.scan_le(
        session, duration=args.duration, active=not args.passive, reporter=log)
    if not devices:
        print("No LE devices found.")
        return 1
    print(f"\n{len(devices)} LE device(s):")
    for device in devices:
        print(f"  {device}")
    return 0


def cmd_advertise(session: HciSession, args) -> int:
    procedures.start_advertising(session, local_name=args.name, reporter=log)
    print(f"\nAdvertising as '{args.name}' for {args.duration:.0f}s "
          "(Ctrl-C to stop early)...")
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\ninterrupted")
    procedures.stop_advertising(session, reporter=log)
    return 0


def cmd_connect(session: HciSession, args) -> int:
    if args.bredr:
        info = procedures.connect_bredr(session, args.address, reporter=log)
    else:
        info = procedures.connect_le(
            session, args.address,
            peer_address_type=1 if args.random else 0, reporter=log)
    print(f"\nConnected: {info}")

    if args.hold:
        print(f"Holding the link for {args.hold:.0f}s...")
        try:
            time.sleep(args.hold)
        except KeyboardInterrupt:
            print("\ninterrupted")

    procedures.disconnect(session, info.handle, reporter=log)
    return 0


def cmd_inquiry(session: HciSession, args) -> int:
    devices = procedures.inquiry(session, duration_units=args.duration, reporter=log)
    if not devices:
        print("No BR/EDR devices found.")
        return 1
    print(f"\n{len(devices)} BR/EDR device(s):")
    for device in devices:
        print(f"  {device}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hci_cli", description="Headless driver for the HCI tool")
    parser.add_argument("--port", help="serial port, e.g. /dev/tty.usbserial-1")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--rtscts", action="store_true",
                        help="enable hardware flow control (recommended >115200)")
    parser.add_argument("--virtual", action="store_true",
                        help="use the emulated controller instead of hardware")
    parser.add_argument("--trace", choices=("none", "decoded", "hex"),
                        default="none", help="print received packets")
    parser.add_argument("--no-init", action="store_true",
                        help="skip the controller init sequence")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ports", help="list serial ports and exit")
    sub.add_parser("info", help="show controller information")

    p_scan = sub.add_parser("scan", help="scan for LE advertisers")
    p_scan.add_argument("--duration", type=float, default=5.0)
    p_scan.add_argument("--passive", action="store_true",
                        help="passive scan (no SCAN_REQ, so no scan responses)")

    p_adv = sub.add_parser("advertise", help="advertise as a connectable LE device")
    p_adv.add_argument("--name", default="HCI Tool")
    p_adv.add_argument("--duration", type=float, default=30.0)

    p_conn = sub.add_parser("connect", help="connect to a device, then disconnect")
    p_conn.add_argument("address", help="peer BD_ADDR, AA:BB:CC:DD:EE:FF")
    p_conn.add_argument("--bredr", action="store_true", help="BR/EDR instead of LE")
    p_conn.add_argument("--random", action="store_true",
                        help="peer uses a random LE address")
    p_conn.add_argument("--hold", type=float, default=3.0,
                        help="seconds to keep the link up")

    p_inq = sub.add_parser("inquiry", help="BR/EDR inquiry")
    p_inq.add_argument("--duration", type=int, default=8,
                       help="inquiry length in 1.28s units")

    args = parser.parse_args(argv)

    if args.command == "ports":
        return cmd_ports(args)

    transport = build_transport(args)
    session = HciSession(transport, name="cli")
    attach_tracing(session, args.trace)

    try:
        if not args.no_init:
            procedures.initialize_controller(session, reporter=log)
            print()

        handler = {
            "info": cmd_info,
            "scan": cmd_scan,
            "advertise": cmd_advertise,
            "connect": cmd_connect,
            "inquiry": cmd_inquiry,
        }[args.command]
        return handler(session, args)

    except CommandError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    finally:
        try:
            procedures.disconnect_all(session, reporter=log)
        except Exception:
            pass
        session.close()
        transport.disconnect()


if __name__ == "__main__":
    sys.exit(main())
