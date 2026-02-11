"""OTA firmware update over BLE GATT characteristics."""

import time
import logging
from threading import Event

from .ota_base import OTAUpdater

logger = logging.getLogger(__name__)

OTA_CHUNK_SIZE = 200


class BLEOTAUpdater(OTAUpdater):
    """OTA firmware update over BLE using OTATransport interface."""

    def __init__(self, transport):
        """transport: a BLETransport instance (which implements OTATransport)."""
        self._transport = transport
        self._event = Event()
        self._status = 0
        transport.subscribe_ota_status(self._status_handler)

    def send_update_file(self, file_id, data, timeout=None):
        self._status = 0
        self._event.clear()
        self._transport.ota_start(file_id)
        print('Waiting for device to ACK our START request')
        is_set = self._event.wait(60.0)
        total_length = len(data)
        count = 0
        if is_set is False:
            raise Exception('Time out waiting for START handshake')
        if self._status == 0:
            print('Received ACK, sending data....')
        else:
            print('Received NACK, aborting....')
            return
        for i in range(0, total_length, OTA_CHUNK_SIZE):
            chunk = data[i:i + OTA_CHUNK_SIZE]
            self._transport.ota_send_chunk(chunk)
            count += len(chunk)
            print(count, '/', total_length, end='\r')
            if self._status:
                print('Aborted remotely')
                self._transport.ota_abort()
                return
        self._transport.ota_finish()
        print('Data has been submitted...')
        print('Waiting for image transfer ACK...this may take some time...CTRL-C to abort')
        is_set = self._event.wait(timeout or self.DEFAULT_TIMEOUT)
        if is_set is False:
            self._transport.ota_abort()
            raise Exception('Time out waiting for STATUS handshake')
        if self._status == 0:
            print('Image transfer ACK')
            time.sleep(3)
        else:
            print('Image transfer NACK')

    def _status_handler(self, data):
        # File Upload Status is 3 bytes:
        # Byte 0 - File Reception: 0=>OK, 1=>Interrupted, FF=>Ignore
        # Byte 1 - File Integrity: 0=>OK, 1=>Not OK, FF=>Ignore
        # Byte 2 - Start Upload: 0=>OK, 1=>Invalid Base Addr 2=>Busy, FF=>Ignore
        if int(data[0]) != 0xFF:
            self._status = int(data[0])
        elif int(data[1]) != 0xFF:
            self._status = int(data[1])
        elif int(data[2]) != 0xFF:
            self._status = int(data[2])
        self._event.set()
