"""BLE transport using Bleak.

Implements DataTransport (NUS with 20-byte fragmentation),
OTATransport (GATT characteristics for firmware update),
and LogTransport (NUS TX notifications for trace output).
"""

import struct
import logging
import threading
import asyncio
import atexit

from bleak import BleakScanner, BleakClient

from .base import DataTransport, OTATransport, LogTransport

logger = logging.getLogger(__name__)

# Nordic UART Service
NUS_CHAR_LENGTH = 20
NUS_RX_CHAR_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
NUS_TX_CHAR_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

# OTA GATT characteristics
OTA_CHAR_LENGTH = 200
OTA_BASE_ADDR_CHAR_UUID = '0000FE22-8E22-4541-9D4C-21EDAE82ED19'
OTA_STATUS_CHAR_UUID = '0000FE23-8E22-4541-9D4C-21EDAE82ED19'
OTA_RAW_DATA_UUID = '0000FE24-8E22-4541-9D4C-21EDAE82ED19'

# OTA action codes
ACTION_START = 1
ACTION_DONE = 7
ACTION_ABORT = 8

DEVICE_NAME_FILTERS = ('Linkit', 'Horizon', 'RSPB')


class BLETransport(DataTransport, OTATransport, LogTransport):
    """BLE transport. Combines NUS data, OTA GATT, and log trace
    into a single transport implementation."""

    _SCAN_INTERVAL = 2.0

    def __init__(self):
        self._connection_client = None
        self._bleak_loop = None
        self._bleak_thread = threading.Thread(target=self._run_bleak_loop)
        self._bleak_thread.daemon = True
        self._bleak_thread_ready = threading.Event()
        self._bleak_thread.start()
        self._bleak_thread_ready.wait()
        self._scanner = None
        self._data_callback = None
        self._log_callback = None
        self._ota_status_callback = None
        self._log_mode = False

        atexit.register(self._cleanup)

    def _cleanup(self):
        self.disconnect()

    # --- Transport interface ---

    def connect(self, address, timeout=5.0):
        self._await_bleak(self._connect_async(address, timeout=timeout))

    def disconnect(self):
        self._await_bleak(self._disconnect_async())

    def is_connected(self):
        return self._connection_client is not None

    # --- DataTransport interface ---

    def send_data(self, data):
        """Fragment data into NUS_CHAR_LENGTH chunks and write to NUS RX."""
        for i in range(0, len(data), NUS_CHAR_LENGTH):
            chunk = data[i:i + NUS_CHAR_LENGTH]
            self._char_write(NUS_RX_CHAR_UUID, chunk)

    def subscribe_data(self, callback):
        """Subscribe to NUS TX notifications for DTE responses."""
        self._data_callback = callback
        self._subscribe(NUS_TX_CHAR_UUID, self._nus_handler)

    # --- OTATransport interface ---

    def ota_start(self, file_id):
        action = ACTION_START | file_id << 8
        self._char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', action))

    def ota_send_chunk(self, data):
        self._char_write(OTA_RAW_DATA_UUID, data)

    def ota_finish(self):
        self._char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', ACTION_DONE))

    def ota_abort(self):
        self._char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', ACTION_ABORT))

    def subscribe_ota_status(self, callback):
        self._ota_status_callback = callback
        self._subscribe(OTA_STATUS_CHAR_UUID, lambda _, data: callback(bytes(data)))

    # --- LogTransport interface ---

    def subscribe_log(self, callback):
        """Subscribe to NUS TX notifications for log/trace output."""
        self._log_callback = callback
        self._log_mode = True
        self._subscribe(NUS_TX_CHAR_UUID, self._nus_handler)

    @property
    def is_read_only(self):
        return False

    def set_log_mode(self, enabled):
        """Switch between DTE data mode and log trace mode."""
        self._log_mode = enabled

    # --- Internal NUS handler ---

    def _nus_handler(self, _, data):
        """Route NUS notifications to data or log callback."""
        raw = bytes(data)
        if self._log_mode and self._log_callback:
            self._log_callback(raw)
        elif self._data_callback:
            self._data_callback(raw)

    # --- BLE scan ---

    @staticmethod
    def scan(interval=2.0, name_filters=DEVICE_NAME_FILTERS):
        """Scan for BLE devices matching name filters."""
        transport = BLETransport()
        devices = transport._await_bleak(transport._scan_for_interval(interval))
        return [d for d in devices if d.name and any(f in d.name for f in name_filters)]

    # --- Low-level BLE operations ---

    def _char_write(self, uuid, value):
        self._await_bleak(self._connection_client.write_gatt_char(uuid, bytearray(value)))

    def _char_read(self, uuid):
        return self._await_bleak(self._connection_client.read_gatt_char(uuid))

    def _subscribe(self, uuid, callback):
        self._await_bleak(
            self._connection_client.start_notify(uuid, lambda x, data: callback(x, bytes(data)))
        )

    # --- Async BLE operations ---

    async def _scan_for_interval(self, interval):
        if not self._scanner:
            self._scanner = BleakScanner()
        await self._scanner.start()
        await asyncio.sleep(interval)
        await self._scanner.stop()
        return self._scanner.discovered_devices if self._scanner.discovered_devices else []

    async def _connect_async(self, address, timeout):
        if self._connection_client is not None:
            raise Exception("Device already connected")
        client = BleakClient(address)
        try:
            await client.connect(timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception("Failed to connect: timeout") from asyncio.TimeoutError
        self._connection_client = client
        return client

    async def _disconnect_async(self):
        if self._connection_client is not None:
            try:
                await self._connection_client.disconnect()
            except Exception:
                pass
            self._connection_client = None

    def _run_bleak_loop(self):
        self._bleak_loop = asyncio.new_event_loop()
        self._bleak_thread_ready.set()
        self._bleak_loop.run_forever()

    def _await_bleak(self, coro, timeout=None):
        future = asyncio.run_coroutine_threadsafe(coro, self._bleak_loop)
        return future.result(timeout)
