pylinkit
========

Python configuration and diagnostic tool for the Linkit V4 tracker
family (Linkit, Horizon, RSPB).

pylinkit talks to the device using the DTE command protocol over BLE
(Nordic UART Service), USB CDC or a raw UART link. It provides a CLI
front-end (``pylinkit``) and a Python API (``pylinkit.Scanner``,
``pylinkit.Tracker``).


Installation
============

.. code-block:: bash

    pip install .

For development install:

.. code-block:: bash

    pip install -e .

Requires Python ``>= 3.8``. Runtime dependencies (installed
automatically): ``bleak``, ``pyserial``, ``requests``.


Transport
=========

pylinkit supports three transports:

- **BLE** (default): Bluetooth Low Energy via the Nordic UART Service.
  Required for OTA firmware updates.
- **USB**: USB-CDC virtual serial (115200 baud by default). Bidirectional
  DTE + log streaming. OTA over USB is also supported.
- **UART**: raw serial link. Read-only by default (log streaming only,
  no commands).

The transport is selected with ``--transport [ble|usb|uart]``. For
serial transports, ``--port`` selects the port, and ``--baudrate``
overrides the default 115200.


CLI usage
=========

Discovery
---------

Scan for BLE devices (filters on names containing ``Linkit``, ``Horizon``
or ``RSPB``):

.. code-block:: bash

    pylinkit --scan

List available serial ports (USB/UART):

.. code-block:: bash

    pylinkit --list-ports


Configuration parameters
------------------------

Read all parameters into an INI file:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --parmr params.cfg

Write parameters from an INI file:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --parmw params.cfg

Poll a single parameter ``N`` times:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --poll BATT_VOLTAGE --value 5

Configuration file format::

    [PARAM]
    PROFILE_NAME = LIAM
    ARGOS_FREQ = 401.6599
    ARGOS_POWER = 500
    TR_NOM = 120
    ARGOS_MODE = DUTY_CYCLE
    NTRY_PER_MESSAGE = 1000
    DUTY_CYCLE = 16777215
    GNSS_EN = 1
    DLOC_ARG_NOM = 10
    ARGOS_DEPTH_PILE = 1
    GNSS_ACQ_TIMEOUT = 60
    ARGOS_HEXID = 4E7B54C

The file must have a ``[PARAM]`` section. Timestamp parameters
(``LAST_KNOWN_RTC``, ``RTC_CURRENT_TIME``) are exported in
``DD/MM/YYYY HH:MM:SS`` UTC format.


Logs and monitoring
-------------------

Live log viewer (works over BLE, USB or UART):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --log
    pylinkit --transport usb  --port COM3 --log
    pylinkit --transport uart --port COM3 --log

``--no-color`` disables ANSI colors. The log viewer parses
``DD/MM/YYYY HH:MM:SS [LEVEL] message`` and color-codes each level.

Download a log file. Output is **raw binary** as received from the
device (use the Python API to decode it into JSON or CSV):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --dumpd gpslog.bin --dumpd_type gnss
    pylinkit --device xx:xx:xx:xx:xx:xx --dumpd syslog.bin --dumpd_type system

Available ``--dumpd_type`` values: ``system``, ``gnss``, ``als``, ``ph``,
``rtd``, ``cdt``, ``cam``, ``axl``, ``pressure``, ``thermistor``,
``tsys01``, ``sws``, ``mortality``.

Erase logs:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --erase all
    pylinkit --device xx:xx:xx:xx:xx:xx --erase sensor
    pylinkit --device xx:xx:xx:xx:xx:xx --erase system

``--erase`` accepts the same set of types as ``--dumpd_type``, plus
the aliases ``all``, ``sensor`` (= ``gnss``) and ``system``.


Device control
--------------

Soft reset:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rstbw

Factory reset (erases configuration, logs, paspw and zones):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --factw

Reset counters:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw tx_counter
    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw boot_counter
    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw rx_counter
    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw rx_time

Power control of internal modules:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --pwron all
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron gnss
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron sensors
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron satellite
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron off


Battery and sensors
-------------------

Read battery (voltage, SoC, low/critical thresholds):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --battery

Read sensors:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --sensr battery
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr pressure
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr gnss --sensr_timeout 120
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr thermistor
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr accel
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr all

Available ``--sensr`` channels: ``all``, ``battery``, ``pressure``,
``gnss``, ``accel``, ``thermistor``, ``sea_temp``, ``als``, ``ph``.


GNSS
----

Read u-blox module info (powers GNSS on, reads, leaves on so chain calls
stay fast):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --gnssi

Check the AssistNow almanac status stored on device:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --gnssa

Send a pre-downloaded AssistNow Offline almanac:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --ano almanac.bin

Download AssistNow Offline from u-blox and push to device. Validity
period in weeks: 1 to 5 (default 5).

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --ano-download --ano-token <ZTP_TOKEN>
    pylinkit --device xx:xx:xx:xx:xx:xx --ano-download --ano-token <ZTP_TOKEN> --ano-period 3 --ano-save almanac.bin

The download flow is:

