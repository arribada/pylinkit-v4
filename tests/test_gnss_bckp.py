"""Unit tests for the GNSSBCKP command.

Covers:
  - GNSSBCKP wire-format matches firmware spec ($GNSSBCKP#<len_hex>;<duration>\r)
  - Client-side range validation [0, 86400]
  - Round-trip dispatch via DTECommands using a fake transport that captures
    the command bytes and feeds back a synthesized $O / $N response.

Note: the GNSSBCKP *command* is still a live entry in the firmware
command_map, but the backup-cell *params* GNP47/GNP48/GNP49
(BACKUP_CELL_CHARGE_*) were removed (firmware reserved slots 223/224/225,
superseded by GNSS_DEEP_IDLE_AFTER_OFF_S/GNP52) and must no longer appear in
the DTE param map.
"""
import pytest

from pylinkit import Tracker
from pylinkit.protocol.dte_params import DTEParamMap
from pylinkit.protocol.dte_commands import DTECommands


# --- param map --------------------------------------------------------------

@pytest.mark.parametrize("long_key,short_key", [
    ("BACKUP_CELL_CHARGE_INTERVAL",        "GNP47"),
    ("BACKUP_CELL_CHARGE_DURATION",        "GNP48"),
    ("BACKUP_CELL_CHARGE_ONLY_SUBMERGED",  "GNP49"),
])
def test_backup_cell_params_removed(long_key, short_key):
    # Firmware reserved these slots; pylinkit must not offer keys the device
    # now rejects (PARAM_KEY_NOT_FOUND).
    with pytest.raises(Exception):
        DTEParamMap.param_to_key(long_key)
    with pytest.raises(Exception):
        DTEParamMap.key_to_param(short_key)


# --- fake transport for wire-format inspection ------------------------------

class _FakeTransport:
    """Minimal DataTransport stand-in. Captures send_data() bytes, returns a
    canned response via the subscribed callback the next time send_data()
    fires."""
    def __init__(self):
        self.last_sent = None
        self._sub = None
        self._next_response = b'$O;GNSSBCKP#000;\r'

    def subscribe_data(self, cb):
        self._sub = cb

    def queue_response(self, raw):
        self._next_response = raw

    def send_data(self, data):
        self.last_sent = data
        # firmware flushes a response asynchronously; emulate it inline
        if self._sub is not None:
            self._sub(self._next_response)


# --- gnssbckp wire format ---------------------------------------------------

def test_gnssbckp_start_wire_format():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    cmds.gnssbckp(600)
    # firmware spec: "$GNSSBCKP#003;600\r" (len is hex of payload byte length)
    assert tx.last_sent == b'$GNSSBCKP#003;600\r'


def test_gnssbckp_stop_wire_format():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    cmds.gnssbckp(0)
    assert tx.last_sent == b'$GNSSBCKP#001;0\r'


@pytest.mark.parametrize("d,payload,length_hex", [
    (1,     b'1',      b'001'),
    (10,    b'10',     b'002'),
    (300,   b'300',    b'003'),
    (3600,  b'3600',   b'004'),
    (86400, b'86400',  b'005'),
])
def test_gnssbckp_length_prefix_is_hex(d, payload, length_hex):
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    cmds.gnssbckp(d)
    assert tx.last_sent == b'$GNSSBCKP#' + length_hex + b';' + payload + b'\r'


# --- gnssbckp client-side validation ---------------------------------------

@pytest.mark.parametrize("bad", [-1, -10, 86401, 100000])
def test_gnssbckp_rejects_oob_before_send(bad):
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    with pytest.raises(ValueError, match='out of range'):
        cmds.gnssbckp(bad)
    assert tx.last_sent is None  # nothing went on the wire


def test_gnssbckp_accepts_string_int():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    cmds.gnssbckp("600")
    assert tx.last_sent == b'$GNSSBCKP#003;600\r'


# --- gnssbckp error response surfacing -------------------------------------

@pytest.mark.parametrize("err_code,fragment", [
    (5, 'error 5'),   # INCORRECT_DATA — "GPS device not detected" upstream
    (6, 'error 6'),   # PARAM_KEY_UNRECOGNISED — old fw without GNSSBCKP support
    (7, 'error 7'),   # VALUE_OUT_OF_RANGE — "duration must be 0..86400"
])
def test_gnssbckp_propagates_firmware_error(err_code, fragment):
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    tx.queue_response(f'$N;GNSSBCKP#001;{err_code}\r'.encode('ascii'))
    with pytest.raises(Exception) as exc_info:
        cmds.gnssbckp(600)
    assert fragment in str(exc_info.value)


# --- success path & boundary acceptance -------------------------------------

def test_gnssbckp_success_returns_none():
    # Default fake response is $O;GNSSBCKP#000;\r — call must complete without
    # raising and return None (DTE methods are void on success).
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    assert cmds.gnssbckp(600) is None


@pytest.mark.parametrize("d", [0, 1, 86400])
def test_gnssbckp_accepts_boundary_values(d):
    # Both range endpoints must encode and send (the OOB tests cover what's
    # just past). 0 is the canonical stop signal.
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    cmds.gnssbckp(d)
    assert tx.last_sent is not None
    assert f';{d}\r'.encode('ascii') in tx.last_sent


# --- Tracker wrapper --------------------------------------------------------

class _StubDTE:
    """Records gnssbckp calls without touching the wire."""
    def __init__(self):
        self.calls = []

    def gnssbckp(self, duration_s):
        self.calls.append(duration_s)


def test_tracker_gnssbckp_delegates_to_dte():
    # Bypass Tracker.__init__ (which would try to open a real transport).
    # The wrapper is one line; this test exists so a refactor that renames
    # or removes _dte.gnssbckp fails loudly at the public API surface.
    t = Tracker.__new__(Tracker)
    t._dte = _StubDTE()
    t.gnssbckp(600)
    t.gnssbckp(0)
    assert t._dte.calls == [600, 0]
