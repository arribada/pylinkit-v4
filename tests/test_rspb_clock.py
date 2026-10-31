"""PWP07 LAST_TIME_SYNC / PWP08 WAKEUP_PERIOD_MEASURED_MS (firmware 2026-10).

What these tests guarantee:
  - PARMR parses with PWP08 (RSPB) and without it (LinkIt V4), new keys at the
    end of the answer, unknown trailing keys skipped; length field in upper-case hex.
  - Zero values read as "jamais" / "pas encore mesurée" / "non bornée".
  - PWP08 deviation from PWP04, the 10 % calibration boundary, and the RSPB
    clock accuracy ±(10 s + t × age of PWP07), t = 2 % calibrated else 5 %.
  - TPL mismatch and CloudLocate MEASC12 warnings fire only when they should.
  - PWP07/PWP08 never reach the device: not in any PARMW frame, not in the
    --parmr export, ignored by --parmw import.
"""
import pytest

import pylinkit.__main__ as cli
from pylinkit import Tracker, clock
from pylinkit.enums import WAKEUP_PERIOD_HELP, LAST_KNOWN_RTC_HELP
from pylinkit.protocol.dte_commands import DTECommands
from pylinkit.protocol.dte_params import DTEParamMap
from pylinkit.utils import OrderedRawConfigParser

NOW = 1_800_000_000                  # 15/01/2027 08:00:00 UTC
SYNC = NOW - (2 * 3600 + 13 * 60)    # 2 h 13 min earlier: 05:47:00 UTC


def _frame(cmd, payload):
    return f'$O;{cmd}#{len(payload):03X};{payload}\r'.encode('ascii')


class _FakeTransport:
    """Replies to each command from a {cmd: payload} table; records every frame."""

    def __init__(self, payloads=None):
        self.sent = []
        self._payloads = payloads or {}
        self._sub = None

    def subscribe_data(self, cb):
        self._sub = cb

    def send_data(self, data):
        self.sent.append(data)
        cmd = data.decode('ascii')[1:].split('#', 1)[0]
        self._sub(_frame(cmd, self._payloads.get(cmd, '')))


# PARMR answers as the firmware sends them: new keys appended at the end.
RSPB_PARMR = ('IDT02=RSPB,IDT03=v4.2.0,PWP01=0,PWP02=12,PWP03=24,PWP04=3600,PWP05=0,'
              f'PWP06={NOW - 600},GNP45=2,GNP46=0,PWP07={SYNC},PWP08=3600123')
LINKIT_PARMR = f'IDT02=LinkIt V4,IDT03=v4.2.0,PWP06={NOW - 600},GNP45=2,GNP46=0,PWP07=0'


def _parmr(payload):
    return DTECommands(_FakeTransport({'PARMR': payload})).parmr()


def _rspb(**overrides):
    params = {'DEVICE_MODEL': 'RSPB', 'WAKEUP_PERIOD': 3600, 'LAST_TIME_SYNC': SYNC,
              'WAKEUP_PERIOD_MEASURED_MS': 3600123}
    params.update(overrides)
    return params


# --- parsing ----------------------------------------------------------------

def test_parmr_rspb_with_pwp08():
    params = _parmr(RSPB_PARMR)
    assert params['LAST_TIME_SYNC'] == SYNC
    assert params['WAKEUP_PERIOD_MEASURED_MS'] == 3600123
    assert params['WAKEUP_PERIOD'] == 3600
    assert clock.is_rspb(params)


def test_parmr_linkit_without_pwp08():
    params = _parmr(LINKIT_PARMR)
    assert params['LAST_TIME_SYNC'] == 0
    assert 'WAKEUP_PERIOD_MEASURED_MS' not in params
    assert not clock.is_rspb(params)
    assert clock.format_wakeup_period_measured(params) is None
    assert clock.format_clock_accuracy(params, NOW) is None
    assert clock.report(params, NOW) == [("Dernière synchro d'heure fiable (PWP07)", "jamais")]
    assert clock.warnings(params) == []


def test_parmr_skips_unknown_trailing_keys():
    params = _parmr(RSPB_PARMR + ',XYZ99=7')
    assert 'XYZ99' not in params
    assert params['WAKEUP_PERIOD_MEASURED_MS'] == 3600123


