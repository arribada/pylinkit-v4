"""OTA firmware update over USB serial.

Sends the same binary data protocol as BLE OTA but over serial.
The firmware must support OTA commands over USB CDC for this to work.
"""

import time
import logging
import struct
from threading import Event

from .ota_base import OTAUpdater

logger = logging.getLogger(__name__)

OTA_CHUNK_SIZE = 200

# OTA serial protocol commands (sent as binary over serial)
OTA_CMD_START = 0x01
OTA_CMD_DATA = 0x02
OTA_CMD_DONE = 0x07
OTA_CMD_ABORT = 0x08
OTA_CMD_STATUS = 0x10


class SerialOTAUpdater(OTAUpdater):
    """OTA firmware update over USB serial.

    Uses a simple binary protocol:
    - START: sends file_id and total size
    - DATA: sends chunks of firmware data
    - DONE: signals transfer complete
    - ABORT: cancels transfer

    The serial transport must be bidirectional (not read-only).
    """

    def __init__(self, transport):
        self._transport = transport
        self._event = Event()
        self._status = 0
        transport.subscribe_data(self._status_handler)

    def send_update_file(self, file_id, data, timeout=None):
        self._status = 0
        total_length = len(data)

        # Send START command with file_id and total size
        start_cmd = struct.pack('<BBI', OTA_CMD_START, file_id, total_length)
        self._event.clear()
        self._transport.send_data(start_cmd)
        print('Waiting for device to ACK our START request')

        is_set = self._event.wait(60.0)
        if is_set is False:
            raise Exception('Time out waiting for START handshake')
        if self._status != 0:
            print('Received NACK, aborting....')
            return

        print('Received ACK, sending data....')

        # Send data in chunks
        count = 0
        for i in range(0, total_length, OTA_CHUNK_SIZE):
            chunk = data[i:i + OTA_CHUNK_SIZE]
            # Prefix with DATA command byte
            data_cmd = struct.pack('<B', OTA_CMD_DATA) + chunk
            self._transport.send_data(data_cmd)
            count += len(chunk)
            print(count, '/', total_length, end='\r')
            if self._status:
                print('Aborted remotely')
                abort_cmd = struct.pack('<B', OTA_CMD_ABORT)
                self._transport.send_data(abort_cmd)
                return

        # Send DONE command
        done_cmd = struct.pack('<B', OTA_CMD_DONE)
        self._transport.send_data(done_cmd)
        print('Data has been submitted...')
        print('Waiting for image transfer ACK...this may take some time...CTRL-C to abort')

        is_set = self._event.wait(timeout or self.DEFAULT_TIMEOUT)
        if is_set is False:
            abort_cmd = struct.pack('<B', OTA_CMD_ABORT)
            self._transport.send_data(abort_cmd)
            raise Exception('Time out waiting for STATUS handshake')

        if self._status == 0:
            print('Image transfer ACK')
            time.sleep(3)
        else:
            print('Image transfer NACK')

    def _status_handler(self, data):
        """Handle status responses from device.
        Expects binary status byte: 0=OK, non-zero=error."""
        try:
            if len(data) >= 1 and data[0] == OTA_CMD_STATUS:
                if len(data) >= 2:
                    self._status = data[1]
                else:
                    self._status = 0
                self._event.set()
        except Exception:
            pass
