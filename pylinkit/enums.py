from enum import IntEnum


class BaseLogDType(IntEnum):
    """DUMPD log types. Matches firmware BaseLogDType."""
    INTERNAL = 0
    GNSS = 1
    ALS = 2
    PH = 3
    RTD = 4
    CDT = 5
    CAM = 6
    AXL = 7
    PRESSURE = 8
    THERMISTOR = 9
    TSYS01 = 10
    SWS_LOG = 11
    MORTALITY = 12

    @classmethod
    def from_name(cls, name: str):
        """Resolve name with backward-compatible aliases."""
        aliases = {'system': 'INTERNAL', 'sensor': 'GNSS', 'sws': 'SWS_LOG'}
        lookup = aliases.get(name.lower(), name.upper())
        return cls[lookup]


class BaseEraseType(IntEnum):
    """ERASE types. Matches firmware BaseEraseType."""
    GNSS = 1
    SYSTEM = 2
    ALL = 3
    ALS = 4
    PH = 5
    RTD = 6
    CDT = 7
    CAM = 8
    AXL = 9
    PRESSURE = 10
    THERMISTOR = 11
    TSYS01 = 12
    SWS_LOG = 13
    MORTALITY = 14

    @classmethod
    def from_name(cls, name: str):
        """Resolve name with backward-compatible aliases."""
        aliases = {'sensor': 'GNSS', 'sws': 'SWS_LOG'}
        lookup = aliases.get(name.lower(), name.upper())
        return cls[lookup]


class BaseSensorCalType(IntEnum):
    """SCALW/SCALR sensor types. Matches firmware BaseSensorCalType."""
    AXL = 0
    PRESSURE = 1
    ALS = 2
    PH = 3
    RTD = 4
    CDT = 5
    MCP47X6 = 6
    THERMISTOR = 7
    SWS = 8


class ComponentPower(IntEnum):
    """PWRON component types."""
    ALL = 0
    GNSS = 1
    SENSORS = 2
    SATELLITE = 3
    OFF = 4


class ArgosModulation(IntEnum):
    """Kineis modulation types. Matches firmware KineisModulation/BaseArgosModulation."""
    LDK = 0
    LDA2 = 1
    VLDA4 = 2


class ArgosDepthPile(IntEnum):
    """ARGOS_DEPTH_PILE (ARP16) allowed values: number of last GPS fixes
    retransmitted per cycle. Same enum applies to LB_ARGOS_DEPTH_PILE (LBP08)
    and ZONE_ARGOS_DEPTH_PILE (ZOP08)."""
    DEPTH_PILE_1 = 1
    DEPTH_PILE_2 = 2
    DEPTH_PILE_3 = 3
    DEPTH_PILE_4 = 4
    DEPTH_PILE_8 = 8
    DEPTH_PILE_12 = 12
    DEPTH_PILE_16 = 16
    DEPTH_PILE_20 = 20
    DEPTH_PILE_24 = 24


DEPTH_PILE_VALUES = tuple(m.value for m in ArgosDepthPile)


def depth_pile_label(radio_mode: str) -> str:
    """UI label for *_ARGOS_DEPTH_PILE params. The DTE key never changes;
    only the user-facing string adapts to the active radio backend."""
    return "LoRa depth pile" if str(radio_mode).lower() == "lora" else "Argos depth pile"


# --- NTRY_PER_MESSAGE family (ARP19, LBP11, ZOP13): UINT, range 0..86400 -------
# Value 0 has a special meaning, so the UI shows a label instead of the raw 0.
NTRY_PER_MESSAGE_MIN = 0
NTRY_PER_MESSAGE_MAX = 86400


def ntry_per_message_label(value) -> str:
    """UI label for the *NTRY_PER_MESSAGE spinbox. 0 = unlimited replay.
    Keep 0 selectable in the widget; only the displayed text changes."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    return "Auto / Illimité" if n == 0 else str(n)


NTRY_PER_MESSAGE_HELP = (
    "Nombre de transmissions par message satellite.\n"
    "• N>0 : chaque position/message est transmis exactement N fois puis devient inerte.\n"
    "• 0 = Illimité : en LEGACY/DUTY_CYCLE/PASS_PREDICTION la depth pile est rejouée en "
    "boucle jusqu'à ce que de nouveaux fix évincent les anciens (borné par ARGOS_DEPTH_PILE).\n"
    "  En SURFACING_BURST, 0 = un seul envoi par fix.\n"
    "En mode BLIND : NTRY = nombre de séquences blind déclenchées par le nRF ; "
    "TR_NOM = intervalle entre deux séquences blind."
)

# --- BLIND Argos mode (ARP44/45/46, firmware 2026-07-03, config version 0x20) --
# The satellite module (KMAC BLIND profile) handles the per-burst repetitions:
# the nRF sends once, the module re-emits retx_nb copies spaced by retx_period_s.
ARGOS_BLIND_EN_HELP = (
    "Active le mode BLIND : le module satellite gère lui-même les répétitions "
    "(au lieu du nRF). Sans effet en SURFACING_BURST et DOPPLER (exclus). "
    "Défaut désactivé = comportement normal inchangé."
)
ARGOS_BLIND_RETX_NB_HELP = (
    "Nombre de répétitions d'un message par burst blind (le module émet N copies). "
    "Distinct de NTRY_PER_MESSAGE (=nombre de séquences blind déclenchées par le nRF). "
    "Ex : NTRY=3 et RETX_NB=4 → 3 séquences × 4 copies = 12 émissions."
)
ARGOS_BLIND_RETX_PERIOD_S_HELP = (
    "Intervalle (secondes) entre deux répétitions AU SEIN d'un burst (géré par le module). "
    "À NE PAS confondre avec TR_NOM = intervalle entre deux séquences blind (géré par le nRF)."
)
# Documented soft constraint (not a hard block): keep retx_nb * retx_period_s
# below 2 h. Beyond 7200 s the firmware clamps the TX window and may raise a
# false TX error.
ARGOS_BLIND_MAX_WINDOW_S = 7200

# --- RSPB TPL5111 clock (PWP04/PWP06; PWP07/PWP08 are shown by clock.py) -----
WAKEUP_PERIOD_HELP = (
    "Période pour laquelle la résistance du TPL5111 a été choisie (1 h ≈ 124,9 kΩ). "
    "Doit correspondre à la résistance montée. "
    "La modifier efface la période mesurée (PWP08)."
)
LAST_KNOWN_RTC_HELP = "Sur RSPB : instant du démarrage du dernier cycle."

# --- Flash journal level (DBP02 SYSTEM_LOG_LEVEL, firmware v4.2.1) -------------
# UINT 0..3 on the wire. Only shown, read or written when PARML lists DBP02: no
# published firmware (v4.0.0 to v4.2.0) has it, and that is not an error.
SYSTEM_LOG_LEVEL_LABELS = {0: 'OFF', 1: 'ERROR', 2: 'WARN', 3: 'INFO'}
SYSTEM_LOG_LEVEL_DEFAULT = 3
SYSTEM_LOG_LEVEL_TITLE = "Journal flash"
SYSTEM_LOG_LEVEL_HELP = (
    "WARN pour une balise qui ne sera pas récupérée : elle n'écrit plus que ce "
    "qui ne va pas. Pris en compte à la sortie du mode configuration."
)
NOT_ON_THIS_FIRMWARE = "non disponible sur ce firmware"


def system_log_level_label(value) -> str:
    """'WARN', ... for DBP02, or 'inconnu (N)' for a value a later firmware
    may return: shown raw, never rewritten."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return f"inconnu ({value})"
    return SYSTEM_LOG_LEVEL_LABELS.get(n, f"inconnu ({n})")


