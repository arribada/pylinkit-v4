"""Regression tests for the DTE param map as a whole.

Why this exists:
  - The param map is hand-edited as a flat Python list. Easy regressions:
      * Duplicate long name -> earliest entry wins, later one silently dead
      * Duplicate short key -> PARMR/PARMW could write the wrong slot
      * Typo in a codec -> AttributeError at first encode/decode (runtime only)
      * Removing/renaming a long name -> silently breaks .cfg files in the field
  - These tests catch each of those before a release.

What they do NOT do:
  - They don't snapshot the full map (would create constant maintenance churn).
  - They snapshot only the params we've explicitly touched in recent migrations,
    so a rename of those specific keys is flagged immediately.
"""
import pytest

from pylinkit.protocol.dte_params import DTEParamMap


# ---------------------------------------------------------------------------
# Structural invariants — every entry must be well-formed.
# ---------------------------------------------------------------------------

def test_every_entry_is_3_tuple():
    bad = [e for e in DTEParamMap.param_map if not (isinstance(e, list) and len(e) == 3)]
    assert bad == [], f'malformed entries (must be [long, short, codec]): {bad}'


def test_long_names_unique():
    names = [e[0] for e in DTEParamMap.param_map]
    seen = {}
    for n in names:
        seen[n] = seen.get(n, 0) + 1
    dupes = {n: c for n, c in seen.items() if c > 1}
    assert dupes == {}, f'duplicate long names: {dupes}'


def test_short_keys_unique():
    keys = [e[1] for e in DTEParamMap.param_map]
    seen = {}
    for k in keys:
        seen[k] = seen.get(k, 0) + 1
    dupes = {k: c for k, c in seen.items() if c > 1}
    assert dupes == {}, f'duplicate short keys: {dupes}'


def test_short_key_format():
    # Short keys are 3 letters + 2 hex-ish digits in pylinkit's convention
    # (e.g. ARP16, GNP49, LBP08). Format drift is a strong signal of a typo.
    import re
    pattern = re.compile(r'^[A-Z]{3}\d{2}$')
    bad = [e[1] for e in DTEParamMap.param_map if not pattern.match(e[1])]
    assert bad == [], f'short keys violate "LLLDD" format: {bad}'


def test_long_name_format():
    # Long names are SCREAMING_SNAKE_CASE. Anything else is a typo.
    import re
    pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')
    bad = [e[0] for e in DTEParamMap.param_map if not pattern.match(e[0])]
    assert bad == [], f'long names violate SCREAMING_SNAKE_CASE: {bad}'


def test_every_codec_has_encode_and_decode():
    bad = []
    for long_name, short_key, codec in DTEParamMap.param_map:
        if not (hasattr(codec, 'encode') and callable(codec.encode)):
            bad.append((long_name, codec, 'missing encode()'))
        if not (hasattr(codec, 'decode') and callable(codec.decode)):
            bad.append((long_name, codec, 'missing decode()'))
    assert bad == [], f'codecs missing encode/decode: {bad}'


# ---------------------------------------------------------------------------
# Round-trip — long ↔ short resolution must be symmetric and total.
# ---------------------------------------------------------------------------

def test_param_to_key_and_back_is_identity():
    for long_name, short_key, _ in DTEParamMap.param_map:
        assert DTEParamMap.param_to_key(long_name) == short_key
        assert DTEParamMap.key_to_param(short_key) == long_name


def test_lookup_raises_on_unknown_long_name():
    with pytest.raises(Exception):
        DTEParamMap.param_to_key('TOTALLY_NOT_A_REAL_PARAM')


def test_lookup_raises_on_unknown_short_key():
    with pytest.raises(Exception):
        DTEParamMap.key_to_param('ZZZ99')


# ---------------------------------------------------------------------------
# Snapshot — params we have explicitly touched in recent migrations.
# If any of these (long, short, codec_name) tuples changes, this test fails
# and the change becomes an explicit, reviewable decision.
# ---------------------------------------------------------------------------

