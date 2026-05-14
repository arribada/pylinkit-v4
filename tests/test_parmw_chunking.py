"""Unit tests for PARMW chunking.

Why chunking exists:
  ~220 params in a single PARMW exhausts the firmware FreeRTOS heap
  (newlib sscanf + per-param substr() allocates aggressively). We slice
  the batch into chunks of N (default 20) and send sequentially.

What these tests guarantee:
  - Small batches still send in 1 chunk.
  - Batches larger than chunk_size split correctly.
  - Order on the wire is sorted by short DTE key (LRPxx, GNPxx, ...) so
    LoRa creds + LORA_NJM land in the same chunk.
  - Per-chunk timeout triggers retry up to N times.
  - Partial reject ($N;PARMW#...;keys) is recorded but does NOT abort
    subsequent chunks.
  - Global firmware error ($N;PARMW#...;<errno>) DOES abort the run; all
    pending chunks' params come back as False.
  - parmw_plan() returns the same chunk layout without sending.
  - Progress callback fires once per chunk before send, with correct args.
"""
import pytest

from pylinkit import Tracker
from pylinkit.protocol.dte_commands import DTECommands
from pylinkit.protocol.dte_params import DTEParamMap
from pylinkit.protocol.dte_types import UINT, BOOLEAN


def _safe_long_names(n):
    """Pick `n` long names whose codec accepts value=0 cleanly (UINT/BOOLEAN).
    DEPTHPILE and SAMPLINGPERIOD reject 0, so we exclude them to keep fixtures
    simple."""
    out = []
    for long_name, _, codec in DTEParamMap.param_map:
        if codec in (UINT, BOOLEAN):
            out.append(long_name)
            if len(out) == n:
                return out
    raise RuntimeError(f'param_map has fewer than {n} UINT/BOOLEAN entries')


# --- shared fake transport --------------------------------------------------

class _FakeTransport:
    """Captures every PARMW frame sent and replies from a scripted queue.

    If ``responses`` runs out, an OK response is returned. ``timeout_first_n``
    swallows the first N sends (no callback) — used to exercise retry logic.
    """

    def __init__(self, responses=None, timeout_first_n=0):
        self.sent = []
        self._responses = list(responses or [])
        self._timeouts_remaining = timeout_first_n
        self._sub = None

    def subscribe_data(self, cb):
        self._sub = cb

    def send_data(self, data):
        self.sent.append(data)
        if self._timeouts_remaining > 0:
            # simulate a wireless drop — no firmware response at all
            self._timeouts_remaining -= 1
            return
        if self._responses:
            resp = self._responses.pop(0)
        else:
            resp = b'$O;PARMW#000;\r'
        if self._sub is not None:
            self._sub(resp)


# Use small, real param names so DTEParamMap.param_to_key works.
# (DEPTH PILE family has 3 short keys; we mix a few families for ordering tests.)
SMALL_VALID_PARAMS = {
    "GNSS_ENABLE":       1,
    "BATT_SOC":          50,
    "ARGOS_DEPTH_PILE":  4,
    "LORA_NJM":          1,
}


# --- plan() — pure ordering & slicing ---------------------------------------

def test_plan_small_batch_is_one_chunk():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    chunks = cmds.parmw_plan(SMALL_VALID_PARAMS, chunk_size=20)
    assert len(chunks) == 1
    assert set(chunks[0]) == set(SMALL_VALID_PARAMS)


def test_plan_splits_into_chunks_of_size_n():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    # 47 params -> 3 chunks at chunk_size=20 (20 + 20 + 7). plan() is pure
    # name-shuffling, so the codec doesn't matter here.
    pool = {n: 0 for n in _safe_long_names(47)}
    chunks = cmds.parmw_plan(pool, chunk_size=20)
    assert [len(c) for c in chunks] == [20, 20, 7]
    flat = [k for c in chunks for k in c]
    assert sorted(flat) == sorted(pool.keys())


def test_plan_sorts_by_short_key():
    # LRP01..LRP07 must all land in the same chunk, in lexicographic order
    # by short key — this is what keeps LORA_NJM (LRP07) with its creds.
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    inputs = {
        "LORA_NJM":     1,           # LRP07 — passed FIRST in dict
        "LORA_DEVEUI":  "AA",        # LRP01
        "LORA_APPSKEY": "BB",        # LRP05
        "LORA_APPKEY":  "CC",        # LRP03
    }
    [chunk] = cmds.parmw_plan(inputs, chunk_size=20)
    ordered_names = list(chunk.keys())
    assert ordered_names == ["LORA_DEVEUI", "LORA_APPKEY", "LORA_APPSKEY", "LORA_NJM"]


def test_plan_rejects_chunk_size_zero():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    with pytest.raises(ValueError):
        cmds.parmw_plan(SMALL_VALID_PARAMS, chunk_size=0)


def test_plan_empty_input_yields_no_chunks():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    assert cmds.parmw_plan({}, chunk_size=20) == []


# --- parmw() — single-chunk happy path --------------------------------------

def test_parmw_small_batch_single_send():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    out = cmds.parmw(SMALL_VALID_PARAMS, chunk_size=20)
    assert all(out.values())
    assert set(out) == set(SMALL_VALID_PARAMS)
    assert len(tx.sent) == 1   # one chunk -> one PARMW frame on the wire


def test_parmw_empty_input_sends_nothing():
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    assert cmds.parmw({}) == {}
    assert tx.sent == []


# --- parmw() — multi-chunk happy path ---------------------------------------

