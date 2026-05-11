"""LoRa payload decoder for LinkIt V4 messages.

Currently exposes the v2 GPS_MULTI parser only. Other LoRa packet types
(Sensor 0b010, Status 0b011, CloudLocate 0b100) are not implemented here.

Public entry points:

    decode_gps_multi(payload) -> dict
    reconstruct_timestamps(entries, year, month) -> list[int|None]
    expected_size(count) -> int
"""

from .decoder import (
    decode_gps_multi,
    reconstruct_timestamps,
    expected_size,
    GPS_MULTI_PKT_TYPE,
    DELTA_T_CLAMP_SENTINEL,
    LAT_NO_FIX,
    LON_NO_FIX,
    SPEED_NO_FIX,
)

__all__ = [
    'decode_gps_multi',
    'reconstruct_timestamps',
    'expected_size',
    'GPS_MULTI_PKT_TYPE',
    'DELTA_T_CLAMP_SENTINEL',
    'LAT_NO_FIX',
    'LON_NO_FIX',
    'SPEED_NO_FIX',
]
