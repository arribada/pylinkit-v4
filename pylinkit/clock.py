"""Clock diagnostics from PWP07 LAST_TIME_SYNC and PWP08 WAKEUP_PERIOD_MEASURED_MS.

An RSPB is powered down between cycles and woken by a TPL5111 whose period is
set by a resistor, so its clock is carried from one cycle to the next with the
period that resistor gives. The error therefore grows with the time elapsed
since the last trusted setting (PWP07: GNSS fix or $RTCW), and faster while the
period the board really gives (PWP08) is unknown or far from WAKEUP_PERIOD
(PWP04).

Pure functions over a PARMR/STATR dict keyed by pylinkit long names (ints read
from the device, or strings from a config file), so the CLI and a GUI share the
same numbers and wording. A missing key (PWP08 on a LinkIt V4, PWP07 on older
firmware) is never an error: the matching line is simply not produced.
"""
import math
import time
from datetime import datetime, timezone

from .enums import WAKEUP_PERIOD_HELP

LAST_TIME_SYNC_LABEL = "Dernière synchro d'heure fiable"
WAKEUP_PERIOD_MEASURED_LABEL = "Période TPL mesurée"
CLOCK_ACCURACY_LABEL = "Précision estimée de l'horloge"

TPL_PERIOD_MISMATCH_WARNING = (
    "La résistance TPL5111 montée ne donne pas WAKEUP_PERIOD : vérifier PWP04"
)
CLOUDLOCATE_MEASC12_WARNING = (
    "MEASC12 transporte l'heure absolue de l'horloge, imprécise sur une carte "
    "TPL5111 entre deux fix : la position CloudLocate peut être fausse. "
    "Préférer MEAS20 (GNP46 = 1), insensible à l'erreur d'horloge."
)

RSPB_DEVICE_MODEL = 'RSPB'          # IDT02 on RSPB builds ('LinkIt V4' otherwise)
# Only EXTERNAL_WAKEUP builds, i.e. RSPB, implement these: a LinkIt V4 PARMR omits them.
RSPB_ONLY_PARAMS = ('SHUTDOWN_TIMER', 'BOOT_COUNTER', 'BOOT_COUNTER_MODULO',
                    'WAKEUP_PERIOD', 'WAKEUP_PERIOD_MEASURED_MS')

# PWP08 is calibrated within this many % of PWP04 x 1000; beyond, the mounted
# resistor does not give WAKEUP_PERIOD.
TPL_TOLERANCE_PCT = 10
# Clock accuracy on RSPB: ±(CLOCK_BASE_ERROR_S + drift x time since PWP07).
# Drifts in integer %, so the bound is not pushed up a second by float noise.
CLOCK_BASE_ERROR_S = 10
CLOCK_DRIFT_CALIBRATED_PCT = 2
CLOCK_DRIFT_UNCALIBRATED_PCT = 5

GNSS_FASTLOC_MODE_CLOUDLOCATE = 2       # GNP45
GNSS_CLOUDLOCATE_FORMAT_MEASC12 = 0     # GNP46 (1 = MEAS20)


def _uint(params, name):
    """``params[name]`` as an int, or None when absent or not a number."""
    try:
        return int(params[name])
    except (KeyError, TypeError, ValueError):
        return None


def _now(now):
    return time.time() if now is None else now


def is_rspb(params):
    """DEVICE_MODEL (IDT02) decides when known; otherwise the presence of a
    key only RSPB builds implement."""
    model = str(params.get('DEVICE_MODEL', '')).strip()
    if model:
        return model.upper() == RSPB_DEVICE_MODEL
    return any(p in params for p in RSPB_ONLY_PARAMS)


def format_duration(seconds):
    """'45 s', '5 min 12 s', '2 h 13 min', '3 j 4 h' (truncated to the units shown)."""
    s = int(seconds)
    if s < 60:
        return f"{s} s"
    if s < 3600:
        m, s = divmod(s, 60)
        return f"{m} min {s} s" if s else f"{m} min"
    if s < 86400:
        h, rem = divmod(s, 3600)
        m = rem // 60
        return f"{h} h {m} min" if m else f"{h} h"
    d, rem = divmod(s, 86400)
    h = rem // 3600
    return f"{d} j {h} h" if h else f"{d} j"


def format_epoch(value):
    """UTC date for an epoch; anything else (0, text) is returned as is."""
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return str(value)
    if ts <= 0:
        return str(value)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')


def time_since_sync_s(params, now=None):
    """Seconds elapsed since PWP07, or None when PWP07 is absent or 0."""
    ts = _uint(params, 'LAST_TIME_SYNC')
    if not ts:
        return None
    return _now(now) - ts


def format_last_time_sync(params, now=None):
    """PWP07 as 'date UTC (il y a 2 h 13 min)', 'jamais' if 0, None if absent."""
    ts = _uint(params, 'LAST_TIME_SYNC')
    if ts is None:
        return None
    if ts == 0:
        return "jamais"
    age = _now(now) - ts
    if age < 0:
        return f"{format_epoch(ts)} (dans {format_duration(-age)} : horloge de ce PC en retard ?)"
    return f"{format_epoch(ts)} (il y a {format_duration(age)})"


def _tpl_periods_ms(params):
    """(measured, nominal) TPL periods in ms, or None unless both are known and non-zero."""
    measured = _uint(params, 'WAKEUP_PERIOD_MEASURED_MS')
    nominal_s = _uint(params, 'WAKEUP_PERIOD')
    if not measured or not nominal_s:
        return None
    return measured, nominal_s * 1000


def wakeup_period_deviation_pct(params):
    """Signed deviation of PWP08 from PWP04 x 1000, in %; None if not computable."""
    periods = _tpl_periods_ms(params)
    if periods is None:
        return None
    measured, nominal = periods
    return (measured - nominal) * 100.0 / nominal


