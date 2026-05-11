"""LoRa GPS_MULTI v2 payload decoder.

Layout (big-endian, MSB first):

    HEADER     14 bits   PKT_TYPE(3, =0b001) + FLAGS(4) + VOLTAGE(7)
    COUNT       4 bits   N entries (1..15)
    ENTRY[0]   86 bits   DAY(5) HOUR(5) MIN(6) LAT(21) LON(22) SPEED(7)
                          HEADING(8) ALT(8) NUMSV(4)
    ENTRY[i]   66 bits   LAT(21) LON(22) SPEED(7) DELTA_T_MIN(16)
                          for i in 1..N-1, going BACK in time

Total bits = 18 + 86 + (N-1)*66 = 104 + 66*(N-1).
Trailing byte is zero-padded.

Timestamp chain:
    t[0] = absolute (DAY/HOUR/MIN, month/year from receiver context)
    t[i] = t[i-1] - delta_t_min[i] * 60        for i = 1..N-1

Sentinels:
    delta_t_min == 0       -> two fixes within the same minute (no warning)
    delta_t_min == 0xFFFF  -> clamp, gap >= ~45 days; warning, t[i] left as None
    lat == 0x1FFFFF        -> no fix latitude
    lon == 0x3FFFFF        -> no fix longitude
    speed == 0x7F          -> no fix speed (always paired with no-fix lat/lon)

The decoder returns a dict with the parsed fields and an `entries` list.
Timestamps are NOT reconstructed inline — call ``reconstruct_timestamps``
with year/month from the receiver context to build absolute timestamps.
"""

from datetime import datetime, timezone, timedelta


GPS_MULTI_PKT_TYPE = 0b001
DELTA_T_CLAMP_SENTINEL = 0xFFFF
LAT_NO_FIX = 0x1FFFFF
LON_NO_FIX = 0x3FFFFF
SPEED_NO_FIX = 0x7F

_HEADER_BITS = 14
_COUNT_BITS = 4
_ENTRY0_BITS = 86
_ENTRY_DELTA_BITS = 66


def expected_size(count: int) -> int:
    """Bytes required to hold a GPS_MULTI v2 packet with ``count`` entries."""
    if not 1 <= count <= 15:
        raise ValueError(f'count {count} out of range [1, 15]')
    total_bits = _HEADER_BITS + _COUNT_BITS + _ENTRY0_BITS + (count - 1) * _ENTRY_DELTA_BITS
    return (total_bits + 7) // 8


# --- bit reader -------------------------------------------------------------

class _BitReader:
    """Sequential MSB-first reader over a byte buffer."""

    def __init__(self, data):
        self._data = bytes(data)
        self._pos = 0

    def read(self, n_bits):
        if n_bits <= 0:
            return 0
        end = self._pos + n_bits
        if end > len(self._data) * 8:
            raise ValueError(
                f'BitReader: cannot read {n_bits} bits at offset {self._pos} '
                f'(buffer is {len(self._data)} bytes)'
            )
        result = 0
        for _ in range(n_bits):
            byte_idx = self._pos >> 3
            bit_idx = 7 - (self._pos & 7)
            result = (result << 1) | ((self._data[byte_idx] >> bit_idx) & 1)
            self._pos += 1
        return result


# --- field decoders ---------------------------------------------------------

def _decode_lat(raw_21):
    if raw_21 == LAT_NO_FIX:
        return None
    sign_bit = 1 << 20
    if raw_21 & sign_bit:
        return -(raw_21 & (sign_bit - 1)) / 10000.0
    return raw_21 / 10000.0


def _decode_lon(raw_22):
    if raw_22 == LON_NO_FIX:
        return None
    sign_bit = 1 << 21
    if raw_22 & sign_bit:
        return -(raw_22 & (sign_bit - 1)) / 10000.0
    return raw_22 / 10000.0


def _decode_speed_mms(raw_7):
    if raw_7 == SPEED_NO_FIX:
        return None
    return raw_7 * 2000000 // 3600


def _decode_heading(raw_8):
    return raw_8 * 1.42


def _decode_altitude(raw_8):
    if raw_8 == 0xFF:
        return None
    return raw_8 * 40


def _decode_voltage_mv(raw_7):
    return raw_7 * 20 + 2700


# --- main entry point -------------------------------------------------------

