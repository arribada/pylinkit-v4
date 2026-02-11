from abc import ABC, abstractmethod
from typing import Callable


class Transport(ABC):
    """Base transport for communicating with the Linkit device."""

    @abstractmethod
    def connect(self, address: str, timeout: float = 5.0):
        """Connect to the device.
        address: BLE MAC address or serial port path (COM3, /dev/ttyUSB0)."""
        ...

    @abstractmethod
    def disconnect(self):
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...


class DataTransport(Transport):
    """Transport that supports bidirectional DTE data exchange."""

    @abstractmethod
    def send_data(self, data: bytes):
        """Send raw bytes to the device (handles fragmentation internally if needed)."""
        ...

    @abstractmethod
    def subscribe_data(self, callback: Callable[[bytes], None]):
        """Register a callback for incoming DTE response data from the device."""
        ...


class OTATransport(Transport):
    """Transport that supports OTA firmware updates."""

    @abstractmethod
    def ota_start(self, file_id: int):
        """Signal start of OTA transfer."""
        ...

    @abstractmethod
    def ota_send_chunk(self, data: bytes):
        """Send a chunk of OTA data."""
        ...

    @abstractmethod
    def ota_finish(self):
        """Signal end of OTA transfer."""
        ...

    @abstractmethod
    def ota_abort(self):
        """Abort OTA transfer."""
        ...

    @abstractmethod
    def subscribe_ota_status(self, callback: Callable[[bytes], None]):
        """Register a callback for OTA status notifications."""
        ...


class LogTransport(Transport):
    """Transport that supports live log/trace streaming."""

    @abstractmethod
    def subscribe_log(self, callback: Callable[[bytes], None]):
        """Register a callback for incoming log lines."""
        ...

    @property
    @abstractmethod
    def is_read_only(self) -> bool:
        """Whether this transport only supports reading (no commands)."""
        ...
