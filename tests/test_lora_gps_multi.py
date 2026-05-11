"""Unit tests for the LoRa GPS_MULTI v2 parser.

The encoder helpers (``_BitWriter``, ``_build_packet``) are test-only —
firmware emits these packets, the GUI/server only decodes. The encoder
is the simplest way to build deterministic fixtures.
"""
from datetime import datetime, timezone, timedelta

import pytest

from pylinkit.lora import (
    decode_gps_multi,
    reconstruct_timestamps,
    expected_size,
    DELTA_T_CLAMP_SENTINEL,
    LAT_NO_FIX,
    LON_NO_FIX,
)


# --- bit writer (test helper) ------------------------------------------------

class _BitWriter:
    def __init__(self):
        self._bits = []

    def write(self, value, n_bits):
        assert 0 <= value < (1 << n_bits), f'value {value} does not fit in {n_bits} bits'
        for shift in range(n_bits - 1, -1, -1):
            self._bits.append((value >> shift) & 1)
        return self

    def bytes(self):
        # zero-pad to the next byte
        while len(self._bits) % 8:
            self._bits.append(0)
        out = bytearray()
        for i in range(0, len(self._bits), 8):
            byte = 0
            for b in self._bits[i:i + 8]:
                byte = (byte << 1) | b
            out.append(byte)
        return bytes(out)


# --- packet builder ---------------------------------------------------------

def _encode_lat(deg):
    if deg is None:
        return LAT_NO_FIX
    raw = int(round(abs(deg) * 10000))
    if deg < 0:
        raw |= (1 << 20)
    return raw


def _encode_lon(deg):
    if deg is None:
        return LON_NO_FIX
    raw = int(round(abs(deg) * 10000))
    if deg < 0:
        raw |= (1 << 21)
    return raw


def _build_packet(flags, voltage_raw, entry0, deltas):
    """entry0: dict with day, hour, minute, lat, lon, speed_raw, heading_raw,
              alt_raw, numsv.
    deltas: list of dicts with lat, lon, speed_raw, delta_t_min."""
    w = _BitWriter()
    # header
    w.write(0b001, 3)         # pkt_type
    w.write(flags, 4)
    w.write(voltage_raw, 7)
    w.write(1 + len(deltas), 4)  # count
    # entry[0]
    w.write(entry0['day'], 5)
    w.write(entry0['hour'], 5)
    w.write(entry0['minute'], 6)
    w.write(_encode_lat(entry0['lat']), 21)
    w.write(_encode_lon(entry0['lon']), 22)
    w.write(entry0['speed_raw'], 7)
    w.write(entry0['heading_raw'], 8)
    w.write(entry0['alt_raw'], 8)
    w.write(entry0['numsv'], 4)
    # entries[i]
    for d in deltas:
        w.write(_encode_lat(d['lat']), 21)
        w.write(_encode_lon(d['lon']), 22)
        w.write(d['speed_raw'], 7)
        w.write(d['delta_t_min'], 16)
    return w.bytes()


# --- expected_size sanity ---------------------------------------------------

@pytest.mark.parametrize("count,expected", [
    (1, 13), (2, 22), (3, 30), (4, 38), (5, 46),
    (7, 63), (10, 88), (13, 112), (15, 129),
])
def test_expected_size(count, expected):
    assert expected_size(count) == expected


@pytest.mark.parametrize("bad", [0, 16, -1, 100])
def test_expected_size_rejects_oob(bad):
    with pytest.raises(ValueError):
        expected_size(bad)


# --- decode: count=1 (single full entry, 13 bytes) --------------------------

def test_decode_count_1_single_full_entry():
    payload = _build_packet(
        flags=0b1010, voltage_raw=80,
        entry0={'day': 12, 'hour': 14, 'minute': 30,
                'lat': 48.8566, 'lon': 2.3522,
                'speed_raw': 5, 'heading_raw': 64, 'alt_raw': 2, 'numsv': 8},
        deltas=[],
    )
    assert len(payload) == 13
    out = decode_gps_multi(payload)
    assert out['message_type'] == 'lora_gps_multi'
    assert out['version'] == 2
    assert out['pkt_type'] == 0b001
    assert out['flags'] == 0b1010
    assert out['voltage_mv'] == 80 * 20 + 2700
    assert out['count'] == 1
    assert len(out['entries']) == 1
    e = out['entries'][0]
    assert e['day'] == 12
    assert e['hour'] == 14
    assert e['minute'] == 30
    assert e['latitude'] == pytest.approx(48.8566, abs=1e-4)
    assert e['longitude'] == pytest.approx(2.3522, abs=1e-4)
    assert e['num_satellites'] == 8
    assert e['altitude_m'] == 2 * 40
    assert e['valid_fix'] is True
    assert e['delta_t_min'] is None
    assert out['warnings'] == []


