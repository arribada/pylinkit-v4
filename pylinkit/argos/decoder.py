"""Argos / CLS satellite payload decoder.

Implements the message format described on the linkit-v4-core wiki page
"10 - Satellite Message Format". Each ``decode_*`` helper takes a raw
payload (``bytes``) and returns a ``dict`` of decoded fields.

Modulation summary:

- VLDA4 = 3 bytes  (Doppler / RSPB Doppler), no firmware CRC
- LDK   = 16 bytes (Short / RSPB Short / CloudLocate MEASC12), no firmware CRC
- LDA2  = 24 bytes (Long, Sensor, Fastloc, RSPB Long, CloudLocate MEAS20),
                   firmware CRC8 in byte 23

The module is self-contained and has no external dependencies.
"""


# --- bit reader (MSB-first, big-endian) --------------------------------------

class BitReader:
    """Sequential MSB-first reader over a byte buffer."""

    def __init__(self, data):
        self._data = bytes(data)
        self._pos = 0  # current bit offset

    def read(self, n_bits):
        if n_bits <= 0:
            return 0
        result = 0
        end = self._pos + n_bits
        if end > len(self._data) * 8:
            raise ValueError(
                f'BitReader: cannot read {n_bits} bits at offset {self._pos} '
                f'(buffer is {len(self._data)} bytes / {len(self._data) * 8} bits)'
            )
        for _ in range(n_bits):
            byte_idx = self._pos >> 3
            bit_idx = 7 - (self._pos & 7)
            result = (result << 1) | ((self._data[byte_idx] >> bit_idx) & 1)
            self._pos += 1
        return result

    def skip(self, n_bits):
        self._pos += n_bits

    def seek(self, bit_offset):
        self._pos = bit_offset

    @property
    def position(self):
        return self._pos


# --- LDA2 CRC8 ---------------------------------------------------------------

def lda2_crc8(payload23):
    """Compute the LDA2 CRC8 over the first 23 bytes of an LDA2 frame.

    The polynomial is the Argos-historic CRC8 expressed as ``0x1070 << 3 = 0x8380``,
    init = 0, calculated bit-by-bit MSB-first. The 16-bit working register is
    XORed with each byte shifted left by 8 then clocked 8 times; the high byte
    of the final register is the 8-bit CRC.
    """
    payload23 = bytes(payload23)
    if len(payload23) != 23:
        raise ValueError(f'lda2_crc8 expects 23 bytes, got {len(payload23)}')
    crc = 0
    for b in payload23:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc ^= 0x8380
            crc = (crc << 1) & 0xFFFF
    return (crc >> 8) & 0xFF


def verify_lda2(frame24):
    """Return True if the CRC8 in byte 23 matches the computed value."""
    frame24 = bytes(frame24)
    if len(frame24) != 24:
        raise ValueError(f'verify_lda2 expects 24 bytes, got {len(frame24)}')
    return lda2_crc8(frame24[:23]) == frame24[23]


# --- field decoders ----------------------------------------------------------

# Battery encoding: encoded = (mV - 2700) / 20  =>  mV = encoded * 20 + 2700
# Range: 0..127 codes  =>  2700..5240 mV
def _decode_battery(raw_7bit):
    return raw_7bit * 20 + 2700


# Speed encoding (per wiki): encoded = (m/s * 3600) / 2000000
# The decode formula returns "mm/s units" — see wiki "Common Field Encodings".
def _decode_speed_mms(raw_7bit):
    return raw_7bit * 2000000 // 3600


# Heading: encoded = degrees / 1.42  =>  degrees = raw * 1.42  (0..360)
def _decode_heading(raw_8bit):
    return raw_8bit * 1.42


# Altitude: encoded = mm / (1000 * 40)  =>  meters = raw * 40
# 255 = no 3D fix
def _decode_altitude(raw_8bit):
    if raw_8bit == 0xFF:
        return None
    return raw_8bit * 40


