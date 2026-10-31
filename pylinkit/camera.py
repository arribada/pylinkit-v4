"""RunCam camera: control mode, CAMTST answer and last session (CAT00-CAT06).

Two camera modes are chosen when the firmware is built, and both stay supported:

- BUTTON, the historical one: the camera is driven by its power-button pin.
  CAP01-CAP05 and LBP13 only, plus the status key CAT00 on firmware v4.2.1.
- UART (firmware v4.2.1, CAM_CONTROL=UART): a RunCam Split 4 driven over its
  UART. Adds CAP06/CAP07, the last-session keys CAT01-CAT06 and the CAMTST test.

Every tag still on a published firmware (v4.0.0 to v4.2.0) with a camera is a
BUTTON one, without CAT00. The mode therefore comes from the PARML list, never
from the version number (IDT03): CAT00 when listed, else CAP01 means BUTTON,
else no camera.

Pure functions over dicts keyed by pylinkit long names, so the CLI and a GUI
share the same numbers and wording. A missing key is never an error: the
matching line is simply not produced.
"""
from .enums import (CAM_REC_MODE_LABELS, CAM_RESOLUTION_LABELS,
                    CAM_RESOLUTION_KEEP_LABEL)

BUTTON = 'BUTTON'
UART = 'UART'
# CAT00 CAM_CONTROL_MODE codes.
CONTROL_MODES = {1: BUTTON, 2: UART}

# CAMTST answers when the camera is off again: ~20 s, ~40 s when CAP07 costs a
# restart, 180 s at most (then status TIMEOUT). Listen a little longer.
CAMTST_TIMEOUT_S = 185.0

CAMTST_FIELDS = ('status', 'features', 'free_mb', 'total_mb', 'remaining_s',
                 'recording', 'stopped', 'clock', 'starts', 'duration_ms',
                 'resolution')

OK, WARN, ERROR = 'ok', 'warn', 'error'

# CAMTST status, also CAT01 CAM_LAST_OUTCOME (0..6): name, meaning, verdict.
CAMTST_STATUS = {
    0: ('OK', "Enregistrement et arrêt vus sur la carte", OK),
    1: ('NO_ANSWER', "Caméra absente, non alimentée ou mal câblée", ERROR),
    2: ('NO_SPACE', "Carte pleine, absente ou inutilisable", ERROR),
    3: ('NOT_RECORDING', "La carte ne se remplit pas, même après un 2e départ", ERROR),
    4: ('UNVERIFIED', "Session faite mais carte illisible, appuis crus sans vérification", WARN),
    5: ('STOP_FAILED', "Encore en enregistrement après tous les arrêts", ERROR),
    6: ('LINK_ERROR', "UART indisponible", ERROR),
    7: ('BUSY', "Caméra déjà en session", WARN),
    8: ('TIMEOUT', "Aucune issue en 180 s, caméra coupée", ERROR),
}
CAT01_NO_SESSION = 255

# Unread SD values: 0xFFFFFFFF in CAT02-CAT04, -1 in the CAMTST answer.
UNREAD = (0xFFFFFFFF, -1)
SPLIT4_FEATURES = 119

STARTS_MISMATCH_WARNING = (
    "Deux départs envoyés : l'enregistrement automatique de la caméra ne "
    "correspond pas à CAP06. Ça fonctionne, mais corriger CAP06 ou le menu de la caméra."
)

# Two settings only exist in the camera's own menu (its UART does not expose
# them): to be done once, by hand, before deployment.
OPERATOR_REMINDERS = (
    "Menu de la caméra : enregistrement automatique en accord avec CAP06 "
    "(désactivé avec TOGGLE, recommandé).",
    "Menu de la caméra : enregistrement en boucle désactivé, sinon une carte "
    "pleine est vue comme « impossible d'enregistrer ».",
)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def camera_mode(supported_keys, control_mode=None):
    """BUTTON, UART or None (no camera), from the PARML list and, when CAT00 is
    listed, its STATR value ``control_mode``.

    CAT00 listed but unreadable or with a code this version does not know gives
    BUTTON when the build has a camera: the mode that never sends CAMTST."""
    keys = set(supported_keys)
    if 'CAT00' in keys:
        mode = CONTROL_MODES.get(_int(control_mode))
        if mode is not None:
            return mode
    if 'CAT00' in keys or 'CAP01' in keys:
        return BUTTON
    return None


def camtst_available(mode):
    """CAMTST exists on UART builds only: never send it anywhere else."""
    return mode == UART


def parse_camtst(payload):
    """The CAMTST answer as a dict of ints (None for an unread SD value or a
    missing field). Fields past the eleventh, from a later firmware, are ignored."""
    parts = [p.strip() for p in payload.split(',')]
    result = {}
    for i, name in enumerate(CAMTST_FIELDS):
        result[name] = _int(parts[i]) if i < len(parts) else None
    for name in ('free_mb', 'total_mb', 'remaining_s'):
        if result[name] in UNREAD:
            result[name] = None
    if result['status'] is None:
        raise ValueError(f'CAMTST: no status in {payload!r}')
    return result


