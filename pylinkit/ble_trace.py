#!/usr/bin/env python3
"""
Standalone BLE trace listener for RSPB boards.
This module runs in isolation to avoid conflicts with pythoncom/GUI threads.
"""

import sys
import asyncio
import signal
from bleak import BleakClient, BleakScanner, BleakError

UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # notify
RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write

# Global flag for clean shutdown
_shutdown_requested = False


async def find_rspb_device(name_filter=None):
    """Scan for RSPB/Linkit/Horizon devices."""
    print("Scanning for RSPB devices... (Press Ctrl+C to cancel)")
    while not _shutdown_requested:
        try:
            devices = await BleakScanner.discover(timeout=3.0)
            rspb_devices = []
            for d in devices:
                if d.name and ('Linkit' in d.name or 'Horizon' in d.name or 'RSPB' in d.name):
                    if name_filter is None or name_filter in d.name:
                        rspb_devices.append(d)
            if rspb_devices:
                return rspb_devices
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Scan error: {e}")
            await asyncio.sleep(2)
    return []


async def ble_trace_terminal(device_address):
    """Main BLE trace listener."""
    global _shutdown_requested
    client = None

    while not _shutdown_requested:
        try:
            print(f"\nConnecting to {device_address}...")
            client = BleakClient(device_address, timeout=10.0)
            await client.connect()

            print(f"Connected to {device_address}")
            print("\n=== BLE Trace Listener Active ===")
            print("Press Ctrl+C to stop\n")

            def handle_notify(sender, data):
                """Handle incoming BLE notifications."""
                try:
                    msg = data.decode("utf-8", errors='replace')
                    print(f"{msg}", end='', flush=True)
                except Exception:
                    print(f"[HEX: {data.hex()}]", flush=True)

            await client.start_notify(TX_CHAR_UUID, handle_notify)

            # Keep connection alive until shutdown or disconnect
            while client.is_connected and not _shutdown_requested:
                await asyncio.sleep(0.1)

        except BleakError as e:
            print(f"\n[BLEAK] Error: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
        finally:
            # Always clean up properly
            if client:
                try:
                    if client.is_connected:
                        await client.stop_notify(TX_CHAR_UUID)
                        await client.disconnect()
                        print("\nDisconnected cleanly.")
                except Exception:
                    pass
                client = None

        if not _shutdown_requested:
            print("\nDisconnected. Retrying in 2 seconds...")
            await asyncio.sleep(2)


async def main(device_address=None):
    """Main entry point."""
    global _shutdown_requested

    # If no address provided, scan for devices
    if not device_address:
        devices = await find_rspb_device()
        if not devices:
            print("No RSPB devices found.")
            return

        print("\nFound devices:")
        for i, d in enumerate(devices):
            print(f"{i+1}. {d.address} - {d.name}")

        choice = input("\nSelect device number: ")
        try:
            device_address = devices[int(choice)-1].address
        except (ValueError, IndexError):
            print("Invalid selection")
            return

    # Start listening
    await ble_trace_terminal(device_address)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\nShutting down...")


if __name__ == '__main__':
    device_addr = sys.argv[1] if len(sys.argv) > 1 else None

    # Setup signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main(device_addr))
    except KeyboardInterrupt:
        pass
    finally:
        print("\n=== Trace listener stopped ===")
