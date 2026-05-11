"""Unit tests for the UNP03/UNP04 UINT -> FLOAT (SAMPLINGPERIOD) migration.

Covers:
  - UW_WET_SAMPLING (UNP03) and UW_DRY_SAMPLING (UNP04) now use SAMPLINGPERIOD
  - SAMPLINGPERIOD accepts floats in [0.1, 86400.0]
  - Out-of-range values are rejected client-side (before reaching firmware)
  - Wire format stays compatible: integer-typed input "10" decodes back as 10.0,
    firmware-style "10" (from %g) decodes correctly, sub-second "0.1" works.
"""
import pytest

from pylinkit.protocol.dte_params import DTEParamMap
from pylinkit.protocol.dte_types import SAMPLINGPERIOD


PARAMS = ["UW_WET_SAMPLING", "UW_DRY_SAMPLING"]
KEYS = {"UW_WET_SAMPLING": "UNP03", "UW_DRY_SAMPLING": "UNP04"}


# --- Param map wiring --------------------------------------------------------

@pytest.mark.parametrize("long_key", PARAMS)
def test_param_map_uses_samplingperiod(long_key):
    short = KEYS[long_key]
    assert DTEParamMap.param_to_key(long_key) == short
    # encoding through the param map matches the SAMPLINGPERIOD codec
    for v in (0.1, 1.0, 10, 60.5, 86400):
        assert DTEParamMap.encode(long_key, v) == SAMPLINGPERIOD.encode(v)


# --- Range validation --------------------------------------------------------

@pytest.mark.parametrize("v", [0.1, 0.5, 1.0, 10, 60.5, 3600.0, 86400.0])
def test_accepts_in_range(v):
    encoded = SAMPLINGPERIOD.encode(v)
    assert SAMPLINGPERIOD.decode(encoded) == pytest.approx(float(v))


@pytest.mark.parametrize("v", [0, 0.05, 0.099, -1, -0.1, 86400.01, 100000])
def test_rejects_out_of_range(v):
    with pytest.raises(ValueError):
        SAMPLINGPERIOD.encode(v)


@pytest.mark.parametrize("long_key", PARAMS)
def test_param_map_propagates_validation(long_key):
    with pytest.raises(ValueError):
        DTEParamMap.encode(long_key, 0)
    with pytest.raises(ValueError):
        DTEParamMap.encode(long_key, 86400.01)


# --- Wire-format backward compat --------------------------------------------

@pytest.mark.parametrize("wire,expected", [
    ("10",   10.0),    # firmware %g for integer
    ("10.0", 10.0),    # legacy explicit
    ("0.1",  0.1),     # sub-second
    ("0.5",  0.5),
    ("86400", 86400.0),
])
def test_decode_accepts_int_and_float_wire(wire, expected):
    assert SAMPLINGPERIOD.decode(wire) == pytest.approx(expected)


def test_legacy_integer_input_string_still_accepted():
    # An older .cfg holding "UW_WET_SAMPLING = 10" is read as the string "10"
    # by ConfigParser. encode() must coerce and accept it.
    assert SAMPLINGPERIOD.decode(SAMPLINGPERIOD.encode("10")) == pytest.approx(10.0)
    assert SAMPLINGPERIOD.decode(SAMPLINGPERIOD.encode("0.1")) == pytest.approx(0.1)


# --- Wire-format output (encode side) ---------------------------------------

@pytest.mark.parametrize("value,expected_wire", [
    (10,    "10.0"),    # int input -> "10.0" (Python's str(float))
    (10.0,  "10.0"),
    (0.1,   "0.1"),
    (0.5,   "0.5"),
    (60.5,  "60.5"),
    (86400, "86400.0"),
])
def test_encode_output_format(value, expected_wire):
    # Locks the on-wire representation. Firmware parser accepts both "10"
    # and "10.0", so the *.0 trailing is tolerable; this test exists so any
    # future change to the output (e.g. dropping the trailing .0) is an
    # explicit decision, not a silent regression.
    assert SAMPLINGPERIOD.encode(value) == expected_wire


def test_encode_boundary_values_exact():
    # The exact min/max must encode (the rejection tests cover what's just past).
    assert SAMPLINGPERIOD.encode(0.1) == "0.1"
    assert SAMPLINGPERIOD.encode(86400.0) == "86400.0"


@pytest.mark.parametrize("garbage", ["", "not-a-number", "10s", "  ", "1.0.0"])
def test_encode_rejects_non_numeric_string(garbage):
    with pytest.raises(ValueError):
        SAMPLINGPERIOD.encode(garbage)