# --- decode: count=5 with irregular deltas, reconstruct timestamps ----------

def test_decode_count_5_irregular_deltas_timestamps():
    # newest 16:00, then back to 14:15 (-105 min), 11:30 (-165), 08:00 (-210), 06:45 (-75)
    deltas_min = [105, 165, 210, 75]
    entry0 = {'day': 5, 'hour': 16, 'minute': 0,
              'lat': 51.5074, 'lon': -0.1278,
              'speed_raw': 3, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 6}
    delta_entries = [
        {'lat': 51.50, 'lon': -0.13, 'speed_raw': 0, 'delta_t_min': delta}
        for delta in deltas_min
    ]
    payload = _build_packet(flags=0, voltage_raw=50, entry0=entry0, deltas=delta_entries)
    assert len(payload) == 46  # count=5

    out = decode_gps_multi(payload)
    assert out['count'] == 5
    assert len(out['entries']) == 5
    assert [e['delta_t_min'] for e in out['entries']] == [None] + deltas_min

    times = reconstruct_timestamps(out['entries'], year=2026, month=5)
    assert times[0] == datetime(2026, 5, 5, 16, 0, tzinfo=timezone.utc)
    assert times[1] == datetime(2026, 5, 5, 14, 15, tzinfo=timezone.utc)
    assert times[2] == datetime(2026, 5, 5, 11, 30, tzinfo=timezone.utc)
    assert times[3] == datetime(2026, 5, 5, 8, 0, tzinfo=timezone.utc)
    assert times[4] == datetime(2026, 5, 5, 6, 45, tzinfo=timezone.utc)


# --- decode: delta_t = 0 (consecutive fixes within the same minute) ---------

def test_decode_delta_zero_no_warning():
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[{'lat': 0.0, 'lon': 0.0, 'speed_raw': 0, 'delta_t_min': 0}],
    )
    out = decode_gps_multi(payload)
    assert out['entries'][1]['delta_t_min'] == 0
    assert out['entries'][1]['delta_t_clamp'] is False
    assert out['warnings'] == []
    times = reconstruct_timestamps(out['entries'], 2026, 5)
    assert times[0] == times[1]  # same minute


# --- decode: delta_t = 0xFFFF (clamp sentinel) ------------------------------

def test_decode_delta_clamp_sentinel_flags_warning():
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[
            {'lat': 0.0, 'lon': 0.0, 'speed_raw': 0, 'delta_t_min': DELTA_T_CLAMP_SENTINEL},
            {'lat': 0.0, 'lon': 0.0, 'speed_raw': 0, 'delta_t_min': 60},
        ],
    )
    out = decode_gps_multi(payload)
    assert out['entries'][1]['delta_t_clamp'] is True
    assert out['entries'][1]['delta_t_min'] == DELTA_T_CLAMP_SENTINEL
    assert any('45 days' in w for w in out['warnings'])

    # Reconstruction: entry[1] is None (chain broken), entry[2] also None
    # because we don't rebuild from a missing anchor.
    times = reconstruct_timestamps(out['entries'], 2026, 5)
    assert times[0] is not None
    assert times[1] is None
    assert times[2] is None


# --- decode: invalid fix in the middle, chain stays intact ------------------

def test_decode_invalid_fix_middle_does_not_break_chain():
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 5, 'hour': 16, 'minute': 0, 'lat': 51.5, 'lon': -0.1,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 6},
        deltas=[
            {'lat': 51.5, 'lon': -0.1, 'speed_raw': 0, 'delta_t_min': 60},
            {'lat': None, 'lon': None, 'speed_raw': 0, 'delta_t_min': 30},  # NO_FIX
            {'lat': 51.5, 'lon': -0.1, 'speed_raw': 0, 'delta_t_min': 45},
        ],
    )
    out = decode_gps_multi(payload)
    assert out['entries'][2]['valid_fix'] is False
    assert out['entries'][2]['latitude'] is None
    assert out['entries'][2]['longitude'] is None
    assert out['entries'][2]['speed_mm_s'] == 0  # speed=0 is still encoded, not no-fix
    # delta still readable, chain still rebuildable through the invalid point
    times = reconstruct_timestamps(out['entries'], 2026, 5)
    assert times[0] == datetime(2026, 5, 5, 16, 0, tzinfo=timezone.utc)
    assert times[1] == times[0] - timedelta(minutes=60)
    assert times[2] == times[1] - timedelta(minutes=30)
    assert times[3] == times[2] - timedelta(minutes=45)
    assert any('invalid fix' in w for w in out['warnings'])


# --- decode: count=13 on DR3 (112 bytes) ------------------------------------