# GPS coordinate decoding (signed: high bit = sign).
def _decode_lat(raw_21bit):
    if raw_21bit == 0x1FFFFF:
        return None
    sign_bit = 1 << 20
    if raw_21bit & sign_bit:
        return -(raw_21bit & (sign_bit - 1)) / 10000.0
    return raw_21bit / 10000.0


def _decode_lon(raw_22bit):
    if raw_22bit == 0x3FFFFF:
        return None
    sign_bit = 1 << 21
    if raw_22bit & sign_bit:
        return -(raw_22bit & (sign_bit - 1)) / 10000.0
    return raw_22bit / 10000.0


# Pressure: encoded = hPa * 1000  =>  hPa = raw / 1000.0
def _decode_pressure_hpa(raw_15bit):
    return raw_15bit / 1000.0


# Temperatures with +40 offset, 14 bits, ×100: raw = (°C + 40) * 100
def _decode_temp_offset40(raw_14bit):
    return raw_14bit / 100.0 - 40.0


# Sea temperature: 21 bits, +126 offset, ×1000
def _decode_sea_temp(raw_21bit):
    return raw_21bit / 1000.0 - 126.0


# pH: 14 bits, ×1000
def _decode_ph(raw_14bit):
    return raw_14bit / 1000.0


# AXL axis: 15 bits, encoded = (g + g_range) * 1000
def _decode_axl_axis(raw_15bit, g_range):
    return raw_15bit / 1000.0 - g_range


# Delta-time-loc: 4-bit firmware index → minutes between fixes
DELTA_TIME_LOC_MINUTES = {
    0: 0,
    1: 10, 2: 15, 3: 30, 4: 60, 5: 120,
    6: 180, 7: 240, 8: 360, 9: 720, 10: 1440,
    11: 1, 12: 2, 13: 5, 14: 20, 15: 45,
}


# --- message-type decoders ---------------------------------------------------

def decode_short(payload12):
    """Type 0 - Short Packet (LDK, 96 bits / 12 bytes)."""
    payload12 = bytes(payload12)
    if len(payload12) != 12:
        raise ValueError(f'short packet expects 12 bytes, got {len(payload12)}')
    r = BitReader(payload12)
    header = r.read(3)
    if header != 0b000:
        raise ValueError(f'short packet: expected header 0b000, got {bin(header)}')
    return {
        'message_type': 'short',
        'modulation': 'LDK',
        'header': header,
        'day': r.read(5),
        'hour': r.read(5),
        'minute': r.read(6),
        'latitude': _decode_lat(r.read(21)),
        'longitude': _decode_lon(r.read(22)),
        'speed_mm_s': _decode_speed_mms(r.read(7)),
        'out_of_zone': bool(r.read(1)),
        'heading_deg': _decode_heading(r.read(8)),
        'altitude_m': _decode_altitude(r.read(8)),
        'battery_mv': _decode_battery(r.read(7)),
        'low_battery': bool(r.read(1)),
    }


def decode_long(payload24):
    """Long Packet (LDA2, 24 bytes, no header). Up to 3 GPS fixes.

    Includes CRC8 verification.
    """
    payload24 = bytes(payload24)
    if len(payload24) != 24:
        raise ValueError(f'long packet expects 24 bytes, got {len(payload24)}')
    crc_valid = verify_lda2(payload24)
    r = BitReader(payload24)
    day = r.read(5)
    hour = r.read(5)
    minute = r.read(6)
    gps0_lat = _decode_lat(r.read(21))
    gps0_lon = _decode_lon(r.read(22))
    gps0_speed = _decode_speed_mms(r.read(7))
    out_of_zone = bool(r.read(1))
    battery_mv = _decode_battery(r.read(7))
    low_battery = bool(r.read(1))
    delta_time_loc_code = r.read(4)
    delta_time_loc_min = DELTA_TIME_LOC_MINUTES.get(delta_time_loc_code)
    gps1_lat = _decode_lat(r.read(21))
    gps1_lon = _decode_lon(r.read(22))
    gps2_lat = _decode_lat(r.read(21))
    gps2_lon = _decode_lon(r.read(22))
    return {
        'message_type': 'long',
        'modulation': 'LDA2',
        'crc_valid': crc_valid,
        'day': day,
        'hour': hour,
        'minute': minute,
        'gps0': {'latitude': gps0_lat, 'longitude': gps0_lon, 'speed_mm_s': gps0_speed},
        'gps1': {'latitude': gps1_lat, 'longitude': gps1_lon},
        'gps2': {'latitude': gps2_lat, 'longitude': gps2_lon},
        'out_of_zone': out_of_zone,
        'battery_mv': battery_mv,
        'low_battery': low_battery,
        'delta_time_loc_code': delta_time_loc_code,
        'delta_time_loc_minutes': delta_time_loc_min,
        'crc8': payload24[23],
    }


