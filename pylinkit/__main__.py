import logging
import argparse
import sys
import pylinkit
import pkg_resources
from .utils import OrderedRawConfigParser, extract_firmware_file_from_dfu, create_wrapped_file_with_crc32, create_smd_wrapped_file, stm32_crc32

erase_options = ['sensor', 'system', 'all', 'als', 'ph', 'rtd', 'cdt', 'cam', 'axl', 'pressure', 'thermistor', 'tsys01']
dumpd_options = ['system', 'gnss', 'als', 'ph', 'rtd', 'cdt', 'cam', 'axl', 'pressure', 'thermistor', 'tsys01']
scalw_options = ['cdt', 'axl', 'ph', 'rtd', 'mcp47x6', 'thermistor']
scalr_options = ['cdt', 'axl', 'thermistor']
resetv_options = {'tx_counter': 1, 'rx_counter': 3, 'rx_time': 4}
modulation_options = {'A2':0, 'A3': 1, 'A4': 2, 'VLDA4': 3, 'LDK':4, 'LDA2':5, 'LDA2L':6}
pwr_options = ['all', 'gnss', 'sensors', 'satellite', 'off']


parser = argparse.ArgumentParser()
parser.add_argument('--fw', type=argparse.FileType('rb'), required=False, help='Firmware filename for FW OTA update')
parser.add_argument('--timeout', type=float, required=False, default=None, help='BLE communications timeout')
parser.add_argument('--erase', type=str, choices=erase_options, required=False, help='Erase log file')
parser.add_argument('--device', type=str, required=False, help='xx:xx:xx:xx:xx:xx BLE device address')
parser.add_argument('--parmr', type=argparse.FileType('w'), required=False, help='Filename to write [PARAM] configuration to')
parser.add_argument('--poll', type=str, required=False, help='Poll a parameter value by key and use --value to denote repetitions')
parser.add_argument('--rstvw', type=str, choices=resetv_options.keys(), required=False, help='Reset variable: tx_counter or rx_counter')
parser.add_argument('--rstbw', action='store_true', required=False, help='Reset beacon')
parser.add_argument('--factw', action='store_true', required=False, help='Factory reset (WARNING: erases all stored logs and configuration!)')
parser.add_argument('--parmw', type=argparse.FileType('r'), required=False, help='Filename to read [PARAM] configuration from')
parser.add_argument('--paspw', type=argparse.FileType('r'), required=False, help='Filename (JSON) to read pass predict configuration from')
parser.add_argument('--scan', action='store_true', required=False, help='Scan for beacons')
parser.add_argument('--debug', action='store_true', required=False, help='Turn on debug trace')
parser.add_argument('--dump_sensor', type=argparse.FileType('wb'), required=False, help='Dump sensor log file')
parser.add_argument('--dump_system', type=argparse.FileType('wb'), required=False, help='Dump system log file')
parser.add_argument('--dumpd', type=argparse.FileType('wb'), required=False, help='Dump the specified log file')
parser.add_argument('--dumpd_type', type=str, choices=dumpd_options, required=False, help='Specified log file')
parser.add_argument('--gui', action='store_true', required=False, help='Launch in GUI mode')
parser.add_argument('--argostx', action='store_true', required=False, help='Send argos TX packet')
parser.add_argument('--argosmod', type=str, default='A2', required=False, help='Argos/Kineis modulation (A2, A3)')
parser.add_argument('--argosfreq', type=float, default=401.65, required=False, help='Argos frequency in MHz')
parser.add_argument('--argossize', type=int, default=15, required=False, help='Packet size in bytes')
parser.add_argument('--argostcxo', type=int, default=5, required=False, help='TCXO warm-up in seconds')
parser.add_argument('--argospower', type=int, default=350, required=False, help='TX power in mW')
parser.add_argument('--smdcd', action='store_true', required=False, help='Send Credentials informations to SMD flash memory (ID, ADDR, and Secret Key, radio conf)')
parser.add_argument('--smdid', type=str, default='', required=False, help='Write Decimal ID to SMD flash Decimal and internal conf')
parser.add_argument('--smdaddr', type=str, default='', required=False, help='Write hexadecimal adress to SMD flash and internal conf')
parser.add_argument('--smdseckey', type=str, default='', required=False, help='Write Secret key to SMD flash and internal conf')
parser.add_argument('--smdradioconf', type=str, default='', required=False, help='Write radio configuration to SMD flash and internal conf')
parser.add_argument('--scalw', type=str, choices=scalw_options, required=False, help='Run a calibration write command')
parser.add_argument('--scalr', type=str, choices=scalr_options, required=False, help='Run a calibration read command')
parser.add_argument('--command', type=int, required=False, help='Calibration command number')
parser.add_argument('--value', type=float, default=0, required=False, help='Calibration command value')
parser.add_argument('--ano', type=argparse.FileType('rb'), required=False, help='GNSS AssistNow Offline filename')
parser.add_argument('--version', action='store_true', required=False, help='Show the version number and exit')
parser.add_argument('--pwron', type=str, choices=pwr_options, required=False, help='Power on the device (GNSS, SENSORS, SATELLITE)')
parser.add_argument('--ble-trace', action='store_true', required=False, help='Read BLE trace output from RSPB board')
parser.add_argument('--smdfw', type=argparse.FileType('rb'), required=False, help='SMD module firmware binary for DFU update')
parser.add_argument('--smdfw_mode', type=str, choices=['uart', 'spi'], default='uart', required=False, help='SMD DFU transport mode: uart or spi (default: uart)')
args = parser.parse_args()


