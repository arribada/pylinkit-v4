"""Unit tests for the GNSS_NBLASTFIX_TOSEND -> ARGOS_DEPTH_PILE migration.

Covers:
  - DTE param map renames (long key + short key + type) for ARP16/LBP08/ZOP08
  - The legacy long key is gone (PARMR/PARMW would otherwise silently target
    the wrong slot or fail with an unhelpful error)
  - DEPTHPILE encode/decode roundtrip on every accepted value
  - DEPTHPILE rejection of values outside the allowed set {1,2,3,4,8,12,16,20,24}
  - ArgosDepthPile IntEnum + DEPTH_PILE_VALUES constant
  - depth_pile_label() switches Argos/LoRa wording
"""
import pytest

from pylinkit.protocol.dte_params import DTEParamMap
from pylinkit.protocol.dte_types import DEPTHPILE
from pylinkit.enums import ArgosDepthPile, DEPTH_PILE_VALUES, depth_pile_label


ALLOWED_VALUES = (1, 2, 3, 4, 8, 12, 16, 20, 24)


# --- Param map renames -------------------------------------------------------

@pytest.mark.parametrize("long_key,short_key", [
    ("ARGOS_DEPTH_PILE",      "ARP16"),
    ("LB_ARGOS_DEPTH_PILE",   "LBP08"),
    ("ZONE_ARGOS_DEPTH_PILE", "ZOP08"),
])
def test_depth_pile_keys_present(long_key, short_key):
    assert DTEParamMap.param_to_key(long_key) == short_key
    assert DTEParamMap.key_to_param(short_key) == long_key


@pytest.mark.parametrize("legacy_long", [
    "GNSS_NBLASTFIX_TOSEND",
    "LB_GNSS_NBLASTFIX_TOSEND",
])
def test_legacy_long_keys_removed(legacy_long):
    with pytest.raises(Exception):
        DTEParamMap.param_to_key(legacy_long)


@pytest.mark.parametrize("long_key", [
    "ARGOS_DEPTH_PILE", "LB_ARGOS_DEPTH_PILE", "ZONE_ARGOS_DEPTH_PILE",
])
def test_depth_pile_uses_DEPTHPILE_codec(long_key):
    for v in ALLOWED_VALUES:
        assert DTEParamMap.encode(long_key, v) == DEPTHPILE.encode(v)


# --- DEPTHPILE encode/decode -------------------------------------------------

@pytest.mark.parametrize("v", ALLOWED_VALUES)
def test_depthpile_roundtrip(v):
    encoded = DEPTHPILE.encode(v)
    assert DEPTHPILE.decode(encoded) == v


@pytest.mark.parametrize("v", ALLOWED_VALUES)
def test_depthpile_encode_returns_string(v):
    assert isinstance(DEPTHPILE.encode(v), str)


@pytest.mark.parametrize("bad", [0, -1, 5, 6, 7, 9, 10, 11, 13, 25, 100])
def test_depthpile_encode_rejects_invalid(bad):
    with pytest.raises(ValueError):
        DEPTHPILE.encode(bad)


def test_depthpile_encode_rejects_string_garbage():
    with pytest.raises(ValueError):
        DEPTHPILE.encode("not-a-number")


# --- ArgosDepthPile enum + DEPTH_PILE_VALUES tuple ---------------------------

def test_enum_values_match_spec():
    assert tuple(m.value for m in ArgosDepthPile) == ALLOWED_VALUES


def test_depth_pile_values_constant():
    assert DEPTH_PILE_VALUES == ALLOWED_VALUES


def test_enum_members_accept_int_and_name():
    assert ArgosDepthPile(8) is ArgosDepthPile.DEPTH_PILE_8
    assert ArgosDepthPile["DEPTH_PILE_24"].value == 24


# --- depth_pile_label -------------------------------------------------------

@pytest.mark.parametrize("mode", ["lora", "LoRa", "LORA"])
def test_label_lora(mode):
    assert depth_pile_label(mode) == "LoRa depth pile"


@pytest.mark.parametrize("mode", ["argos", "Argos", "ARGOS", "kim2", "smd", "", None])
def test_label_falls_back_to_argos(mode):
    assert depth_pile_label(mode) == "Argos depth pile"