def decode_sensor(payload24, sensor_mask=None, axl_g_range=16):
    """Type 1 - Sensor Packet (LDA2, 24 bytes, no header in payload).

    The set of sensors actually present is *not* embedded in the packet:
    the decoder needs the device's sensor enable mask to know which fields
    to read. ``sensor_mask`` is a dict with the sensors that were enabled
    when the packet was emitted, e.g.::

        {'als': True, 'ph': False, 'pressure': True, 'sea_temp': False,
         'thermistor': False, 'axl': True}

    If ``sensor_mask`` is None, the decoder returns only the base fields and
    leaves the sensor bytes as raw hex in ``sensor_bits_remaining``.
    Includes CRC8 verification.
    """
    payload24 = bytes(payload24)
    if len(payload24) != 24:
        raise ValueError(f'sensor packet expects 24 bytes, got {len(payload24)}')
    crc_valid = verify_lda2(payload24)
    r = BitReader(payload24)
    out = {
        'message_type': 'sensor',
        'modulation': 'LDA2',
        'crc_valid': crc_valid,
        'day': r.read(5),
        'hour': r.read(5),
        'minute': r.read(6),
        'latitude': _decode_lat(r.read(21)),
        'longitude': _decode_lon(r.read(22)),
        'speed_mm_s': _decode_speed_mms(r.read(7)),
        'out_of_zone': bool(r.read(1)),
        'battery_mv': _decode_battery(r.read(7)),
        'low_battery': bool(r.read(1)),
        'crc8': payload24[23],
    }

    # Bit budget: 184 (CRC8 reserves the last 8). Bits 75..183 hold sensors.
    if sensor_mask is None:
        out['sensor_bits_remaining'] = payload24[9:23].hex()
        out['sensors_decoded'] = False
        return out

    sensors = {}
    bits_left = 184 - r.position

    def _enabled(name):
        return bool(sensor_mask.get(name, False))

    if _enabled('als') and bits_left >= 17:
        sensors['als_lux'] = r.read(17)
        bits_left -= 17
    if _enabled('ph') and bits_left >= 14:
        sensors['ph'] = _decode_ph(r.read(14))
        bits_left -= 14
    if _enabled('pressure') and bits_left >= 29:
        sensors['pressure_hpa'] = _decode_pressure_hpa(r.read(15))
        sensors['pressure_temp_c'] = _decode_temp_offset40(r.read(14))
        bits_left -= 29
    if _enabled('sea_temp') and bits_left >= 21:
        sensors['sea_temp_c'] = _decode_sea_temp(r.read(21))
        bits_left -= 21
    if _enabled('thermistor') and bits_left >= 14:
        sensors['thermistor_c'] = _decode_temp_offset40(r.read(14))
        bits_left -= 14
    if _enabled('axl'):
        # AXL temp may be dropped if budget is tight (firmware behavior)
        if bits_left >= 14 + 15 + 15 + 15 + 8:
            sensors['axl_temp_c'] = _decode_temp_offset40(r.read(14))
            bits_left -= 14
        else:
            sensors['axl_temp_c'] = None  # firmware dropped it
        if bits_left >= 15 + 15 + 15 + 8:
            sensors['axl_x_g'] = _decode_axl_axis(r.read(15), axl_g_range)
            sensors['axl_y_g'] = _decode_axl_axis(r.read(15), axl_g_range)
            sensors['axl_z_g'] = _decode_axl_axis(r.read(15), axl_g_range)
            sensors['axl_activity'] = r.read(8)
            bits_left -= 15 + 15 + 15 + 8

    out['sensors'] = sensors
    out['sensors_decoded'] = True
    return out