def test_parmr_old_firmware_without_pwp07():
    params = _parmr('IDT02=RSPB,PWP04=3600')
    assert clock.report(params, NOW) == []
    assert clock.format_last_time_sync(params, NOW) is None


def test_length_field_is_upper_case_hex():
    tx = _FakeTransport({'PARMR': 'PWP07=0'})
    DTECommands(tx).parmr(['LAST_TIME_SYNC', 'WAKEUP_PERIOD_MEASURED_MS'])
    assert tx.sent == [b'$PARMR#00B;PWP07,PWP08\r']


@pytest.mark.parametrize("params,expected", [
    ({'DEVICE_MODEL': 'RSPB'}, True),
    ({'DEVICE_MODEL': 'LinkIt V4'}, False),
    ({'DEVICE_MODEL': 'LinkIt V4', 'WAKEUP_PERIOD': 3600}, False),   # IDT02 decides
    ({'WAKEUP_PERIOD': 3600}, True),                                  # fallback: RSPB-only key
    ({'LAST_TIME_SYNC': 0}, False),
])
def test_is_rspb(params, expected):
    assert clock.is_rspb(params) is expected


# --- PWP07 ------------------------------------------------------------------

def test_last_time_sync_date_and_age():
    assert clock.format_last_time_sync({'LAST_TIME_SYNC': SYNC}, NOW) == \
        "15/01/2027 05:47:00 UTC (il y a 2 h 13 min)"


def test_last_time_sync_zero_is_never():
    assert clock.format_last_time_sync({'LAST_TIME_SYNC': 0}, NOW) == "jamais"


@pytest.mark.parametrize("seconds,text", [
    (0, "0 s"), (45, "45 s"), (60, "1 min"), (312, "5 min 12 s"),
    (3600, "1 h"), (7980, "2 h 13 min"), (86400, "1 j"), (3 * 86400 + 4 * 3600 + 59, "3 j 4 h"),
])
def test_format_duration(seconds, text):
    assert clock.format_duration(seconds) == text


# --- PWP08 ------------------------------------------------------------------

def test_wakeup_period_measured_zero():
    params = _rspb(WAKEUP_PERIOD_MEASURED_MS=0)
    assert clock.format_wakeup_period_measured(params) == "pas encore mesurée"
    assert clock.wakeup_period_deviation_pct(params) is None
    assert not clock.is_tpl_calibrated(params)
    assert clock.warnings(params) == []


def test_wakeup_period_measured_three_decimals_and_deviation():
    params = _rspb(WAKEUP_PERIOD_MEASURED_MS=3636000)
    assert clock.wakeup_period_deviation_pct(params) == pytest.approx(1.0)
    assert clock.format_wakeup_period_measured(params) == "3636.000 s (écart +1.00 % / PWP04 = 3600 s)"
    assert clock.format_wakeup_period_measured(_rspb()) == "3600.123 s (écart +0.00 % / PWP04 = 3600 s)"


def test_wakeup_period_deviation_without_pwp04():
    params = _rspb(WAKEUP_PERIOD=0)
    assert clock.wakeup_period_deviation_pct(params) is None
    assert clock.format_wakeup_period_measured(params) == \
        "3600.123 s (écart non calculable : PWP04 inconnu ou nul)"
    assert clock.warnings(params) == []


@pytest.mark.parametrize("measured_ms,calibrated", [
    (3600123, True),
    (3960000, True),     # +10 % exactly: still calibrated
    (3240000, True),     # -10 % exactly
    (3960001, False),
    (3239999, False),
    (4000000, False),    # +11.1 %
])
def test_tpl_calibration_boundary(measured_ms, calibrated):
    params = _rspb(WAKEUP_PERIOD_MEASURED_MS=measured_ms)
    assert clock.is_tpl_calibrated(params) is calibrated
    mismatch = clock.TPL_PERIOD_MISMATCH_WARNING in clock.warnings(params)
    assert mismatch is (not calibrated)


def test_tpl_mismatch_warning_text():
    assert clock.warnings(_rspb(WAKEUP_PERIOD_MEASURED_MS=4000000)) == [
        "La résistance TPL5111 montée ne donne pas WAKEUP_PERIOD : vérifier PWP04"]


