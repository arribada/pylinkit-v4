"""DBP02 SYSTEM_LOG_LEVEL and the RunCam camera (CAP06/CAP07, CAT00-CAT06,
CAMTST), firmware v4.2.1.

What these tests guarantee:
  - PARML decides everything. A key the firmware does not list is never read,
    never written, never sent: a template carrying DBP02 is applied to an older
    firmware without it, DBP02 reported as ignored, and no frame mentions it.
  - A targeted read keeps only the keys asked for (up to v4.1.10 an unknown key
    makes the firmware answer with the whole configuration).
  - Values are checked before sending: DBP02 0..3, CAP06 0..2, CAP07 0..4, text
    at most 128 characters. A refused value is never sent.
  - Every written key is read back and compared.
  - A reply is matched to its request by command name: an answer under another
    name (firmware before v4.2.0 answering an unknown command) is ignored.
  - Camera mode: CAT00 when listed, else CAP01 = BUTTON, else no camera. CAMTST
    is only ever sent when CAT00 = 2; its answer parses, extra fields ignored.
  - SMDTST asks for confirmation (it transmits).
"""
import pytest

import pylinkit.__main__ as cli
from pylinkit import Tracker, camera, CommandUnavailable
from pylinkit.enums import system_log_level_label, NOT_ON_THIS_FIRMWARE
from pylinkit.protocol.dte_commands import DTECommands
from pylinkit.protocol.dte_params import DTEParamMap


def _ok(cmd, payload=''):
    return f'$O;{cmd}#{len(payload):03X};{payload}\r'


class FakeFirmware:
    """The tag at the other end of the DTE link.

    ``values``: {key: wire value}, in table order; its keys are the PARML list.
    ``legacy_read``: a targeted read with a key it does not know returns the
    whole configuration (v4.0.0 to v4.1.10) instead of the known ones.
    ``camtst``: CAMTST answer payload; None = command unknown, no answer.
    ``stray``: frames sent before every answer (another command's answer).
    ``stores``: {key: value} the firmware stores whatever is written."""

    def __init__(self, values, legacy_read=False, camtst=None, stray=(), stores=None):
        self.values = dict(values)
        self.legacy_read = legacy_read
        self.camtst = camtst
        self.stray = list(stray)
        self.stores = stores or {}
        self.sent = []
        self._sub = None

    def subscribe_data(self, cb):
        self._sub = cb

    def send_data(self, data):
        frame = data.decode('ascii')
        self.sent.append(frame)
        cmd, rest = frame[1:].split('#', 1)
        payload = rest.split(';', 1)[1].rstrip('\r')
        answer = self._answer(cmd, payload)
        if answer is None:
            return
        for stray in self.stray:
            self._sub(stray.encode('ascii'))
        self._sub(answer.encode('ascii'))

    def _pairs(self, keys):
        return ','.join(f'{k}={self.values[k]}' for k in keys)

    def _answer(self, cmd, payload):
        if cmd == 'PARML':
            return _ok('PARML', ','.join(self.values))
        if cmd in ('PARMR', 'STATR'):
            if not payload:
                letter = 'P' if cmd == 'PARMR' else 'T'
                return _ok(cmd, self._pairs(k for k in self.values if k[2] == letter))
            asked = payload.split(',')
            known = [k for k in asked if k in self.values]
            if len(known) < len(asked) and self.legacy_read:
                return _ok(cmd, self._pairs(self.values))
            if not known:
                return f'$N;{cmd}#001;6\r'
            return _ok(cmd, self._pairs(known))
        if cmd == 'PARMW':
            rejected = []
            for item in payload.split(','):
                key, value = item.split('=', 1)
                if key not in self.values:
                    rejected.append(key)
                else:
                    self.values[key] = self.stores.get(key, value)
            if rejected:
                keys = ','.join(rejected)
                return f'$N;PARMW#{len(keys):03X};{keys}\r'
            return _ok('PARMW')
        if cmd == 'CAMTST' and self.camtst is not None:
            return _ok('CAMTST', self.camtst)
        return None


def _tracker(fw):
    """A Tracker over ``fw``, without a real transport."""
    t = Tracker.__new__(Tracker)
    t._dte = DTECommands(fw)
    t._parml = None
    t._map = {}
    return t


def _sent_keys(fw):
    return ' '.join(fw.sent)


