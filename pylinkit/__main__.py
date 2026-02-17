import logging
import argparse
import sys
import importlib.metadata

from .transport import TransportType, create_transport
from .transport.serial import SerialTransport
from .utils import OrderedRawConfigParser, extract_firmware_file_from_dfu, create_wrapped_file_with_crc32, create_smd_wrapped_file, stm32_crc32

erase_options = ['sensor', 'system', 'all', 'als', 'ph', 'rtd', 'cdt', 'cam', 'axl', 'pressure', 'thermistor', 'tsys01']
dumpd_options = ['system', 'gnss', 'als', 'ph', 'rtd', 'cdt', 'cam', 'axl', 'pressure', 'thermistor', 'tsys01']
scalw_options = ['cdt', 'axl', 'ph', 'rtd', 'mcp47x6', 'thermistor']
scalr_options = ['cdt', 'axl', 'thermistor']
resetv_options = {'tx_counter': 1, 'rx_counter': 3, 'rx_time': 4}
modulation_options = {'LDK': 0, 'LDA2': 1, 'VLDA4': 2}
pwr_options = ['all', 'gnss', 'sensors', 'satellite', 'off']


parser = argparse.ArgumentParser(
    prog='pylinkit',
    description='Linkit V4 tracker configuration tool (BLE/USB/UART)'
)

# === Transport selection ===
transport_group = parser.add_argument_group('Transport')
transport_group.add_argument('--transport', '-t', type=str, choices=['ble', 'usb', 'uart'], default='ble',
                             help='Communication transport (default: ble)')
transport_group.add_argument('--port', '-p', type=str, required=False,
                             help='Serial port for USB/UART (e.g., COM3, /dev/ttyUSB0)')
transport_group.add_argument('--baudrate', type=int, default=115200,
                             help='Serial baudrate (default: 115200)')
transport_group.add_argument('--device', type=str, required=False,
                             help='BLE device address (xx:xx:xx:xx:xx:xx)')

# === Discovery ===
discovery_group = parser.add_argument_group('Discovery')
discovery_group.add_argument('--scan', action='store_true', required=False, help='Scan for BLE beacons')
discovery_group.add_argument('--list-ports', action='store_true', required=False, help='List available serial ports')

# === Log viewer ===
log_group = parser.add_argument_group('Log Viewer')
log_group.add_argument('--log', '--trace', action='store_true', required=False,
                       help='Start live log viewer (works over BLE, USB, or UART)')
log_group.add_argument('--no-color', action='store_true', required=False,
                       help='Disable colored log output')
log_group.add_argument('--ble-trace', action='store_true', required=False,
                       help='(Legacy) Read BLE trace output. Use --log --transport ble instead')

# === Device commands ===
cmd_group = parser.add_argument_group('Device Commands')
cmd_group.add_argument('--fw', type=argparse.FileType('rb'), required=False,
                       help='Firmware filename for FW OTA update')
cmd_group.add_argument('--timeout', type=float, required=False, default=None,
                       help='Communications timeout')
cmd_group.add_argument('--erase', type=str, choices=erase_options, required=False,
                       help='Erase log file')
cmd_group.add_argument('--parmr', type=argparse.FileType('w'), required=False,
                       help='Filename to write [PARAM] configuration to')
cmd_group.add_argument('--poll', type=str, required=False,
                       help='Poll a parameter value by key and use --value to denote repetitions')
cmd_group.add_argument('--rstvw', type=str, choices=resetv_options.keys(), required=False,
                       help='Reset variable: tx_counter or rx_counter')
cmd_group.add_argument('--rstbw', action='store_true', required=False, help='Reset beacon')
cmd_group.add_argument('--factw', action='store_true', required=False,
                       help='Factory reset (WARNING: erases all stored logs and configuration!)')
cmd_group.add_argument('--parmw', type=argparse.FileType('r'), required=False,
                       help='Filename to read [PARAM] configuration from')
cmd_group.add_argument('--paspw', type=argparse.FileType('r'), required=False,
                       help='Filename (JSON) to read pass predict configuration from')
cmd_group.add_argument('--dump_sensor', type=argparse.FileType('wb'), required=False,
                       help='Dump sensor log file')
cmd_group.add_argument('--dump_system', type=argparse.FileType('wb'), required=False,
                       help='Dump system log file')
cmd_group.add_argument('--dumpd', type=argparse.FileType('wb'), required=False,
                       help='Dump the specified log file')
cmd_group.add_argument('--dumpd_type', type=str, choices=dumpd_options, required=False,
                       help='Specified log file')
cmd_group.add_argument('--pwron', type=str, choices=pwr_options, required=False,
                       help='Power on the device (GNSS, SENSORS, SATELLITE)')
cmd_group.add_argument('--ano', type=argparse.FileType('rb'), required=False,
                       help='GNSS AssistNow Offline filename')

