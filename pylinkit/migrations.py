"""Template migrations for firmware-side breaking changes.

Each ``migrate_*`` helper is named after the firmware change it compensates for
and is idempotent: running it twice on the same template is a no-op after the
first pass (the post-migration value either still falls in range, or was
already clamped to the new max).

Helpers operate on plain string -> string dicts (the natural shape of a
ConfigParser ``[PARAM]`` section). They mutate the input dict in place AND
return it, so they compose:

    params = migrate_unp08_ms_to_us(params)
    params = migrate_next_thing(params)
"""

# Config version bumps that introduced the migrations below — for documentation
# only, pylinkit doesn't read this value off the device today.
CONFIG_VERSION_UNP08_US = 0x1E


def migrate_unp08_ms_to_us(params):
    """Firmware 0x1D -> 0x1E: UNP08 renamed UW_PIN_SAMPLE_DELAY (ms) ->
    UW_PIN_SAMPLE_DELAY_US (µs).

    Rewrites the dict in place:
      - drops the legacy long name(s) if present
      - converts the numeric value: ms * 1000, clamped to the new [50, 30000]
        firmware range
      - leaves an already-migrated key untouched

    Legacy long names accepted as input (any of these is treated as the old
    UNP08 ms value): ``UW_PIN_SAMPLE_DELAY``, ``SWS_SAMPLE_DELAY_INITIAL``.
    """
    NEW_KEY = "UW_PIN_SAMPLE_DELAY_US"
    LEGACY_KEYS = ("UW_PIN_SAMPLE_DELAY", "SWS_SAMPLE_DELAY_INITIAL")
    NEW_MIN_US = 50
    NEW_MAX_US = 30000

    legacy_ms = None
    for k in LEGACY_KEYS:
        if k in params:
            legacy_ms = params.pop(k)
            break

    if legacy_ms is None:
        return params

    try:
        ms = int(legacy_ms)
    except (TypeError, ValueError):
        # Can't parse — drop it; firmware would reject anyway. Caller can
        # inspect the returned dict and notice the legacy key is gone with
        # no replacement.
        return params

    us = ms * 1000
    if us > NEW_MAX_US:
        us = NEW_MAX_US
    elif us < NEW_MIN_US:
        us = NEW_MIN_US

    params[NEW_KEY] = str(us)
    return params


# Public registry — list of all known migrations in order. apply_all() runs
# them on a template before upload. Keep ordered oldest-first so a 0x1D-era
# template upgrades through every step.
ALL_MIGRATIONS = (
    migrate_unp08_ms_to_us,
)


def apply_all(params):
    """Run every known migration on ``params`` in registration order.
    Idempotent; safe to call on already-current templates."""
    for fn in ALL_MIGRATIONS:
        fn(params)
    return params