def status_name(code):
    entry = CAMTST_STATUS.get(code)
    return entry[0] if entry else f'inconnu ({code})'


def status_text(code):
    """'OK : Enregistrement et arrêt vus sur la carte'."""
    entry = CAMTST_STATUS.get(code)
    return f'{entry[0]} : {entry[1]}' if entry else f'inconnu ({code})'


def verdict(code):
    """ok (green), warn (orange) or error (red)."""
    entry = CAMTST_STATUS.get(code)
    return entry[2] if entry else ERROR


def _go(mb):
    return f'{mb / 1000:.1f}'.replace('.', ',')


def format_sd_card(free_mb, total_mb):
    """'6,1 Go libres sur 15,1 Go', or None when the card was not read."""
    free, total = _int(free_mb), _int(total_mb)
    if free is None or total is None or free in UNREAD or total in UNREAD:
        return None
    return f'{_go(free)} Go libres sur {_go(total)} Go'


def format_rec_time(seconds):
    """'18 min', '2 h 05 min', '45 s', or None when not read."""
    s = _int(seconds)
    if s is None or s in UNREAD or s < 0:
        return None
    if s < 60:
        return f'{s} s'
    minutes = round(s / 60)
    if minutes < 60:
        return f'{minutes} min'
    return f'{minutes // 60} h {minutes % 60:02d} min'


def resolution_label(code, setting=False):
    """Label of a CAP07 code. 0 means 'keep the camera's own' for the setting
    (CAP07), 'unknown' for what was read (CAT05, CAMTST)."""
    n = _int(code)
    if n == 0:
        return CAM_RESOLUTION_KEEP_LABEL if setting else 'inconnue'
    return CAM_RESOLUTION_LABELS.get(n, f'inconnue ({code})')


def rec_mode_label(code):
    n = _int(code)
    return CAM_REC_MODE_LABELS.get(n, f'inconnu ({code})')


def features_label(value):
    n = _int(value)
    if n == 0:
        return 'pas de réponse'
    if n == SPLIT4_FEATURES:
        return f'{n} (Split 4)'
    return str(value)


def _check(flag):
    # Words, not check marks: a redirected Windows console cannot encode them.
    return 'oui' if _int(flag) == 1 else 'non'


def settings_rows(params):
    """(label, value) for CAP06/CAP07 when present."""
    rows = []
    if 'CAM_REC_MODE' in params:
        rows.append(('CAM_REC_MODE (CAP06)', rec_mode_label(params['CAM_REC_MODE'])))
    if 'CAM_RESOLUTION' in params:
        rows.append(('CAM_RESOLUTION (CAP07)',
                     resolution_label(params['CAM_RESOLUTION'], setting=True)))
    return rows


def last_session_rows(params):
    """(label, value) for the last camera session, from CAT01-CAT06."""
    if 'CAM_LAST_OUTCOME' not in params:
        return []
    outcome = _int(params['CAM_LAST_OUTCOME'])
    if outcome == CAT01_NO_SESSION:
        return [('Issue', 'aucune session encore')]
    rows = [('Issue', status_text(outcome))]
    card = format_sd_card(params.get('CAM_SD_FREE_MB'), params.get('CAM_SD_TOTAL_MB'))
    if card:
        rows.append(('Carte SD', card))
    left = format_rec_time(params.get('CAM_REC_TIME_LEFT_S'))
    if left:
        rows.append(("Temps d'enregistrement restant", left))
    if 'CAM_RESOLUTION_READ' in params:
        rows.append(('Résolution', resolution_label(params['CAM_RESOLUTION_READ'])))
    if 'CAM_FEATURES' in params:
        rows.append(('Fonctions caméra', features_label(params['CAM_FEATURES'])))
    return rows


def camtst_rows(result):
    """(label, value) for a CAMTST answer, verdict first."""
    rows = [('Verdict', status_text(result['status']))]
    card = format_sd_card(result.get('free_mb'), result.get('total_mb'))
    rows.append(('Carte SD', card or 'non lue'))
    left = format_rec_time(result.get('remaining_s'))
    rows.append(("Temps d'enregistrement restant", left or 'non lu'))
    if result.get('resolution') is not None:
        rows.append(('Résolution', resolution_label(result['resolution'])))
    rows.append(('Enregistrement', _check(result.get('recording'))))
    rows.append(('Arrêt', _check(result.get('stopped'))))
    rows.append(('Horloge', _check(result.get('clock'))))
    if result.get('features') is not None:
        rows.append(('Fonctions caméra', features_label(result['features'])))
    if result.get('duration_ms') is not None:
        rows.append(('Durée du test', f"{result['duration_ms'] / 1000:.1f} s".replace('.', ',')))
    return rows


def camtst_warnings(result):
    return [STARTS_MISMATCH_WARNING] if _int(result.get('starts')) == 2 else []
