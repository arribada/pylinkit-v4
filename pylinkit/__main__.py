import logging
import argparse
import sys
import importlib.metadata

from .transport import TransportType, create_transport
from .transport.serial import SerialTransport
from .utils import OrderedRawConfigParser, extract_firmware_file_from_dfu, create_wrapped_file_with_crc32, create_smd_wrapped_file, stm32_crc32

erase_options = ['sensor', 'system', 'all', 'als', 'ph', 'rtd', 'cdt', 'cam', 'axl', 'pressure', 'thermistor', 'tsys01', 'sws', 'mortality']
dumpd_options = ['system', 'gnss', 'als', 'ph', 'rtd', 'cdt', 'cam', 'axl', 'pressure', 'thermistor', 'tsys01', 'sws', 'mortality']
scalw_options = ['cdt', 'axl', 'ph', 'rtd', 'thermistor', 'pressure', 'sws']
scalr_options = ['cdt', 'axl', 'thermistor', 'pressure', 'sws']
resetv_options = {'tx_counter': 1, 'boot_counter': 2, 'rx_counter': 3, 'rx_time': 4}
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
                       help='Reset variable (tx_counter, boot_counter, rx_counter, rx_time)')
cmd_group.add_argument('--rstbw', action='store_true', required=False, help='Reset beacon')
cmd_group.add_argument('--factw', action='store_true', required=False,
                       help='Factory reset (WARNING: erases all stored logs and configuration!)')
cmd_group.add_argument('--parmw', type=argparse.FileType('r'), required=False,
                       help='Filename to read [PARAM] configuration from')
cmd_group.add_argument('--paspw', type=argparse.FileType('r'), required=False,
                       help='Filename (JSON) to read pass predict configuration from')
cmd_group.add_argument('--dumpd', type=argparse.FileType('wb'), required=False,
                       help='Dump the specified log file')
cmd_group.add_argument('--dumpd_type', type=str, choices=dumpd_options, required=False,
                       help='Specified log file')
cmd_group.add_argument('--pwron', type=str, choices=pwr_options, required=False,
                       help='Power on the device (GNSS, SENSORS, SATELLITE)')
cmd_group.add_argument('--ano', type=argparse.FileType('rb'), required=False,
                       help='GNSS AssistNow Offline filename')
cmd_group.add_argument('--ano-download', action='store_true', required=False,
                       help='Download AssistNow almanac from u-blox and send to device')
cmd_group.add_argument('--ano-token', type=str, required=False,
                       help='u-blox ZTP token for AssistNow almanac download')
cmd_group.add_argument('--ano-save', type=str, required=False,
                       help='Save downloaded almanac to local file')
cmd_group.add_argument('--ano-period', type=int, required=False, default=5, choices=[1, 2, 3, 4, 5],
                       help='Almanac duration in weeks (1-5, default: 5)')

# === Calibration ===
cal_group = parser.add_argument_group('Calibration')
cal_group.add_argument('--scalw', type=str, choices=scalw_options, required=False,
                       help='Run a calibration write command')
cal_group.add_argument('--scalr', type=str, choices=scalr_options, required=False,
                       help='Run a calibration read command')
cal_group.add_argument('--command', type=int, required=False, help='Calibration command number')
cal_group.add_argument('--value', type=float, default=0, required=False, help='Calibration command value')

# === Sensor Read ===
sensr_options = {'all': 0xFF, 'battery': 0x01, 'pressure': 0x02, 'gnss': 0x04, 'accel': 0x08, 'thermistor': 0x10, 'sea_temp': 0x20, 'als': 0x40, 'ph': 0x80}
sensor_group = parser.add_argument_group('Sensor Read')
sensor_group.add_argument('--battery', action='store_true', required=False,
                          help='Read battery status (voltage, SOC, low/critical)')
sensor_group.add_argument('--sensr', type=str, choices=sensr_options.keys(), required=False,
                          help='Read sensors (all, battery, pressure, gnss, accel, thermistor, sea_temp, als, ph)')