def test_decode_count_13_size_matches_dr3_budget():
    deltas = [
        {'lat': 0.0, 'lon': 0.0, 'speed_raw': 0, 'delta_t_min': 30}
        for _ in range(12)
    ]
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=deltas,
    )
    assert len(payload) == 112
    out = decode_gps_multi(payload)
    assert out['count'] == 13
    assert len(out['entries']) == 13
    times = reconstruct_timestamps(out['entries'], 2026, 5)
    assert times[12] == times[0] - timedelta(minutes=12 * 30)


# --- decode: count=15 max packet (129 bytes) --------------------------------

def test_decode_count_15_max_packet():
    deltas = [
        {'lat': 0.0, 'lon': 0.0, 'speed_raw': 0, 'delta_t_min': 1}
        for _ in range(14)
    ]
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=deltas,
    )
    assert len(payload) == 129
    out = decode_gps_multi(payload)
    assert out['count'] == 15


# --- input validation -------------------------------------------------------

def test_decode_rejects_wrong_pkt_type():
    # Build a packet with pkt_type=0b010 (sensor on LoRa, not GPS_MULTI)
    w = _BitWriter()
    w.write(0b010, 3); w.write(0, 4); w.write(0, 7); w.write(1, 4)
    w.write(0, 86)  # filler
    with pytest.raises(ValueError, match='pkt_type'):
        decode_gps_multi(w.bytes())


def test_decode_rejects_truncated():
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[{'lat': 0.0, 'lon': 0.0, 'speed_raw': 0, 'delta_t_min': 10}],
    )
    # Drop the last few bytes; decoder should refuse instead of reading garbage
    with pytest.raises(ValueError):
        decode_gps_multi(payload[:10])


def test_decode_accepts_hex_string_input():
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[],
    )
    out_bytes = decode_gps_multi(payload)
    out_hex = decode_gps_multi(payload.hex())
    out_hex_spaced = decode_gps_multi(' '.join(f'{b:02x}' for b in payload))
    assert out_bytes == out_hex == out_hex_spaced


# --- field decoders: voltage --------------------------------------------------

