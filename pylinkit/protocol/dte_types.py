import base64
import json
import binascii
import logging
import struct


logger = logging.getLogger(__name__)


class BOOLEAN():
    @staticmethod
    def encode(value):
        return '1' if int(value) else '0'

    @staticmethod
    def decode(value):
        return 1 if int(value) else 0


class UINT():
    @staticmethod
    def encode(value):
        return str(int(value))

    @staticmethod
    def decode(value):
        return int(value)


class FLOAT():
    @staticmethod
    def encode(value):
        return str(float(value))

    @staticmethod
    def decode(value):
        return float(value)


class DECIMAL(UINT):
    pass


class SAMPLINGPERIOD():
    """SWS sampling period in seconds. Float, range [0.1, 86400.0].
    Wire format compatible with both integer ("10") and float ("0.1") strings —
    firmware uses %g, so integer values come back without trailing ".0"."""
    MIN = 0.1
    MAX = 86400.0

    @staticmethod
    def encode(value):
        v = float(value)
        if v < SAMPLINGPERIOD.MIN or v > SAMPLINGPERIOD.MAX:
            raise ValueError(
                f'sampling period {v} s out of range '
                f'[{SAMPLINGPERIOD.MIN}, {SAMPLINGPERIOD.MAX}]'
            )
        return str(v)

    @staticmethod
    def decode(value):
        return float(value)


class TEXT():
    @staticmethod
    def encode(value):
        return value

    @staticmethod
    def decode(value):
        return value


class UPPERCASETEXT():
    @staticmethod
    def encode(value):
        return value.upper()

    @staticmethod
    def decode(value):
        return value.upper()


class ARGOSDUTYCYLE():
    @staticmethod
    def encode(value):
        return str(int(value, 16))

    @staticmethod
    def decode(value):
        return '{:06X}'.format(int(value))


class DATESTRING():
    @staticmethod
    def encode(value):
        return value

    @staticmethod
    def decode(value):
        return value


class BASE64():
    @staticmethod
    def encode(value):
        return base64.b64encode(value).decode('ascii')

    @staticmethod
    def decode(value):
        return base64.b64decode(value)


class ARGOSFREQ():
    ARGOS_FREQUENCY_OFFSET = 4016200
    ARGOS_FREQUENCY_MULT = 10000

    @staticmethod
    def encode(value):
        return str(int((float(value) * ARGOSFREQ.ARGOS_FREQUENCY_MULT) - ARGOSFREQ.ARGOS_FREQUENCY_OFFSET))

    @staticmethod
    def decode(value):
        return (float(value) + ARGOSFREQ.ARGOS_FREQUENCY_OFFSET) / ARGOSFREQ.ARGOS_FREQUENCY_MULT


class ARGOSPOWER():
    """
    POWER_3_MW = 1,
    POWER_40_MW,
    POWER_200_MW,
    POWER_500_MW,
    POWER_5_MW,
    POWER_50_MW,
    POWER_350_MW,
    POWER_750_MW,
    POWER_1000_MW,
    POWER_1500_MW
    """
    allowed = [-1, 3, 40, 200, 500, 5, 50, 350, 750, 1000, 1500]

    @staticmethod
    def encode(value):
        return str(ARGOSPOWER.allowed.index(int(value)))

    @staticmethod
    def decode(value):
        return ARGOSPOWER.allowed[int(value)]