# Firmware v4.2.0 (published): no DBP02, camera BUTTON without CAT00.
FW_420 = {'IDT03': 'v4.2.0', 'GNP01': '1', 'LBP02': '15', 'DBP01': '3',
          'CAP01': '1', 'CAP02': '0', 'CAP03': '0', 'CAP04': '60', 'CAP05': '0',
          'LBP13': '0'}
# Firmware v4.2.1 camera UART build: DBP02, CAP06/CAP07, CAT00-CAT06 at the end.
FW_421_UART = {**FW_420, 'IDT03': 'v4.2.0-205-g1ac5d894', 'CAP06': '0', 'CAP07': '0',
               'CAT01': '0', 'CAT02': '14300', 'CAT03': '15079', 'CAT04': '3600',
               'CAT05': '4', 'CAT06': '119', 'CAT00': '2', 'DBP02': '3'}
FW_421_BUTTON = {**FW_420, 'CAT00': '1', 'DBP02': '3'}

CAMTST_REAL = '0,119,6141,15079,1079,1,1,1,1,35095,4'


# --- Parameter map --------------------------------------------------------------

def test_dbp02_is_a_writable_uint():
    assert DTEParamMap.param_to_key('SYSTEM_LOG_LEVEL') == 'DBP02'
    assert not DTEParamMap.is_read_only('DBP02')
    assert DTEParamMap.decode('DBP02', '2') == 2


@pytest.mark.parametrize('value', [0, 1, 2, 3, '2'])
def test_dbp02_accepts_0_to_3(value):
    assert DTEParamMap.encode('SYSTEM_LOG_LEVEL', value) == str(int(value))


@pytest.mark.parametrize('name,value', [
    ('SYSTEM_LOG_LEVEL', 4), ('SYSTEM_LOG_LEVEL', -1), ('SYSTEM_LOG_LEVEL', 'WARN'),
    ('CAM_REC_MODE', 3), ('CAM_RESOLUTION', 5), ('PROFILE_NAME', 'x' * 129),
])
def test_out_of_range_values_are_refused_by_the_tool(name, value):
    assert name in DTEParamMap.invalid_values({name: value})


def test_text_of_128_characters_is_accepted():
    assert DTEParamMap.invalid_values({'PROFILE_NAME': 'x' * 128}) == {}


def test_camera_status_keys_are_read_only_and_kept_out_of_exports():
    for key in ('CAT00', 'CAT01', 'CAT02', 'CAT03', 'CAT04', 'CAT05', 'CAT06'):
        assert DTEParamMap.is_read_only(key)
        assert DTEParamMap.is_status_key(key)
    assert not DTEParamMap.is_read_only('CAP06') and not DTEParamMap.is_read_only('CAP07')
    export = DTEParamMap.exportable({'CAM_CONTROL_MODE': 2, 'CAM_LAST_OUTCOME': 0,
                                     'CAM_SD_FREE_MB': 1, 'CAM_RESOLUTION': 4})
    assert export == {'CAM_CONTROL_MODE': 2, 'CAM_RESOLUTION': 4}


@pytest.mark.parametrize('value,label', [(0, 'OFF'), (1, 'ERROR'), (2, 'WARN'),
                                         (3, 'INFO'), (7, 'inconnu (7)')])
def test_system_log_level_label(value, label):
    assert system_log_level_label(value) == label


# --- Reads ------------------------------------------------------------------------

def test_full_read_with_and_without_dbp02():
    old = DTECommands(FakeFirmware(FW_420)).parmr()
    assert 'SYSTEM_LOG_LEVEL' not in old and old['GNSS_ENABLE'] == 1
    new = DTECommands(FakeFirmware({**FW_420, 'DBP02': '2', 'ZZP99': '7'})).parmr()
    assert new['SYSTEM_LOG_LEVEL'] == 2          # unknown ZZP99 ignored, no error


def test_targeted_read_keeps_only_the_keys_asked_for():
    # v4.1.x: an unknown key in a targeted read returns the whole configuration.
    fw = FakeFirmware(FW_420, legacy_read=True)
    assert DTECommands(fw).parmr(['SYSTEM_LOG_LEVEL', 'GNSS_ENABLE']) == {'GNSS_ENABLE': 1}


def test_tracker_never_asks_for_a_key_parml_does_not_list():
    fw = FakeFirmware(FW_420)
    t = _tracker(fw)
    assert t.read(['SYSTEM_LOG_LEVEL', 'CAM_CONTROL_MODE', 'GNSS_ENABLE']) == {'GNSS_ENABLE': 1}
    assert 'DBP02' not in _sent_keys(fw) and 'CAT00' not in _sent_keys(fw)


