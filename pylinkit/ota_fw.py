import struct, time
from threading import Event

OTA_CHAR_LENGTH = 200
OTA_BASE_ADDR_CHAR_UUID = '0000FE22-8E22-4541-9D4C-21EDAE82ED19'
OTA_STATUS_CHAR_UUID = '0000FE23-8E22-4541-9D4C-21EDAE82ED19'
OTA_RAW_DATA_UUID = '0000FE24-8E22-4541-9D4C-21EDAE82ED19'

ACTION_START = 1
ACTION_DONE = 7
ACTION_ABORT = 8

DEFAULT_TIMEOUT = 20 * 60

class OTAFW():
    def __init__(self, device):
        self._device = device
        self._event = Event()
        self._status = 0
        device.subscribe(OTA_STATUS_CHAR_UUID, self._status_handler)

    def send_update_file(self, file_id, data, timeout):
        self._status = 0
        action = ACTION_START | file_id << 8
        self._event.clear()
        self._device.char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', action))
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
        for x in [ data[0+i:OTA_CHAR_LENGTH+i] for i in range(0, len(data), OTA_CHAR_LENGTH) ]:
            self._device.char_write(OTA_RAW_DATA_UUID, x)
            count += len(x)
            print(count, '/', total_length, end = '\r')
            if self._status:
                print('Aborted remotely')
                self._device.char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', ACTION_ABORT))
                return
        self._device.char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', ACTION_DONE))
        print('Data has been submitted...')
        print('Waiting for image transfer ACK...this may take some time...CTRL-C to abort')
        is_set = self._event.wait(timeout or DEFAULT_TIMEOUT)
        if is_set is False:
            # Abort pending OTA update
            self._device.char_write(OTA_BASE_ADDR_CHAR_UUID, struct.pack('<I', ACTION_ABORT))
            raise Exception('Time out waiting for STATUS handshake')
        if (self._status == 0):
            print('Image transfer ACK')
            time.sleep(3)  # Allow time for procedure to clean up
        else:
            print('Image transfer NACK')

    def _status_handler(self, _, data):
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
        #self._event.clear()
