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
    # PWP07/PWP08 (firmware 2026-10): firmware-owned, READ-ONLY (READ_ONLY_KEYS),
    # appended at the end of the firmware table. Display helpers: pylinkit/clock.py.
    # PWP07 = UTC epoch (s) of the last TRUSTED time setting (GNSS fix or $RTCW),
    # every board. 0 = never, or wiped by a non-TPL wake-up (magnet, watchdog, OTA).
    # PWP08 = TPL5111 period this board's resistor really gives, in ms, learnt
    # from GNSS fixes. RSPB only: absent from a LinkIt V4 PARMR. 0 = not measured
    # yet; the firmware resets it when WAKEUP_PERIOD (PWP04) changes.
    [ "LAST_TIME_SYNC", "PWP07", UINT ],
    [ "WAKEUP_PERIOD_MEASURED_MS", "PWP08", UINT ],
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
    # Argos modulation guard (firmware 2026-10): READ-ONLY status keys returned
    # by STATR, absent from LoRa builds. ART12 = configuration warning bitmask,
    # 0 = nothing to report (bit0 CloudLocate frame does not fit the verified
    # master modulation, bit1 master modulation not verified yet -> run SATVF,
    # bit2 master RCONF IDP14 empty, bit3 MEAS50 on an Argos build). ART13 =
    # master modulation read back (0 LDA2, 1 LDK, 2 VLDA4, 3 unknown). ART14 /
    # ART15 = fingerprints of the IDP14 read back / last resync attempt.
    [ "ARGOS_CFG_WARNINGS", "ART12", UINT ],
    [ "ARGOS_MASTER_MODULATION", "ART13", UINT ],
    [ "ARGOS_MASTER_RCONF_FP", "ART14", UINT ],
    [ "ARGOS_MASTER_SYNC_ATTEMPT_FP", "ART15", UINT ],
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
    # RunCam driven over its UART (firmware v4.2.1, CAM_CONTROL=UART builds only;
    # a BUTTON build and every firmware up to v4.2.0 have CAP01-CAP05 only).
    # CAP06 = what the camera does at power-on, must match its own auto-record
    # menu: 0 TOGGLE (default), 1 AUTO, 2 COMMANDS (bench only). CAP07 = the
    # resolution to apply: 0 keep the camera's own, 1 1080P60, 2 1080P50,
    # 3 1080P30, 4 720P60. Labels and help: pylinkit/enums.py, pylinkit/camera.py.
    [ "CAM_REC_MODE", "CAP06", UINT ],
    [ "CAM_RESOLUTION", "CAP07", UINT ],
    # READ-ONLY status keys, read with STATR. CAT00 = how the build drives the
    # camera, 1 BUTTON, 2 UART, on every camera build of firmware v4.2.1 (absent
    # before). CAT01-CAT06 = the last camera session, UART builds only: outcome
    # (CAMTST codes, 255 none yet), SD free / total MB and recording time left
    # in s (0xFFFFFFFF unread), resolution read (CAP07 codes), feature bits.
    [ "CAM_CONTROL_MODE", "CAT00", UINT ],
    [ "CAM_LAST_OUTCOME", "CAT01", UINT ],
    [ "CAM_SD_FREE_MB", "CAT02", UINT ],
    [ "CAM_SD_TOTAL_MB", "CAT03", UINT ],
    [ "CAM_REC_TIME_LEFT_S", "CAT04", UINT ],
    [ "CAM_RESOLUTION_READ", "CAT05", UINT ],
    [ "CAM_FEATURES", "CAT06", UINT ],
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
    # Flash journal (system.log) level, firmware v4.2.1 on every build: 0 OFF,
    # 1 ERROR, 2 WARN, 3 INFO (default, what every earlier firmware wrote). No
    # published firmware has it: only ever sent when PARML lists it.
    [ "SYSTEM_LOG_LEVEL", "DBP02", UINT ],
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
    # DX1 turtle Doppler extension (firmware 2026-10, replaces the never-released
    # ARP47). 0 OFF = legacy Doppler frame, 1 AUTO (default) = DX1 only on a build
    # whose ground decoder is ready, 2 FORCE = bench / pilots with a patched
    # decoder ONLY, never in a template. Inert without UW_ENABLE (UNP01).
    [ "SWS_SENSOR_ENABLE_TX_MODE", "UNP26", UINT ],
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
    # [283-287] External barometer (Vaisala PTB110 through an ADS1115), CLS
    # woodbuoy builds only (ENABLE_BARO_SENSOR): other builds do not list them.
    [ "BARO_SENSOR_ENABLE", "BAP01", BOOLEAN ],
    [ "BARO_SENSOR_PERIODIC", "BAP02", UINT ],
    [ "BARO_SENSOR_ENABLE_TX_MODE", "BAP03", SENSORTXENABLEMODE ],
    [ "BARO_SENSOR_ENABLE_TX_MAX_SAMPLES", "BAP04", UINT ],
    [ "BARO_SENSOR_ENABLE_TX_SAMPLE_PERIOD", "BAP05", UINT ],
    ]

    # Firmware-owned keys: is_writable == false in the firmware param table
    # (core/protocol/dte_params.cpp). The device refuses them in PARMW, so
    # pylinkit never sends them: parmw() drops them, and they are ignored when a
    # configuration file is imported (a --parmr export may still carry some).
    READ_ONLY_KEYS = frozenset({
        'IDT03', 'IDT04', 'IDT10',                     # firmware / hardware identity
        'ART01', 'ART02', 'ART03', 'ART10', 'ART11',   # Argos dates and counters
        'ART12', 'ART13', 'ART14', 'ART15',            # Argos modulation guard
        'POT03', 'POT06',                              # battery
        'PWP02', 'PWP06', 'PWP07', 'PWP08',            # TPL5111 / clock state
        'SYT01',                                       # live RTC
        'MTP07', 'SMP01', 'MRT01',
        'PPT01', 'PPT02', 'PPT03', 'PPT04',            # prepass / AOP status
        'CAT00', 'CAT01', 'CAT02', 'CAT03',            # camera mode, last session
        'CAT04', 'CAT05', 'CAT06',
    })

    # Read-only keys also kept out of a configuration export (--parmr file):
    # clock and last camera session of THIS board, meaningless in a template.
    # The other read-only keys stay in exports for information and are ignored
    # on import.
    EXPORT_EXCLUDED_KEYS = frozenset({
        'PWP07', 'PWP08',
        'CAT01', 'CAT02', 'CAT03', 'CAT04', 'CAT05', 'CAT06',
    })

    # Inclusive wire ranges checked before anything is sent, from the firmware
    # table (core/protocol/dte_params.cpp). Firmware before v4.2.0 did not
    # validate every value, so the tool does it whatever the version.
    VALUE_RANGES = {
        'DBP02': (0, 3),    # SYSTEM_LOG_LEVEL
        'CAP06': (0, 2),    # CAM_REC_MODE
        'CAP07': (0, 4),    # CAM_RESOLUTION
    }

    # Longest text value: beyond it, firmware before v4.2.0 went mute until
    # the next reboot (wiki 09).
    TEXT_MAX_LEN = 128

    @staticmethod
    def _find_key(p):
        """Short key for ``p`` given as a long name or a short key, else None."""
        for (param, key, cls) in DTEParamMap.param_map:
            if p == param or p == key:
                return key
        return None

    @staticmethod
    def is_read_only(p):
        """True if ``p`` (long name or short key) is firmware-owned. Unknown
        names return False: encoding them fails later, as before."""
        return DTEParamMap._find_key(p) in DTEParamMap.READ_ONLY_KEYS

    @staticmethod
    def read_only_names(param_values):
        """Names in ``param_values`` that must never be written."""
        return [p for p in param_values if DTEParamMap.is_read_only(p)]

    @staticmethod
    def writable_only(param_values):
        """Copy of ``param_values`` without the read-only parameters."""
        return {p: v for p, v in param_values.items() if not DTEParamMap.is_read_only(p)}

    @staticmethod
    def exportable(params):
        """Copy of ``params`` fit for a configuration export."""
        return {p: v for p, v in params.items()
                if DTEParamMap._find_key(p) not in DTEParamMap.EXPORT_EXCLUDED_KEYS}

    @staticmethod
    def is_status_key(key):
        """True for a status key (``..T..``), read with STATR rather than PARMR."""
        return len(key) == 5 and key[2] == 'T'

    @staticmethod
    def unsupported_names(param_values, supported_keys):
        """Names in ``param_values`` whose key the firmware does not list
        (``supported_keys``: the PARML answer). Names unknown to pylinkit are
        not reported here: encoding refuses them."""
        supported = set(supported_keys)
        out = []
        for p in param_values:
            key = DTEParamMap._find_key(p)
            if key is not None and key not in supported:
                out.append(p)
        return out

    @staticmethod
    def invalid_values(param_values):
        """``{name: reason}`` for every value the tool must refuse before
        sending: unknown name, value the codec rejects, out of range, too long."""
        out = {}
        for p, v in param_values.items():
            try:
                DTEParamMap.encode(p, v)
            except Exception as e:
                out[p] = str(e) or type(e).__name__
        return out

    @staticmethod
    def _canonical(p, v):
        """``v`` as the device would read it back: encoded, then decoded."""
        return DTEParamMap.decode(DTEParamMap.param_to_key(p), DTEParamMap.encode(p, v))

    @staticmethod
    def same_value(p, sent, read):
        """True when ``read`` (PARMR read-back) is the value ``sent`` for ``p``.
        Both sides are compared in their decoded form, floats with a tolerance
        for the firmware's float storage."""
        try:
            a = DTEParamMap._canonical(p, sent)
            b = DTEParamMap._canonical(p, read)
        except Exception:
            return str(sent) == str(read)
        if isinstance(a, float) or isinstance(b, float):
            try:
                return abs(float(a) - float(b)) <= 1e-6 + 1e-5 * abs(float(a))
            except (TypeError, ValueError):
                return False
        return a == b

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
        for (param, key, cls) in DTEParamMap.param_map:
            if p == param:
                wire = cls.encode(v)
                if key in DTEParamMap.VALUE_RANGES:
                    lo, hi = DTEParamMap.VALUE_RANGES[key]
                    if not lo <= int(wire) <= hi:
                        raise ValueError(f'{p} ({key}) value {wire} out of range [{lo}, {hi}]')
                if cls in (TEXT, UPPERCASETEXT) and len(wire) > DTEParamMap.TEXT_MAX_LEN:
                    raise ValueError(f'{p} ({key}) text of {len(wire)} characters, '
                                     f'max {DTEParamMap.TEXT_MAX_LEN}')
                return wire
        raise Exception('Param {} not found'.format(p))