def test_status_keys_are_read_with_statr():
    fw = FakeFirmware(FW_421_UART)
    assert _tracker(fw).read(['CAM_CONTROL_MODE', 'SYSTEM_LOG_LEVEL']) == {
        'CAM_CONTROL_MODE': 2, 'SYSTEM_LOG_LEVEL': 3}
    assert '$STATR#005;CAT00\r' in fw.sent and '$PARMR#005;DBP02\r' in fw.sent


def test_answer_under_another_command_name_is_ignored():
    fw = FakeFirmware(FW_420, stray=[_ok('PARMW')])
    assert DTECommands(fw).parmr(['GNSS_ENABLE']) == {'GNSS_ENABLE': 1}


# --- Writes (template push) -------------------------------------------------------

TEMPLATE = {'GNSS_ENABLE': '0', 'LB_THRESHOLD': '20', 'SYSTEM_LOG_LEVEL': '2'}


def test_push_to_a_firmware_without_dbp02_applies_the_rest():
    fw = FakeFirmware(FW_420)
    result = _tracker(fw).push(TEMPLATE)
    assert result.unsupported == ['SYSTEM_LOG_LEVEL']
    assert sorted(result.written) == ['GNSS_ENABLE', 'LB_THRESHOLD']
    assert result.ok                              # not a failure
    assert fw.values['GNP01'] == '0' and fw.values['LBP02'] == '20'
    assert 'DBP02' not in _sent_keys(fw)          # no DBP02 frame at all


def test_push_dbp02_to_a_firmware_that_lists_it():
    fw = FakeFirmware(FW_421_UART)
    result = _tracker(fw).push({'SYSTEM_LOG_LEVEL': 2})
    assert result.ok and result.written == ['SYSTEM_LOG_LEVEL']
    assert '$PARMW#007;DBP02=2\r' in fw.sent
    assert '$PARMR#005;DBP02\r' in fw.sent        # read back
    assert fw.values['DBP02'] == '2'


def test_out_of_range_dbp02_is_never_sent():
    fw = FakeFirmware(FW_421_UART)
    result = _tracker(fw).push({'SYSTEM_LOG_LEVEL': 4, 'GNSS_ENABLE': 0})
    assert list(result.invalid) == ['SYSTEM_LOG_LEVEL'] and not result.ok
    assert result.written == ['GNSS_ENABLE']
    assert 'DBP02' not in _sent_keys(fw) and fw.values['DBP02'] == '3'


def test_read_back_reports_a_value_the_firmware_did_not_keep():
    fw = FakeFirmware(FW_421_UART, stores={'DBP02': '3'})
    result = _tracker(fw).push({'SYSTEM_LOG_LEVEL': 2})
    assert result.mismatched == {'SYSTEM_LOG_LEVEL': (2, 3)} and not result.ok


def test_parmw_refuses_invalid_values_before_sending_anything():
    fw = FakeFirmware(FW_421_UART)
    with pytest.raises(ValueError, match='DBP02'):
        DTECommands(fw).parmw({'GNSS_ENABLE': 0, 'SYSTEM_LOG_LEVEL': 9})
    assert fw.sent == []


def test_read_only_and_unsupported_camera_keys_are_never_sent():
    fw = FakeFirmware(FW_420)
    result = _tracker(fw).push({'CAM_CONTROL_MODE': 2, 'CAM_RESOLUTION': 4, 'CAM_ENABLE': 1})
    assert result.read_only == ['CAM_CONTROL_MODE']
    assert result.unsupported == ['CAM_RESOLUTION']
    assert result.written == ['CAM_ENABLE']
    assert 'CAT00' not in _sent_keys(fw) and 'CAP07' not in _sent_keys(fw)


# --- Camera mode --------------------------------------------------------------------

@pytest.mark.parametrize('keys,cat00,mode', [
    ({'GNP01'}, None, None),                       # no camera
    ({'CAP01', 'CAP05'}, None, camera.BUTTON),     # v4.0.0..v4.2.0 with a camera
    ({'CAP01', 'CAT00'}, 1, camera.BUTTON),
    ({'CAP01', 'CAP06', 'CAT00'}, 2, camera.UART),
    ({'CAP01', 'CAT00'}, None, camera.BUTTON),     # CAT00 listed, unreadable
    ({'CAP01', 'CAT00'}, 9, camera.BUTTON),        # code unknown to this version
])
def test_camera_mode(keys, cat00, mode):
    assert camera.camera_mode(keys, cat00) == mode