# --- clock accuracy -----------------------------------------------------------

def test_accuracy_calibrated_uses_2_percent():
    params = _rspb()
    assert clock.clock_accuracy_s(params, NOW) == pytest.approx(10 + 0.02 * 7980)
    assert clock.format_clock_accuracy(params, NOW) == \
        "±2 min 50 s (10 s + 2 % × 2 h 13 min, PWP08 calibrée)"


@pytest.mark.parametrize("measured_ms", [0, 4000000])
def test_accuracy_uncalibrated_uses_5_percent(measured_ms):
    params = _rspb(WAKEUP_PERIOD_MEASURED_MS=measured_ms)
    assert clock.clock_accuracy_s(params, NOW) == 10 + 0.05 * 7980
    assert clock.format_clock_accuracy(params, NOW) == \
        "±6 min 49 s (10 s + 5 % × 2 h 13 min, PWP08 non calibrée)"


def test_accuracy_without_pwp08_uses_5_percent():
    params = _rspb()
    del params['WAKEUP_PERIOD_MEASURED_MS']
    assert clock.clock_accuracy_s(params, NOW) == 10 + 0.05 * 7980


def test_accuracy_unbounded_when_never_synced():
    params = _rspb(LAST_TIME_SYNC=0)
    assert clock.clock_accuracy_s(params, NOW) is None
    assert clock.format_clock_accuracy(params, NOW) == "non bornée"


def test_accuracy_right_after_sync_is_base_error():
    assert clock.clock_accuracy_s(_rspb(LAST_TIME_SYNC=NOW), NOW) == 10


def test_accuracy_only_on_rspb():
    params = {'DEVICE_MODEL': 'LinkIt V4', 'LAST_TIME_SYNC': SYNC}
    assert clock.format_clock_accuracy(params, NOW) is None
    assert [label for label, _ in clock.report(params, NOW)] == ["Dernière synchro d'heure fiable (PWP07)"]


def test_report_rspb_lines():
    assert clock.report(_rspb(), NOW) == [
        ("Dernière synchro d'heure fiable (PWP07)", "15/01/2027 05:47:00 UTC (il y a 2 h 13 min)"),
        ("Période TPL mesurée (PWP08)", "3600.123 s (écart +0.00 % / PWP04 = 3600 s)"),
        ("Précision estimée de l'horloge", "±2 min 50 s (10 s + 2 % × 2 h 13 min, PWP08 calibrée)"),
    ]


# --- CloudLocate MEASC12 on RSPB ----------------------------------------------

@pytest.mark.parametrize("model,fastloc,fmt,expected", [
    ('RSPB', 2, 0, True),
    ('RSPB', '2', '0', True),       # values from a config file are strings
    ('RSPB', 2, 1, False),          # MEAS20: insensitive to the clock error
    ('RSPB', 1, 0, False),          # not CloudLocate
    ('LinkIt V4', 2, 0, False),     # LinkIt keeps a real RTC
])
def test_cloudlocate_measc12_warning(model, fastloc, fmt, expected):
    params = {'DEVICE_MODEL': model, 'GNSS_FASTLOC_MODE': fastloc, 'GNSS_CLOUDLOCATE_FORMAT': fmt}
    assert (clock.CLOUDLOCATE_MEASC12_WARNING in clock.warnings(params)) is expected


def test_cloudlocate_warning_from_parmr():
    assert clock.warnings(_parmr(RSPB_PARMR)) == [clock.CLOUDLOCATE_MEASC12_WARNING]
    assert clock.warnings(_parmr(LINKIT_PARMR)) == []


# --- PARMW pre-flight ---------------------------------------------------------

def test_preflight_wakeup_period_change_note():
    notes, warns = clock.parmw_preflight({'DEVICE_MODEL': 'RSPB', 'WAKEUP_PERIOD': 3600},
                                         {'WAKEUP_PERIOD': '7200'})
    assert notes == [f"WAKEUP_PERIOD (PWP04) 3600 s -> 7200 s. {WAKEUP_PERIOD_HELP}"]
    assert warns == []