def setup_logging(enabled, level):
    if enabled:
        logging.basicConfig(format='%(asctime)s\t%(module)s\t%(levelname)s\t%(message)s', level=logging.ERROR)
        if level == 'error':
            logging.getLogger().setLevel(logging.ERROR)
        elif level == 'warn':
            logging.getLogger().setLevel(logging.WARN)
        elif level == 'info':
            logging.getLogger().setLevel(logging.INFO)
        elif level == 'debug':
            logging.getLogger().setLevel(logging.DEBUG)


def gui_main():
    from .gui import run
    run()


def main():
    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(2)

    if args.version:
        version = pkg_resources.get_distribution("pylinkit").version
        print(f"Version: {version}")
        sys.exit(0)

    if args.debug:
        setup_logging(True, 'debug')
    else:
        setup_logging(True, 'info')

    if args.gui:
        gui_main()

    dev = None
    if args.device:
        dev = pylinkit.Tracker(args.device)

    if args.parmr:
        dev.sync()
        d = {}
        d['PARAM'] = dev.get()
        cfg = OrderedRawConfigParser()
        cfg.optionxform = lambda option: option
        cfg.read_dict(dictionary=d)
        cfg.write(args.parmr)
        args.parmr.close()

    if args.poll and args.value is not None:
        dev.poll(args.poll, int(args.value))

    if args.parmw:
        cfg = OrderedRawConfigParser()
        cfg.optionxform = lambda option: option
        cfg.read_string(args.parmw.read())
        dev.set(cfg['PARAM'])

    if args.paspw:
        dev.paspw(args.paspw.read())

    if args.dump_sensor:
        args.dump_sensor.write(dev.dumpd('sensor'))
        args.dump_sensor.close()

    if args.dump_system:
        args.dump_system.write(dev.dumpd('system'))
        args.dump_system.close()

    if args.dumpd and args.dumpd_type:
        args.dumpd.write(dev.dumpd(args.dumpd_type))
        args.dumpd.close()

    if args.erase:
        dev.erase(args.erase)

    if args.fw:
        if (args.fw.name.endswith('.zip')):
            dev.firmware_update(extract_firmware_file_from_dfu(args.fw), 0, args.timeout)
        else:
            dev.firmware_update(args.fw.read(), 0, args.timeout)

    if args.ano:
        dev.firmware_update(create_wrapped_file_with_crc32(args.ano.read()), 2, args.timeout)

    if args.factw:
        dev.factw()

    if args.rstvw:
        dev.rstvw(resetv_options[args.rstvw])

    if args.rstbw:
        dev.rstbw()

    if args.pwron:
        dev.pwron(args.pwron)

    if args.scalw:
        if args.command is None:
            print("""
            Calibration requires a command.  Use --command to provide a command:

            cdt::

            --scalw cdt --command 0 ; to reset existing CDT calibration
            --scalw cdt --command 2 --value xxxx ; to override CA polynomial coefficient
            --scalw cdt --command 3 --value xxxx ; to override CB polynomial coefficient
            --scalw cdt --command 4 --value xxxx ; to override CC polynomial coefficient
            --scalw cdt --command 5 ; to save all CDT calibration values to filesystem
            --scalw cdt --command 6 --value xxxx ; set gain factor calibration value
            --scalw cdt --command 7 --value xxxx; power on and configure AD9533 for sweep @ frequency xxxx
            --scalw cdt --command 8 ; power off AD9533

            ph::

            --scalw ph --command 0 ; reset PH calibration
            --scalw ph --command 1 ; perform PH 7 (Mid) calibration
            --scalw ph --command 2 ; perform PH 1 (Low) calibration
            --scalw ph --command 3 ; perform PH 14 (High) calibration

            axl::

            --scalw axl --command 0 --value xxxx ; to override threshold value
            --scalw axl --command 1 --value xxxx ; to override wakeup duration value
            --scalw axl --command 2 --value xxxx ; to override wakeup gforce value
            --scalw axl --command 3 --value xxxx ; to override power mode value
            --scalw axl --command 4 --value xxxx ; to override x value
            --scalw axl --command 5 --value xxxx ; to override y value
            --scalw axl --command 6 --value xxxx ; to override z value

            rtd::

            --scalw rtd --command 0 ; reset RTD calibration, wakeup device
            --scalw rtd --command 1 ; perform 0C calibration
            --scalw rtd --command 2 ; perform 100C calibration
            --scalw rtd --command 3 ; put device back into sleep mode

            mcp47x6::

            --scalw mcp47x6 --command 0 ; reset mcp47x6 calibration
            --scalw mcp47x6 --command 350 --value 2345 ; calibration point for DAC for 350 mW power
            --scalw mcp47x6 --command 500 --value 2645 ; calibration point for DAC for 500 mW power
            --scalw mcp47x6 --command 1 ; save mcp47x6 calibration to file

            Note: use in conjunction with --argostx to send a packet at calibrated mW

            Thermistor::
            --scalw thermistor --command 0 ; reset thermistor calibration
            --scalw thermistor --command 1 --value XXXX; perform for millidegree
            --scalw thermistor --command 2 ; save for millidegree

            """)
            return
        dev.scalw(args.scalw, args.command, args.value)

    if args.scalr:
        if args.command is None:
            print("""
            Calibration read requires a command.  Use --command to provide a command:

            cdt::

            --scalr cdt --command 0 ; read CA polynomial coefficient
            --scalr cdt --command 1 ; read CB polynomial coefficient
            --scalr cdt --command 2 ; read CC polynomial coefficient
            --scalr cdt --command 3 ; read gain factor
            --scalr cdt --command 4 ; read AD5933 raw sensor real value
            --scalr cdt --command 5 ; read AD5933 raw sensor imaginary value
            --scalr cdt --command 6 ; read impedence value using stored calibrated gain factor

            axl::

            --scalr axl --command 0 ; read X
            --scalr axl --command 1 ; read Y
            --scalr axl --command 2 ; read Z
            --scalr axl --command 3 ; read XYZ

            thermistor::

            --scalr thermistor --command 0 ; read threshold temp
            """)
            return
        print(dev.scalr(args.scalr, args.command))

    if args.argostx:
        dev.argostx(args.argosmod, args.argospower, args.argosfreq, args.argossize, args.argostcxo)

    if args.smdcd:
        dev.smdcd(args.smdid, args.smdaddr, args.smdseckey, args.smdradioconf)

    if args.smdfw:
        fw_data = args.smdfw.read()
        fw_crc = stm32_crc32(fw_data)
        print(f"SMD firmware size: {len(fw_data)} bytes")
        print(f"SMD firmware STM32 CRC32: 0x{fw_crc:08X}")
        print(f"SMD DFU mode: {args.smdfw_mode.upper()}")
        print(f"  file_id={'3 (UART)' if args.smdfw_mode == 'uart' else '4 (SPI)'}")
        wrapped = create_smd_wrapped_file(fw_data)
        dev.smd_firmware_update(wrapped, mode=args.smdfw_mode, timeout=args.timeout)

    if args.scan:
        scan_dev = pylinkit.Scanner()
        result = scan_dev.scan()
        for x in result:
            print(x.address, x.name)

    if args.ble_trace:
        import subprocess
        import os

        def configure_ble_mode(address):
            import time
            print(f"\nConfiguring device {address} for BLE trace output...")
            temp_dev = pylinkit.Tracker(address)
            temp_dev.sync()
            temp_dev.set({'DEBUG_OUTPUT_MODE': 'BLE'})
            print("Configuration updated: DEBUG_OUTPUT_MODE = BLE")
            del temp_dev
            print("Waiting for BLE connection to be released...")
            time.sleep(3)

        device_address = args.device

        if device_address:
            response = input("\nIs the device configured with DEBUG_OUTPUT_MODE = BLE? (y/n): ")
            if response.lower() != 'y':
                configure_ble_mode(device_address)

        ble_trace_script = os.path.join(os.path.dirname(__file__), 'ble_trace.py')

        try:
            cmd = [sys.executable, ble_trace_script]
            if device_address:
                cmd.append(device_address)
            process = subprocess.run(cmd)
            sys.exit(process.returncode)
        except KeyboardInterrupt:
            print("\n\n=== Trace listener stopped ===")
            sys.exit(0)


if __name__ == "__main__":
    main()
