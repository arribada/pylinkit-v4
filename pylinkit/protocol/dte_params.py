from .dte_types import *     # noqa

class DTEParamMap():
    param_map = [
    [ "DEVICE_MODEL", "IDT02", TEXT ],
    [ "FW_APP_VERSION", "IDT03", TEXT ],
    [ "HW_VERSION", "IDT04", TEXT ],
    [ "LAST_TX", "ART01", DATESTRING ],
    [ "TX_COUNTER", "ART02", UINT ],
    [ "BATT_SOC", "POT03", UINT ],
    [ "BATT_VOLTAGE", "POT06", FLOAT ],
    [ "SHUTDOWN_TIMER", "PWP01", UINT ],
    [ "BOOT_COUNTER", "PWP02", UINT ],
    [ "BOOT_COUNTER_MODULO", "PWP03", UINT ],
    [ "WAKEUP_PERIOD", "PWP04", UINT ],
    [ "SHUTDOWN_NTIME_SAT", "PWP05", UINT ],
    [ "LAST_KNOWN_RTC", "PWP06", UINT ],
    [ "PROFILE_NAME", "IDP11", TEXT ],
    [ "ARGOS_DECID", "IDP12", UINT ],
    [ "ARGOS_HEXID", "IDT06", TEXT ],
    [ "ARGOS_SECKEY", "IDP13", TEXT ],
    [ "ARGOS_RADIOCONF", "IDP14", TEXT ],
    [ "ARGOS_AOP_DATE", "ART03", DATESTRING ],
    [ "ARGOS_TX_REPETITION", "ARP05", UINT ],
    [ "ARGOS_MODE", "ARP01", ARGOSMODE ],
    [ "ARGOS_NTRY_PER_MESSAGE", "ARP19", UINT ],
    [ "ARGOS_DUTY_CYCLE", "ARP18", ARGOSDUTYCYLE ],
    [ "GNSS_ENABLE", "GNP01", BOOLEAN ],
    [ "GNSS_DELTATIME_ACQ", "ARP11", AQPERIOD ],
    [ "ARGOS_DEPTH_PILE", "ARP16", DEPTHPILE ],
    [ "GNSS_HDOPFILT_ENABLE", "GNP02", BOOLEAN ],
    [ "GNSS_HDOPFILT_THR", "GNP03", UINT ],
    [ "GNSS_ACQ_TIMEOUT", "GNP05", UINT ],
    [ "GNSS_NTRY", "GNP04", UINT ],
    [ "GNSS_COLD_ACQ_TIMEOUT", "GNP09", UINT ],
    [ "GNSS_FIX_MODE", "GNP10", GNSSFIXMODE ],
    [ "GNSS_DYN_MODEL", "GNP11", GNSSDYNMODEL ],
    [ "UW_ENABLE", "UNP01", BOOLEAN ],
    [ "UW_DRY_TIME_BEFORE_TX", "UNP02", UINT ],
    [ "UW_WET_SAMPLING", "UNP03", SAMPLINGPERIOD ],
    [ "UW_DRY_SAMPLING", "UNP04", SAMPLINGPERIOD ],
    [ "UW_MAX_SAMPLES", "UNP05", UINT ],
    [ "UW_MIN_DRY_SAMPLES", "UNP06", UINT ],
    [ "UW_SAMPLE_GAP", "UNP07", UINT ],
    [ "LB_EN", "LBP01", BOOLEAN ],
    [ "LB_THRESHOLD", "LBP02", UINT ],
    [ "LB_ARGOS_TX_REPETITION", "ARP06", UINT  ],
    [ "LB_ARGOS_MODE", "LBP04", ARGOSMODE ],
    [ "LB_ARGOS_DUTY_CYCLE", "LBP05", ARGOSDUTYCYLE ],
    [ "LB_GNSS_EN", "LBP06", BOOLEAN ],
    [ "LB_GNSS_DELTATIME_ACQ", "ARP12", AQPERIOD ],
    [ "LB_GNSS_HDOPFILT_THR", "LBP07", UINT ],
    [ "LB_ARGOS_DEPTH_PILE", "LBP08", DEPTHPILE ],
    [ "LB_GNSS_ACQ_TIMEOUT", "LBP09", UINT ],
    [ "PP_MIN_ELEVATION", "PPP01", FLOAT ],
    [ "PP_MAX_ELEVATION", "PPP02", FLOAT ],
    [ "PP_MIN_DURATION", "PPP03", UINT ],
    [ "PP_MAX_PASSES", "PPP04", UINT ],
    [ "PP_LINEAR_MARGIN", "PPP05", UINT ],
    [ "PP_COMP_STEP", "PPP06", UINT ],
    [ "GNSS_HACCFILT_ENABLE", "GNP20", BOOLEAN ],
    [ "GNSS_HACCFILT_THR", "GNP21", UINT ],
    [ "GNSS_MIN_NUM_FIXES", "GNP22", UINT ],
    [ "GNSS_COLD_START_RETRY_PERIOD", "GNP23", UINT ],
    [ "ARGOS_TIME_SYNC_BURST_EN", "ARP30", BOOLEAN ],
    [ "LED_MODE", "LDP01", LEDMODE ],
    [ "ARGOS_TX_JITTER_EN", "ARP31", BOOLEAN ],
    [ "ARGOS_RX_EN", "ARP32", BOOLEAN ],
    [ "ARGOS_RX_MAX_WINDOW", "ARP33", UINT ],
    [ "ARGOS_RX_AOP_UPDATE_PERIOD", "ARP34", UINT ],
    [ "ARGOS_TCXO_WARMUP_TIME", "ARP35", UINT ],
    [ "SURFACING_BURST_INITIAL_INTERVAL", "ARP40", UINT ],
    [ "SURFACING_BURST_STEP", "ARP41", UINT ],
    [ "SURFACING_BURST_MAX_INTERVAL", "ARP42", UINT ],
    [ "SURFACING_BURST_MAX_MSG", "ARP43", UINT ],
    # BLIND Argos mode (fw 2026-07-03, config version 0x20): the satellite module
    # handles the per-burst repetitions instead of the nRF. Excluded in
    # SURFACING_BURST and DOPPLER. Firmware bounds/defaults:
    #   ARP44 BOOLEAN (default 0), ARP45 UINT 1..127 (default 4),
    #   ARP46 UINT 60..65535 s (default 60). Keep NB*PERIOD < 7200 s (see enums.py help).
    [ "ARGOS_BLIND_EN", "ARP44", BOOLEAN ],
    [ "ARGOS_BLIND_RETX_NB", "ARP45", UINT ],
    [ "ARGOS_BLIND_RETX_PERIOD_S", "ARP46", UINT ],
    [ "RX_COUNTER", "ART10", UINT ],
    [ "RX_TIME", "ART11", UINT ],
    [ "GNSS_ASSISTNOW_EN", "GNP24", BOOLEAN ],
    [ "LB_GNSS_HACCFILT_THR", "LBP10", UINT ],
    [ "LB_NTRY_PER_MESSAGE", "LBP11", UINT ],
    [ "ZONE_TYPE", "ZOP01", ZONETYPE ],
    [ "ZONE_ENABLE_OUT_OF_ZONE_DETECTION_MODE", "ZOP04", BOOLEAN ],
    [ "ZONE_ENABLE_ACTIVATION_DATE", "ZOP05", BOOLEAN ],
    [ "ZONE_ACTIVATION_DATE", "ZOP06", DATESTRING ],
    [ "ZONE_ARGOS_DEPTH_PILE", "ZOP08", DEPTHPILE ],
    [ "ZONE_ARGOS_REPETITION_SECONDS", "ZOP10", UINT ],
    [ "ZONE_ARGOS_MODE", "ZOP11", ARGOSMODE ],
    [ "ZONE_ARGOS_DUTY_CYCLE", "ZOP12", ARGOSDUTYCYLE ],
    [ "ZONE_ARGOS_NTRY_PER_MESSAGE", "ZOP13", UINT ],
    [ "ZONE_GNSS_DELTATIME_ACQ", "ZOP14", AQPERIOD ],
    [ "ZONE_GNSS_HDOPFILT_THR", "ZOP15", UINT ],
    [ "ZONE_GNSS_HACCFILT_THR", "ZOP16", UINT ],
    [ "ZONE_GNSS_ACQ_TIMEOUT", "ZOP17", UINT ],
    [ "ZONE_CENTER_LONGITUDE", "ZOP18", FLOAT ],
    [ "ZONE_CENTER_LATITUDE", "ZOP19", FLOAT ],
    [ "ZONE_RADIUS", "ZOP20", UINT ],
    [ "CERT_TX_ENABLE", "CTP01", BOOLEAN ],
    [ "CERT_TX_PAYLOAD", "CTP02", TEXT ],
    [ "CERT_TX_MODULATION", "CTP03", ARGOSMODULATION ],
    [ "CERT_TX_REPETITION", "CTP04", UINT ],
    [ "DEVICE_DECID", "IDT10", UINT ],
    [ "GNSS_TRIGGER_ON_SURFACED", "GNP25", BOOLEAN ],
    [ "GNSS_TRIGGER_ON_AXL_WAKEUP", "GNP26", BOOLEAN ],
    [ "UNDERWATER_DETECT_THRESH", "UNP11", FLOAT ],
    [ "PH_SENSOR_ENABLE", "PHP01", BOOLEAN ],
    [ "PH_SENSOR_PERIODIC", "PHP02", UINT ],
    [ "PH_SENSOR_VALUE", "PHP03", FLOAT ],
    [ "PH_SENSOR_ENABLE_TX_MODE", "PHP04", SENSORTXENABLEMODE ],
    [ "PH_SENSOR_ENABLE_TX_MAX_SAMPLES", "PHP05", UINT ],
    [ "PH_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "PHP06", UINT ],
    [ "SEA_TEMP_SENSOR_ENABLE", "STP01", BOOLEAN ],
    [ "SEA_TEMP_SENSOR_PERIODIC", "STP02", UINT ],
    [ "SEA_TEMP_SENSOR_VALUE", "STP03", FLOAT ],
    [ "SEA_TEMP_SENSOR_ENABLE_TX_MODE", "STP04", SENSORTXENABLEMODE ],
    [ "SEA_TEMP_SENSOR_ENABLE_TX_MAX_SAMPLES", "STP05", UINT ],
    [ "SEA_TEMP_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "STP06", UINT ],
    [ "ALS_SENSOR_ENABLE", "LTP01", BOOLEAN ],
    [ "ALS_SENSOR_PERIODIC", "LTP02", UINT ],
    [ "ALS_SENSOR_VALUE", "LTP03", FLOAT ],
    [ "ALS_SENSOR_ENABLE_TX_MODE", "LTP04", SENSORTXENABLEMODE ],
    [ "ALS_SENSOR_ENABLE_TX_MAX_SAMPLES", "LTP05", UINT ],
    [ "ALS_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "LTP06", UINT ],
    [ "CDT_SENSOR_ENABLE", "CDP01", BOOLEAN ],
    [ "CDT_SENSOR_PERIODIC", "CDP02", UINT ],
    [ "CDT_SENSOR_CONDUCTIVITY_VALUE", "CDP03", FLOAT ],
    [ "CDT_SENSOR_DEPTH_VALUE", "CDP04", FLOAT ],
    [ "CDT_SENSOR_TEMPERATURE_VALUE", "CDP05", FLOAT ],
    [ "CAM_ENABLE", "CAP01", BOOLEAN ],
    [ "CAM_TRIGGER_ON_SURFACED", "CAP02", BOOLEAN ],
    [ "CAM_TRIGGER_ON_AXL_WAKEUP", "CAP03", BOOLEAN ],
    [ "CAM_PERIOD_ON", "CAP04", UINT ],
    [ "CAM_PERIOD_OFF", "CAP05", UINT ],
    [ "LB_CAM_EN", "LBP13", BOOLEAN ],
    # LDP02 EXT_LED_MODE removed: firmware slot 117 is _RESERVED_117 (EXT_LED_PIN
    # is not wired on LinkIt V4 / RSPB); PARMR/PARMW on LDP02 are rejected.
    [ "LED_HRS24_RTC_CUTOFF", "LDP03", DATESTRING ],
    [ "AXL_SENSOR_ENABLE", "AXP01", BOOLEAN ],
    [ "AXL_SENSOR_PERIODIC", "AXP02", UINT ],
    [ "AXL_SENSOR_WAKEUP_THRESH", "AXP03", FLOAT ],
    [ "AXL_SENSOR_WAKEUP_SAMPLES", "AXP04", UINT ],
    [ "AXL_SENSOR_ENABLE_TX_MODE", "AXP05", SENSORTXENABLEMODE ],
    [ "AXL_SENSOR_ENABLE_TX_MAX_SAMPLES", "AXP06", UINT ],
    [ "AXL_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "AXP07", UINT ],
    [ "AXL_SENSOR_MEASUREMENT_RANGE", "AXP08", ACCRANGE ],
    # AXP09 is a raw UINT 0..2 on the wire; the previous AXLPOWERMODE label
    # ordering (['NORMAL','LOWPOWER','AUTOLOWPOWER']) contradicted the firmware
    # meaning (0=Low Power, 1=Normal, 2=Sleep) and swapped 0/1. Use plain UINT
    # until the exact BMA400 mode mapping is confirmed in the accel driver.
    [ "AXL_SENSOR_POWER_MODE", "AXP09", UINT ],
    [ "AXL_FIFO_ENABLE", "AXP10", BOOLEAN ],
    [ "AXL_FIFO_SAMPLE_COUNT", "AXP11", UINT ],
    [ "THERMISTOR_SENSOR_ENABLE", "THP01", BOOLEAN ],
    [ "THERMISTOR_SENSOR_PERIODIC", "THP02", UINT ],
    [ "THERMISTOR_SENSOR_VALUE", "THP03", FLOAT ],
    [ "THERMISTOR_SENSOR_WAKEUP_THRESH", "THP04", FLOAT ],
    [ "THERMISTOR_SENSOR_WAKEUP_SAMPLES", "THP05", UINT ],
    [ "THERMISTOR_SENSOR_ENABLE_TX_MODE", "THP06", SENSORTXENABLEMODE ],
    [ "THERMISTOR_SENSOR_ENABLE_TX_MAX_SAMPLES", "THP07", UINT ],
    [ "THERMISTOR_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "THP08", UINT ],
    [ "PRESSURE_SENSOR_ENABLE", "PRP01", BOOLEAN ],
    [ "PRESSURE_SENSOR_PERIODIC", "PRP02", UINT ],
    [ "PRESSURE_SENSOR_LOGGING_MODE", "PRP03", PRESSURESENSORLOGGINGMODE ],
    [ "PRESSURE_SENSOR_ENABLE_TX_MODE", "PRP04", SENSORTXENABLEMODE ],
    [ "PRESSURE_SENSOR_ENABLE_TX_MAX_SAMPLES", "PRP05", UINT ],
    [ "PRESSURE_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "PRP06", UINT ],
    [ "PRESSURE_SENSOR_FULL_SCALE", "PRP07", PRESSUREFULLSCALE ],
    [ "DEBUG_OUTPUT_MODE", "DBP01", DEBUGMODE ],
    [ "GNSS_ASSISTNOW_OFFLINE_EN", "GNP27", BOOLEAN ],
    [ "GNSS_TRIGGER_COLD_START_ON_SURFACED", "GNP28", BOOLEAN ],
    [ "GNSS_SESSION_SINGLE_FIX", "GNP30", BOOLEAN ],
    [ "UW_PIN_SAMPLE_DELAY_US", "UNP08", PINSAMPLEDELAYUS ],
    [ "SWS_DELAY_MIN", "UNP09", UINT ],
    [ "SWS_DELAY_MAX", "UNP10", UINT ],
    [ "UW_DIVE_MODE_ENABLE", "UNP12", BOOLEAN ],
    [ "UW_DIVE_MODE_START_TIME", "UNP13", UINT ],
    [ "SWS_ANALOG_HYSTERESIS", "UNP22", UINT ],
    [ "SWS_ANALOG_CALIB_INTERVAL", "UNP23", UINT ],
    [ "UW_MAX_DIVE_TIME", "UNP24", UINT ],
    [ "UW_MIN_SURFACE_TIME", "UNP25", UINT ],
    [ "MIN_SURFACE_CYCLE_INTERVAL", "UNP20", UINT ],
    [ "LB_CRITICAL_THRESH", "LBP12", UINT ],
    [ "LB_SHUTDOWN_NTIME_SAT", "LBP14", UINT ],
    [ "GNSS_TOKEN", "GNP31", TEXT ],
    [ "GNSS_CONSTELLATION_MASK", "GNP40", UINT ],
    [ "GNSS_ORBIT_MAX_ERROR", "GNP41", UINT ],
    [ "GNSS_MIN_CNO", "GNP42", UINT ],
    [ "GNSS_MIN_ELEVATION", "GNP43", UINT ],
    [ "GNSS_ANO_STALE_DAYS", "GNP44", UINT ],
    [ "GNSS_FASTLOC_MODE", "GNP45", UINT ],
    [ "GNSS_CLOUDLOCATE_FORMAT", "GNP46", UINT ],
    # GNP47/GNP48/GNP49 (BACKUP_CELL_CHARGE_*) removed: firmware reserved slots
    # 223/224/225 and rejects these keys. Superseded by GNSS_DEEP_IDLE_AFTER_OFF_S
    # (GNP52) below. The GNSSBCKP *command* still exists and is kept in dte_commands.
    [ "GNSS_REUSE_FIX_MAX_AGE_S", "GNP50", UINT ],
    [ "RTC_CURRENT_TIME", "SYT01", UINT ],
    [ "LORA_DEVEUI", "LRP01", UPPERCASETEXT ],
    [ "LORA_APPEUI", "LRP02", UPPERCASETEXT ],
    [ "LORA_APPKEY", "LRP03", UPPERCASETEXT ],
    [ "LORA_DEVADDR", "LRP04", UPPERCASETEXT ],
    [ "LORA_APPSKEY", "LRP05", UPPERCASETEXT ],
    [ "LORA_NWKSKEY", "LRP06", UPPERCASETEXT ],
    [ "LORA_NJM", "LRP07", BOOLEAN ],
    [ "LORA_BAND", "LRP08", UINT ],
    [ "LORA_CLASS", "LRP09", UINT ],
    [ "LORA_DR", "LRP10", UINT ],
    [ "LORA_ADR", "LRP11", BOOLEAN ],
    [ "LORA_TXP", "LRP12", UINT ],
    [ "LORA_CFM", "LRP13", BOOLEAN ],
    [ "LORA_FPORT", "LRP14", UINT ],
    [ "LORA_LP_MODE", "LRP15", UINT ],
    [ "RSPB_PACKET_FORMAT", "RSP01", RSPBPACKETFORMAT ],
    [ "ARGOS_RADIOCONF_LDK", "ARP51", UPPERCASETEXT ],
    [ "ARGOS_RADIOCONF_LDA2", "ARP52", UPPERCASETEXT ],
    [ "ARGOS_RADIOCONF_VLDA4", "ARP53", UPPERCASETEXT ],
    [ "ARGOS_ADAPTIVE_MODULATION", "ARP54", BOOLEAN ],
    [ "MORTALITY_EN", "MTP01", BOOLEAN ],
    [ "MORTALITY_ACTIVITY_THR", "MTP02", UINT ],
    [ "MORTALITY_TEMP_THR", "MTP03", FLOAT ],
    [ "MORTALITY_GPS_DIST_THR", "MTP04", UINT ],
    [ "MORTALITY_CONFIRM_DAYS", "MTP05", UINT ],
    [ "MORTALITY_DUTY_CYCLE_MODULO", "MTP06", UINT ],
    [ "MORTALITY_ORIGINAL_MODULO", "MTP07", UINT ],
    [ "COOLDOWN_TRIGGER_MODE", "UNP30", UINT ],
    [ "HAULED_DETECT_EN", "HMP00", BOOLEAN ],
    [ "HAULED_IDLE_THRESHOLD_H", "HMP01", UINT ],
    [ "HAULED_RETURN_EVENTS", "HMP02", UINT ],
    [ "HAULED_ARGOS_MODE", "HMP10", ARGOSMODE ],
    [ "HAULED_TR_NOM", "HMP11", UINT ],
    [ "HAULED_GNSS_EN", "HMP12", BOOLEAN ],
    [ "HAULED_GNSS_STRAT", "HMP13", HAULEDGNSSSTRAT ],
    [ "RATE_LIMIT_EN", "RLP01", BOOLEAN ],
    [ "RATE_LIMIT_WINDOW_S", "RLP02", UINT ],
    [ "RATE_LIMIT_MAX_TX", "RLP03", UINT ],
    [ "SMD_LPM_MODE", "ARP60", UINT ],
    [ "SMD_DEGRADED_MODE", "SMP00", UINT ],
    [ "ARGOS_CACHED_MODULATION", "SMP01", UINT ],
    # --- 2026-06 firmware sync: params not already present on main ---
    # NB: HAULED_*, RATE_LIMIT_*, SMD_*, UW_* and GNSS_FASTLOC_MODE/CLOUDLOCATE_FORMAT/
    # REUSE_FIX_MAX_AGE_S were added independently on main, so they are intentionally
    # NOT re-added here (re-adding would create duplicate keys).
    # NOTE (2026-07 firmware): ARP36 ARGOS_TX_NO_FIX_POLICY and ARP37
    # ARGOS_LAST_KNOWN_MAX_AGE_S were REMOVED — slots 223/224 are now reserved and
    # PARMW rejects them. The "no-fix TX policy" (NO_TX/LAST_KNOWN/EMPTY_POS) concept
    # no longer exists. Do NOT re-add these keys.
    # GNSS cloudlocate / deep-idle / cold-start
    [ "GNSS_CLOUDLOCATE_ALWAYS", "GNP51", BOOLEAN ],
    [ "GNSS_DEEP_IDLE_AFTER_OFF_S", "GNP52", UINT ],
    [ "GNSS_CLOUDLOCATE_ONLY", "GNP53", BOOLEAN ],
    [ "GNSS_COLD_START_AFTER_NTRY", "GNP54", UINT ],
    # Prepass / AOP (firmware 2026-08). Le gating prepass est devenu orthogonal
    # a ARGOS_MODE: PPP07 l'active sur n'importe quel mode, et ARGOS_MODE=
    # PASS_PREDICTION reste equivalent par compatibilite. Quand les AOP sont
    # inexploitables (absents, RTC non reglee, bulletin non date, ou plus vieux
    # que PPP08) la balise retombe en emission periodique au lieu de rester
    # muette. PPT01-PPT04 sont en LECTURE SEULE, lus via STATR.
    [ "SAT_PREPASS_EN", "PPP07", BOOLEAN ],
    [ "SAT_AOP_MAX_AGE_DAYS", "PPP08", UINT ],
    [ "SAT_PREPASS_MAX_WAIT_S", "PPP09", UINT ],
    # PREPASS v4.0 filters (firmware 2026-08). Culmination = the highest
    # elevation a pass reaches at its middle. PPP10 gates the TX path, PPP11 the
    # AOP-downlink RX window (default 20), PPP12 widens the visibility circle by
    # the beacon position uncertainty. All UINT: PPP10/PPP11 in degrees (0-90),
    # PPP12 in km (0-100).
    [ "PP_MIN_CULMINATION", "PPP10", UINT ],
    [ "PP_RX_MIN_CULMINATION", "PPP11", UINT ],
    [ "PP_POSITION_MARGIN_KM", "PPP12", UINT ],
    [ "SAT_AOP_VALID", "PPT01", BOOLEAN ],
    [ "SAT_AOP_AGE_S", "PPT02", UINT ],
    [ "SAT_NEXT_PASS_TS", "PPT03", UINT ],
    [ "SAT_LAST_PASS_TS", "PPT04", UINT ],
    # Mode "a quai" / en route (firmware 2026-08, traceur bateau Cyprus).
    # Le classifieur MooredModeService bascule en MOORED apres MRP02 points GNSS
    # consecutifs a moins de MRP01 metres d'une ancre de reference FIXE, et en
    # ressort des qu'un point sort du rayon, que gSpeed depasse 1 m/s, ou apres
    # MRP03 reveils accelerometre (anti-rebond MRP04). En MOORED, MRP05 remplace
    # GNSS_DELTATIME_ACQ (ARP11) et MRP06 remplace ARGOS_TX_REPETITION (ARP05).
    # Priorite: LOW_BATTERY > HAULED > MOORED > OUT_OF_ZONE > NORMAL.
    # Desactive par defaut (MRP00=0) : aucun impact sur les autres deploiements.
    # MRT01 est en LECTURE SEULE, lu via STATR.
    [ "MOORED_DETECT_EN", "MRP00", BOOLEAN ],
    [ "MOORED_RADIUS_M", "MRP01", UINT ],
    [ "MOORED_ENTER_FIXES", "MRP02", UINT ],
    [ "MOORED_EXIT_EVENTS", "MRP03", UINT ],
    [ "MOORED_AXL_HOLDOFF_S", "MRP04", UINT ],
    [ "MOORED_DLOC", "MRP05", AQPERIOD ],
    [ "MOORED_TR_NOM", "MRP06", UINT ],
    [ "MOORED_GNSS_EN", "MRP07", BOOLEAN ],
    [ "MOORED_TX_LAST_POS", "MRP08", BOOLEAN ],
    [ "MOORED_STATE", "MRT01", UINT ],
    ]

    @staticmethod
    def param_to_key(p):
        for (param, key, cls) in DTEParamMap.param_map:
            if p == param:
                return key
        raise Exception('Param {} not found'.format(p))

    @staticmethod
    def key_to_param(k):
        for (param, key, cls) in DTEParamMap.param_map:
            if k == key:
                return param
        raise Exception('Key {} not found'.format(k))

    @staticmethod
    def decode(k, v):
        for (_, key, cls) in DTEParamMap.param_map:
            if k == key:
                return cls.decode(v)
        raise Exception('Key {} not found'.format(k))

    @staticmethod
    def encode(p, v):
        for (param, _, cls) in DTEParamMap.param_map:
            if p == param:
                return cls.encode(v)
        raise Exception('Param {} not found'.format(p))