def test_preflight_same_wakeup_period_is_silent():
    assert clock.parmw_preflight({'WAKEUP_PERIOD': 3600}, {'WAKEUP_PERIOD': '3600'}) == ([], [])


def test_preflight_cloudlocate_on_effective_values():
    device = {'DEVICE_MODEL': 'RSPB', 'GNSS_FASTLOC_MODE': 2, 'GNSS_CLOUDLOCATE_FORMAT': 1}
    assert clock.parmw_preflight(device, {'GNSS_CLOUDLOCATE_FORMAT': '0'})[1] == \
        [clock.CLOUDLOCATE_MEASC12_WARNING]
    assert clock.parmw_preflight(device, {'GNSS_CLOUDLOCATE_FORMAT': '1'})[1] == []


def test_preflight_board_identity_beats_file():
    # A file exported from an RSPB pushed onto a LinkIt V4: no RSPB warning.
    new = {'DEVICE_MODEL': 'RSPB', 'GNSS_FASTLOC_MODE': '2', 'GNSS_CLOUDLOCATE_FORMAT': '0'}
    assert clock.parmw_preflight({'DEVICE_MODEL': 'LinkIt V4'}, new) == ([], [])
    # Board unreadable: fall back on the file.
    assert clock.parmw_preflight({}, new)[1] == [clock.CLOUDLOCATE_MEASC12_WARNING]


# --- never written to the device ---------------------------------------------

@pytest.mark.parametrize("p", ['LAST_TIME_SYNC', 'PWP07', 'WAKEUP_PERIOD_MEASURED_MS', 'PWP08'])
def test_pwp07_pwp08_are_read_only(p):
    assert DTEParamMap.is_read_only(p)


def test_parmw_never_sends_pwp07_pwp08():
    tx = _FakeTransport()
    out = DTECommands(tx).parmw({'LAST_TIME_SYNC': SYNC, 'WAKEUP_PERIOD_MEASURED_MS': 3600123,
                                 'WAKEUP_PERIOD': 3600})
    assert out == {'WAKEUP_PERIOD': True}
    assert tx.sent == [b'$PARMW#00A;PWP04=3600\r']


def test_parmw_with_only_read_only_sends_nothing():
    tx = _FakeTransport()
    assert DTECommands(tx).parmw({'LAST_TIME_SYNC': 0, 'WAKEUP_PERIOD_MEASURED_MS': 0}) == {}
    assert tx.sent == []


def test_parmw_plan_excludes_read_only():
    plan = DTECommands(_FakeTransport()).parmw_plan({'LAST_TIME_SYNC': 0, 'GNSS_ENABLE': 1})
    assert plan == [{'GNSS_ENABLE': 1}]


def test_encoder_refuses_read_only_frame():
    cmds = DTECommands(_FakeTransport())
    with pytest.raises(ValueError, match='LAST_TIME_SYNC'):
        cmds._encode_command('PARMW', param_values={'LAST_TIME_SYNC': 0})
    with pytest.raises(ValueError, match='WAKEUP_PERIOD_MEASURED_MS'):
        cmds._encode_command('PARMW', param_values={'GNSS_ENABLE': 1, 'WAKEUP_PERIOD_MEASURED_MS': 0})


def test_tracker_set_never_sends_pwp07_pwp08():
    tx = _FakeTransport()
    t = Tracker.__new__(Tracker)
    t._dte = DTECommands(tx)
    t.set(_rspb())
    assert all(b'PWP07' not in f and b'PWP08' not in f for f in tx.sent)
    assert any(b'PWP04=3600' in f for f in tx.sent)


def test_export_excludes_pwp07_pwp08():
    export = DTEParamMap.exportable(_parmr(RSPB_PARMR))
    assert 'LAST_TIME_SYNC' not in export
    assert 'WAKEUP_PERIOD_MEASURED_MS' not in export
    assert export['WAKEUP_PERIOD'] == 3600