def test_parmw_large_batch_splits_and_succeeds():
    big = {n: 0 for n in _safe_long_names(50)}
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    out = cmds.parmw(big, chunk_size=20)
    assert all(out.values())
    assert set(out) == set(big)
    assert len(tx.sent) == 3   # 50 / 20 -> 3 chunks (20 + 20 + 10)


# --- parmw() — progress callback --------------------------------------------

def test_parmw_progress_fires_once_per_chunk_with_correct_args():
    big = {n: 0 for n in _safe_long_names(25)}
    calls = []
    tx = _FakeTransport()
    cmds = DTECommands(tx)
    cmds.parmw(big, chunk_size=20, progress=lambda i, t, s: calls.append((i, t, s)))
    # 25 params at chunk_size=20 -> chunks of 20 + 5
    assert calls == [(1, 2, 20), (2, 2, 5)]


# --- parmw() — partial reject keeps going -----------------------------------

def test_parmw_partial_reject_does_not_abort_subsequent_chunks():
    # Firmware rejects ARP16 in whichever chunk it lands in. Subsequent
    # chunks must still go out, and the final dict must mark ARGOS_DEPTH_PILE
    # as False while every other param succeeds.
    inputs = {n: 0 for n in _safe_long_names(21)}
    inputs["ARGOS_DEPTH_PILE"] = 4
    tmp_cmds = DTECommands(_FakeTransport())
    plan = tmp_cmds.parmw_plan(inputs, chunk_size=20)
    arp16_chunk = next(i for i, c in enumerate(plan) if "ARGOS_DEPTH_PILE" in c)

    responses = []
    for i in range(len(plan)):
        if i == arp16_chunk:
            responses.append(b'$N;PARMW#005;ARP16\r')
        else:
            responses.append(b'$O;PARMW#000;\r')

    tx = _FakeTransport(responses=responses)
    cmds = DTECommands(tx)
    out = cmds.parmw(inputs, chunk_size=20)
    assert out["ARGOS_DEPTH_PILE"] is False
    other_failures = [k for k, v in out.items() if not v and k != "ARGOS_DEPTH_PILE"]
    assert other_failures == []
    assert len(tx.sent) == len(plan)   # every chunk went out


# --- parmw() — global error aborts the run ----------------------------------

def test_parmw_global_error_aborts_remaining_chunks():
    # Chunk 1 returns a numeric error (firmware-level), chunk 2 is never sent.
    # The result dict must contain every input key, with False for any param
    # not confirmed-OK.
    inputs = {n: 0 for n in _safe_long_names(30)}
    tx = _FakeTransport(responses=[
        b'$N;PARMW#001;5\r',       # chunk 1 — global error code 5
    ])
    cmds = DTECommands(tx)
    out = cmds.parmw(inputs, chunk_size=20)
    assert all(v is False for v in out.values())
    assert set(out) == set(inputs)
    assert len(tx.sent) == 1   # chunk 2 was NOT sent


# --- parmw() — retry on timeout ---------------------------------------------

def test_parmw_retries_on_timeout_then_succeeds():
    # First send times out (no callback), second send gets a response. The
    # final result must report success and the wire must show 2 sends for the
    # single chunk.
    tx = _FakeTransport(timeout_first_n=1)   # drop first send, OK after
    cmds = DTECommands(tx)
    out = cmds.parmw(SMALL_VALID_PARAMS, chunk_size=20, chunk_timeout=0.05, max_retries=3)
    assert all(out.values())
    assert len(tx.sent) == 2   # 1 timeout + 1 successful retry


def test_parmw_gives_up_after_max_retries():
    # All 3 attempts time out -> chunk fails -> all its params are False.
    tx = _FakeTransport(timeout_first_n=10)
    cmds = DTECommands(tx)
    out = cmds.parmw(SMALL_VALID_PARAMS, chunk_size=20, chunk_timeout=0.05, max_retries=3)
    assert all(v is False for v in out.values())
    assert len(tx.sent) == 3   # exactly max_retries attempts


# --- Tracker wrapper --------------------------------------------------------

class _StubDTE:
    def __init__(self):
        self.last_call = None
        self.last_plan = None

    def parmw(self, param_values, chunk_size, chunk_timeout, max_retries, progress):
        self.last_call = {
            'param_values': param_values,
            'chunk_size': chunk_size,
            'chunk_timeout': chunk_timeout,
            'max_retries': max_retries,
            'progress': progress,
        }
        return {n: True for n in param_values}

    def parmw_plan(self, param_values, chunk_size):
        self.last_plan = {'param_values': param_values, 'chunk_size': chunk_size}
        return [{'X': 1}]


def test_tracker_set_passes_through_chunking_kwargs():
    t = Tracker.__new__(Tracker)
    t._dte = _StubDTE()
    progress = lambda i, n, s: None
    t.set({"GNSS_ENABLE": 1}, chunk_size=15, chunk_timeout=2.0, max_retries=2, progress=progress)
    call = t._dte.last_call
    assert call['chunk_size'] == 15
    assert call['chunk_timeout'] == 2.0
    assert call['max_retries'] == 2
    assert call['progress'] is progress


def test_tracker_plan_set_passes_through_chunk_size():
    t = Tracker.__new__(Tracker)
    t._dte = _StubDTE()
    t.plan_set({"GNSS_ENABLE": 1}, chunk_size=10)
    assert t._dte.last_plan == {'param_values': {"GNSS_ENABLE": 1}, 'chunk_size': 10}
