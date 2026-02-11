import logging
import re

logger = logging.getLogger(__name__)


class DTEProtocolError(Exception):
    pass


class DTEProtocol:
    """DTE protocol framing layer.

    Handles: $CMD#HEX_LEN;PAYLOAD\r format parsing,
    multi-response tracking (DUMPD pagination),
    and progress reporting.

    Transport-independent: works the same over BLE NUS or serial.
    """

    def __init__(self):
        self._queued_data = ''
        self._progress_callback = None
        self.reset()

    def data(self):
        return self._queued_data

    def push(self, buffer):
        """Push received data into the protocol state machine."""
        self._queued_data += buffer
        if self._expected_length == 0:
            buffer = self._extract_header(buffer)
        if buffer:
            if self._is_header(buffer):
                self.reset()
                logger.error(f'Unexpected header received: {buffer}')
                raise DTEProtocolError(f'Unexpected header received: {buffer}')
            if self._expected_length < len(buffer):
                self.reset()
                logger.error(f'Too many bytes received: remaining {self._expected_length} got {len(buffer)}')
                raise DTEProtocolError(f'Too many bytes: remaining {self._expected_length} got {len(buffer)}')
            self._expected_length -= len(buffer)
            if self._expected_length == 0:
                if self._expected_MMM is not None:
                    percent = int((100 * (self._last_mmm + 1)) / (self._expected_MMM + 1))
                    if self._progress_callback:
                        self._progress_callback(percent)
                    if self._last_mmm == self._expected_MMM:
                        self.reset()
                else:
                    self.reset()

    def is_terminated(self):
        return self._is_terminated

    def reset(self):
        self._expected_length = 0
        self._expected_MMM = None
        self._is_terminated = True
        self._last_mmm = None

    def set_progress_callback(self, callback):
        """Optional callback(percent: int) for DUMPD progress."""
        self._progress_callback = callback

    def _is_header(self, buffer):
        return buffer[0] == '$'

    def _extract_header(self, buffer):
        success_regexp = r'^\$O;(?P<cmd>[A-Z]+)#(?P<len>[0-9a-fA-F]+);(?P<payload>.*)'
        fail_regexp = r'^\$N;(?P<cmd>[A-Z]+)#(?P<len>[0-9a-fA-F]+);(?P<error>[0-9]+)\r$'
        success = re.match(success_regexp, buffer)
        if success:
            self._is_terminated = False
            self._expected_length = int(success.group('len'), 16) + 1  # +1 for \r terminator
            buffer = success.group('payload')
            if success.group('cmd') == 'DUMPD':
                try:
                    args = buffer.split(',')
                    mmm = int(args[0], 16)
                    MMM = int(args[1], 16)
                    if self._last_mmm is None:
                        if mmm != 0:
                            self.reset()
                            logger.error(f'First DUMPD mmm must be zero: got {mmm}')
                            raise DTEProtocolError(f'First DUMPD mmm must be zero: got {mmm}')
                        if MMM < 0:
                            self.reset()
                            logger.error(f'First DUMPD MMM must be >=0: got {MMM}')
                            raise DTEProtocolError(f'First DUMPD MMM must be >=0: got {MMM}')
                        self._last_mmm = 0
                        self._expected_MMM = MMM
                    else:
                        self._last_mmm += 1
                        if mmm != self._last_mmm:
                            self.reset()
                            logger.error(f'Unexpected DUMPD mmm: got {mmm} but expected {self._last_mmm}')
                            raise DTEProtocolError(f'Unexpected DUMPD mmm: got {mmm} expected {self._last_mmm}')
                        if mmm > self._expected_MMM:
                            self.reset()
                            logger.error(f'Unexpected DUMPD mmm: got {mmm} which exceeds {self._expected_MMM}')
                            raise DTEProtocolError(f'DUMPD mmm {mmm} exceeds max {self._expected_MMM}')
                except DTEProtocolError:
                    raise
                except Exception:
                    self.reset()
                    logger.error(f'Unexpected DUMPD payload: {buffer}')
                    raise DTEProtocolError(f'Unexpected DUMPD payload: {buffer}')
            return buffer

        fail = re.match(fail_regexp, buffer)
        if fail:
            self.reset()
            return ''

        self.reset()
        raise DTEProtocolError(f'Malformed header received: {buffer}')
