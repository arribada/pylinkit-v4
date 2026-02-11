# Heavily based on https://github.com/adafruit/Adafruit_Blinka_bleio
# This provides a synchronous interface to the asynchronous "Bleak" BLE library

from bleak import BleakScanner, BleakClient
import threading
import asyncio
import atexit

class BLEDevice(object):

    _SCAN_INTERVAL = 2.0

    def __init__(self):

        self._connection_client = None

        self._bleak_loop = None
        self._bleak_thread = threading.Thread(target=self._run_bleak_loop)
        # Discard thread quietly on exit.
        self._bleak_thread.daemon = True
        self._bleak_thread_ready = threading.Event()
        self._bleak_thread.start()
        # Wait for thread to start.
        self._bleak_thread_ready.wait()
        self._scanner = None

        # Clean up connections, etc. when exiting (even by KeyboardInterrupt)
        atexit.register(self._cleanup)

    def _cleanup(self):
        """Clean up connections, so that the underlying OS software does not
        leave them open.
        """
        self.disconnect()

    def scan(self):
        return self._await_bleak(self._scan_for_interval(self._SCAN_INTERVAL))

    def connect(self, address, timeout: float):
        return self._await_bleak(self._connect_async(address, timeout=timeout))

    def disconnect(self):
        self._await_bleak(self._disconnect_async())

    def char_write(self, uuid, value):
        self._await_bleak(self._connection_client.write_gatt_char(uuid, bytearray(value)))

    def char_read(self, uuid):
        return self._await_bleak(self._connection_client.read_gatt_char(uuid))

    def subscribe(self, uuid, callback):
        self._await_bleak(self._connection_client.start_notify(uuid, lambda x, data: callback(x, bytes(data))))


    async def _scan_for_interval(self, interval: float):
        """Scan advertisements for the given interval and return ScanEntry objects
        for all advertisements heard.
        """
        if not self._scanner:
            self._scanner = BleakScanner()

        await self._scanner.start()
        await asyncio.sleep(interval)
        await self._scanner.stop()
        return self._scanner.discovered_devices if self._scanner.discovered_devices else []

    async def _connect_async(self, address, timeout: float):
        if self._connection_client is not None:
            raise BluetoothError("Device already connected")

        client = BleakClient(address)
        # connect() takes a timeout, but it's a timeout to do a
        # discover() scan, not an actual connect timeout.
        try:
            await client.connect(timeout=timeout)
            # This does not seem to connect reliably.
            # await asyncio.wait_for(client.connect(), timeout)
        except asyncio.TimeoutError:
            raise BluetoothError("Failed to connect: timeout") from asyncio.TimeoutError

        self._connection_client = client
        return client

    async def _disconnect_async(self):
        """Disconnects from the remote peripheral. Does nothing if already disconnected."""
        if self._connection_client is not None:
            try:
                await self._connection_client.disconnect()
            except Exception:
                pass
            self._connection_client = None

    def _run_bleak_loop(self):
        self._bleak_loop = asyncio.new_event_loop()
        # Event loop is now available.
        self._bleak_thread_ready.set()
        self._bleak_loop.run_forever()

    def _await_bleak(self, coro, timeout=None):
        """Call an async routine in the bleak thread from sync code, and await its result."""
        # This is a concurrent.Future.
        future = asyncio.run_coroutine_threadsafe(coro, self._bleak_loop)
        return future.result(timeout)
