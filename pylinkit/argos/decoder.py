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


def decode_sensor(payload24, axl_g_range=16):
    """Type 1 - Sensor Packet v3 (LDA2, 24 bytes, header 0b001).

    Self-describing: the embedded 5-bit ``sensor_mask`` (bits 78..82) tells
    the decoder which sensor fields are present. No external mask needed.

    Layout::

        bits 0..2     header (0b001)
             3..7     day            (5)
             8..12    hour           (5)
             13..18   minute         (6)
             19..39   latitude       (21)
             40..61   longitude      (22)
             62..68   speed          (7)
             69       out_of_zone    (1)
             70..76   battery        (7)
             77       low_battery    (1)
             78..82   sensor_mask    (5)  MSB-first: ALS|PH|Pressure|SeaTemp|AXL
             83..     sensor data, in order ALS -> PH -> Pressure -> SeaTemp -> AXL
             184..191 CRC8

    Sensor field sizes:

    - ALS: 17 bits raw lux
    - PH: 14 bits, decoded as ``raw / 1000.0``
    - Pressure: 29 bits = 15 (hPa*1000) + 14 ((C+40)*100)
    - SeaTemp/Thermistor (shared slot): 21 bits, decoded as ``raw/1000.0 - 126``
    - AXL: variable, see rules below

    AXL temperature rule (deterministic):
        ``has_other_temp = pressure_bit OR seatemp_bit``.
        AXL temp (14 bits) is included only when ``not has_other_temp``.

    AXL activity truncation:
        After XYZ, the firmware reads ``min(8, 184 - position)`` bits and
        left-aligns the value: ``activity = raw << (8 - bits_read)``.
        ``axl_activity_resolution_bits`` reports the actual bit width
        (< 8 means reduced resolution).

    Includes LDA2 CRC8 verification.
    """
    payload24 = bytes(payload24)
    if len(payload24) != 24:
        raise ValueError(f'sensor packet expects 24 bytes, got {len(payload24)}')
    crc_valid = verify_lda2(payload24)
    r = BitReader(payload24)
    header = r.read(3)
    if header != 0b001:
        raise ValueError(f'sensor: expected header 0b001, got {bin(header)}')

    out = {
        'message_type': 'sensor',
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
    }

    mask = r.read(5)
    has_als      = bool(mask & 0b10000)
    has_ph       = bool(mask & 0b01000)
    has_pressure = bool(mask & 0b00100)
    has_seatemp  = bool(mask & 0b00010)
    has_axl      = bool(mask & 0b00001)

    out['sensor_mask'] = mask
    out['sensor_mask_bits'] = {
        'als': has_als,
        'ph': has_ph,
        'pressure': has_pressure,
        'sea_temp': has_seatemp,
        'axl': has_axl,
    }

    sensors = {}
    if has_als:
        sensors['als_lux'] = r.read(17)
    if has_ph:
        sensors['ph'] = _decode_ph(r.read(14))
    if has_pressure:
        sensors['pressure_hpa'] = _decode_pressure_hpa(r.read(15))
        sensors['pressure_temp_c'] = _decode_temp_offset40(r.read(14))
    if has_seatemp:
        sensors['sea_temp_or_thermistor_c'] = _decode_sea_temp(r.read(21))
    if has_axl:
        # AXL die temperature is included only when no other temp source is in
        # the packet (deterministic, no ambiguity for the decoder).
        if not (has_pressure or has_seatemp):
            sensors['axl_temp_c'] = _decode_temp_offset40(r.read(14))
        sensors['axl_x_g'] = _decode_axl_axis(r.read(15), axl_g_range)
        sensors['axl_y_g'] = _decode_axl_axis(r.read(15), axl_g_range)
        sensors['axl_z_g'] = _decode_axl_axis(r.read(15), axl_g_range)
        bits_left = max(0, 184 - r.position)
        activity_bits = min(8, bits_left)
        if activity_bits > 0:
            raw = r.read(activity_bits)
            sensors['axl_activity'] = raw << (8 - activity_bits)
            sensors['axl_activity_resolution_bits'] = activity_bits
        else:
            sensors['axl_activity'] = None
            sensors['axl_activity_resolution_bits'] = 0

    out['sensors'] = sensors
    out['crc8'] = payload24[23]
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


def decode(payload, msg_type='auto', axl_g_range=16):
    """Decode an Argos satellite payload.

    payload: bytes or hex string (whitespace, ``:`` and ``-`` accepted)
    msg_type: 'auto' (default) or one of the names in MSG_TYPES.

    Auto-detection rules:

        - 3  bytes -> VLDA4: header 0b110 -> rspb_doppler, else doppler
        - 12 bytes -> LDK:   short packet (header 0b000)
        - 16 bytes -> LDK:   header 0b101 -> rspb_short, 0b111 -> cloudlocate (MEASC12)
        - 24 bytes -> LDA2:  header 0b001 -> sensor, 0b010 -> fastloc,
                             0b100 -> rspb_long, 0b111 -> cloudlocate (MEAS20).
                             Long Packet has no header (Day fills bits 0..4),
                             so a 24-byte payload with another header value
                             cannot be auto-detected and must be passed with
                             ``msg_type='long'``. Conversely a Long Packet
                             whose Day starts with the bit pattern of an
                             above header would be misidentified — disambiguate
                             via the explicit ``msg_type``.
    """
    data = _coerce_payload(payload)
    if msg_type not in MSG_TYPES:
        raise ValueError(f'unknown msg_type {msg_type!r}, expected one of {MSG_TYPES}')

    if msg_type == 'short':
        return decode_short(data)
    if msg_type == 'long':
        return decode_long(data)
    if msg_type == 'sensor':
        return decode_sensor(data, axl_g_range=axl_g_range)
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
        if header == 0b001:
            return decode_sensor(data, axl_g_range=axl_g_range)
        if header == 0b010:
            return decode_fastloc(data)
        if header == 0b100:
            return decode_rspb_long(data)
        if header == 0b111:
            return decode_cloudlocate(data)
        raise ValueError(
            f'auto-detect: 24-byte payload with header 0b{header:03b} has no '
            f"typed match. It is most likely a Long Packet -- pass "
            f"msg_type='long' explicitly."
        )
    raise ValueError(
        f'auto-detect: unsupported payload size {size} bytes '
        f'(expected 3 / 12 / 16 / 24)'
    )