class SENSORTXENABLEMODE():
    allowed = ['OFF', 'ONESHOT', 'MEAN', 'MEDIAN']

    @staticmethod
    def encode(value):
        return str(SENSORTXENABLEMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return SENSORTXENABLEMODE.allowed[int(value)]


class ARGOSMODE():
    allowed = ['OFF', 'PASS_PREDICTION', 'LEGACY', 'DUTY_CYCLE', 'DOPPLER', 'SURFACING_BURST']

    @staticmethod
    def encode(value):
        return str(ARGOSMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return ARGOSMODE.allowed[int(value)]


class ARGOSMODEZONE():
    allowed = ['OFF', 'PASS_PREDICTION', 'LEGACY', 'DUTY_CYCLE', 'DOPPLER', 'SURFACING_BURST']

    @staticmethod
    def encode(value):
        return str(ARGOSMODEZONE.allowed.index(value))

    @staticmethod
    def decode(value):
        return ARGOSMODEZONE.allowed[int(value)]


class ARGOSMODULATION():
    allowed = ['LDK', 'LDA2', 'VLDA4']

    @staticmethod
    def encode(value):
        return str(ARGOSMODULATION.allowed.index(value))

    @staticmethod
    def decode(value):
        return ARGOSMODULATION.allowed[int(value)]


class DEPTHPILE():
    # Index -> firmware value mapping. -1 entries are reserved/unused indices.
    allowed = [-1,1,2,3,4,-1,-1,-1,8,12,16,20,24]
    valid = (1, 2, 3, 4, 8, 12, 16, 20, 24)

    @staticmethod
    def encode(value):
        v = int(value)
        if v not in DEPTHPILE.valid:
            raise ValueError(
                f'DEPTH_PILE value {v} is invalid; allowed: {DEPTHPILE.valid}'
            )
        return str(DEPTHPILE.allowed.index(v))

    @staticmethod
    def decode(value):
        return DEPTHPILE.allowed[int(value)]


class AQPERIOD():
    # firmware index → value in minutes (non-sequential indices since v4.0.5)
    _index_to_minutes = {
        0: 0,
        1: 10, 2: 15, 3: 30, 4: 60, 5: 120,
        6: 180, 7: 240, 8: 360, 9: 720, 10: 1440,
        11: 1, 12: 2, 13: 5, 14: 20, 15: 45,
    }
    _minutes_to_index = {v: k for k, v in _index_to_minutes.items()}

    @staticmethod
    def encode(value):
        return str(AQPERIOD._minutes_to_index[int(value)])

    @staticmethod
    def decode(value):
        return AQPERIOD._index_to_minutes[int(value)]


class LEDMODE():
    allowed = ['OFF', '24HRS', -1, 'ALWAYS']

    @staticmethod
    def encode(value):
        return str(LEDMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return LEDMODE.allowed[int(value)]


class DEBUGMODE():
    allowed = ['UART', 'USB_CDC', 'BLE_NUS', 'NONE']

    @staticmethod
    def encode(value):
        return str(DEBUGMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return DEBUGMODE.allowed[int(value)]


class PRESSURESENSORLOGGINGMODE():
    allowed = ['ALWAYS', 'UW_THRESHOLD']

    @staticmethod
    def encode(value):
        return str(PRESSURESENSORLOGGINGMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return PRESSURESENSORLOGGINGMODE.allowed[int(value)]


class PRESSUREFULLSCALE():
    allowed = ['1260', '4060']

    @staticmethod
    def encode(value):
        return str(PRESSUREFULLSCALE.allowed.index(str(value)))

    @staticmethod
    def decode(value):
        return PRESSUREFULLSCALE.allowed[int(value)]


class ZONETYPE():
    allowed = ['NONE', 'CIRCLE']

    @staticmethod
    def encode(value):
        return str(ZONETYPE.allowed.index(value))

    @staticmethod
    def decode(value):
        return ZONETYPE.allowed[int(value)]


class GNSSFIXMODE():
    allowed = [-1, '2D', '3D', 'AUTO']

    @staticmethod
    def encode(value):
        return str(GNSSFIXMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return GNSSFIXMODE.allowed[int(value)]


class GNSSDYNMODEL():
    allowed = ['PORTABLE', -1, 'STATIONARY', 'PEDESTRIAN', 'AUTOMOTIVE', 'SEA', 'AIRBORNE_1G', 'AIRBORNE_2G', 'AIRBORNE_4G',
               'WRIST_WORN_WATCH', 'BIKE']

    @staticmethod
    def encode(value):
        return str(GNSSDYNMODEL.allowed.index(value))

    @staticmethod
    def decode(value):
        return GNSSDYNMODEL.allowed[int(value)]


class AXLPOWERMODE():
    allowed = ['NORMAL', 'LOWPOWER', 'AUTOLOWPOWER']

    @staticmethod
    def encode(value):
        return str(AXLPOWERMODE.allowed.index(value))

    @staticmethod
    def decode(value):
        return AXLPOWERMODE.allowed[int(value)]


class ACCRANGE():
    allowed = ['2G', '4G', '8G', '16G']

    @staticmethod
    def encode(value):
        return str(ACCRANGE.allowed.index(value))

    @staticmethod
    def decode(value):
        return ACCRANGE.allowed[int(value)]


class RSPBPACKETFORMAT():
    allowed = ['RSPB_LONG', 'RSPB_SHORT']

    @staticmethod
    def encode(value):
        return str(RSPBPACKETFORMAT.allowed.index(value))

    @staticmethod
    def decode(value):
        return RSPBPACKETFORMAT.allowed[int(value)]


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Packer():

    def __init__(self, data):
        self._data = [int(x) for x in data]
        self._pack_pos = 0
        self._unpack_pos = 0

    def result(self):
        return bytearray(self._data)

    def extract_bits(self, total_bits):
        result = 0
        start = self._unpack_pos
        num_bits = total_bits
        in_byte_offset = int(start / 8)
        in_bit_offset = start % 8
        out_bit_offset = 0
        n_bits = min(8 - in_bit_offset, num_bits)

        while (num_bits):
            mask = 0xFF >> (8 - n_bits)
            result |= (((self._data[in_byte_offset] >> (8-in_bit_offset-n_bits)) & mask) << (total_bits - out_bit_offset - n_bits))
            out_bit_offset = out_bit_offset + n_bits
            in_bit_offset = in_bit_offset + n_bits
            if (in_bit_offset >= 8):
                in_byte_offset += 1
                in_bit_offset %= 8
            num_bits -= n_bits
            n_bits = min(8 - in_bit_offset, num_bits)
        self._unpack_pos += total_bits
        return result

    def pack_bits(self, value, total_bits):
        start = self._unpack_pos
        num_bits = total_bits
        out_byte_offset = int(start / 8)
        out_bit_offset = start % 8
        in_bit_offset = 0
        n_bits = min(8 - out_bit_offset, num_bits)

        while (num_bits):
            mask = (0xFFFFFFFF >> (total_bits - in_bit_offset - n_bits)) if ((total_bits - in_bit_offset) == 32) else (((1 << (total_bits - in_bit_offset))-1) >> (total_bits - in_bit_offset - n_bits))
            self._data[out_byte_offset] |= (((value >> (total_bits - in_bit_offset - n_bits)) & mask) << (8-out_bit_offset-n_bits))
            out_bit_offset = out_bit_offset + n_bits
            in_bit_offset = in_bit_offset + n_bits

            if (out_bit_offset >= 8):
                out_byte_offset += 1
                out_bit_offset = out_bit_offset % 8
            num_bits -= n_bits
            n_bits = min(8 - out_bit_offset, num_bits)

        self._unpack_pos += total_bits


class PASPW():

    @staticmethod
    def encode(value):
        d = json.loads(value)
        allcast = d['allcastFormats']
        hex_bytes = ''
        for entry in allcast:
            for x in entry['adaptedOrbitParametersBurst']:
                hex_bytes += entry['adaptedOrbitParametersBurst'][x]
            for x in entry['constellationStatusBurst']:
                csb = entry['constellationStatusBurst'][x]
                if len(csb) & 1:
                    logger.warning('Stuffing CSB record %s with 0000 missing bits', x)
                    csb += '0'
                hex_bytes += csb
        logger.debug('Allcast packet: %s', hex_bytes)
        return base64.b64encode(binascii.unhexlify(hex_bytes)).decode('ascii')


PRESSURE_SEA_LEVEL_DEFAULT = 1013.25


def barometric_altitude(pressure_hpa, sea_level_hpa=PRESSURE_SEA_LEVEL_DEFAULT):
    """Compute altitude in meters from pressure using the barometric formula.
    altitude = 44330 * (1 - (P/P0)^(1/5.255))"""
    if pressure_hpa <= 0 or sea_level_hpa <= 0:
        return 0.0
    return 44330.0 * (1.0 - (pressure_hpa / sea_level_hpa) ** (1.0 / 5.255))


class LOGRECORD(dotdict):
    pass


class LOGFILE():
    LOG_TYPES = ['LOG_GPS',
                 'LOG_STARTUP',
                 'LOG_ARTIC',
                 'LOG_UNDERWATER',
                 'LOG_BATTERY',
                 'LOG_STATE',
                 'LOG_ZONE',
                 'LOG_OTA_UPDATE',
                 'LOG_BLE',
                 'LOG_ERROR',
                 'LOG_WARN',
                 'LOG_INFO',
                 'LOG_TRACE',
                 'LOG_RESERVED_13',
                 'LOG_MORTALITY']

    MORTALITY_STATUS_NAMES = {0: 'ALIVE', 1: 'SUSPECTED', 2: 'CONFIRMED'}

    @staticmethod
    def decode_log_gps(payload, r):
        r.batt_voltage, r.iTOW, r.fix_year, r.fix_month, r.fix_day, r.fix_hour, r.fix_min, r.fix_sec, r.valid, r.onTime, r.ttff, r.fixType, _, _, _, r.numSV, \
        r.lon, r.lat, r.height, r.hMSL, r.hAcc, r.vAcc, r.velN, r.velE, r.velD, r.gSpeed, r.headMot, \
        r.sAcc, r.headAcc, r.pDOP, r.vDOP, r.hDOP, r.headVeh = \
            struct.unpack('<xHIHBBBBBBIiBBBBBddiiIIiiiifIfffff', payload[:104])
        return r

    @staticmethod
    def decode_log_pressure(payload_text, r):
        """Parse pressure log payload (CSV text: pressure,temperature[,altitude]).
        Old format: 2 fields (pressure, temperature).
        New format: 3 fields (pressure, temperature, altitude).
        For old format, altitude is computed via barometric formula."""
        parts = payload_text.strip().split(',')
        r.pressure = float(parts[0])
        r.temperature = float(parts[1])
        if len(parts) >= 3:
            r.altitude = float(parts[2])
        else:
            r.altitude = barometric_altitude(r.pressure)
        return r

    @staticmethod
    def decode_log_mortality(payload, r):
        """Parse mortality log payload (26 bytes binary)."""
        r.confidence, r.consecutive_days, r.status, r.last_activity, \
        r.last_body_temp, r.last_lat, r.last_lon, r.last_eval_epoch = \
            struct.unpack('<BBBBHddI', payload[:26])
        r.status_name = LOGFILE.MORTALITY_STATUS_NAMES.get(r.status, f'UNKNOWN({r.status})')
        return r

    @staticmethod
    def decode(data, log_type=None):
        records = []
        while data:
            r = LOGRECORD()
            r.day, r.month, r.year, r.hours, r.mins, r.secs, r.log_t, payload_size = struct.unpack('<BBHBBBBB', data[:9])
            r.log_t = LOGFILE.LOG_TYPES[r.log_t]
            payload_bytes = data[9:9+payload_size]
            if r.log_t == 'LOG_GPS':
                LOGFILE.decode_log_gps(payload_bytes, r)
            elif r.log_t == 'LOG_MORTALITY':
                LOGFILE.decode_log_mortality(payload_bytes, r)
            elif log_type == 'pressure':
                payload_text = payload_bytes.decode('ascii', errors='ignore')
                LOGFILE.decode_log_pressure(payload_text, r)
            else:
                r.message = payload_bytes.decode('ascii', errors='ignore')
            records.append(r)
            data = data[9+payload_size:]
        return records

    @staticmethod
    def parse_pressure_csv(csv_text):
        """Parse pressure CSV from DUMPD into LOGRECORD list.
        CSV format: log_datetime,pressure,temperature[,altitude]
        Datetime format: DD/MM/YYYY HH:MM:SS"""
        records = []
        lines = csv_text.strip().split('\n')
        for line in lines[1:]:  # skip header
            if not line.strip():
                continue
            r = LOGRECORD()
            parts = line.split(',')
            dt_str = parts[0].strip()
            date_part, time_part = dt_str.split(' ')
            d, m, y = date_part.split('/')
            h, mi, s = time_part.split(':')
            r.day = int(d)
            r.month = int(m)
            r.year = int(y)
            r.hours = int(h)
            r.mins = int(mi)
            r.secs = int(s)
            r.pressure = float(parts[1])
            r.temperature = float(parts[2])
            if len(parts) >= 4 and parts[3].strip():
                r.altitude = float(parts[3])
            else:
                r.altitude = barometric_altitude(r.pressure)
            records.append(r)
        return records

    @staticmethod
    def pressure_records_to_csv(records):
        """Convert pressure log records to CSV string.
        Header: log_datetime,pressure,temperature,altitude"""
        lines = ['log_datetime,pressure,temperature,altitude']
        for r in records:
            dt = '{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(
                r.year, r.month, r.day, r.hours, r.mins, r.secs)
            lines.append('{},{:.2f},{:.2f},{:.2f}'.format(
                dt, r.pressure, r.temperature, r.altitude))
        return '\n'.join(lines)