def is_tpl_calibrated(params):
    """PWP08 measured and within ±TPL_TOLERANCE_PCT % of PWP04 x 1000."""
    periods = _tpl_periods_ms(params)
    if periods is None:
        return False
    measured, nominal = periods
    # Integer comparison: the 10 % boundary must not depend on float rounding.
    return abs(measured - nominal) * 100 <= TPL_TOLERANCE_PCT * nominal


def tpl_period_mismatch(params):
    """PWP08 measured but more than TPL_TOLERANCE_PCT % away from PWP04."""
    return _tpl_periods_ms(params) is not None and not is_tpl_calibrated(params)


def format_wakeup_period_measured(params):
    """PWP08 in s (3 decimals) with its deviation from PWP04; None if absent."""
    measured = _uint(params, 'WAKEUP_PERIOD_MEASURED_MS')
    if measured is None:
        return None
    if measured == 0:
        return "pas encore mesurée"
    text = f"{measured / 1000:.3f} s"
    deviation = wakeup_period_deviation_pct(params)
    if deviation is None:
        return f"{text} (écart non calculable : PWP04 inconnu ou nul)"
    return f"{text} (écart {deviation:+.2f} % / PWP04 = {_uint(params, 'WAKEUP_PERIOD')} s)"


def clock_drift_pct(params):
    """Drift used for the accuracy bound: 2 % once PWP08 is calibrated, else 5 %."""
    return CLOCK_DRIFT_CALIBRATED_PCT if is_tpl_calibrated(params) else CLOCK_DRIFT_UNCALIBRATED_PCT


def clock_accuracy_s(params, now=None):
    """Half-width in s of the RSPB clock error: 10 s + drift x time since
    PWP07. None means unbounded (PWP07 is 0 or absent)."""
    age = time_since_sync_s(params, now)
    if age is None:
        return None
    return CLOCK_BASE_ERROR_S + clock_drift_pct(params) * max(age, 0) / 100


def format_clock_accuracy(params, now=None):
    """'±2 min 50 s (10 s + 2 % × 2 h 13 min)', 'non bornée', or None off RSPB."""
    if not is_rspb(params):
        return None
    accuracy = clock_accuracy_s(params, now)
    if accuracy is None:
        return "non bornée"
    age = max(time_since_sync_s(params, now), 0)
    calibrated = "PWP08 calibrée" if is_tpl_calibrated(params) else "PWP08 non calibrée"
    # Rounded up: a bound must not be understated.
    return (f"±{format_duration(math.ceil(accuracy))} "
            f"({CLOCK_BASE_ERROR_S} s + {clock_drift_pct(params)} % × {format_duration(age)}, "
            f"{calibrated})")


def cloudlocate_clock_sensitive(params):
    """RSPB in CloudLocate (GNP45 = 2) with the MEASC12 format (GNP46 = 0)."""
    return (is_rspb(params)
            and _uint(params, 'GNSS_FASTLOC_MODE') == GNSS_FASTLOC_MODE_CLOUDLOCATE
            and _uint(params, 'GNSS_CLOUDLOCATE_FORMAT') == GNSS_CLOUDLOCATE_FORMAT_MEASC12)


def report(params, now=None):
    """(label, value) lines for PWP07, PWP08 and, on RSPB, the clock accuracy.
    Lines whose parameters were not read are left out."""
    rows = []
    if 'LAST_TIME_SYNC' in params:
        rows.append((f"{LAST_TIME_SYNC_LABEL} (PWP07)", format_last_time_sync(params, now)))
    if 'WAKEUP_PERIOD_MEASURED_MS' in params:
        rows.append((f"{WAKEUP_PERIOD_MEASURED_LABEL} (PWP08)", format_wakeup_period_measured(params)))
    if 'LAST_TIME_SYNC' in params and is_rspb(params):
        rows.append((CLOCK_ACCURACY_LABEL, format_clock_accuracy(params, now)))
    return rows


def warnings(params):
    """Warnings to show prominently next to the clock lines."""
    out = []
    if tpl_period_mismatch(params):
        out.append(TPL_PERIOD_MISMATCH_WARNING)
    if cloudlocate_clock_sensitive(params):
        out.append(CLOUDLOCATE_MEASC12_WARNING)
    return out


# A PARMW touching one of these deserves a pre-flight: read PREFLIGHT_PARAMS
# from the board and feed them to parmw_preflight().
PREFLIGHT_TRIGGERS = ('WAKEUP_PERIOD', 'GNSS_FASTLOC_MODE', 'GNSS_CLOUDLOCATE_FORMAT')
PREFLIGHT_PARAMS = ('DEVICE_MODEL',) + PREFLIGHT_TRIGGERS


def parmw_preflight(device, new):
    """(notes, warnings) before writing ``new`` to a board whose current values
    are ``device`` (a PARMR of PREFLIGHT_PARAMS, possibly empty if unreadable)."""
    notes = []
    old_period, new_period = _uint(device, 'WAKEUP_PERIOD'), _uint(new, 'WAKEUP_PERIOD')
    if old_period is not None and new_period is not None and old_period != new_period:
        notes.append(f"WAKEUP_PERIOD (PWP04) {old_period} s -> {new_period} s. {WAKEUP_PERIOD_HELP}")
    effective = {**device, **new}
    if 'DEVICE_MODEL' in device:
        effective['DEVICE_MODEL'] = device['DEVICE_MODEL']   # the board decides, not the file
    found = [CLOUDLOCATE_MEASC12_WARNING] if cloudlocate_clock_sensitive(effective) else []
    return notes, found