@pytest.mark.parametrize('values,mode', [
    (FW_420, camera.BUTTON), (FW_421_BUTTON, camera.BUTTON), (FW_421_UART, camera.UART),
    ({'GNP01': '1'}, None),
])
def test_tracker_camera_mode(values, mode):
    fw = FakeFirmware(values)
    assert _tracker(fw).camera_mode() == mode
    if 'CAT00' not in values:
        assert 'CAT00' not in _sent_keys(fw)      # never probed


# --- CAMTST -----------------------------------------------------------------------

def test_parse_camtst_real_answer():
    r = camera.parse_camtst(CAMTST_REAL)
    assert r == {'status': 0, 'features': 119, 'free_mb': 6141, 'total_mb': 15079,
                 'remaining_s': 1079, 'recording': 1, 'stopped': 1, 'clock': 1,
                 'starts': 1, 'duration_ms': 35095, 'resolution': 4}
    assert camera.format_sd_card(r['free_mb'], r['total_mb']) == '6,1 Go libres sur 15,1 Go'
    assert camera.format_rec_time(r['remaining_s']) == '18 min'
    assert camera.verdict(r['status']) == camera.OK


def test_parse_camtst_ignores_extra_fields_and_unread_card():
    r = camera.parse_camtst('2,119,-1,-1,-1,0,0,0,0,1200,0,42,43')
    assert r['free_mb'] is None and r['remaining_s'] is None
    assert camera.verdict(r['status']) == camera.ERROR
    assert camera.resolution_label(r['resolution']) == 'inconnue'


def test_camtst_on_a_uart_build():
    fw = FakeFirmware(FW_421_UART, camtst=CAMTST_REAL, stray=[_ok('SWSST', '1,2,3')])
    r = _tracker(fw).camtst()
    assert fw.sent[-1] == '$CAMTST#000;\r' and r['duration_ms'] == 35095


@pytest.mark.parametrize('values', [FW_420, FW_421_BUTTON, {'GNP01': '1'}])
def test_camtst_is_never_sent_outside_a_uart_build(values):
    fw = FakeFirmware(values, camtst=CAMTST_REAL)
    with pytest.raises(CommandUnavailable):
        _tracker(fw).camtst()
    assert 'CAMTST' not in _sent_keys(fw)


def test_camtst_answer_under_another_name_is_no_answer():
    # Before v4.2.0 an unknown command gets another command's answer.
    class Old(FakeFirmware):
        def _answer(self, cmd, payload):
            return _ok('PARMR', 'GNP01=1') if cmd == 'CAMTST' else super()._answer(cmd, payload)
    with pytest.raises(TimeoutError):
        DTECommands(Old(FW_420)).camtst(timeout=0.2)


def test_camtst_busy_and_starts_warning():
    r = camera.parse_camtst('7,0,-1,-1,-1,0,0,0,0,0,0')
    assert camera.status_name(r['status']) == 'BUSY' and camera.verdict(7) == camera.WARN
    r = camera.parse_camtst('0,119,6141,15079,1079,1,1,0,2,41000,4')
    assert camera.camtst_warnings(r) == [camera.STARTS_MISMATCH_WARNING]


def test_camtst_firmware_error():
    class NoCamera(FakeFirmware):
        def _answer(self, cmd, payload):
            return '$N;CAMTST#001;5\r' if cmd == 'CAMTST' else super()._answer(cmd, payload)
    with pytest.raises(Exception, match='CAMTST - error 5'):
        DTECommands(NoCamera(FW_421_UART)).camtst()


def test_last_session_rows():
    params = {'CAM_LAST_OUTCOME': 0, 'CAM_SD_FREE_MB': 14300, 'CAM_SD_TOTAL_MB': 15079,
              'CAM_REC_TIME_LEFT_S': 4294967295, 'CAM_RESOLUTION_READ': 4}
    rows = dict(camera.last_session_rows(params))
    assert rows['Carte SD'] == '14,3 Go libres sur 15,1 Go'
    assert "Temps d'enregistrement restant" not in rows   # unread
    assert rows['Résolution'] == '720P60'
    assert camera.last_session_rows({'CAM_LAST_OUTCOME': 255}) == [
        ('Issue', 'aucune session encore')]
    assert camera.last_session_rows({}) == []