@pytest.mark.parametrize("raw,expected_mv", [
    (0,   2700),    # min — 7-bit floor
    (1,   2720),
    (50,  3700),
    (80,  4300),
    (100, 4700),
    (127, 5240),    # max — 7-bit ceil
])
def test_voltage_mv_decoding(raw, expected_mv):
    # voltage encoding: mV = raw * 20 + 2700. The decoder must honour this for
    # the full 7-bit range; the count=1 test only exercises raw=80.
    payload = _build_packet(
        flags=0, voltage_raw=raw,
        entry0={'day': 1, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[],
    )
    out = decode_gps_multi(payload)
    assert out['voltage_mv'] == expected_mv


# --- field decoders: timestamp boundary values --------------------------------

def test_decode_day_hour_minute_max_values():
    # Spec field widths: day=5 (max 31), hour=5 (max 31, valid 0..23),
    # minute=6 (max 63, valid 0..59). The decoder does not range-check the
    # values it reads — it returns them verbatim. Lock that contract so a
    # naïve future "validate hour < 24" doesn't silently start dropping
    # entries.
    payload = _build_packet(
        flags=0, voltage_raw=0,
        entry0={'day': 31, 'hour': 23, 'minute': 59,
                'lat': 89.9999, 'lon': 179.9999,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 0},
        deltas=[],
    )
    out = decode_gps_multi(payload)
    e = out['entries'][0]
    assert e['day'] == 31
    assert e['hour'] == 23
    assert e['minute'] == 59
    # the timestamp reconstruction itself uses datetime() which *will* reject
    # invalid combinations — covered separately below
    t = reconstruct_timestamps(out['entries'], 2026, 1)
    assert t[0] == datetime(2026, 1, 31, 23, 59, tzinfo=timezone.utc)


def test_reconstruct_timestamps_rejects_invalid_date():
    # If the firmware ever ships day=32 (it shouldn't), the reconstruction
    # surfaces the problem rather than silently fabricating a date.
    payload = _build_packet(
        flags=0, voltage_raw=0,
        entry0={'day': 31, 'hour': 12, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 0},
        deltas=[],
    )
    out = decode_gps_multi(payload)
    with pytest.raises(ValueError):
        # February doesn't have 31 days
        reconstruct_timestamps(out['entries'], 2026, 2)


# --- field decoders: negative coordinates -------------------------------------

@pytest.mark.parametrize("lat,lon", [
    (-89.9999, -179.9999),    # extreme SW
    (89.9999,  179.9999),     # extreme NE
    (-0.0001,  -0.0001),      # just-negative near origin
    (0.0,      0.0),          # null island
])
def test_decode_signed_coordinates_roundtrip(lat, lon):
    payload = _build_packet(
        flags=0, voltage_raw=0,
        entry0={'day': 1, 'hour': 0, 'minute': 0, 'lat': lat, 'lon': lon,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 0, 'numsv': 0},
        deltas=[],
    )
    out = decode_gps_multi(payload)
    e = out['entries'][0]
    # encoding is fixed-point 1e-4 deg, so tolerate one LSB of rounding
    assert e['latitude'] == pytest.approx(lat, abs=1e-4)
    assert e['longitude'] == pytest.approx(lon, abs=1e-4)


# --- field decoders: altitude & speed sentinels ------------------------------

def test_altitude_no_fix_sentinel():
    # alt_raw = 0xFF means "no 3D fix" per the field encoding. The decoder
    # must surface this as altitude_m=None rather than 0xFF*40 = 10200 m.
    payload = _build_packet(
        flags=0, voltage_raw=0,
        entry0={'day': 1, 'hour': 0, 'minute': 0, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 0xFF, 'numsv': 0},
        deltas=[],
    )
    out = decode_gps_multi(payload)
    assert out['entries'][0]['altitude_m'] is None


def test_speed_no_fix_sentinel():
    # speed_raw = 0x7F means "no speed". Distinct from the lat/lon NO_FIX
    # path — needs its own test or a bit-flip there would never surface.
    payload = _build_packet(
        flags=0, voltage_raw=0,
        entry0={'day': 1, 'hour': 0, 'minute': 0, 'lat': 51.5, 'lon': -0.1,
                'speed_raw': 0x7F, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[
            # also exercise the sentinel in a delta entry
            {'lat': 51.5, 'lon': -0.1, 'speed_raw': 0x7F, 'delta_t_min': 5},
        ],
    )
    out = decode_gps_multi(payload)
    assert out['entries'][0]['speed_mm_s'] is None
    assert out['entries'][1]['speed_mm_s'] is None
    # speed sentinel does NOT mark the fix as invalid (lat/lon are still good)
    assert out['entries'][0]['valid_fix'] is True
    assert out['entries'][1]['valid_fix'] is True


# --- count=2: smallest packet that exercises the delta loop ------------------

def test_decode_count_2_exercises_delta_loop():
    # count=1 skips the loop body entirely; count=5+ runs it several times
    # and might mask an off-by-one. count=2 is the minimal case that runs the
    # body exactly once — keep it as a regression anchor.
    payload = _build_packet(
        flags=0, voltage_raw=50,
        entry0={'day': 10, 'hour': 9, 'minute': 30,
                'lat': 1.234, 'lon': -5.678,
                'speed_raw': 3, 'heading_raw': 42, 'alt_raw': 2, 'numsv': 7},
        deltas=[
            {'lat': 1.230, 'lon': -5.670, 'speed_raw': 2, 'delta_t_min': 17},
        ],
    )
    assert len(payload) == 22
    out = decode_gps_multi(payload)
    assert out['count'] == 2
    assert len(out['entries']) == 2

    e0 = out['entries'][0]
    assert e0['day'] == 10 and e0['hour'] == 9 and e0['minute'] == 30
    assert e0['num_satellites'] == 7
    assert e0['heading_deg'] == pytest.approx(42 * 1.42)
    assert e0['delta_t_min'] is None

    e1 = out['entries'][1]
    assert e1['delta_t_min'] == 17
    assert e1['delta_t_clamp'] is False
    assert e1['latitude'] == pytest.approx(1.230, abs=1e-4)
    assert e1['longitude'] == pytest.approx(-5.670, abs=1e-4)
    # delta entries do NOT carry day/hour/minute/heading/altitude/numsv
    assert 'day' not in e1
    assert 'heading_deg' not in e1

    times = reconstruct_timestamps(out['entries'], 2026, 5)
    assert times[0] == datetime(2026, 5, 10, 9, 30, tzinfo=timezone.utc)
    assert times[1] == datetime(2026, 5, 10, 9, 30, tzinfo=timezone.utc) - timedelta(minutes=17)


# --- reconstruct_timestamps: empty / single-entry edges ----------------------

def test_reconstruct_timestamps_empty_list():
    assert reconstruct_timestamps([], 2026, 5) == []


def test_reconstruct_timestamps_single_entry_skips_loop():
    # No deltas to walk back. Output should be [t0] with no None tail.
    payload = _build_packet(
        flags=0, voltage_raw=0,
        entry0={'day': 7, 'hour': 8, 'minute': 9, 'lat': 0.0, 'lon': 0.0,
                'speed_raw': 0, 'heading_raw': 0, 'alt_raw': 1, 'numsv': 4},
        deltas=[],
    )
    out = decode_gps_multi(payload)
    times = reconstruct_timestamps(out['entries'], 2026, 11)
    assert times == [datetime(2026, 11, 7, 8, 9, tzinfo=timezone.utc)]