def decode_fastloc(payload24):
    """Type 2 - Fastloc Packet (LDA2, 24 bytes, header 0b010)."""
    payload24 = bytes(payload24)
    if len(payload24) != 24:
        raise ValueError(f'fastloc packet expects 24 bytes, got {len(payload24)}')
    crc_valid = verify_lda2(payload24)
    r = BitReader(payload24)
    header = r.read(3)
    if header != 0b010:
        raise ValueError(f'fastloc: expected header 0b010, got {bin(header)}')
    return {
        'message_type': 'fastloc',
        'modulation': 'LDA2',
        'crc_valid': crc_valid,
        'header': header,
        'day': r.read(5),
        'hour': r.read(5),
        'minute': r.read(6),
        'latitude': _decode_lat(r.read(21)),
        'longitude': _decode_lon(r.read(22)),
        'speed_mm_s': _decode_speed_mms(r.read(7)),
        'heading_deg': _decode_heading(r.read(8)),
        'altitude_m': _decode_altitude(r.read(8)),
        'battery_mv': _decode_battery(r.read(7)),
        'low_battery': bool(r.read(1)),
        'fix_type': r.read(2),  # 0=none, 1=DR, 2=2D, 3=3D
        'num_satellites': r.read(4),
        'h_acc_m': r.read(16),
        'v_acc_m': r.read(16),
        'p_dop': r.read(8) / 10.0,
        'h_dop': r.read(8) / 10.0,
        'gps_on_time_s': r.read(10),
        'crc8': payload24[23],
    }


def decode_doppler(payload3):
    """Type 3 - Doppler Packet (VLDA4, 3 bytes, no header)."""
    payload3 = bytes(payload3)
    if len(payload3) != 3:
        raise ValueError(f'doppler packet expects 3 bytes, got {len(payload3)}')
    r = BitReader(payload3)
    return {
        'message_type': 'doppler',
        'modulation': 'VLDA4',
        'last_position_index': r.read(8),
        'battery_mv': _decode_battery(r.read(7)),
        'low_battery': bool(r.read(1)),
    }


def decode_rspb_long(payload24):
    """Type 4 - RSPB Long Packet (LDA2, 24 bytes, header 0b100)."""
    payload24 = bytes(payload24)
    if len(payload24) != 24:
        raise ValueError(f'rspb_long packet expects 24 bytes, got {len(payload24)}')
    crc_valid = verify_lda2(payload24)
    r = BitReader(payload24)
    header = r.read(3)
    if header != 0b100:
        raise ValueError(f'rspb_long: expected header 0b100, got {bin(header)}')
    return {
        'message_type': 'rspb_long',
        'modulation': 'LDA2',
        'crc_valid': crc_valid,
        'header': header,
        'day': r.read(5),
        'hour': r.read(5),
        'minute': r.read(6),
        'latitude': _decode_lat(r.read(21)),
        'longitude': _decode_lon(r.read(22)),
        'speed_mm_s': _decode_speed_mms(r.read(7)),
        'out_of_zone': bool(r.read(1)),
        'battery_mv': _decode_battery(r.read(7)),
        'low_battery': bool(r.read(1)),
        'pressure_hpa': _decode_pressure_hpa(r.read(15)),
        'pressure_temp_c': _decode_temp_offset40(r.read(14)),
        'body_temp_c': _decode_temp_offset40(r.read(14)),
        'axl_x_g': _decode_axl_axis(r.read(15), 16),
        'axl_y_g': _decode_axl_axis(r.read(15), 16),
        'axl_z_g': _decode_axl_axis(r.read(15), 16),
        'axl_activity': r.read(8),
        'mortality_pct': r.read(7),
        'crc8': payload24[23],
    }