1. Try the chipcode stored on the device (``GNSS_TOKEN``).
2. Try a chipcode from the local cache (``~/.pylinkit/assistnow_cache.json``).
3. Otherwise register via u-blox ZTP and store the new chipcode.
4. Fall back to the unauthenticated AssistNow Offline endpoint on 403.

Open a passthrough UART bridge to the u-blox M10 (use Tera Term or
u-center on the released port; type ``+++`` to exit):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --gnssbr


Argos / Satellite
-----------------

Send a test Argos packet using the radio configuration stored on the
device:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argostx
    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosmod LDK
    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosmod LDA2 --argossize 10
    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosmod VLDA4 --argostcxo 3

Send with a custom radioconf (32 hex chars, same format as ARP51/52/53):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosradioconf 0123456789ABCDEF0123456789ABCDEF --argossize 10

Maximum payload size per modulation: ``LDK = 16``, ``LDA2 = 28``,
``VLDA4 = 28``.

Switch the active Kineis modulation. This persists the default
RADIOCONF (IDP14) for the chosen modulation onto the SMD module:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod LDK
    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod LDA2
    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod VLDA4

Persist a *custom* RADIOCONF when switching modulation (overrides the
built-in default):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod LDA2 --argosradioconf 0123456789ABCDEF0123456789ABCDEF

Start a Doppler calibration (periodic TX until reset):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --satdp


SMD (Kineis satellite module)
-----------------------------

Provision Argos credentials. The values are written to the local
configuration store via ``--parmw``, then ``--satvf 1`` pushes them
into the SMD hardware after verification:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --parmw ARGOS_DECID=<ID>,ARGOS_HEXID=<ADDR>,ARGOS_SECKEY=<KEY>,ARGOS_RADIOCONF=<CONF>
    pylinkit --device xx:xx:xx:xx:xx:xx --satvf 1

Read-only verification of the credentials (config store vs hardware):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --satvf 0

SMD firmware update:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smdfw firmware.bin --smdfw_mode uart
    pylinkit --device xx:xx:xx:xx:xx:xx --smdfw firmware.bin --smdfw_mode spi

SMD DFU control:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu enter
    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu status
    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu version
    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu exit

Run a SMD SPI test (14 A+ commands):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smdtst

Open a passthrough bridge to the KIM2 AT command interface
(type ``+++<CR><LF>`` to exit):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --kimbr


LoRa
----

Send a LoRa test transmission (payload size 1 to 222 bytes, depending
on data rate):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --loratx 10

Open a passthrough UART bridge to the RAK3172 AT command interface
(type ``+++`` to exit):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --lorabr


Salt Water Switch (SWS)
-----------------------

Read the current SWS status:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --swsst

Stream live SWS samples with surface-level indicators (Ctrl+C to stop):

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --swstst start
    pylinkit --device xx:xx:xx:xx:xx:xx --swstst stop

Run a guided air/water calibration:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --swscal start
    pylinkit --device xx:xx:xx:xx:xx:xx --swscal cancel


RTC (real-time clock)
---------------------

Read the device clock:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rtcr

Set the device clock to the current host UTC:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rtcw

Set the device clock to a specific Unix timestamp:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rtcw_timestamp 1678900000


Sensor calibration
------------------

Read calibration:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --scalr pressure --command 0

Write calibration:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --scalw pressure --command 0 --value 1013.25

Run ``--scalw <sensor>`` or ``--scalr <sensor>`` without ``--command``
to print the per-sensor command reference (axl, pressure, ph, rtd, cdt,
thermistor, sws).


Firmware update (OTA)
---------------------

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --fw firmware.img

Notes:

- The transfer typically takes 5 to 6 minutes over BLE.
- Do **not** start the OTA on a low battery and do **not** reset the
  device during the transfer.
- The new firmware is applied at the next reboot.
- Both ``.img`` (raw) and ``.zip`` (Nordic DFU package) are accepted.


Pass prediction
---------------

Push pass predictions from a JSON file:

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --paspw paspw.json


Argos / CLS payload decoder
---------------------------

Decode a satellite payload received from CLS / Argos. This command runs
**offline** — no device connection required.

.. code-block:: bash

    pylinkit --cls-decode 7b1e3eddc409c40292c87dbb8813880fb771027100000041 \
             --cls-decode-type long

Auto-detection rules (when ``--cls-decode-type`` is left as ``auto``):

- 3-byte payload  -> VLDA4: ``rspb_doppler`` if header ``0b110``, else ``doppler``
- 12-byte payload -> LDK ``short`` packet (header ``0b000``)
- 16-byte payload -> LDK: ``rspb_short`` (header ``0b101``) or ``cloudlocate``
  MEASC12 (header ``0b111``)
- 24-byte payload -> LDA2: CRC8 verified, then dispatched on header to
  ``long`` (``0b000``), ``sensor`` (``0b001``), ``fastloc`` (``0b010``),
  ``rspb_long`` (``0b100``), ``cloudlocate`` MEAS20 (``0b111``).

Short and Long packets share header ``0b000``; the 12-byte vs 24-byte size
disambiguates them. Auto-detect on a 24-byte LDA2 frame is now fully
deterministic — no need to pass ``--cls-decode-type`` unless you want to
override.