# --- RunCam over UART (CAP06/CAP07, firmware v4.2.1 CAM_CONTROL=UART builds) ---
CAM_REC_MODE_LABELS = {0: 'TOGGLE', 1: 'AUTO', 2: 'COMMANDS'}
CAM_REC_MODE_TITLE = "Comportement de la caméra à l'allumage"
CAM_REC_MODE_HELP = (
    "Doit correspondre au réglage d'enregistrement automatique du menu de la "
    "caméra. Recommandé : enregistrement automatique désactivé dans la caméra et "
    "TOGGLE ici, pour que l'heure soit réglée avant chaque fichier. Un désaccord "
    "fonctionne quand même (détecté sur la carte SD) mais coûte un appui et un "
    "petit fichier en trop à chaque session. COMMANDS : pour essais uniquement "
    "(la Split 4 ignore ces commandes)."
)
# CAP07 codes, also those of CAT05 and of CAMTST's resolution field, where 0
# means "unknown" rather than "keep the camera's own".
CAM_RESOLUTION_LABELS = {1: '1080P60', 2: '1080P50', 3: '1080P30', 4: '720P60'}
CAM_RESOLUTION_KEEP_LABEL = "ne pas toucher"
CAM_RESOLUTION_TITLE = "Résolution d'enregistrement"
CAM_RESOLUTION_HELP = (
    "720P60 enregistre ~2,6 fois plus longtemps (≈1,9 Mo/s contre ≈5 Mo/s pour "
    "les trois modes 1080p). Appliquée par un redémarrage de la caméra."
)


# Symmetric swap between KineisModulation and SmdArgosModulation (byte 9 of radioconf).
# LDK and LDA2 are swapped: Kineis LDK=0 <-> SMD 1, Kineis LDA2=1 <-> SMD 0, VLDA4=2 unchanged.
KINEIS_TO_SMD_MOD = {0: 1, 1: 0, 2: 2}
SMD_TO_KINEIS_MOD = {0: 1, 1: 0, 2: 2}


class ResetVariable(IntEnum):
    """RSTVW variable types."""
    TX_COUNTER = 1
    BOOT_COUNTER = 2  # EXTERNAL_WAKEUP builds only (RSPB); firmware permits {1,2,3,4}
    RX_COUNTER = 3
    RX_TIME = 4


class SensrMask(IntEnum):
    """Sensor bitmask for SENSR command."""
    BATTERY = 0x01
    PRESSURE = 0x02
    GNSS = 0x04
    ACCEL = 0x08
    THERMISTOR = 0x10
    SEA_TEMP = 0x20
    ALS = 0x40
    PH = 0x80
    ALL = 0xFF


class DTEError(IntEnum):
    """DTE error codes returned in $N responses."""
    OK = 0
    INCORRECT_COMMAND = 1
    NO_LENGTH_DELIMITER = 2
    NO_DATA_DELIMITER = 3
    DATA_LENGTH_MISMATCH = 4
    INCORRECT_DATA = 5
    PARAM_KEY_UNRECOGNISED = 6
    VALUE_OUT_OF_RANGE = 7
    MISSING_ARGUMENT = 8
    BAD_FORMAT = 9
    MESSAGE_TOO_LARGE = 10
    UNEXPECTED_ARGUMENT = 11
    INVALID_ACCESS_CODE = 12

    @property
    def message(self):
        messages = {
            0: "OK",
            1: "Incorrect command",
            2: "No length delimiter",
            3: "No data delimiter",
            4: "Data length mismatch",
            5: "Incorrect data",
            6: "Unrecognised parameter key",
            7: "Value out of range",
            8: "Missing argument",
            9: "Bad format",
            10: "Message too large",
            11: "Unexpected argument",
            12: "Invalid access code",
        }
        return messages.get(self.value, f"Unknown error ({self.value})")