# (long_name, short_key, codec class name) for params with a known migration
# history. Update only when intentionally re-renaming or re-typing.
SNAPSHOT = [
    # GNSS depth pile family (rename: GNSS_NBLASTFIX_TOSEND -> ARGOS_DEPTH_PILE)
    ("ARGOS_DEPTH_PILE",                  "ARP16", "DEPTHPILE"),
    ("LB_ARGOS_DEPTH_PILE",               "LBP08", "DEPTHPILE"),
    ("ZONE_ARGOS_DEPTH_PILE",             "ZOP08", "DEPTHPILE"),

    # SWS sampling periods (type change: UINT -> SAMPLINGPERIOD)
    ("UW_WET_SAMPLING",                   "UNP03", "SAMPLINGPERIOD"),
    ("UW_DRY_SAMPLING",                   "UNP04", "SAMPLINGPERIOD"),

    # LED HRS_24 cutoff (added)
    ("LED_HRS24_RTC_CUTOFF",              "LDP03", "DATESTRING"),

    # GNSS backup-cell charge (added)
    ("BACKUP_CELL_CHARGE_INTERVAL",       "GNP47", "UINT"),
    ("BACKUP_CELL_CHARGE_DURATION",       "GNP48", "UINT"),
    ("BACKUP_CELL_CHARGE_ONLY_SUBMERGED", "GNP49", "BOOLEAN"),
]


@pytest.mark.parametrize("long_name,short_key,codec_name", SNAPSHOT)
def test_migrated_param_snapshot(long_name, short_key, codec_name):
    for entry_long, entry_short, entry_codec in DTEParamMap.param_map:
        if entry_long == long_name:
            assert entry_short == short_key, (
                f'{long_name}: short key changed from {short_key} to {entry_short}'
            )
            assert entry_codec.__name__ == codec_name, (
                f'{long_name}: codec changed from {codec_name} to {entry_codec.__name__}'
            )
            return
    pytest.fail(f'snapshot key {long_name} no longer present in param_map')


# ---------------------------------------------------------------------------
# Removed-key allow-list — keys we explicitly deleted must STAY deleted.
# A re-add would be either a deliberate revert (update this list) or a
# careless copy-paste from an old branch (catch it here).
# ---------------------------------------------------------------------------

REMOVED = [
    "LAST_FULL_CHARGE_DATE",     # POT05, removed (firmware no longer exposes it)
    "GNSS_NBLASTFIX_TOSEND",     # ARP16 renamed to ARGOS_DEPTH_PILE
    "LB_GNSS_NBLASTFIX_TOSEND",  # LBP08 renamed to LB_ARGOS_DEPTH_PILE
]


@pytest.mark.parametrize("removed_long", REMOVED)
def test_removed_keys_stay_removed(removed_long):
    present = [e[0] for e in DTEParamMap.param_map]
    assert removed_long not in present, (
        f'{removed_long} was deliberately removed; if you re-added it, '
        f'update REMOVED in this file with a comment explaining why.'
    )


# ---------------------------------------------------------------------------
# Codec sanity — a tiny encode/decode round-trip on every (codec, sample)
# we can derive a representative value for. Catches "codec wired but broken".
# ---------------------------------------------------------------------------

# Per-codec representative sample value. Anything not listed here is skipped
# (TEXT, UPPERCASETEXT, BASE64 etc. need specific inputs we don't want to
# guess for every map entry).
CODEC_SAMPLES = {
    "UINT":      1,
    "BOOLEAN":   1,
    "FLOAT":     1.5,
    "DATESTRING": "01/01/2026 12:00:00",
}


def test_codec_round_trip_smoke():
    """For every map entry whose codec we have a sample for, encode then
    decode and assert no exception. This catches a codec class that has
    encode/decode methods but is otherwise broken (e.g. missing
    ``allowed`` table after a refactor)."""
    failures = []
    for long_name, _, codec in DTEParamMap.param_map:
        sample = CODEC_SAMPLES.get(codec.__name__)
        if sample is None:
            continue
        try:
            encoded = codec.encode(sample)
            codec.decode(encoded)
        except Exception as exc:
            failures.append((long_name, codec.__name__, repr(exc)))
    assert failures == [], f'codec round-trip failures: {failures}'
