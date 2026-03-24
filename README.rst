Installation
============

python setup.py install


Transport
=========

pylinkit supporte trois modes de transport pour communiquer avec le tracker :

- **BLE** (Bluetooth Low Energy) : mode par defaut, utilise le Nordic UART Service (NUS)
- **USB** : lecture des logs en temps reel via port serie CDC (115200 baud)
- **UART** : lecture des logs en temps reel via port serie

Le transport se selectionne avec l'option ``--transport [ble|usb|uart]``.


Usage
=====

Scan & decouverte
-----------------

Pour scanner les beacons BLE :

.. code-block:: bash

    pylinkit --scan

Pour lister les ports serie disponibles :

.. code-block:: bash

    pylinkit --list-ports


Configuration
-------------

Pour lire les parametres de configuration dans un fichier :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --parmr params.txt

Pour ecrire les parametres de configuration depuis un fichier :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --parmw params.txt

Pour interroger un parametre specifique :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --poll BATT_VOLTAGE --value 1


Logs & monitoring
-----------------

Pour visualiser les logs en temps reel (BLE, USB ou UART) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --log
    pylinkit --transport usb --port COM3 --log
    pylinkit --transport uart --port COM3 --log

L'option ``--no-color`` desactive la coloration ANSI.

Pour telecharger les logs (sensor ou systeme) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --dumpd gpslog.json --dumpd_type gnss
    pylinkit --device xx:xx:xx:xx:xx:xx --dumpd syslog.json --dumpd_type system [--format csv]

Types de logs disponibles : ``system``, ``gnss``, ``als``, ``ph``, ``rtd``, ``cdt``,
``cam``, ``axl``, ``pressure``, ``thermistor``, ``tsys01``.

Pour effacer les logs :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --erase all
    pylinkit --device xx:xx:xx:xx:xx:xx --erase sensor
    pylinkit --device xx:xx:xx:xx:xx:xx --erase system


Controle du device
------------------

Pour effectuer un reset logiciel :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rstbw

Pour effectuer un reset usine (efface config, logs, paspw, zones) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --factw

Pour reinitialiser les compteurs :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw tx_counter
    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw boot_counter
    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw rx_counter
    pylinkit --device xx:xx:xx:xx:xx:xx --rstvw rx_time

Pour controler l'alimentation des modules :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --pwron all
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron gnss
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron sensors
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron satellite
    pylinkit --device xx:xx:xx:xx:xx:xx --pwron off


Batterie & capteurs
-------------------

Pour lire la batterie :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --battery

Pour lire un capteur :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --sensr battery
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr pressure
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr gnss --sensr_timeout 120
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr thermistor
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr accel
    pylinkit --device xx:xx:xx:xx:xx:xx --sensr all


GNSS
----

Pour lire les informations du module GNSS :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --gnssi

Pour verifier le statut de l'almanach AssistNow :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --gnssa

Pour envoyer un almanach AssistNow offline :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --ano almanac.bin

Pour telecharger et envoyer l'almanach depuis u-blox :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --ano-download --ano-token <ZTP_TOKEN>
    pylinkit --device xx:xx:xx:xx:xx:xx --ano-download --ano-token <ZTP_TOKEN> --ano-save almanac.bin

Pour demarrer le bridge GNSS UART (acces direct au u-blox M10, quitter avec ``+++``) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --gnssbr


Argos / Satellite
-----------------

Pour envoyer un paquet TX de test Argos (utilise la radioconf stockee sur le device) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argostx
    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosmod LDK
    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosmod LDA2 --argossize 10
    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosmod VLDA4 --argostcxo 3

Pour envoyer avec une radioconf custom (hex 32 chars, meme format que ARP51/52/53) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argostx --argosradioconf 0123456789ABCDEF0123456789ABCDEF --argossize 10

Taille max par modulation : LDK = 16 octets, LDA2 = 28 octets, VLDA4 = 28 octets.

Pour changer la modulation Kineis (met a jour RADIOCONF + KMAC sur le device) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod LDK
    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod LDA2
    pylinkit --device xx:xx:xx:xx:xx:xx --argosmod VLDA4

