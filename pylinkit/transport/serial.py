"""Serial transport for USB CDC and UART connections using pyserial.

Supports:
- USB CDC: bidirectional DTE commands + log viewing
- UART (via USB converter): log viewing only (read_only mode)

The reader thread discriminates between DTE responses (lines starting with '$')
and log output (everything else), routing to the appropriate callback.
"""

import logging
import threading
import time

import serial
import serial.tools.list_ports

from .base import DataTransport, LogTransport

logger = logging.getLogger(__name__)


class SerialTransport(DataTransport, LogTransport):
    """Serial transport for USB CDC or UART connections."""

    def __init__(self, read_only=False):
        self._read_only = read_only
        self._serial = None
        self._reader_thread = None
        self._running = False
        self._data_callback = None
        self._log_callback = None
        self._raw_callback = None
        self._raw_mode = False

    # --- Transport interface ---

    def connect(self, port, timeout=5.0, baudrate=115200):
        """Connect to a serial port.

        Args:
            port: Serial port path (e.g., COM3, /dev/ttyUSB0)
            timeout: Read timeout in seconds
            baudrate: Serial baudrate (default 115200)
        """
        self._serial = serial.Serial(
            port,
            baudrate=baudrate,
            timeout=0.1,  # Short read timeout for responsive reader thread
            write_timeout=timeout
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        logger.info(f"Connected to {port} at {baudrate} baud")

    def disconnect(self):
        self._running = False
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("Serial port closed")
        self._serial = None

    def is_connected(self):
        return self._serial is not None and self._serial.is_open

    # --- DataTransport interface ---

    def send_data(self, data):
        """Send data directly -- no fragmentation needed for serial."""
        if self._read_only:
            raise RuntimeError("Transport is read-only (UART log mode)")
        if not self.is_connected():
            raise RuntimeError("Serial port not connected")
        self._serial.write(data)
        self._serial.flush()

    def subscribe_data(self, callback):
        self._data_callback = callback

    # --- Raw bridge mode (byte-level passthrough, no line buffering) ---

    def subscribe_raw(self, callback):
        """Register a callback for raw byte chunks (used during bridge mode)."""
        self._raw_callback = callback

    def set_raw_mode(self, enabled):
        """Enable/disable raw passthrough. When enabled, all incoming bytes are
        forwarded to the raw callback without line parsing; data/log callbacks
        are bypassed."""
        self._raw_mode = bool(enabled)

    # --- LogTransport interface ---

    def subscribe_log(self, callback):
        self._log_callback = callback

    @property
    def is_read_only(self):
        return self._read_only

    # --- Reader thread ---

    def _read_loop(self):
        """Background thread that reads from serial port and dispatches
        to data_callback (DTE responses) or log_callback (log lines)."""
        buffer = b''
        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    time.sleep(0.1)
                    continue

                # Read available data
                waiting = self._serial.in_waiting
                if waiting > 0:
                    chunk = self._serial.read(waiting)
                else:
                    chunk = self._serial.read(1)  # Blocking read with timeout

                if not chunk:
                    continue

                # Raw passthrough: bypass line buffering.
                if self._raw_mode:
                    if self._raw_callback:
                        self._raw_callback(chunk)
                    continue

                buffer += chunk

                # Process complete messages
                while b'\r' in buffer or b'\n' in buffer:
                    # Find the first terminator
                    cr_pos = buffer.find(b'\r')
                    lf_pos = buffer.find(b'\n')

                    if cr_pos >= 0 and (lf_pos < 0 or cr_pos < lf_pos):
                        # \r found first - could be DTE response or log line
                        line = buffer[:cr_pos + 1]
                        buffer = buffer[cr_pos + 1:]
                        # Skip trailing \n if present
                        if buffer.startswith(b'\n'):
                            buffer = buffer[1:]
                    elif lf_pos >= 0:
                        # \n found first - log line
                        line = buffer[:lf_pos]
                        buffer = buffer[lf_pos + 1:]
                    else:
                        break

                    if not line.strip():
                        continue

                    self._dispatch_line(line)

            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                self._running = False
                break
            except Exception as e:
                logger.error(f"Reader thread error: {e}")

    def _dispatch_line(self, line):
        """Route a complete line to the appropriate callback.

        DTE responses start with '$' -> data_callback
        Everything else -> log_callback
        """
        if line.startswith(b'$') and self._data_callback:
            # DTE response
            self._data_callback(line)
        elif self._log_callback:
            # Log line
            self._log_callback(line)
        elif self._data_callback:
            # No log callback, try data callback as fallback
            self._data_callback(line)

    # --- Utility ---

    @staticmethod
    def list_ports():
        """List available serial ports."""
        return list(serial.tools.list_ports.comports())