def decode_rspb_short(payload16):
    """Type 5 - RSPB Short Packet (LDK, 16 bytes, header 0b101)."""
    payload16 = bytes(payload16)
    if len(payload16) != 16:
        raise ValueError(f'rspb_short packet expects 16 bytes, got {len(payload16)}')
    r = BitReader(payload16)
    header = r.read(3)
    if header != 0b101:
        raise ValueError(f'rspb_short: expected header 0b101, got {bin(header)}')
    return {
        'message_type': 'rspb_short',
        'modulation': 'LDK',
        'header': header,
        'day': r.read(5),
        'hour': r.read(5),
        'minute': r.read(6),
        'latitude': _decode_lat(r.read(21)),
        'longitude': _decode_lon(r.read(22)),
        'speed_mm_s': _decode_speed_mms(r.read(7)),
        'out_of_zone': bool(r.read(1)),
        'battery_mv': _decode_battery(r.read(7)),
        'low_battery': bool(r.read(1)),
        'pressure_hpa': _decode_pressure_hpa(r.read(15)),
        'body_temp_c': _decode_temp_offset40(r.read(14)),
        'axl_activity': r.read(8),
        'mortality_pct': r.read(7),
    }


def decode_rspb_doppler(payload3):
    """Type 6 - RSPB Doppler Packet (VLDA4, 3 bytes, header 0b110)."""
    payload3 = bytes(payload3)
    if len(payload3) != 3:
        raise ValueError(f'rspb_doppler packet expects 3 bytes, got {len(payload3)}')
    r = BitReader(payload3)
    header = r.read(3)
    if header != 0b110:
        raise ValueError(f'rspb_doppler: expected header 0b110, got {bin(header)}')
    return {
        'message_type': 'rspb_doppler',
        'modulation': 'VLDA4',
        'header': header,
        'battery_soc_pct': r.read(7),
        'activity': r.read(7) * 2,  # encoded as activity / 2
        'mortality_pct': r.read(7),
    }


def decode_cloudlocate(payload):
    """Type 7 - CloudLocate Packet (LDK 16B / LDA2 24B, header 0b111).

    The opaque u-blox blob (MEASC12 12 bytes / MEAS20 20 bytes) is
    returned as a hex string under ``ublox_payload_hex`` for upstream
    processing by the CloudLocate service. The blob itself is NOT decoded.
    """
    payload = bytes(payload)
    r = BitReader(payload)
    header = r.read(3)
    if header != 0b111:
        raise ValueError(f'cloudlocate: expected header 0b111, got {bin(header)}')
    fmt = r.read(2)

    if fmt == 0b00 and len(payload) == 16:
        # MEASC12 (LDK)
        blob = bytearray()
        for _ in range(12):
            blob.append(r.read(8))
        return {
            'message_type': 'cloudlocate_measc12',
            'modulation': 'LDK',
            'header': header,
            'format': fmt,
            'ublox_payload_hex': bytes(blob).hex(),
            'battery_mv': _decode_battery(r.read(7)),
            'low_battery': bool(r.read(1)),
        }
    if fmt == 0b01 and len(payload) == 24:
        # MEAS20 (LDA2)
        crc_valid = verify_lda2(payload)
        blob = bytearray()
        for _ in range(20):
            blob.append(r.read(8))
        return {
            'message_type': 'cloudlocate_meas20',
            'modulation': 'LDA2',
            'crc_valid': crc_valid,
            'header': header,
            'format': fmt,
            'ublox_payload_hex': bytes(blob).hex(),
            'battery_mv': _decode_battery(r.read(7)),
            'low_battery': bool(r.read(1)),
            'crc8': payload[23],
        }
    raise ValueError(
        f'cloudlocate: unsupported (format={bin(fmt)}, size={len(payload)} bytes)'
    )