def decode_gps_multi(payload):
    """Decode a LoRa GPS_MULTI v2 packet.

    payload: bytes-like or hex string (whitespace, ``:`` and ``-`` accepted).

    Returns a dict::

        {
          'message_type': 'lora_gps_multi',
          'version': 2,
          'pkt_type': 1,
          'flags': int,
          'voltage_mv': int,
          'count': int,
          'entries': [
            # entry[0] — newest, full timestamp:
            {'day': 12, 'hour': 14, 'minute': 30,
             'latitude': 48.8566, 'longitude': 2.3522,
             'speed_mm_s': 1389, 'heading_deg': 92.3,
             'altitude_m': 80, 'num_satellites': 8,
             'valid_fix': True,
             'delta_t_min': None},
            # entry[i>=1] — older, delta to entry[i-1]:
            {'latitude': ..., 'longitude': ..., 'speed_mm_s': ...,
             'delta_t_min': 195, 'delta_t_clamp': False,
             'valid_fix': True},
            ...
          ],
          'warnings': [...],
        }
    """
    data = _coerce_payload(payload)
    if len(data) < 2:
        raise ValueError(f'payload too short: {len(data)} bytes')

    r = _BitReader(data)
    pkt_type = r.read(3)
    if pkt_type != GPS_MULTI_PKT_TYPE:
        raise ValueError(
            f'lora_gps_multi: expected pkt_type 0b{GPS_MULTI_PKT_TYPE:03b}, '
            f'got 0b{pkt_type:03b}'
        )
    flags = r.read(4)
    voltage_raw = r.read(7)
    count = r.read(4)
    if not 1 <= count <= 15:
        raise ValueError(f'lora_gps_multi: count {count} out of range [1, 15]')

    need = expected_size(count)
    if len(data) < need:
        raise ValueError(
            f'lora_gps_multi: payload {len(data)} bytes, need at least {need} '
            f'for count={count}'
        )

    warnings = []
    entries = []

    # ENTRY[0] — newest, with full timestamp -------------------------------
    e0_day = r.read(5)
    e0_hour = r.read(5)
    e0_min = r.read(6)
    e0_lat_raw = r.read(21)
    e0_lon_raw = r.read(22)
    e0_speed_raw = r.read(7)
    e0_heading = r.read(8)
    e0_alt = r.read(8)
    e0_numsv = r.read(4)
    e0_valid = (e0_lat_raw != LAT_NO_FIX) and (e0_lon_raw != LON_NO_FIX)
    if not e0_valid:
        warnings.append('entry[0]: invalid fix (timestamp still usable)')
    entries.append({
        'day': e0_day,
        'hour': e0_hour,
        'minute': e0_min,
        'latitude': _decode_lat(e0_lat_raw),
        'longitude': _decode_lon(e0_lon_raw),
        'speed_mm_s': _decode_speed_mms(e0_speed_raw),
        'heading_deg': _decode_heading(e0_heading),
        'altitude_m': _decode_altitude(e0_alt),
        'num_satellites': e0_numsv,
        'valid_fix': e0_valid,
        'delta_t_min': None,
    })

    # ENTRY[i] for i = 1..count-1 — older, with delta ----------------------
    for i in range(1, count):
        lat_raw = r.read(21)
        lon_raw = r.read(22)
        speed_raw = r.read(7)
        delta_t = r.read(16)
        valid = (lat_raw != LAT_NO_FIX) and (lon_raw != LON_NO_FIX)
        clamp = (delta_t == DELTA_T_CLAMP_SENTINEL)
        if clamp:
            warnings.append(f'entry[{i}]: delta_t clamped (gap >= ~45 days)')
        if not valid:
            warnings.append(f'entry[{i}]: invalid fix (timestamp chain unbroken)')
        entries.append({
            'latitude': _decode_lat(lat_raw),
            'longitude': _decode_lon(lon_raw),
            'speed_mm_s': _decode_speed_mms(speed_raw),
            'delta_t_min': delta_t,
            'delta_t_clamp': clamp,
            'valid_fix': valid,
        })

    return {
        'message_type': 'lora_gps_multi',
        'version': 2,
        'pkt_type': pkt_type,
        'flags': flags,
        'voltage_mv': _decode_voltage_mv(voltage_raw),
        'count': count,
        'entries': entries,
        'warnings': warnings,
    }


def reconstruct_timestamps(entries, year, month):
    """Build absolute UTC timestamps for a decoded entries list.

    Year and month come from the receiver context (e.g. LoRaWAN gateway
    reception time). Returns a list of ``datetime`` (UTC) the same length
    as ``entries``; positions where the chain breaks (clamped delta_t)
    are returned as ``None``.

    The order matches the input: index 0 = newest, index N-1 = oldest.
    """
    if not entries:
        return []
    e0 = entries[0]
    try:
        t0 = datetime(year, month, e0['day'], e0['hour'], e0['minute'], 0, tzinfo=timezone.utc)
    except (ValueError, KeyError) as exc:
        raise ValueError(f'reconstruct_timestamps: invalid entry[0] date fields: {exc}')

    out = [t0]
    prev = t0
    for i in range(1, len(entries)):
        e = entries[i]
        delta = e.get('delta_t_min')
        if delta is None or e.get('delta_t_clamp'):
            out.append(None)
            prev = None
            continue
        if prev is None:
            # chain was broken upstream; cannot rebuild from a None anchor
            out.append(None)
            continue
        prev = prev - timedelta(minutes=int(delta))
        out.append(prev)
    return out


def _coerce_payload(payload):
    if isinstance(payload, str):
        clean = payload.replace(' ', '').replace(':', '').replace('-', '')
        return bytes.fromhex(clean)
    return bytes(payload)
