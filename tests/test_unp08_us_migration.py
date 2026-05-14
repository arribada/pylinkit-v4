"""Unit tests for the UNP08 ms->µs migration.

Firmware change (config_version 0x1D -> 0x1E):
  - Param UNP08 renamed: SWS_SAMPLE_DELAY_INITIAL (UINT, ms, default 1)
    -> UW_PIN_SAMPLE_DELAY_US (PINSAMPLEDELAYUS, µs, range [50, 30000],
       default 1000)

Covers:
  - DTE map: new long name resolves to UNP08 with the new codec
  - DTE map: legacy long names are gone
  - PINSAMPLEDELAYUS accepts [50, 30000] and rejects everything else
  - migrate_unp08_ms_to_us() handles legacy keys, conversion, clamping,
    idempotency, and unparseable values
"""
import pytest

from pylinkit.protocol.dte_params import DTEParamMap
from pylinkit.protocol.dte_types import PINSAMPLEDELAYUS
from pylinkit.migrations import migrate_unp08_ms_to_us, apply_all


# --- DTE param map ----------------------------------------------------------

def test_unp08_uses_new_long_name_and_codec():
    assert DTEParamMap.param_to_key("UW_PIN_SAMPLE_DELAY_US") == "UNP08"
    assert DTEParamMap.key_to_param("UNP08") == "UW_PIN_SAMPLE_DELAY_US"


@pytest.mark.parametrize("legacy", ["UW_PIN_SAMPLE_DELAY", "SWS_SAMPLE_DELAY_INITIAL"])
def test_legacy_long_names_removed(legacy):
    with pytest.raises(Exception):
        DTEParamMap.param_to_key(legacy)


def test_unp08_map_round_trip_uses_validated_codec():
    # encode through the map must validate against the new bounds.
    assert DTEParamMap.encode("UW_PIN_SAMPLE_DELAY_US", 1000) == "1000"
    with pytest.raises(ValueError):
        DTEParamMap.encode("UW_PIN_SAMPLE_DELAY_US", 49)
    with pytest.raises(ValueError):
        DTEParamMap.encode("UW_PIN_SAMPLE_DELAY_US", 30001)


# --- PINSAMPLEDELAYUS codec --------------------------------------------------

@pytest.mark.parametrize("v", [50, 51, 500, 1000, 15000, 29999, 30000])
def test_codec_accepts_in_range(v):
    encoded = PINSAMPLEDELAYUS.encode(v)
    assert PINSAMPLEDELAYUS.decode(encoded) == v


@pytest.mark.parametrize("bad", [0, 1, 49, -1, 30001, 100000])
def test_codec_rejects_out_of_range(bad):
    with pytest.raises(ValueError):
        PINSAMPLEDELAYUS.encode(bad)


def test_codec_accepts_string_int():
    assert PINSAMPLEDELAYUS.encode("1000") == "1000"
    with pytest.raises(ValueError):
        PINSAMPLEDELAYUS.encode("not-a-number")


def test_codec_boundary_values_exact():
    assert PINSAMPLEDELAYUS.encode(50) == "50"
    assert PINSAMPLEDELAYUS.encode(30000) == "30000"


# --- migration helper -------------------------------------------------------

@pytest.mark.parametrize("ms,expected_us", [
    (1,   1000),    # spec example
    (5,   5000),    # spec example
    (10,  10000),
    (30,  30000),   # exactly at the new ceiling
])
def test_migrate_in_range_converts_ms_to_us(ms, expected_us):
    params = {"UW_PIN_SAMPLE_DELAY": str(ms)}
    out = migrate_unp08_ms_to_us(params)
    assert out["UW_PIN_SAMPLE_DELAY_US"] == str(expected_us)
    assert "UW_PIN_SAMPLE_DELAY" not in out


@pytest.mark.parametrize("ms", [31, 50, 100, 1000, 4_294_967])
def test_migrate_above_30ms_clamps_to_max(ms):
    params = {"UW_PIN_SAMPLE_DELAY": str(ms)}
    out = migrate_unp08_ms_to_us(params)
    assert out["UW_PIN_SAMPLE_DELAY_US"] == "30000"


def test_migrate_zero_ms_floors_to_new_min():
    # 0 ms * 1000 = 0 µs, below the new floor of 50 µs. Clamp up to 50.
    params = {"UW_PIN_SAMPLE_DELAY": "0"}
    out = migrate_unp08_ms_to_us(params)
    assert out["UW_PIN_SAMPLE_DELAY_US"] == "50"


def test_migrate_accepts_legacy_pylinkit_name():
    # The old pylinkit name (SWS_SAMPLE_DELAY_INITIAL) is treated the same as
    # the firmware-side legacy name.
    params = {"SWS_SAMPLE_DELAY_INITIAL": "5"}
    out = migrate_unp08_ms_to_us(params)
    assert out == {"UW_PIN_SAMPLE_DELAY_US": "5000"}


def test_migrate_no_op_on_already_current_template():
    # A template that has the new name is left untouched.
    params = {"UW_PIN_SAMPLE_DELAY_US": "1500", "OTHER": "x"}
    out = migrate_unp08_ms_to_us(params)
    assert out == {"UW_PIN_SAMPLE_DELAY_US": "1500", "OTHER": "x"}


def test_migrate_is_idempotent():
    # Running the migration twice must give the same final dict as running it
    # once. (After the first call, the legacy key is gone, so the second call
    # is structurally a no-op.)
    params = {"UW_PIN_SAMPLE_DELAY": "5"}
    once = migrate_unp08_ms_to_us(dict(params))
    twice = migrate_unp08_ms_to_us(migrate_unp08_ms_to_us(dict(params)))
    assert once == twice


def test_migrate_template_without_unp08_is_untouched():
    params = {"GNSS_ENABLE": "1", "BATT_SOC": "50"}
    out = migrate_unp08_ms_to_us(params)
    assert out == {"GNSS_ENABLE": "1", "BATT_SOC": "50"}


def test_migrate_drops_unparseable_legacy_value():
    # Garbage in the legacy field is dropped (no spurious key added). The
    # caller can detect the missing replacement and re-prompt the user.
    params = {"UW_PIN_SAMPLE_DELAY": "garbage", "OTHER": "x"}
    out = migrate_unp08_ms_to_us(params)
    assert "UW_PIN_SAMPLE_DELAY" not in out
    assert "UW_PIN_SAMPLE_DELAY_US" not in out
    assert out["OTHER"] == "x"


def test_migrate_mutates_in_place_and_returns_same_dict():
    params = {"UW_PIN_SAMPLE_DELAY": "1"}
    out = migrate_unp08_ms_to_us(params)
    assert out is params   # same object, not a copy


# --- apply_all() -------------------------------------------------------------

def test_apply_all_runs_unp08_migration():
    params = {"UW_PIN_SAMPLE_DELAY": "5", "GNSS_ENABLE": "1"}
    out = apply_all(params)
    assert out["UW_PIN_SAMPLE_DELAY_US"] == "5000"
    assert "UW_PIN_SAMPLE_DELAY" not in out
    assert out["GNSS_ENABLE"] == "1"


def test_apply_all_post_state_passes_parmw_encoding():
    # End-to-end: a legacy template runs through apply_all() and the result
    # encodes through the PARMW pipeline without raising. This is the most
    # important regression — a botched migration would surface here.
    params = {"UW_PIN_SAMPLE_DELAY": "5"}
    apply_all(params)
    encoded = DTEParamMap.encode("UW_PIN_SAMPLE_DELAY_US",
                                 params["UW_PIN_SAMPLE_DELAY_US"])
    assert encoded == "5000"
