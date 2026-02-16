import re
import logging
from threading import Event

from .dte_protocol import DTEProtocol, DTEProtocolError
from .dte_params import DTEParamMap
from .dte_types import BASE64, PASPW
from ..enums import BaseLogDType, BaseEraseType, BaseSensorCalType, ComponentPower, ArgosModulation, SensrMask, DTEError

logger = logging.getLogger(__name__)


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
        self._event.clear()

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
        fail_regexp = r'^\$N;(?P<cmd>[A-Z]+)#(?P<len>[0-9a-fA-F]+);(?P<error>[0-9]+)\r$'
        success = re.match(success_regexp, resp)
        if success:
            return success.group('payload')
        fail = re.match(fail_regexp, resp)
        if fail:
            cmd = fail.group('cmd')
            error_code = int(fail.group('error'))
            try:
                err = DTEError(error_code)
                raise Exception(f'{cmd} - error {error_code}: {err.message}')
            except ValueError:
                raise Exception(f'{cmd} - error {error_code}: Unknown error')
        raise Exception('Bad response - {}'.format(resp))

    def _decode_multi_response(self, resp):
        return [self._decode_response(r + '\r') for r in resp.split('\r') if r]

    def _decode_key_values(self, payload):
        m = {}
        for x in payload.strip().split(','):
            key, value = x.split('=')
            try:
                m[DTEParamMap.key_to_param(key)] = DTEParamMap.decode(key, value)
            except Exception:
                continue
        return m

    def parmr(self, params=[]):
        resp = self._send_and_receive(self._encode_command('PARMR', params=params))
        return self._decode_key_values(self._decode_response(resp))

    def statr(self, params=[]):
        resp = self._send_and_receive(self._encode_command('STATR', params=params))
        return self._decode_key_values(self._decode_response(resp))

    def parmw(self, param_values={}):
        resp = self._send_and_receive(self._encode_command('PARMW', param_values=param_values))
        self._decode_response(resp)

    def dumpd(self, log_type='sensor'):
        type_value = BaseLogDType.from_name(log_type).value
        resp = self._send_and_receive(
            self._encode_command('DUMPD', args=[str(type_value)]),
            timeout=60.0
        )
        responses = self._decode_multi_response(resp)
        raw_data = b''
        for r in responses:
            _, _, data = r.split(',')
            decoded_data = BASE64.decode(data)
            raw_data += decoded_data
        return raw_data

    def paspw(self, json_file_data):
        resp = self._send_and_receive(
            self._encode_command('PASPW', args=[PASPW.encode(json_file_data)]),
            timeout=5.0
        )
        self._decode_response(resp)

    def erase(self, log_type):
        type_value = BaseEraseType.from_name(log_type).value
        resp = self._send_and_receive(self._encode_command('ERASE', args=[str(type_value)]))
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

    def argostx(self, mod, power, freq, size, tcxo):
        mod_value = ArgosModulation[mod.upper()].value
        resp = self._send_and_receive(
            self._encode_command('SATTX', args=[str(mod_value), str(power), str(freq), str(size), str(tcxo)]),
            timeout=30.0
        )
        self._decode_response(resp)

    def smdcd(self, id, addr, seckey, radioconf):
        resp = self._send_and_receive(
            self._encode_command('SMDCD', args=[str(id), str(addr), str(seckey), str(radioconf)]),
            timeout=30.0
        )
        self._decode_response(resp)

    def sensr(self, mask=SensrMask.ALL, timeout=60):
        """Read sensors. mask: bitmask (1=battery, 2=pressure, 4=gnss, 7=all).
        Returns dict with battery_mv, battery_soc, pressure_mbar, temperature_c,
        latitude, longitude, hdop, num_satellites."""
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
            'temperature_c': float(parts[3]),
            'latitude': float(parts[4]),
            'longitude': float(parts[5]),
            'hdop': float(parts[6]),
            'num_satellites': int(parts[7]),
        }
        if len(parts) > 8:
            result['accel_x'] = float(parts[8])
            result['accel_y'] = float(parts[9])
            result['accel_z'] = float(parts[10])
            result['accel_temp'] = float(parts[11])
            result['activity'] = int(parts[12])
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

    def smdtst(self):
        """Send SMDTST command. Tests 14 SPI A+ commands on the SMD module."""
        resp = self._send_and_receive(
            self._encode_command('SMDTST'),
            timeout=30.0
        )
        return self._decode_response(resp)