sensor_group.add_argument('--sensr_timeout', type=int, default=60, required=False,
                          help='GNSS timeout in seconds (default: 60)')

# === GNSS ===
gnss_group = parser.add_argument_group('GNSS')
gnss_group.add_argument('--gnssi', action='store_true', required=False,
                        help='Read GNSS module info (powers on GNSS, reads, powers off)')
gnss_group.add_argument('--gnssa', action='store_true', required=False,
                        help='Check GNSS AssistNow almanac status on device')
gnss_group.add_argument('--gnssbr', action='store_true', required=False,
                        help='Start GNSS UART bridge (USB <-> u-blox, releases port for Tera Term/u-center)')

# === Argos/Satellite ===
sat_group = parser.add_argument_group('Argos/Satellite')
sat_group.add_argument('--argostx', action='store_true', required=False, help='Send argos TX test packet')
sat_group.add_argument('--argosmod', type=str, default=None, required=False,
                       choices=['LDK', 'LDA2', 'VLDA4'],
                       help='Kineis modulation. If set, updates RADIOCONF + KMAC on device')
sat_group.add_argument('--argossize', type=int, default=None, required=False,
                       help='TX payload size in bytes (default: max for modulation, LDK=16, LDA2/VLDA4=28)')
sat_group.add_argument('--argosradioconf', type=str, default=None, required=False,
                       help='Custom radioconf hex string (32 chars). If omitted, uses stored config (ARP51/52/53)')
sat_group.add_argument('--argostcxo', type=int, default=0, required=False, help='TCXO warm-up in seconds (default: 0)')
sat_group.add_argument('--satdp', action='store_true', required=False,
                       help='Start Doppler calibration (periodic TX until reset)')

# === LoRa ===
lora_group = parser.add_argument_group('LoRa')
lora_group.add_argument('--loratx', type=int, required=False, metavar='SIZE',
                        help='Send LoRa test TX (payload size in bytes, 1-222)')
lora_group.add_argument('--lorabr', action='store_true', required=False,
                        help='Start LoRa UART bridge (USB <-> RAK3172 AT commands, +++ to exit)')

# === SMD ===
smd_group = parser.add_argument_group('SMD Module')
smd_group.add_argument('--smdcd', action='store_true', required=False,
                       help='Write SMD credentials (applied to hardware at next TX)')
smd_group.add_argument('--smdid', type=str, default='', required=False, help='SMD Decimal ID')
smd_group.add_argument('--smdaddr', type=str, default='', required=False, help='SMD hexadecimal address')
smd_group.add_argument('--smdseckey', type=str, default='', required=False, help='SMD Secret key')
smd_group.add_argument('--smdradioconf', type=str, default='', required=False, help='SMD radio configuration')
smd_group.add_argument('--satvf', action='store_true', required=False,
                       help='Verify satellite credentials (config store vs hardware, SMD + KIM2)')
smd_group.add_argument('--smdfw', type=argparse.FileType('rb'), required=False,
                       help='SMD module firmware binary for DFU update')
smd_group.add_argument('--smdfw_mode', type=str, choices=['uart', 'spi'], default='uart', required=False,
                       help='SMD DFU transport mode: uart or spi (default: uart)')
smddfu_actions = {'enter': 0, 'exit': 1, 'status': 2, 'update': 3, 'info': 4, 'version': 5}
smd_group.add_argument('--smddfu', type=str, choices=smddfu_actions.keys(), required=False,
                       help='SMD DFU action (enter, exit, status, update, info, version)')
smd_group.add_argument('--smdtst', action='store_true', required=False,
                       help='Run SMD SPI test')

# === SWS (Salt Water Switch) ===
sws_group = parser.add_argument_group('SWS (Salt Water Switch)')
sws_group.add_argument('--swsst', action='store_true', required=False,
                       help='Read Salt Water Switch status')
sws_group.add_argument('--swstst', type=str, choices=['start', 'stop'], required=False,
                       help='Start or stop SWS test mode')
sws_group.add_argument('--swscal', type=str, choices=['start', 'cancel'], required=False,
                       help='SWS guided calibration (start or cancel)')

