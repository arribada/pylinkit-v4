"""Argos satellite payload decoder for LinkIt V4 messages.

Decodes the binary payloads transmitted by the tracker over the Kineis
SMD/KIM2 module. See `Satellite Message Format` on the
linkit-v4-core wiki for the full specification.

Public entry points:

    decode(payload, msg_type='auto') -> dict
    lda2_crc8(payload23) -> int
    verify_lda2(frame24) -> bool

The ``decode`` helper auto-detects the message type from size + header
bits when possible. For ambiguous LDA2 frames (Long Packet vs Sensor
Packet share the same first 75 bits), pass an explicit ``msg_type``.

CloudLocate payloads are NOT decoded: the raw u-blox blob is returned
as a hex string, ready to be fed to u-blox CloudLocate.
"""

from .decoder import (
    decode,
    decode_short,
    decode_long,
    decode_sensor,
    decode_fastloc,
    decode_doppler,
    decode_rspb_long,
    decode_rspb_short,
    decode_rspb_doppler,
    decode_cloudlocate,
    lda2_crc8,
    verify_lda2,
    MSG_TYPES,
    DELTA_TIME_LOC_MINUTES,
)

__all__ = [
    'decode',
    'decode_short',
    'decode_long',
    'decode_sensor',
    'decode_fastloc',
    'decode_doppler',
    'decode_rspb_long',
    'decode_rspb_short',
    'decode_rspb_doppler',
    'decode_cloudlocate',
    'lda2_crc8',
    'verify_lda2',
    'MSG_TYPES',
    'DELTA_TIME_LOC_MINUTES',
]
