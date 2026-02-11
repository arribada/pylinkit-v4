"""Unified log viewer with color-coded output.

Works over any LogTransport (BLE, USB serial, UART).
Supports TRACE/INFO/WARN/ERROR color coding.

Log format: DD/MM/YYYY HH:MM:SS [LEVEL]     message
"""

import re
import sys
import time
import logging

logger = logging.getLogger(__name__)

# ANSI color codes
COLORS = {
    'TRACE': '\033[2m',        # Dim/gray
    'INFO':  '\033[36m',       # Cyan
    'WARN':  '\033[33m',       # Yellow
    'ERROR': '\033[31;1m',     # Bright red
    'RESET': '\033[0m',
}

# Log line format: DD/MM/YYYY HH:MM:SS [LEVEL]     message
LOG_LINE_REGEX = re.compile(
    r'^(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\s+'
    r'\[(\w+)\]\s+'
    r'(.*)$'
)


class LogViewer:
    """Unified log viewer with color-coded output.

    Works over any LogTransport (BLE, USB serial, UART).
    Supports read-only mode (just listen, no commands).
    """

    def __init__(self, transport, enable_colors=True):
        self._transport = transport
        self._enable_colors = enable_colors
        self._running = False
        self._line_buffer = ''

    def start(self):
        """Start the log viewer. Blocks until stopped (Ctrl-C)."""
        self._running = True
        self._transport.subscribe_log(self._on_data)

        # Enable ANSI colors on Windows
        if sys.platform == 'win32' and self._enable_colors:
            self._enable_windows_ansi()

        print("=== Log Viewer Active ===")
        if hasattr(self._transport, 'is_read_only') and self._transport.is_read_only:
            print("Mode: read-only (UART)")
        print("Press Ctrl+C to stop\n")

        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._running = False
            print("\n=== Log Viewer Stopped ===")

    def stop(self):
        self._running = False

    def _on_data(self, data):
        """Handle incoming data, buffer partial lines,
        parse and colorize complete lines."""
        try:
            text = data.decode('utf-8', errors='replace')
        except AttributeError:
            text = str(data)

        self._line_buffer += text

        while '\n' in self._line_buffer or '\r' in self._line_buffer:
            # Find the first line terminator
            cr_pos = self._line_buffer.find('\r')
            lf_pos = self._line_buffer.find('\n')

            if cr_pos >= 0 and (lf_pos < 0 or cr_pos < lf_pos):
                line = self._line_buffer[:cr_pos]
                self._line_buffer = self._line_buffer[cr_pos + 1:]
                # Skip trailing \n if present
                if self._line_buffer.startswith('\n'):
                    self._line_buffer = self._line_buffer[1:]
            elif lf_pos >= 0:
                line = self._line_buffer[:lf_pos]
                self._line_buffer = self._line_buffer[lf_pos + 1:]
            else:
                break

            line = line.rstrip()
            if line:
                self._print_line(line)

    def _print_line(self, line):
        """Print a log line with color coding based on log level."""
        match = LOG_LINE_REGEX.match(line)
        if match and self._enable_colors:
            timestamp, level, message = match.groups()
            color = COLORS.get(level, '')
            reset = COLORS['RESET']
            print(f"{color}{timestamp} [{level}]\t{message}{reset}", flush=True)
        else:
            # No match or colors disabled - print raw
            if self._enable_colors:
                # Try to detect level even without timestamp
                for level_name, color_code in COLORS.items():
                    if level_name == 'RESET':
                        continue
                    if f'[{level_name}]' in line:
                        print(f"{color_code}{line}{COLORS['RESET']}", flush=True)
                        return
            print(line, flush=True)

    @staticmethod
    def _enable_windows_ansi():
        """Enable ANSI escape code processing on Windows 10+."""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(-11)
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass
