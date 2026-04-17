import re
import logging
from threading import Event

from .dte_protocol import DTEProtocol, DTEProtocolError
from .dte_params import DTEParamMap
from .dte_types import BASE64, PASPW, LOGFILE
from ..enums import BaseLogDType, BaseEraseType, BaseSensorCalType, ComponentPower, ArgosModulation, SensrMask, DTEError

logger = logging.getLogger(__name__)


class ParmwPartialError(Exception):
    """Raised when PARMW partially succeeds: some params written, some rejected."""
    def __init__(self, cmd, rejected_keys):
        self.cmd = cmd
        self.rejected_keys = rejected_keys
        super().__init__(f'{cmd} - partial write, rejected keys: {", ".join(rejected_keys)}')


class DTECommands:
    """DTE command layer. Encodes commands, sends them via a DataTransport,
    receives responses using DTEProtocol framing.

    Transport-agnostic: works over BLE NUS or serial.
    """

    def __init__(self, transport):
        """transport: any DataTransport instance (BLE or Serial)."""
        self._transport = transport
        self._protocol = DTEProtocol()
        self._event = Event()
        self._terminate = False
        transport.subscribe_data(self._data_handler)

    def _send_and_receive(self, command_str, timeout=10.0):
        """Send a DTE command string and wait for the complete response."""
        self._protocol = DTEProtocol()
        self._terminate = False
        self._event.clear()
        logger.debug('PC -> DTE: %s', command_str.encode('ascii'))
        self._transport.send_data(command_str.encode('ascii'))
        while True:
            is_set = self._event.wait(timeout)
            self._event.clear()
            if not is_set:
                raise TimeoutError(f'DTE command timed out after {timeout}s')
            if self._terminate:
                break
        return self._protocol.data()

    def _data_handler(self, data):
        """Callback for incoming data from transport."""
        logger.debug('PC <- DTE: %s', data.decode('ascii', errors='replace'))
        try:
            self._protocol.push(data.decode('ascii', errors='replace'))
            self._terminate = self._protocol.is_terminated()
        except DTEProtocolError:
            self._terminate = True
        self._event.set()

    def _encode_command(self, command, params=[], param_values={}, args=[]):
        if params:
            payload = ','.join([DTEParamMap.param_to_key(x) for x in params])
        elif args:
            payload = ','.join(args)
        elif param_values:
            payload = ','.join([
                '{}={}'.format(DTEParamMap.param_to_key(x), DTEParamMap.encode(x, param_values[x]))
                for x in param_values
            ])
        else:
            payload = ''
        return '${cmd}#{length:03x};{payload}\r'.format(cmd=command, length=len(payload), payload=payload)

    def _decode_response(self, resp):
        success_regexp = r'^\$O;(?P<cmd>[A-Z]+)#(?P<len>[0-9a-fA-F]+);(?P<payload>.*)\r$'
        fail_regexp = r'^\$N;(?P<cmd>[A-Z]+)#(?P<len>[0-9a-fA-F]+);(?P<payload>.+)\r$'
        success = re.match(success_regexp, resp)
        if success:
            return success.group('payload')
        fail = re.match(fail_regexp, resp)
        if fail:
            cmd = fail.group('cmd')
            payload = fail.group('payload')
            # Pure numeric payload = global error code
            if payload.isdigit():
                error_code = int(payload)
                try:
                    err = DTEError(error_code)
                    raise Exception(f'{cmd} - error {error_code}: {err.message}')
                except ValueError:
                    raise Exception(f'{cmd} - error {error_code}: Unknown error')
            # Non-numeric payload = partial reject (list of rejected DTE keys)
            rejected_keys = [k.strip() for k in payload.split(',')]
            raise ParmwPartialError(cmd, rejected_keys)
        raise Exception('Bad response - {}'.format(resp))

    def _decode_multi_response(self, resp):
        return [self._decode_response(r + '\r') for r in resp.split('\r') if r]

    def _decode_key_values(self, payload):
        m = {}
        for x in payload.strip().split(','):
            key, value = x.split('=', 1)
            try:
                m[DTEParamMap.key_to_param(key)] = DTEParamMap.decode(key, value)
            except Exception as e:
                logger.warning('Skipping unknown/invalid param key=%s value=%s: %s', key, value, e)
                continue
        return m

    def parmr(self, params=[]):
        resp = self._send_and_receive(self._encode_command('PARMR', params=params))
        return self._decode_key_values(self._decode_response(resp))

    def statr(self, params=[]):
        resp = self._send_and_receive(self._encode_command('STATR', params=params))
        return self._decode_key_values(self._decode_response(resp))

    def parmw(self, param_values={}):
        """Write parameters. Returns dict {param_name: True/False} indicating per-param success.
        Raises Exception on global format errors. Partial rejects are handled gracefully."""
        resp = self._send_and_receive(self._encode_command('PARMW', param_values=param_values))
        try:
            self._decode_response(resp)
            return {name: True for name in param_values}
        except ParmwPartialError as e:
            result = {}
            for name in param_values:
                key = DTEParamMap.param_to_key(name)
                result[name] = key not in e.rejected_keys
            return result

    def battery(self):
        """Read battery status via PARMR (BATT_SOC, BATT_VOLTAGE, LB_TRESHOLD, LB_CRITICAL_THRESH)."""
        params = self.parmr(['POT03', 'POT06', 'LBP02', 'LBP12'])
        voltage_v = params.get('BATT_VOLTAGE', 0)
        voltage_mv = int(voltage_v * 1000) if isinstance(voltage_v, float) else int(voltage_v)
        soc = int(params.get('BATT_SOC', 0))
        lb_thresh = int(params.get('LB_TRESHOLD', 0))
        critical_pct = int(params.get('LB_CRITICAL_THRESH', 0))
        return {
            'voltage_mv': voltage_mv,
            'soc': soc,
            'low_battery': soc <= lb_thresh,
            'critical': soc <= critical_pct,
            'lb_threshold_pct': lb_thresh,
            'critical_threshold_pct': critical_pct,
        }

    def dumpd(self, log_type='sensor'):
        type_value = BaseLogDType.from_name(log_type).value
        resp = self._send_and_receive(
            self._encode_command('DUMPD', args=[format(type_value, 'x')]),
            timeout=60.0
        )
        responses = self._decode_multi_response(resp)
        raw_data = b''
        for r in responses:
            _, _, data = r.split(',', 2)
            decoded_data = BASE64.decode(data)
            raw_data += decoded_data
        return raw_data

    def dumpd_pressure(self):
        """Dump pressure logs and decode to structured records with altitude.
        Returns list of LOGRECORD with pressure, temperature, altitude fields."""
        raw_data = self.dumpd('pressure')
        csv_text = raw_data.decode('ascii', errors='ignore')
        return LOGFILE.parse_pressure_csv(csv_text)

    def pressure_log_to_csv(self):
        """Dump pressure logs and return CSV string.
        Header: log_datetime,pressure,temperature,altitude"""
        return self.dumpd('pressure').decode('ascii', errors='ignore')

    def dumpd_mortality(self):
        """Dump mortality logs and decode to structured records.
        Returns list of LOGRECORD with mortality fields."""
        raw_data = self.dumpd('mortality')
        return LOGFILE.decode(raw_data, log_type='mortality')

    def mortality_log_to_csv(self):
        """Dump mortality logs and return CSV string."""
        records = self.dumpd_mortality()
        lines = ['log_datetime,confidence,consecutive_days,status,last_activity,last_body_temp,last_lat,last_lon,last_eval_epoch']
        for r in records:
            dt = '{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(
                r.year, r.month, r.day, r.hours, r.mins, r.secs)
            lines.append('{},{},{},{},{},{},{:.6f},{:.6f},{}'.format(
                dt, r.confidence, r.consecutive_days, r.status_name,
                r.last_activity, r.last_body_temp, r.last_lat, r.last_lon,
                r.last_eval_epoch))
        return '\n'.join(lines)

    def sws_log_to_csv(self):
        """Dump SWS logs and return CSV string.
        Header: log_datetime,raw_adc,filtered_adc,threshold,hysteresis,air,water,calibrated,underwater,time_in_state,surface_level,contrast_x10,observed_peak,sample_delay_us"""
        return self.dumpd('sws').decode('ascii', errors='ignore')

    def paspw(self, json_file_data):
        resp = self._send_and_receive(
            self._encode_command('PASPW', args=[PASPW.encode(json_file_data)]),
            timeout=5.0
        )
        self._decode_response(resp)

    def erase(self, log_type):
        type_value = BaseEraseType.from_name(log_type).value
        resp = self._send_and_receive(self._encode_command('ERASE', args=[format(type_value, 'x')]))
        self._decode_response(resp)

    def factw(self):
        resp = self._send_and_receive(self._encode_command('FACTW'))
        self._decode_response(resp)

    def rstvw(self, var_id):
        resp = self._send_and_receive(self._encode_command('RSTVW', args=[str(var_id)]))
        self._decode_response(resp)

    def rstbw(self):
        resp = self._send_and_receive(self._encode_command('RSTBW'))
        self._decode_response(resp)

    def deplw(self):
        resp = self._send_and_receive(self._encode_command('DEPLW'))
        self._decode_response(resp)

    def scalw(self, sensor, step, value=0):
        type_value = BaseSensorCalType[sensor.upper()].value
        resp = self._send_and_receive(
            self._encode_command('SCALW', args=[str(type_value), str(step), str(value)])
        )
        self._decode_response(resp)

    def scalr(self, sensor, step):
        timeout = 25.0 if sensor == 'axl' else 10.0
        type_value = BaseSensorCalType[sensor.upper()].value
        resp = self._send_and_receive(
            self._encode_command('SCALR', args=[str(type_value), str(step)]),
            timeout=timeout
        )
        return self._decode_response(resp)

    def pwron(self, component):
        comp_value = ComponentPower[component.upper()].value
        resp = self._send_and_receive(
            self._encode_command('PWRON', args=[str(comp_value)])
        )
        self._decode_response(resp)

    def gnssi(self):
        """Read GNSS module info (unique_id, sw_version, hw_version).
        Requires GNSS to be powered on first (PWRON GNSS + ~2s wait)."""
        resp = self._send_and_receive(
            self._encode_command('GNSSI'),
            timeout=30.0
        )
        payload = self._decode_response(resp)
        parts = payload.split(',', 2)
        return {
            'unique_id': parts[0],
            'sw_version': parts[1],
            'hw_version': parts[2],
        }

    def gnssa(self):
        """Check GNSS AssistNow almanac status on device.
        Returns dict with present, file_size, total_records, valid_records, stale."""
        resp = self._send_and_receive(
            self._encode_command('GNSSA'),
            timeout=10.0
        )
        payload = self._decode_response(resp)
        parts = payload.split(',')
        return {
            'present': bool(int(parts[0])),
            'file_size': int(parts[1]),
            'total_records': int(parts[2]),
            'valid_records': int(parts[3]),
            'stale': bool(int(parts[4])),
        }

    def rtcw(self, timestamp=None):
        """Write RTC time. If timestamp is None, uses current UTC time."""
        import time as _time
        if timestamp is None:
            timestamp = int(_time.time())
        resp = self._send_and_receive(
            self._encode_command('RTCW', args=[str(timestamp)])
        )
        self._decode_response(resp)

    # Max payload size per modulation
    MODULATION_MAX_SIZE = {'LDK': 16, 'LDA2': 28, 'VLDA4': 28}

    def argostx(self, mod='LDA2', size=None, radioconf=None, tcxo=0):
        """Send Argos TX test packet.
        mod: LDK, LDA2 or VLDA4
        size: payload size in bytes (default: max for modulation)
        radioconf: 32-char hex string (optional, uses stored config if None)
        tcxo: TCXO warmup time in seconds (default: 0)
        """
        mod_upper = mod.upper()
        mod_value = ArgosModulation[mod_upper].value
        max_size = self.MODULATION_MAX_SIZE.get(mod_upper, 28)
        if size is None:
            size = max_size
        if size < 1 or size > max_size:
            raise ValueError(f"Size must be 1-{max_size} for {mod_upper}")
        if radioconf is not None:
            args = [str(mod_value), radioconf, str(size)]
        else:
            args = [str(mod_value), str(size)]
        if tcxo > 0:
            args.append(str(tcxo))
        resp = self._send_and_receive(
            self._encode_command('SATTX', args=args),
            timeout=30.0
        )
        self._decode_response(resp)

    def loratx(self, size=12):
        """Send a LoRa test transmission. size: payload bytes (1-222, depends on DR)."""
        resp = self._send_and_receive(
            self._encode_command('LORATX', args=[str(size)]),
            timeout=30.0
        )
        self._decode_response(resp)

    # RADIOCONF per modulation (16 bytes hex = 32 chars, from Kineis SDK kns_app_conf.h)
    RADIOCONF = {
        'LDK':   '03921fb104b92859209b18abd009de96',
        'LDA2':  '',  # TODO: fill from Kineis SDK
        'VLDA4': '',  # TODO: fill from Kineis SDK
    }

    def update_radioconf(self, mod):
        """Update RADIOCONF (IDP14) for given modulation. KIM2 applies at next power-on."""
        rconf = self.RADIOCONF.get(mod.upper(), '')
        if not rconf:
            raise ValueError(f'No RADIOCONF defined for modulation {mod}')
        self.parmw({'ARGOS_RADIOCONF': rconf})

    def satvf(self, force=0):
        """Verify satellite/LoRa module credentials: reads hardware values and checks
        against config store. force=0 read-only, force=1 rewrites config store into
        module on mismatch then re-reads. Returns dict with id, addr, seckey,
        radioconf, match (bool), forced (bool)."""
        resp = self._send_and_receive(
            self._encode_command('SATVF', args=[str(int(force))]),
            timeout=30.0
        )
        payload = self._decode_response(resp)
        parts = payload.split(',')
        return {
            'id': int(parts[0]),
            'addr': int(parts[1]),
            'seckey': parts[2],
            'radioconf': parts[3],
            'match': bool(int(parts[4])),
            'forced': bool(int(parts[5])),
        }

    def sensr(self, mask=SensrMask.ALL, timeout=60):
        """Read sensors. mask: bitmask (0x01=battery, 0x02=pressure, 0x04=gnss,
        0x08=accel, 0x10=thermistor, 0x20=sea_temp, 0x40=als, 0x80=ph, 0xFF=all).
        Response: 19 fields including sensor_status bitmask.
        Non-requested sensors return 0 in their fields."""
        resp = self._send_and_receive(
            self._encode_command('SENSR', args=[str(mask), str(timeout)]),
            timeout=float(timeout) + 5.0
        )
        payload = self._decode_response(resp)
        parts = payload.split(',')
        result = {
            'battery_mv': int(parts[0]),
            'battery_soc': int(parts[1]),
            'pressure_mbar': float(parts[2]),
            'temperature': float(parts[3]),
            'altitude': float(parts[4]),
            'latitude': float(parts[5]),
            'longitude': float(parts[6]),
            'hdop': float(parts[7]),
            'num_satellites': int(parts[8]),
            'accel_x': float(parts[9]),
            'accel_y': float(parts[10]),
            'accel_z': float(parts[11]),
            'accel_temp': float(parts[12]),
            'activity': int(parts[13]),
            'thermistor_temp': float(parts[14]),
        }
        # New fields (v2) — handle backward compat with old firmware
        if len(parts) > 15:
            result['sea_temp'] = float(parts[15])
            result['als_lux'] = float(parts[16])
            result['ph'] = float(parts[17])
            result['sensor_status'] = int(parts[18])
        return result

    def smddfu(self, action):
        """Send SMDDFU command.
        Actions: 0=ENTER, 1=EXIT, 2=STATUS, 3=UPDATE, 4=INFO, 5=VERSION"""
        resp = self._send_and_receive(
            self._encode_command('SMDDFU', args=[str(action)]),
            timeout=10.0
        )
        payload = self._decode_response(resp)
        parts = payload.split(',')
        return {
            'status': int(parts[0]),
            'dfu_mode': int(parts[1]),
            'progress': int(parts[2]),
            'info': parts[3] if len(parts) > 3 else ''
        }

    def wait_smd_dfu_result(self, timeout=180.0):
        """Wait for async SMDDFU notification after SPI firmware transfer.
        The tracker sends $O;SMDDFU#<len>;<status>,<dfu_mode>,<progress>,<info>\r
        asynchronously once DFU completes.
        Returns dict with status, dfu_mode, progress, info."""
        self._protocol = DTEProtocol()
        self._terminate = False
        self._event.clear()
        logger.debug('Waiting for async SMDDFU notification (timeout=%ss)', timeout)
        while True:
            is_set = self._event.wait(timeout)
            self._event.clear()
            if not is_set:
                raise TimeoutError(f'SMD DFU: no response after {timeout}s')
            if self._terminate:
                break
        resp = self._protocol.data()
        payload = self._decode_response(resp)
        parts = payload.split(',')
        return {
            'status': int(parts[0]),
            'dfu_mode': int(parts[1]),
            'progress': int(parts[2]),
            'info': ','.join(parts[3:]) if len(parts) > 3 else ''
        }

    def smdtst(self):
        """Send SMDTST command. Tests 14 SPI A+ commands on the SMD module."""
        resp = self._send_and_receive(
            self._encode_command('SMDTST'),
            timeout=30.0
        )
        return self._decode_response(resp)

    def satdp(self):
        """Start Doppler calibration. Periodic satellite TX until device reset.
        Async response: device waits for first TX result before responding."""
        resp = self._send_and_receive(
            self._encode_command('SATDP'),
            timeout=30.0
        )
        self._decode_response(resp)

    SWSCAL_STATUS = {0: 'IN_PROGRESS', 1: 'SUCCESS', 2: 'FAILED', 3: 'CANCELLED'}

    def swscal(self, start=True):
        """Start or cancel SWS guided calibration.
        start=True: begin calibration (async phases: air → water → result).
        start=False: cancel in-progress calibration.
        Returns immediately with initial ACK, then sends async push with result."""
        resp = self._send_and_receive(
            self._encode_command('SWSCAL', args=['1' if start else '0'])
        )
        self._decode_response(resp)

    def wait_swscal_result(self, timeout=60.0):
        """Wait for async SWSCAL result push.
        Returns dict with status (0-3), air (uint), water (uint), status_name."""
        resp = self._wait_for_push(timeout=timeout)
        if resp is None:
            raise TimeoutError(f'SWS calibration: no result after {timeout}s')
        payload = self._decode_response(resp)
        parts = payload.split(',')
        status = int(parts[0])
        return {
            'status': status,
            'status_name': self.SWSCAL_STATUS.get(status, f'UNKNOWN({status})'),
            'air': int(parts[1]),
            'water': int(parts[2]),
        }

    def swstst(self, start=True):
        """Start or stop SWS test mode. start=True to start, False to stop."""
        resp = self._send_and_receive(
            self._encode_command('SWSTST', args=['1' if start else '0'])
        )
        payload = self._decode_response(resp)
        return bool(int(payload))

    def _wait_for_push(self, timeout=5.0):
        """Wait for a single unsolicited pushed frame. Returns raw response string or None on timeout."""
        self._protocol = DTEProtocol()
        self._terminate = False
        self._event.clear()
        while True:
            is_set = self._event.wait(timeout)
            self._event.clear()
            if not is_set:
                return None
            if self._terminate:
                break
        return self._protocol.data()

    def swstst_stream(self, callback):
        """Start SWS test mode and stream pushed SWSST samples to callback.

        callback receives a dict with the same keys as swsst().
        Blocks until KeyboardInterrupt, then stops test mode.
        """
        self.swstst(start=True)
        try:
            while True:
                resp = self._wait_for_push(timeout=5.0)
                if resp is None:
                    continue
                try:
                    payload = self._decode_response(resp)
                    parts = payload.split(',')
                    if len(parts) < 13:
                        continue
                    callback(self._parse_swsst(parts))
                except Exception as e:
                    logger.debug('Failed to parse pushed SWSST frame: %s', e)
        except KeyboardInterrupt:
            pass
        finally:
            try:
                self.swstst(start=False)
            except Exception:
                pass

    def gnssbr(self, action=1):
        """Start or stop GNSS UART bridge.
        action=1: start bridge (powers on GNSS at 9600 baud, enters passthrough).
        action=0: stop bridge (GNSS off, return to DTE).
        In bridge mode, raw bytes are forwarded USB <-> GNSS UART.
        Send +++ to exit bridge mode."""
        resp = self._send_and_receive(
            self._encode_command('GNSSBR', args=[str(action)]),
            timeout=10.0
        )
        self._decode_response(resp)

    def lorabr(self, action=1):
        """Start or stop LoRa UART bridge.
        action=1: start bridge (pauses LoRa state machine, enters passthrough).
        action=0: stop bridge (return to DTE).
        In bridge mode, raw bytes are forwarded USB <-> RAK3172 UART.
        Send +++ to exit bridge mode."""
        resp = self._send_and_receive(
            self._encode_command('LORABR', args=[str(action)]),
            timeout=10.0
        )
        self._decode_response(resp)

    def kimbr(self, action=1):
        """Start or stop KIM2 UART bridge.
        action=1: start bridge (powers on KIM2, enters AT passthrough).
        action=0: stop bridge (return to DTE).
        In bridge mode, raw bytes are forwarded USB <-> KIM2 UART (line-based).
        Send +++\\r\\n to exit bridge mode."""
        resp = self._send_and_receive(
            self._encode_command('KIMBR', args=[str(action)]),
            timeout=10.0
        )
        self._decode_response(resp)

    SURFACE_LEVEL_NAMES = {
        0: 'NONE',
        1: 'L1_DROP_25',
        2: 'L2_CONSEC_5',
        3: 'L3_TREND_MA3',
        4: 'L4_DROP_BASELINE',
        5: 'L5_CUMUL_BACKUP',
    }

    @staticmethod
    def _parse_swsst(parts):
        """Parse SWSST fields (13 fields) into a dict."""
        return {
            'air': int(parts[0]),
            'water': int(parts[1]),
            'threshold': int(parts[2]),
            'hysteresis': int(parts[3]),
            'raw_adc': int(parts[4]),
            'filtered_adc': int(parts[5]),
            'calibrated': bool(int(parts[6])),
            'underwater': bool(int(parts[7])),
            'time_in_state': int(parts[8]),
            'surface_level': int(parts[9]),
            'contrast_x10': int(parts[10]),
            'observed_peak': int(parts[11]),
            'sample_delay_us': int(parts[12]),
        }

    def swsst(self):
        """Send SWSST command. Returns SWS (Salt Water Switch) status (13 fields)."""
        resp = self._send_and_receive(
            self._encode_command('SWSST'),
            timeout=10.0
        )
        payload = self._decode_response(resp)
        parts = payload.split(',')
        return self._parse_swsst(parts)