# === RTC ===
rtc_group = parser.add_argument_group('RTC')
rtc_group.add_argument('--rtcr', action='store_true', required=False,
                       help='Read device RTC current time')
rtc_group.add_argument('--rtcw', action='store_true', required=False,
                       help='Set device RTC to current UTC time')
rtc_group.add_argument('--rtcw_timestamp', type=int, required=False,
                       help='Set device RTC to specific unix timestamp')

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
                response = input("\nIs the device configured with DEBUG_OUTPUT_MODE = BLE_NUS? (y/n): ")
                if response.lower() != 'y':
                    import time
                    print(f"\nConfiguring device {address} for BLE trace output...")
                    import pylinkit
                    temp_dev = pylinkit.Tracker(address)
                    temp_dev.sync()
                    temp_dev.set({'DEBUG_OUTPUT_MODE': 'BLE_NUS'})
                    print("Configuration updated: DEBUG_OUTPUT_MODE = BLE_NUS")
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
        from datetime import datetime, timezone
        dev.sync()
        params = dev.get()
        # Format unix timestamps as DD/MM/YYYY HH:MM:SS
        TIMESTAMP_PARAMS = ('LAST_KNOWN_RTC', 'RTC_CURRENT_TIME')
        for key in TIMESTAMP_PARAMS:
            if key in params:
                ts = int(params[key])
                if ts > 0:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    params[key] = dt.strftime('%d/%m/%Y %H:%M:%S')
        d = {}
        d['PARAM'] = params
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
        try:
            result = dev.set(cfg['PARAM'])
            ok = [k for k, v in result.items() if v]
            nok = [k for k, v in result.items() if not v]
            if ok:
                print(f"Parameters written OK: {', '.join(ok)}")
            if nok:
                print(f"Parameters REJECTED (unknown key or invalid value): {', '.join(nok)}")
                print("  Note: some parameters may not exist depending on firmware build configuration")
        except Exception as e:
            print(f"PARMW FAILED: {e}")

    if args.paspw:
        dev.paspw(args.paspw.read())

    if args.dumpd and args.dumpd_type:
        try:
            args.dumpd.write(dev.dumpd(args.dumpd_type))
            args.dumpd.close()
            print(f"Dump '{args.dumpd_type}' saved to {args.dumpd.name}")
        except Exception as e:
            args.dumpd.close()
            print(f"Dump '{args.dumpd_type}' FAILED: {e}")
            print(f"  (sensor log may not exist - check firmware Makefile configuration)")

    if args.erase:
        dev.erase(args.erase)

    if args.fw:
        if args.fw.name.endswith('.zip'):
            dev.firmware_update(extract_firmware_file_from_dfu(args.fw), 0, args.timeout)
        else:
            dev.firmware_update(args.fw.read(), 0, args.timeout)

    if args.ano:
        dev.firmware_update(create_wrapped_file_with_crc32(args.ano.read()), 2, args.timeout)

    if args.ano_download:
        if not args.ano_token:
            parser.error('--ano-token is required for --ano-download')
        try:
            print("Downloading AssistNow almanac...")
            almanac_data, chipcode = dev.download_almanac(args.ano_token, period=args.ano_period)
            print(f"  Downloaded {len(almanac_data)} bytes, chipcode={chipcode}")
            if args.ano_save:
                with open(args.ano_save, 'wb') as f:
                    f.write(almanac_data)
                print(f"Almanac saved to {args.ano_save}")
        except Exception as e:
            print(f"AssistNow download FAILED: {e}")

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

            axl (BMA400, device_id=0)::

            --scalw axl --command 0 --value X ; set coefficient X (g-force)
            --scalw axl --command 1 --value X ; set coefficient Y (g-force)
            --scalw axl --command 2 --value X ; set coefficient Z (g-force)
            --scalw axl --command 3 ; auto-calibrate (X=0, Y=0, Z=1g)
            --scalw axl --command 6 ; save calibration to AXL.CAL

            pressure (LPS28DFW, device_id=1)::

            --scalw pressure --command 0 --value 1013.25 ; set sea level pressure in hPa (default 1013.25)
            --scalw pressure --command 1 --value X ; set temperature offset in °C (default 0.0)

            ph (OEM pH, device_id=3)::

            --scalw ph --command 0 ; reset all pH calibration
            --scalw ph --command 1 ; calibrate midpoint (pH 7.0)
            --scalw ph --command 2 ; calibrate low point (pH 4.0)
            --scalw ph --command 3 ; calibrate high point (pH 10.0)
            --scalw ph --command 4 --value X ; set temperature compensation (C)
            Order: clear -> low -> mid -> high

            rtd (OEM/EZO temperature, device_id=4)::

            --scalw rtd --command 0 ; clear calibration
            --scalw rtd --command 1 ; calibrate 0C (ice water)
            --scalw rtd --command 2 ; calibrate 100C (boiling water)
            --scalw rtd --command 3 --value X ; calibrate arbitrary temperature (C) [EZO only]
            --scalw rtd --command 4 ; find (LED blink) [EZO only]
            --scalw rtd --command 5 ; factory reset [EZO only]

            cdt (conductivity/impedance, device_id=5)::

            --scalw cdt --command 0 ; reset CDT calibration
            --scalw cdt --command 2 --value X ; set CA coefficient (quadratic)
            --scalw cdt --command 3 --value X ; set CB coefficient (linear)
            --scalw cdt --command 4 --value X ; set CC coefficient (constant)
            --scalw cdt --command 5 ; save calibration to CDT.CAL
            --scalw cdt --command 6 --value X ; set gain factor
            --scalw cdt --command 7 --value X ; start AD5933 at frequency X Hz
            --scalw cdt --command 8 ; stop AD5933

            thermistor (device_id=7)::

            --scalw thermistor --command 0 ; reset calibration (offset = 0)
            --scalw thermistor --command 1 --value X ; calibrate with reference temp in °C (firmware auto-computes offset)

            sws (Salt Water Switch, device_id=8)::

            --scalw sws --command 0 --value X ; set water hint (ADC 0-16383)
            --scalw sws --command 1 --value X ; set air hint (ADC 0-16383)

            """)
            return
        dev.scalw(args.scalw, args.command, args.value)

    if args.scalr:
        if args.command is None:
            print("""
            Calibration read requires a command.  Use --command to provide a command:

            axl (BMA400, device_id=0)::

            --scalr axl --command 1 ; read calibrated X value (g)
            --scalr axl --command 2 ; read calibrated Y value (g)
            --scalr axl --command 3 ; read calibrated Z value (g)
            --scalr axl --command 5 ; read saved X offset (g)
            --scalr axl --command 6 ; read saved Y offset (g)
            --scalr axl --command 7 ; read saved Z offset (g)

            pressure (LPS28DFW, device_id=1)::

            --scalr pressure --command 0 ; read sea level pressure (hPa)
            --scalr pressure --command 1 ; read temperature offset (°C)

            cdt (conductivity/impedance, device_id=5)::

            --scalr cdt --command 0 ; read CA coefficient
            --scalr cdt --command 1 ; read CB coefficient
            --scalr cdt --command 2 ; read CC coefficient
            --scalr cdt --command 3 ; read gain factor
            --scalr cdt --command 4 ; read impedance real (I)
            --scalr cdt --command 5 ; read impedance imaginary (Q)
            --scalr cdt --command 6 ; read calibrated impedance

            thermistor (device_id=7)::

            --scalr thermistor --command 0 ; read current offset (°C)
            --scalr thermistor --command 1 ; read current live temperature (°C)

            sws (Salt Water Switch, device_id=8)::

            --scalr sws --command 0 ; read water hint (ADC)
            --scalr sws --command 1 ; read air hint (ADC)
            --scalr sws --command 2 ; read running water value (ADC)
            --scalr sws --command 3 ; read running air value (ADC)
            --scalr sws --command 4 ; read observed peak (ADC)
            """)
            return
        print(dev.scalr(args.scalr, args.command))

    if args.battery:
        try:
            r = dev.battery()
            print(f"Battery:")
            print(f"  Voltage:  {r['voltage_mv']}mV ({r['voltage_mv']/1000:.3f}V)")
            print(f"  SOC:      {r['soc']}%")
            print(f"  Low:      {'YES' if r['low_battery'] else 'No'} (threshold: {r['lb_threshold_pct']}%)")
            print(f"  Critical: {'YES' if r['critical'] else 'No'} (threshold: {r['critical_threshold_pct']}%)")
        except Exception as e:
            print(f"Battery read FAILED: {e}")

    if args.sensr:
        r = dev.sensr(sensr_options[args.sensr], args.sensr_timeout)
        mask = sensr_options[args.sensr]
        status = r.get('sensor_status', mask)  # backward compat: assume all OK if missing

        def _sensr_avail(bit):
            return bool(status & bit)

        if mask & 0x01:
            if _sensr_avail(0x01):
                print(f"Battery: {r['battery_mv']}mV ({r['battery_soc']}%)")
            else:
                print("Battery: N/A")
        if mask & 0x02:
            if _sensr_avail(0x02):
                print(f"Pressure: {r['pressure_mbar']:.1f} mbar, Temp: {r['temperature']:.1f} C, Alt: {r['altitude']:.1f} m")
            else:
                print("Pressure: N/A")
        if mask & 0x04:
            if _sensr_avail(0x04):
                if r['hdop'] < 99.0:
                    print(f"GNSS: {r['latitude']:.6f}, {r['longitude']:.6f}")
                    print(f"HDOP: {r['hdop']:.1f}, Satellites: {r['num_satellites']}")
                else:
                    print(f"GNSS: No valid fix (satellites: {r['num_satellites']})")
            else:
                print("GNSS: N/A")
        if mask & 0x08:
            if _sensr_avail(0x08):
                print(f"Accel: X={r['accel_x']:.3f}g Y={r['accel_y']:.3f}g Z={r['accel_z']:.3f}g")
            else:
                print("Accel: N/A")
        if mask & 0x10:
            if _sensr_avail(0x10):
                print(f"Thermistor: {r['thermistor_temp']:.1f} C")
            else:
                print("Thermistor: N/A")
        if mask & 0x20:
            if _sensr_avail(0x20):
                print(f"Sea Temp: {r.get('sea_temp', 0):.1f} C")
            else:
                print("Sea Temp: N/A")
        if mask & 0x40:
            if _sensr_avail(0x40):
                print(f"ALS: {r.get('als_lux', 0):.1f} lux")
            else:
                print("ALS: N/A")
        if mask & 0x80:
            if _sensr_avail(0x80):
                print(f"pH: {r.get('ph', 0):.2f}")
            else:
                print("pH: N/A")

    if args.gnssi:
        try:
            r = dev.gnssi()
            print(f"GNSS Module Info:")
            print(f"  Unique ID:  {r['unique_id']}")
            print(f"  SW Version: {r['sw_version']}")
            print(f"  HW Version: {r['hw_version']}")
        except Exception as e:
            print(f"GNSSI FAILED: {e}")

    if args.gnssa:
        try:
            r = dev.gnssa()
            print(f"GNSS Almanac Status:")
            if r['present']:
                print(f"  File:          Present ({r['file_size']} bytes)")
                print(f"  Total records: {r['total_records']}")
                print(f"  Valid records: {r['valid_records']} (matching today)")
                if r['stale']:
                    print(f"  Status:        STALE (data >24h old or RTC not set)")
                else:
                    print(f"  Status:        Valid")
            else:
                print(f"  File:          Absent (no almanac uploaded)")
        except Exception as e:
            print(f"GNSSA FAILED: {e}")

    def start_bridge(name, start_fn, connect_hint):
        try:
            print(f"Starting {name} bridge...")
            start_fn()
            dev.disconnect()
            print(f"{name} bridge active on {address}. Port released.")
            print(f"Connect {connect_hint} to {address}. Send +++ to exit bridge mode.")
            sys.exit(0)
        except Exception as e:
            print(f"{name} bridge FAILED: {e}")

    if args.gnssbr:
        start_bridge("GNSS UART (USB <-> u-blox M10 at 9600 baud)",
                      lambda: dev.gnssbr(1), "Tera Term / u-center")

    if args.argostx:
        mod = args.argosmod or 'LDA2'
        if args.argosmod is not None:
            print(f"WARNING: --argosmod {args.argosmod} will update RADIOCONF (IDP14) on the SMD module")
            dev.update_radioconf(args.argosmod)
        dev.argostx(mod, args.argossize, args.argosradioconf, args.argostcxo)

    if args.loratx is not None:
        try:
            dev.loratx(args.loratx)
            print(f"LoRa TX sent ({args.loratx} bytes)")
        except Exception as e:
            print(f"LoRa TX FAILED: {e}")

    if args.lorabr:
        start_bridge("LoRa UART (USB <-> RAK3172 AT commands)",
                      lambda: dev.lorabr(1), "Tera Term")

    if args.satdp:
        try:
            dev.satdp()
            print("Doppler calibration started (periodic TX until device reset)")
        except Exception as e:
            print(f"Doppler calibration FAILED: {e}")

    if args.smdcd:
        dev.smdcd(args.smdid, args.smdaddr, args.smdseckey, args.smdradioconf)
        print("SMD credentials written (will be applied to hardware at next TX)")

    if args.satvf:
        try:
            r = dev.satvf()
            print(f"Satellite Module Credentials:")
            print(f"  ID:        {r['id']}")
            print(f"  Address:   {r['addr']}")
            print(f"  SecKey:    {r['seckey']}")
            print(f"  RadioConf: {r['radioconf']}")
            if r['match']:
                print(f"  Status:    MATCH (config store == hardware)")
            else:
                print(f"  Status:    MISMATCH (credentials will be updated at next TX)")
        except Exception as e:
            print(f"Credential verify FAILED: {e}")

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

    if args.swsst:
        try:
            from .protocol.dte_commands import DTECommands
            r = dev.swsst()
            level = r['surface_level']
            level_name = DTECommands.SURFACE_LEVEL_NAMES.get(level, f"UNKNOWN({level})")
            contrast = r['contrast_x10'] / 10
            if r['contrast_x10'] >= 80:
                bio_status = 'Clean'
            elif r['contrast_x10'] >= 30:
                bio_status = 'Moderate biofouling'
            else:
                bio_status = 'Severe biofouling'
            print(f"SWS Status:")
            print(f"  Air baseline:    {r['air']} ADC")
            print(f"  Water baseline:  {r['water']} ADC")
            print(f"  Threshold:       {r['threshold']} ADC")
            print(f"  Hysteresis:      {r['hysteresis']} ADC")
            print(f"  Raw ADC:         {r['raw_adc']}")
            print(f"  Filtered ADC:    {r['filtered_adc']}")
            print(f"  Contrast:        {contrast:.1f}x ({bio_status})")
            print(f"  Observed peak:   {r['observed_peak']} ADC")
            print(f"  Sample delay:    {r['sample_delay_us']} us")
            print(f"  Calibrated:      {'Yes' if r['calibrated'] else 'No'}")
            print(f"  State:           {'Underwater' if r['underwater'] else 'Surface'}")
            print(f"  Time in state:   {r['time_in_state']}s")
            print(f"  Surface level:   {level_name}")
        except Exception as e:
            print(f"SWS Status FAILED: {e}")

    if args.swstst:
        try:
            if args.swstst == 'start':
                # ANSI color codes for surface level indicators
                _LEVEL_COLORS = {
                    0: '\033[0m',       # reset (no detection)
                    1: '\033[92m',      # bright green  - L1 instant drop 25%
                    2: '\033[32m',      # green         - L2 2 consec drops 5%
                    3: '\033[93m',      # yellow        - L3 trend MA3
                    4: '\033[33m',      # orange        - L4 drop vs baseline
                    5: '\033[91m',      # red           - L5 cumul backup
                }
                _RESET = '\033[0m'
                sample_count = [0]
                prev_level = [0]

                def _on_swsst_sample(r):
                    sample_count[0] += 1
                    state = 'Underwater' if r['underwater'] else 'Surface'
                    level = r['surface_level']
                    contrast = r['contrast_x10'] / 10

                    # Surface level with color
                    if level > 0:
                        color = _LEVEL_COLORS.get(level, _RESET)
                        level_str = f"{color}L{level}{_RESET}"
                    else:
                        level_str = '--'

                    # Contrast quality indicator
                    if r['contrast_x10'] >= 80:
                        ctr_str = f"{contrast:.1f}x"
                    elif r['contrast_x10'] >= 30:
                        ctr_str = f"\033[93m{contrast:.1f}x{_RESET}"
                    else:
                        ctr_str = f"\033[91m{contrast:.1f}x{_RESET}"

                    # Event marker when surface_level transitions 0 -> N
                    event = ''
                    if level > 0 and prev_level[0] == 0:
                        color = _LEVEL_COLORS.get(level, _RESET)
                        event = f"  {color}<<< L{level} DETECTED >>>{_RESET}"
                    prev_level[0] = level

                    print(f"[{sample_count[0]:>4}] raw={r['raw_adc']:>5}  filt={r['filtered_adc']:>5}  "
                          f"air={r['air']:>5}  water={r['water']:>5}  "
                          f"thr={r['threshold']:>5}  hyst={r['hysteresis']:>5}  "
                          f"cal={'Y' if r['calibrated'] else 'N'}  {state:<10}  "
                          f"t={r['time_in_state']}s  lvl={level_str}  ctr={ctr_str}  "
                          f"peak={r['observed_peak']:>5}  delay={r['sample_delay_us']}us"
                          f"{event}")

                print("SWS Test: STREAMING (Ctrl+C to stop)")
                print("-" * 110)
                dev.swstst_stream(_on_swsst_sample)
                print("SWS Test: STOPPED")
            else:
                running = dev.swstst(start=False)
                print(f"SWS Test: {'RUNNING' if running else 'STOPPED'}")
        except Exception as e:
            print(f"SWS Test FAILED: {e}")

    if args.swscal:
        try:
            if args.swscal == 'start':
                print("SWS Guided Calibration: starting...")
                print("  Phase 1: Place device in AIR (green LED flashing)")
                dev.swscal(start=True)
                print("  Waiting for calibration result...")
                r = dev.wait_swscal_result(timeout=120.0)
                if r['status'] == 1:
                    print(f"  Calibration SUCCESS — air={r['air']} water={r['water']}")
                elif r['status'] == 2:
                    print(f"  Calibration FAILED")
                elif r['status'] == 3:
                    print(f"  Calibration CANCELLED")
                else:
                    print(f"  Status: {r['status_name']} air={r['air']} water={r['water']}")
            else:
                dev.swscal(start=False)
                print("SWS Guided Calibration: cancelled")
        except Exception as e:
            print(f"SWS Calibration FAILED: {e}")

    if args.rtcr:
        from datetime import datetime, timezone
        try:
            status = dev._dte.statr(['RTC_CURRENT_TIME'])
            ts = int(status.get('RTC_CURRENT_TIME', 0))
            if ts > 0:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                print(f"Device RTC: {dt.strftime('%d/%m/%Y %H:%M:%S')} UTC (unix: {ts})")
            else:
                print(f"Device RTC: not set (0)")
        except Exception as e:
            print(f"RTC read FAILED: {e}")

    if args.rtcw or args.rtcw_timestamp is not None:
        from datetime import datetime, timezone
        try:
            ts = args.rtcw_timestamp
            dev.rtcw(ts)
            actual = ts if ts is not None else int(__import__('time').time())
            dt = datetime.fromtimestamp(actual, tz=timezone.utc)
            print(f"RTC set to: {dt.isoformat()} (unix: {actual})")
        except Exception as e:
            print(f"RTCW FAILED: {e}")

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