def test_import_ignores_pwp07_pwp08():
    cfg = OrderedRawConfigParser()
    cfg.optionxform = lambda option: option
    cfg.read_string('[PARAM]\nLAST_TIME_SYNC = 123\nWAKEUP_PERIOD_MEASURED_MS = 3600000\n'
                    'WAKEUP_PERIOD = 3600\n')
    params = dict(cfg['PARAM'])
    assert DTEParamMap.read_only_names(params) == ['LAST_TIME_SYNC', 'WAKEUP_PERIOD_MEASURED_MS']
    assert DTEParamMap.writable_only(params) == {'WAKEUP_PERIOD': '3600'}


# --- CLI ------------------------------------------------------------------------

class _CliTracker:
    """Stands in for Tracker in pylinkit.__main__.main(): the real read and
    push logic over a dict, on a firmware whose PARML lists ``supported``
    (every key pylinkit knows when None)."""
    params = {}
    supported = None
    written = None

    READ_CHUNK = Tracker.READ_CHUNK
    read = Tracker.read
    plan_push = Tracker.plan_push
    push = Tracker.push

    def __init__(self, *args, **kwargs):
        self._dte = self

    def sync(self):
        pass

    def get(self):
        return dict(self.params)

    def parml(self):
        if self.supported is None:
            return frozenset(key for _, key, _ in DTEParamMap.param_map)
        return frozenset(self.supported)

    def parmr(self, names):
        return {n: self.params[n] for n in names if n in self.params}

    statr = parmr

    def set(self, params, **kwargs):
        type(self).written = dict(params)
        type(self).params = {**type(self).params, **params}
        return {n: True for n in params}


def _run_cli(monkeypatch, argv, params, supported=None):
    _CliTracker.params = params
    _CliTracker.supported = supported
    _CliTracker.written = None
    monkeypatch.setattr(cli, 'Tracker', _CliTracker)
    monkeypatch.setattr('sys.argv', ['pylinkit', '--transport', 'usb', '--port', 'COM0'] + argv)
    cli.main()


def test_cli_parmr_export_and_display(monkeypatch, tmp_path, capsys):
    out = tmp_path / 'export.cfg'
    _run_cli(monkeypatch, ['--parmr', str(out)], _parmr(RSPB_PARMR))
    text = out.read_text()
    assert 'LAST_TIME_SYNC' not in text and 'WAKEUP_PERIOD_MEASURED_MS' not in text
    assert 'WAKEUP_PERIOD = 3600' in text
    shown = capsys.readouterr().out
    assert "Dernière synchro d'heure fiable (PWP07)" in shown
    assert "Période TPL mesurée (PWP08)" in shown
    assert "Précision estimée de l'horloge" in shown
    assert "Période pour laquelle la résistance du TPL5111" in shown
    assert LAST_KNOWN_RTC_HELP in shown
    assert f"AVERTISSEMENT : {clock.CLOUDLOCATE_MEASC12_WARNING}" in shown


def test_cli_parmr_linkit_without_pwp08(monkeypatch, tmp_path, capsys):
    _run_cli(monkeypatch, ['--parmr', str(tmp_path / 'export.cfg')], _parmr(LINKIT_PARMR))
    shown = capsys.readouterr().out
    assert "Dernière synchro d'heure fiable (PWP07) : jamais" in shown
    assert "PWP08" not in shown
    assert "Précision estimée" not in shown
    assert "AVERTISSEMENT" not in shown


def test_cli_parmw_round_trip_drops_pwp07_pwp08(monkeypatch, tmp_path, capsys):
    cfg = tmp_path / 'in.cfg'
    cfg.write_text('[PARAM]\nLAST_TIME_SYNC = 123\nWAKEUP_PERIOD_MEASURED_MS = 3600000\n'
                   'WAKEUP_PERIOD = 7200\nGNSS_ENABLE = 1\n')
    _run_cli(monkeypatch, ['--parmw', str(cfg)], {'DEVICE_MODEL': 'RSPB', 'WAKEUP_PERIOD': 3600})
    assert _CliTracker.written == {'WAKEUP_PERIOD': '7200', 'GNSS_ENABLE': '1'}
    shown = capsys.readouterr().out
    assert "Ignored read-only param(s) from file (2): LAST_TIME_SYNC, WAKEUP_PERIOD_MEASURED_MS" in shown
    assert "NOTE: WAKEUP_PERIOD (PWP04) 3600 s -> 7200 s." in shown
