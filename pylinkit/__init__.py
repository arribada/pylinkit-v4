from .transport import TransportType, create_transport
from .transport.ble import BLETransport
from .protocol.dte_commands import DTECommands, ParmwPartialError
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

    def disconnect(self):
        """Release the transport connection."""
        self._transport.disconnect()

    def sync(self):
        a = self._dte.parmr()
        b = self._dte.statr()
        self._map = {**a, **b}

    def set(self, param_values):
        """Write parameters. Returns dict {param_name: True/False} for per-param success."""
        return self._dte.parmw(param_values=param_values)

    def get(self, attr=None, default=KeyError):
        if attr is None:
            return self._map
        if default is KeyError:
            return self._map[attr]
        return self._map.get(attr, default)

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

    def dumpd_pressure(self):
        """Dump pressure logs decoded with altitude (retrocompat with old logs)."""
        return self._dte.dumpd_pressure()

    def pressure_log_to_csv(self):
        """Dump pressure logs as CSV string: log_datetime,pressure,temperature,altitude"""
        return self._dte.pressure_log_to_csv()

    def sws_log_to_csv(self):
        """Dump SWS logs as CSV string: log_datetime,raw_adc,filtered_adc,...,sample_delay_us"""
        return self._dte.sws_log_to_csv()

    def dumpd_mortality(self):
        """Dump mortality logs decoded to structured records."""
        return self._dte.dumpd_mortality()

    def mortality_log_to_csv(self):
        """Dump mortality logs as CSV string."""
        return self._dte.mortality_log_to_csv()

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

    def battery(self):
        """Read battery status (voltage, SOC, low/critical flags)."""
        return self._dte.battery()

    def pwron(self, component):
        self._dte.pwron(component)

    def gnssi(self):
        """Read GNSS module info. Requires GNSS powered on (pwron('gnss') + 2s wait).
        Returns dict with unique_id, sw_version, hw_version."""
        return self._dte.gnssi()

    def gnssa(self):
        """Check GNSS AssistNow almanac status.
        Returns dict with present, file_size, total_records, valid_records, stale."""
        return self._dte.gnssa()

    def rtcw(self, timestamp=None):
        """Write RTC time. If timestamp is None, uses current UTC time."""
        self._dte.rtcw(timestamp)

    def download_almanac(self, token):
        """Download AssistNow almanac and send to device.
        Reads existing chipcode from device, powers on GNSS, reads module info,
        downloads from u-blox (skipping ZTP if chipcode exists), uploads to device,
        and saves any new chipcode as GNSS_TOKEN parameter.
        Returns tuple of (almanac_bytes, chipcode)."""
        import time
        from .assistnow import download_almanac
        from .utils import create_wrapped_file_with_crc32
        existing_chipcode = self._dte.parmr(['GNSS_TOKEN']).get('GNSS_TOKEN') or None
        self.pwron('gnss')
        time.sleep(2)
        info = self.gnssi()
        data, chipcode = download_almanac(
            token, info['unique_id'], info['sw_version'], info['hw_version'],
            chipcode=existing_chipcode
        )
        self.firmware_update(create_wrapped_file_with_crc32(data), 2)
        if chipcode and chipcode != existing_chipcode:
            self.set({'GNSS_TOKEN': chipcode})
        return data, chipcode

    def argostx(self, mod='LDA2', tcxo=2):
        self._dte.argostx(mod, tcxo)

    def loratx(self, size=12):
        """Send a LoRa test transmission. size: payload bytes (1-222)."""
        self._dte.loratx(size)

    def update_radioconf(self, mod):
        """Update RADIOCONF (IDP14) for given modulation."""
        self._dte.update_radioconf(mod)

    def smdcd(self, id, addr, seckey, radioconf):
        """Write SMD credentials via SMDCD command (backward-compatible convenience wrapper).
        Same effect as PARMW on IDP12, IDT06, IDP13, IDP14.
        Credentials are applied to SMD hardware at next TX."""
        self._dte.smdcd(id, addr, seckey, radioconf)

    def satvf(self):
        """Verify satellite module credentials (SMD/KIM2): config store vs hardware.
        Returns dict with id, addr, seckey, radioconf, match (bool)."""
        return self._dte.satvf()

    def sensr(self, mask=0xFF, timeout=60):
        """Read sensors. Returns dict with battery, pressure, gnss, accel, thermistor,
        sea_temp, als_lux, ph, sensor_status."""
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

    def satdp(self):
        """Start Doppler calibration. Periodic TX until device reset."""
        self._dte.satdp()

    def swstst(self, start=True):
        """Start or stop SWS test mode. Returns True if test running."""
        return self._dte.swstst(start)

    def swstst_stream(self, callback):
        """Start SWS test mode and stream pushed samples to callback.
        Blocks until KeyboardInterrupt, then stops test mode."""
        self._dte.swstst_stream(callback)

    def gnssbr(self, action=1):
        """Start/stop GNSS UART bridge. action=1 start, 0 stop. Send +++ to exit."""
        self._dte.gnssbr(action)

    def lorabr(self, action=1):
        """Start/stop LoRa UART bridge. action=1 start, 0 stop. Send +++ to exit."""
        self._dte.lorabr(action)

    def swsst(self):
        """Read SWS (Salt Water Switch) status."""
        return self._dte.swsst()

    def poll(self, key, repetitions=1):
        for i in range(repetitions):
            result = self._dte.parmr([key])
            print(result)