# === Calibration ===
cal_group = parser.add_argument_group('Calibration')
cal_group.add_argument('--scalw', type=str, choices=scalw_options, required=False,
                       help='Run a calibration write command')
cal_group.add_argument('--scalr', type=str, choices=scalr_options, required=False,
                       help='Run a calibration read command')
cal_group.add_argument('--command', type=int, required=False, help='Calibration command number')
cal_group.add_argument('--value', type=float, default=0, required=False, help='Calibration command value')

# === Sensor Read ===
sensr_options = {'all': 0x0F, 'battery': 0x01, 'pressure': 0x02, 'gnss': 0x04, 'accel': 0x08}
sensor_group = parser.add_argument_group('Sensor Read')
sensor_group.add_argument('--sensr', type=str, choices=sensr_options.keys(), required=False,
                          help='Read sensors (all, battery, pressure, gnss, accel)')
sensor_group.add_argument('--sensr_timeout', type=int, default=60, required=False,
                          help='GNSS timeout in seconds (default: 60)')

# === Argos/Satellite ===
sat_group = parser.add_argument_group('Argos/Satellite')
sat_group.add_argument('--argostx', action='store_true', required=False, help='Send argos TX packet')
sat_group.add_argument('--argosmod', type=str, default='LDA2', required=False,
                       help='Kineis modulation (LDK, LDA2, VLDA4)')
sat_group.add_argument('--argosfreq', type=float, default=401.65, required=False,
                       help='Argos frequency in MHz')
sat_group.add_argument('--argossize', type=int, default=15, required=False, help='Packet size in bytes')
sat_group.add_argument('--argostcxo', type=int, default=5, required=False, help='TCXO warm-up in seconds')
sat_group.add_argument('--argospower', type=int, default=350, required=False, help='TX power in mW')

# === SMD ===
smd_group = parser.add_argument_group('SMD Module')
smd_group.add_argument('--smdcd', action='store_true', required=False,
                       help='Send Credentials to SMD flash memory')
smd_group.add_argument('--smdid', type=str, default='', required=False, help='SMD Decimal ID')
smd_group.add_argument('--smdaddr', type=str, default='', required=False, help='SMD hexadecimal address')
smd_group.add_argument('--smdseckey', type=str, default='', required=False, help='SMD Secret key')
smd_group.add_argument('--smdradioconf', type=str, default='', required=False, help='SMD radio configuration')
smd_group.add_argument('--smdfw', type=argparse.FileType('rb'), required=False,
                       help='SMD module firmware binary for DFU update')
smd_group.add_argument('--smdfw_mode', type=str, choices=['uart', 'spi'], default='uart', required=False,
                       help='SMD DFU transport mode: uart or spi (default: uart)')
smddfu_actions = {'enter': 0, 'exit': 1, 'status': 2, 'update': 3, 'info': 4, 'version': 5}
smd_group.add_argument('--smddfu', type=str, choices=smddfu_actions.keys(), required=False,
                       help='SMD DFU action (enter, exit, status, update, info, version)')
smd_group.add_argument('--smdtst', action='store_true', required=False,
                       help='Run SMD SPI test')
# === Misc ===
parser.add_argument('--debug', action='store_true', required=False, help='Turn on debug trace')
parser.add_argument('--version', action='version', version='%(prog)s ' + importlib.metadata.version('pylinkit'))


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


