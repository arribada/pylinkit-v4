from .transport import TransportType, create_transport
from .transport.ble import BLETransport
from .protocol.dte_commands import DTECommands
from .ota.ota_ble import BLEOTAUpdater


class Scanner:
    """Scan for Linkit/Horizon/RSPB devices over BLE."""

    def scan(self):
        return BLETransport.scan()


class Tracker:
    """Main interface to a Linkit tracker device.

    Supports BLE and USB serial transports.
    """

    def __init__(self, address, transport_type=TransportType.BLE, timeout=5.0, **transport_kwargs):
        self._transport = create_transport(transport_type, **transport_kwargs)
        self._transport.connect(address, timeout=timeout)
        self._dte = DTECommands(self._transport)

        # Create appropriate OTA updater based on transport
        if transport_type == TransportType.BLE:
            self._ota = BLEOTAUpdater(self._transport)
        elif transport_type == TransportType.USB:
            from .ota.ota_serial import SerialOTAUpdater
            self._ota = SerialOTAUpdater(self._transport)
        else:
            self._ota = None  # UART (read-only) has no OTA

        self._map = {}

    def sync(self):
        a = self._dte.parmr()
        b = self._dte.statr()
        self._map = {**a, **b}

    def set(self, param_values):
        self._dte.parmw(param_values=param_values)

    def get(self, attr=None):
        return self._map[attr] if attr else self._map

    def get_attrs(self):
        return self._map.keys()

    def firmware_update(self, data, file_id=0, timeout=None):
        if self._ota is None:
            raise RuntimeError("OTA not available on this transport (read-only)")
        self._ota.send_update_file(file_id, data, timeout)

    def smd_firmware_update(self, data, mode='uart', timeout=None):
        """Send SMD module firmware update.
        mode: 'uart' (file_id=3) or 'spi' (file_id=4)"""
        file_id = 3 if mode == 'uart' else 4
        if self._ota is None:
            raise RuntimeError("OTA not available on this transport (read-only)")
        self._ota.send_update_file(file_id, data, timeout)

    def paspw(self, json_file_data):
        self._dte.paspw(json_file_data)

    def dumpd(self, log_type):
        return self._dte.dumpd(log_type)

    def erase(self, log_type):
        return self._dte.erase(log_type)

    def factw(self):
        self._dte.factw()

    def rstvw(self, index):
        self._dte.rstvw(index)

    def rstbw(self):
        self._dte.rstbw()

    def deplw(self):
        self._dte.deplw()

    def scalw(self, sensor, step, value=0):
        self._dte.scalw(sensor, step, value)

    def scalr(self, sensor, step):
        return self._dte.scalr(sensor, step)

    def pwron(self, component):
        self._dte.pwron(component)

    def argostx(self, mod, power, freq, size, tcxo):
        self._dte.argostx(mod, power, freq, size, tcxo)

    def smdcd(self, id, addr, seckey, radioconf):
        self._dte.smdcd(id, addr, seckey, radioconf)

    def sensr(self, mask=0x0F, timeout=60):
        """Read sensors. Returns dict with battery, pressure, temperature, GNSS."""
        return self._dte.sensr(mask, timeout)

    def smddfu(self, action):
        """Send SMDDFU command. Returns dict with status, dfu_mode, progress, info."""
        return self._dte.smddfu(action)

    def smdtst(self):
        """Run SMD SPI test (14 A+ commands). Returns test summary string."""
        return self._dte.smdtst()

    def wait_smd_dfu_result(self, timeout=180.0):
        """Wait for async SMDDFU notification after SPI firmware transfer.
        Returns dict with status, dfu_mode, progress, info."""
        return self._dte.wait_smd_dfu_result(timeout)

    def poll(self, key, repetitions=1):
        for i in range(repetitions):
            result = self._dte.parmr([key])
            print(result)
