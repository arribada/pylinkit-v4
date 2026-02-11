from abc import ABC, abstractmethod


class OTAUpdater(ABC):
    """Abstract OTA firmware updater."""

    DEFAULT_TIMEOUT = 20 * 60  # 20 minutes

    @abstractmethod
    def send_update_file(self, file_id, data, timeout=None):
        """Send a firmware/data file to the device via OTA."""
        ...
