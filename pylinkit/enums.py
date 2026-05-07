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


# Symmetric swap between KineisModulation and SmdArgosModulation (byte 9 of radioconf).
# LDK and LDA2 are swapped: Kineis LDK=0 <-> SMD 1, Kineis LDA2=1 <-> SMD 0, VLDA4=2 unchanged.
KINEIS_TO_SMD_MOD = {0: 1, 1: 0, 2: 2}
SMD_TO_KINEIS_MOD = {0: 1, 1: 0, 2: 2}


class ResetVariable(IntEnum):
    """RSTVW variable types."""
    TX_COUNTER = 1
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