# --- CLI --------------------------------------------------------------------------

def _run_cli(monkeypatch, argv, fw, stdin=None):
    monkeypatch.setattr(cli, 'Tracker', lambda *a, **k: _tracker(fw))
    monkeypatch.setattr('sys.argv', ['pylinkit', '--transport', 'usb', '--port', 'COM0'] + argv)
    if stdin is not None:
        monkeypatch.setattr('builtins.input', stdin)
    cli.main()


def test_cli_parmr_shows_the_log_level(monkeypatch, tmp_path, capsys):
    _run_cli(monkeypatch, ['--parmr', str(tmp_path / 'x.cfg')], FakeFirmware(FW_421_UART))
    shown = capsys.readouterr().out
    assert 'Journal flash (DBP02) : INFO' in shown
    assert 'Caméra (mode UART) :' in shown and '14,3 Go libres sur 15,1 Go' in shown
    assert 'CAM_LAST_OUTCOME' not in (tmp_path / 'x.cfg').read_text()


def test_cli_parmr_on_a_published_firmware(monkeypatch, tmp_path, capsys):
    fw = FakeFirmware(FW_420)
    _run_cli(monkeypatch, ['--parmr', str(tmp_path / 'x.cfg')], fw)
    shown = capsys.readouterr().out
    assert f'Journal flash (DBP02) : {NOT_ON_THIS_FIRMWARE}' in shown
    assert 'Caméra : mode BUTTON' in shown
    assert 'DBP02' not in _sent_keys(fw) and 'CAT00' not in _sent_keys(fw)


def test_cli_parmw_template_on_a_published_firmware(monkeypatch, tmp_path, capsys):
    cfg = tmp_path / 'turtle.cfg'
    cfg.write_text('[PARAM]\nGNSS_ENABLE = 0\nSYSTEM_LOG_LEVEL = 2\n')
    fw = FakeFirmware(FW_420)
    _run_cli(monkeypatch, ['--parmw', str(cfg)], fw)
    shown = capsys.readouterr().out
    assert 'SYSTEM_LOG_LEVEL (DBP02) ignoré : firmware sans ce paramètre' in shown
    assert 'Parameters written OK (1): GNSS_ENABLE' in shown
    assert 'Relecture : 1 paramètre(s) conforme(s).' in shown
    assert 'FAILED' not in shown and 'REJECTED' not in shown
    assert 'DBP02' not in _sent_keys(fw)


def test_cli_parmw_refuses_an_out_of_range_value(monkeypatch, tmp_path, capsys):
    cfg = tmp_path / 'bad.cfg'
    cfg.write_text('[PARAM]\nSYSTEM_LOG_LEVEL = 4\n')
    fw = FakeFirmware(FW_421_UART)
    _run_cli(monkeypatch, ['--parmw', str(cfg)], fw)
    assert "REFUSÉ par l'outil, non envoyé : SYSTEM_LOG_LEVEL" in capsys.readouterr().out
    assert not any(f.startswith('$PARMW') for f in fw.sent)


def test_cli_camtst_on_a_button_build_sends_nothing(monkeypatch, capsys):
    fw = FakeFirmware(FW_421_BUTTON, camtst=CAMTST_REAL)
    _run_cli(monkeypatch, ['--camtst'], fw)
    assert 'CAMTST non disponible (caméra en mode BUTTON)' in capsys.readouterr().out
    assert 'CAMTST' not in _sent_keys(fw)


def test_cli_camtst_on_a_uart_build(monkeypatch, capsys):
    _run_cli(monkeypatch, ['--camtst'], FakeFirmware(FW_421_UART, camtst=CAMTST_REAL))
    shown = capsys.readouterr().out
    assert 'OK : Enregistrement et arrêt vus sur la carte' in shown
    assert '6,1 Go libres sur 15,1 Go' in shown and '18 min' in shown


def test_cli_smdtst_needs_confirmation(monkeypatch, capsys):
    def no_tty(prompt):
        raise EOFError
    fw = FakeFirmware(FW_420)
    _run_cli(monkeypatch, ['--smdtst'], fw, stdin=no_tty)
    assert 'SMDTST annulé' in capsys.readouterr().out
    assert not any(f.startswith('$SMDTST') for f in fw.sent)