def main():
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(2)

    if args.debug:
        setup_logging(True, 'debug')
    else:
        setup_logging(True, 'info')

    # --- List serial ports ---
    if args.list_ports:
        ports = SerialTransport.list_ports()
        if ports:
            print("Available serial ports:")
            for p in ports:
                print(f"  {p.device} - {p.description}")
        else:
            print("No serial ports found")
        sys.exit(0)

    # --- Scan for BLE devices ---
    if args.scan:
        import pylinkit
        scan_dev = pylinkit.Scanner()
        result = scan_dev.scan()
        for x in result:
            print(x.address, x.name)
        sys.exit(0)

    # --- Determine transport type and address ---
    transport_type = TransportType(args.transport)

    # Handle legacy --ble-trace
    if args.ble_trace:
        args.log = True
        transport_type = TransportType.BLE

    # --- Log viewer mode ---
    if args.log:
        from .log_viewer import LogViewer

        if transport_type == TransportType.BLE:
            address = args.device
            if not address:
                # Auto-scan and select
                import pylinkit
                scan_dev = pylinkit.Scanner()
                result = scan_dev.scan()
                if not result:
                    print("No BLE devices found")
                    sys.exit(1)
                print("\nFound devices:")
                for i, d in enumerate(result):
                    print(f"  {i + 1}. {d.address} - {d.name}")
                choice = input("\nSelect device number: ")
                try:
                    address = result[int(choice) - 1].address
                except (ValueError, IndexError):
                    print("Invalid selection")
                    sys.exit(1)

            # Configure BLE trace mode if needed
            if args.ble_trace and address:
                response = input("\nIs the device configured with DEBUG_OUTPUT_MODE = BLE? (y/n): ")
                if response.lower() != 'y':
                    import time
                    print(f"\nConfiguring device {address} for BLE trace output...")
                    import pylinkit
                    temp_dev = pylinkit.Tracker(address)
                    temp_dev.sync()
                    temp_dev.set({'DEBUG_OUTPUT_MODE': 'BLE'})
                    print("Configuration updated: DEBUG_OUTPUT_MODE = BLE")
                    del temp_dev
                    print("Waiting for BLE connection to be released...")
                    time.sleep(3)

            transport = create_transport(transport_type)
            transport.connect(address)
            # Switch BLE transport to log mode
            transport.set_log_mode(True)
        else:
            # USB or UART
            if not args.port:
                parser.error(f'--port is required for {args.transport} transport')
            transport = create_transport(transport_type)
            transport.connect(args.port, baudrate=args.baudrate)

        viewer = LogViewer(transport, enable_colors=not args.no_color)
        try:
            viewer.start()
        finally:
            transport.disconnect()
        sys.exit(0)

    # --- All other commands require a connected device ---
    address = None
    if transport_type == TransportType.BLE:
        address = args.device
        if not address:
            parser.error('--device is required for BLE transport')
    else:
        address = args.port
        if not address:
            parser.error(f'--port is required for {args.transport} transport')

    import pylinkit
    dev = pylinkit.Tracker(
        address,
        transport_type=transport_type,
        timeout=args.timeout or 5.0,
        baudrate=args.baudrate
    )

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
        if args.fw.name.endswith('.zip'):
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

    if args.sensr:
        r = dev.sensr(sensr_options[args.sensr], args.sensr_timeout)
        mask = sensr_options[args.sensr]
        if mask & 0x01:
            print(f"Battery: {r['battery_mv']}mV ({r['battery_soc']}%)")
        if mask & 0x02:
            print(f"Pressure: {r['pressure_mbar']:.1f} mbar")
            print(f"Temperature: {r['temperature_c']:.1f} C")
        if mask & 0x04:
            if r['hdop'] < 99.0:
                print(f"GNSS: {r['latitude']:.6f}, {r['longitude']:.6f}")
                print(f"HDOP: {r['hdop']:.1f}, Satellites: {r['num_satellites']}")
            else:
                print(f"GNSS: No valid fix (satellites: {r['num_satellites']})")
        if mask & 0x08 and 'accel_x' in r:
            print(f"Accel: X={r['accel_x']:.3f}g Y={r['accel_y']:.3f}g Z={r['accel_z']:.3f}g")
            print(f"Accel Temp: {r['accel_temp']:.1f} C")
            print(f"Activity: {r['activity']}")

    if args.argostx:
        dev.argostx(args.argosmod, args.argospower, args.argosfreq, args.argossize, args.argostcxo)

    if args.smdcd:
        dev.smdcd(args.smdid, args.smdaddr, args.smdseckey, args.smdradioconf)

    if args.smddfu:
        try:
            result = dev.smddfu(smddfu_actions[args.smddfu])
            print(f"SMD DFU [{args.smddfu.upper()}] OK")
            print(f"  Mode: {'Bootloader (DFU)' if result['dfu_mode'] else 'Application'}")
            if result['info']:
                print(f"  Info: {result['info']}")
        except Exception as e:
            print(f"SMD DFU [{args.smddfu.upper()}] FAILED: {e}")

    if args.smdtst:
        try:
            result = dev.smdtst()
            print(f"SMD SPI TEST: {result}")
        except Exception as e:
            print(f"SMD SPI TEST FAILED: {e}")

    if args.smdfw:
        fw_data = args.smdfw.read()
        fw_crc = stm32_crc32(fw_data)
        print(f"SMD firmware size: {len(fw_data)} bytes")
        print(f"SMD firmware STM32 CRC32: 0x{fw_crc:08X}")
        print(f"SMD DFU mode: {args.smdfw_mode.upper()}")
        print(f"  file_id={'3 (UART)' if args.smdfw_mode == 'uart' else '4 (SPI)'}")
        wrapped = create_smd_wrapped_file(fw_data)
        dev.smd_firmware_update(wrapped, mode=args.smdfw_mode, timeout=args.timeout)
        if args.smdfw_mode == 'spi':
            print("SPI DFU: waiting for device to complete flashing (up to 3min)...")
            try:
                result = dev.wait_smd_dfu_result(timeout=180.0)
                if result['status'] == 0:
                    print(f"SPI DFU SUCCESS: progress={result['progress']}% firmware={result['info']}")
                else:
                    print(f"SPI DFU FAILED: {result['info']}")
            except TimeoutError:
                print("SPI DFU: no response from device (timeout 180s)")


if __name__ == "__main__":
    main()