# --- top-level dispatch -----------------------------------------------------

# Recognised type names for ``msg_type``.
MSG_TYPES = (
    'auto', 'short', 'long', 'sensor', 'fastloc', 'doppler',
    'rspb_long', 'rspb_short', 'rspb_doppler', 'cloudlocate',
)


def _coerce_payload(payload):
    """Accept hex string or bytes-like, return bytes."""
    if isinstance(payload, str):
        clean = payload.replace(' ', '').replace(':', '').replace('-', '')
        return bytes.fromhex(clean)
    return bytes(payload)


def decode(payload, msg_type='auto', sensor_mask=None, axl_g_range=16):
    """Decode an Argos satellite payload.

    payload: bytes or hex string (whitespace, ``:`` and ``-`` accepted)
    msg_type: 'auto' (default) or one of the names in MSG_TYPES.

    Auto-detection rules:

        - 3  bytes -> VLDA4: header 0b110 -> rspb_doppler, else doppler
        - 12 bytes -> LDK:   short packet (header 0b000)
        - 16 bytes -> LDK:   header 0b101 -> rspb_short, 0b111 -> cloudlocate (MEASC12)
        - 24 bytes -> LDA2:  header 0b010 -> fastloc, 0b100 -> rspb_long,
                             0b111 -> cloudlocate (MEAS20).
                             Long Packet and Sensor Packet share the same
                             first 75 bits and cannot be distinguished from
                             the bytes alone -- pass msg_type='long' or
                             'sensor' explicitly.

    Sensor packets need the device's sensor enable mask to be decoded
    fully (see decode_sensor for the schema).
    """
    data = _coerce_payload(payload)
    if msg_type not in MSG_TYPES:
        raise ValueError(f'unknown msg_type {msg_type!r}, expected one of {MSG_TYPES}')

    if msg_type == 'short':
        return decode_short(data)
    if msg_type == 'long':
        return decode_long(data)
    if msg_type == 'sensor':
        return decode_sensor(data, sensor_mask=sensor_mask, axl_g_range=axl_g_range)
    if msg_type == 'fastloc':
        return decode_fastloc(data)
    if msg_type == 'doppler':
        return decode_doppler(data)
    if msg_type == 'rspb_long':
        return decode_rspb_long(data)
    if msg_type == 'rspb_short':
        return decode_rspb_short(data)
    if msg_type == 'rspb_doppler':
        return decode_rspb_doppler(data)
    if msg_type == 'cloudlocate':
        return decode_cloudlocate(data)

    # auto
    size = len(data)
    if size == 3:
        header = data[0] >> 5
        if header == 0b110:
            return decode_rspb_doppler(data)
        return decode_doppler(data)
    if size == 12:
        return decode_short(data)
    if size == 16:
        header = data[0] >> 5
        if header == 0b101:
            return decode_rspb_short(data)
        if header == 0b111:
            return decode_cloudlocate(data)
        raise ValueError(
            f'auto-detect: unrecognised header 0b{header:03b} for 16-byte payload. '
            f'Pass msg_type=... explicitly.'
        )
    if size == 24:
        header = data[0] >> 5
        if header == 0b010:
            return decode_fastloc(data)
        if header == 0b100:
            return decode_rspb_long(data)
        if header == 0b111:
            return decode_cloudlocate(data)
        raise ValueError(
            f'auto-detect: 24-byte payload with header 0b{header:03b} is ambiguous '
            f'(Long Packet vs Sensor Packet share the same prefix). '
            f"Pass msg_type='long' or msg_type='sensor' explicitly."
        )
    raise ValueError(
        f'auto-detect: unsupported payload size {size} bytes '
        f'(expected 3 / 16 / 24)'
    )