Sensor Packet (Type 1) is **self-describing** since this firmware version:
the embedded 5-bit ``sensor_mask`` (bits 78..82, MSB-first
``ALS|PH|Pressure|SeaTemp|AXL``) tells the decoder which fields are
present. No external sensor list is needed.

The decoder reports the parsed mask under ``sensor_mask`` (raw int) and
``sensor_mask_bits`` (named booleans), and decodes the corresponding
fields in the order ALS → PH → Pressure → SeaTemp → AXL.

AXL handling has two deterministic rules:

- ``axl_temp_c`` is included only when no other temperature source is in
  the packet (``not (has_pressure or has_seatemp)``).
- ``axl_activity`` may be truncated when the bit budget after XYZ is
  < 8 bits. The decoder reports the actual width under
  ``axl_activity_resolution_bits``; the value is left-aligned (high-bit
  padded with zeros), so a 6-bit reading produces an 8-bit value with
  step 4 (0..252) instead of step 1 (0..255).

CloudLocate payloads are **not** decoded — the raw 12-byte (MEASC12) or
20-byte (MEAS20) u-blox blob is returned as a hex string under
``ublox_payload_hex``, ready to be sent to the u-blox CloudLocate
service for position resolution.

LDA2 frame format
~~~~~~~~~~~~~~~~~

Every LDA2 frame embeds a CRC8 in byte 23. The SMD/KIM2 module does
**not** add an over-the-air CRC for LDA2 (unlike LDK and VLDA4).
Affected message types: ``long``, ``sensor``, ``fastloc``,
``rspb_long``, ``cloudlocate`` MEAS20.

Polynomial ``0x8380`` (= ``0x1070 << 3``), init = 0, MSB-first,
computed over bytes 0 to 22. The decoder reports ``crc_valid`` for
every LDA2 frame; ``False`` means the frame is corrupted and the
decoded fields should not be trusted.

Note on the long packet: ``ARGOS_DEPTH_PILE > 3`` produces multiple
long packets to drain the FIFO (max 3 fixes per packet). When only a
single fix sits in the trailing slot, the firmware downgrades it to a
96-bit short packet on LDK.

Python API:

.. code-block:: python

    from pylinkit.argos import decode, lda2_crc8, verify_lda2

    result = decode(hex_or_bytes, msg_type='auto', sensor_mask={'als': True})
    # result is a dict with message_type, modulation, decoded fields,
    # and crc_valid (LDA2 only).


Common options
--------------

- ``--debug`` enables debug-level logging
- ``--no-color`` disables ANSI colors in the log viewer
- ``--timeout SECONDS`` overrides the default 5 s connection timeout
- ``--version`` prints the installed pylinkit version


Python API
==========

.. code-block:: python

    from pylinkit import Scanner, Tracker, TransportType

    # BLE scan
    for d in Scanner().scan():
        print(d.address, d.name)

    # Connect over BLE
    dev = Tracker('xx:xx:xx:xx:xx:xx')
    dev.sync()
    print(dev.get('BATT_VOLTAGE'))
    dev.set({'GNSS_ACQ_TIMEOUT': 60})
    dev.disconnect()

    # Connect over USB CDC
    dev = Tracker('COM3', transport_type=TransportType.USB, baudrate=115200)
    print(dev.battery())
    dev.disconnect()

The ``Tracker`` class exposes a method per DTE command (``parmr``,
``parmw``, ``dumpd``, ``erase``, ``rtcw``, ``argostx``, ``loratx``,
``sensr``, ``swsst``, ``smddfu``, ``smdtst``, ``swscal``,
``swstst_stream``, ``firmware_update``, ``smd_firmware_update``,
``download_almanac``, ...). See ``pylinkit/__init__.py`` for the full
surface.


Log file decoding
=================

``pylinkit --dumpd ... --dumpd_type ...`` writes the raw binary stream
returned by the firmware. Use the Python API to decode it.

GPS / system / generic logs:

.. code-block:: python

    from pylinkit.protocol.dte_types import LOGFILE
    raw = open('gpslog.bin', 'rb').read()
    records = LOGFILE.decode(raw)
    for r in records:
        print(r)

Pressure logs (CSV transcoded by firmware):

.. code-block:: python

    csv_text = dev.pressure_log_to_csv()

Mortality logs (binary records):

.. code-block:: python

    csv_text = dev.mortality_log_to_csv()

Salt-water-switch logs (CSV transcoded by firmware):

.. code-block:: python

    csv_text = dev.sws_log_to_csv()

Sample GPS record::

    {
      "log_t": "LOG_GPS",
      "year": 2021, "month": 3, "day": 1,
      "hours": 13, "mins": 26, "secs": 31,
      "lat": 51.3767097, "lon": -2.1183726,
      "hMSL": 240, "hAcc": 18700,
      "numSV": 6, "fixType": 2,
      "valid": 1, "iTOW": 134807995,
      "batt_voltage": 4200,
      ...
    }


License
=======

pylinkit is distributed under the terms of the GNU General Public
License v3.0 or later. See ``LICENSE`` for the full text.