Pour demarrer la calibration Doppler (TX periodique jusqu'au reset) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --satdp


SMD (module satellite Kineis)
-----------------------------

Pour envoyer les credentials SMD :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smdcd --smdid <ID> --smdaddr <ADDR> --smdseckey <KEY> --smdradioconf <CONF>

Pour la mise a jour firmware SMD :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smdfw firmware.bin --smdfw_mode uart

Pour controler le DFU SMD :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu enter
    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu status
    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu version
    pylinkit --device xx:xx:xx:xx:xx:xx --smddfu exit

Pour lancer un test SPI SMD :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --smdtst


LoRa
----

Pour envoyer une transmission LoRa de test :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --loratx 10

Pour demarrer le bridge LoRa UART (acces direct aux commandes AT du RAK3172, quitter avec ``+++``) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --lorabr


Salt Water Switch (SWS)
------------------------

Pour lire le statut du SWS :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --swsst

Pour demarrer/arreter le mode test SWS (streaming temps reel avec indicateurs de surface) :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --swstst start
    pylinkit --device xx:xx:xx:xx:xx:xx --swstst stop


RTC (horloge temps reel)
-------------------------

Pour lire l'heure du device :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rtcr

Pour synchroniser l'heure avec l'UTC actuel :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rtcw

Pour definir un timestamp specifique :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --rtcw_timestamp 1678900000


Calibration capteurs
--------------------

Pour lire la calibration d'un capteur :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --scalr pressure

Pour ecrire une calibration :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --scalw pressure --command 1 --value 1.5


Mise a jour firmware (OTA)
--------------------------

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --fw firmware.img

WARNING: l'operation peut prendre 5-6 minutes. Il est conseille de ne pas
lancer cette commande si la batterie est faible et de ne pas reset le device
pendant l'operation. La mise a jour ne prend effet qu'au prochain redemarrage.


Pass prediction
---------------

Pour envoyer des predictions de passage depuis un fichier JSON :

.. code-block:: bash

    pylinkit --device xx:xx:xx:xx:xx:xx --paspw paspw.json


Options generales
-----------------

``--debug`` active les traces de debug pour toute commande.

``--no-color`` desactive la coloration ANSI dans les logs.


Logging file format
===================

Log files are downloaded as binary and transcoded to JSON or CSV (if --format csv is passed).


Example GPS
-----------

[
    {
        "batt_voltage": 4200,
        "day": 1,
        "fixType": 2,
        "fix_day": 1,
        "fix_hour": 13,
        "fix_min": 26,
        "fix_month": 3,
        "fix_sec": 31,
        "fix_year": 2021,
        "gSpeed": 4,
        "hAcc": 18700,
        "hDOP": 1.3799999952316284,
        "hMSL": 240,
        "headAcc": 180.0,
        "headMot": 0.0,
        "headVeh": 0.0,
        "height": 48232,
        "hours": 13,
        "iTOW": 134807995,
        "lat": 51.3767097,
        "log_t": "LOG_GPS",
        "lon": -2.1183726,
        "mins": 26,
        "month": 3,
        "nano": -4712236,
        "numSV": 6,
        "pDOP": 1.6799999475479126,
        "sAcc": 263,
        "secs": 31,
        "tAcc": 4294967295,
        "vAcc": 4116,
        "vDOP": 0.9599999785423279,
        "valid": 1,
        "velD": 0,
        "velE": -3,
        "velN": 1,
        "year": 2021
    },
	...
]

Example System
--------------

[
	...
    {
        "day": 1,
        "hours": 13,
        "log_t": "LOG_INFO",
        "message": "GPSScheduler::task_process_gnss_data: lon=-2.118220 lat=51.376792 height=47992",
        "mins": 42,
        "month": 3,
        "secs": 10,
        "year": 2021
    },
    {
        "day": 1,
        "hours": 13,
        "log_t": "LOG_INFO",
        "message": "GPSScheduler::schedule_aquisition in 470 seconds",
        "mins": 42,
        "month": 3,
        "secs": 10,
        "year": 2021
    },
    {
        "day": 1,
        "hours": 13,
        "log_t": "LOG_INFO",
        "message": "ArgosScheduler::next_duty_cycle: found schedule: 1614606165",
        "mins": 42,
        "month": 3,
        "secs": 10,
        "year": 2021
    },
    {
        "day": 1,
        "hours": 13,
        "log_t": "LOG_INFO",
        "message": "ArticTransceiver::send_packet: sending message total_bits=176 tail_bits=7 burst_size=24",
        "mins": 42,
        "month": 3,
        "secs": 52,
        "year": 2021
    },
    {
        "day": 1,
        "hours": 13,
        "log_t": "LOG_INFO",
        "message": "ArgosScheduler::next_duty_cycle: found schedule: 1614606210",
        "mins": 42,
        "month": 3,
        "secs": 56,
        "year": 2021
    },
    {
        "day": 1,
        "hours": 13,
        "log_t": "LOG_INFO",
        "message": "ArticTransceiver::send_packet: sending message total_bits=176 tail_bits=7 burst_size=24",
        "mins": 43,
        "month": 3,
        "secs": 38,
        "year": 2021
    },
	...
]



Configuration file format
=========================

Configuration files are organised in sections accordingly:

[PARAM]  # Optional params for --parmw command
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

A configuration should have a [PARAM] section.
