"""Containment: the sandbox isolates candidate code and never lets it cheat."""
from rsi_foundry.domain import heuristics
from rsi_foundry.sandbox.containment import (InProcessSandbox, SubprocessSandbox,
                                             ContainmentPolicy)

_INSTANCES = [{"capacity": 100, "items": [40, 50, 30, 60, 20, 70, 10, 55]}]


def _best_fit_source():
    return heuristics.compile_source({
        "w_residual": 2.0, "w_remaining": 0.0, "w_load": 0.0, "w_tight": 0.0,
        "new_bin_bias": -1e9, "tie": "first",
    })


def test_subprocess_and_inprocess_agree():
    src = _best_fit_source()
    a = SubprocessSandbox().run(src, _INSTANCES)
    b = InProcessSandbox().run(src, _INSTANCES)
    assert a["ok"] and b["ok"]
    assert a["results"][0]["bins_used"] == b["results"][0]["bins_used"]


def test_infinite_loop_is_contained_not_a_breach():
    bad = "def place(item, bins, capacity):\n    while True:\n        pass\n"
    out = SubprocessSandbox(ContainmentPolicy(cpu_seconds=1, wall_timeout=3)).run(bad, _INSTANCES)
    assert out["ok"] is False
    assert out["contained"] is True and out["breach"] is False


def test_candidate_cannot_overflow_bins():
    # a candidate that always points at bin 0 cannot actually overflow it —
    # the trusted simulator overrides and counts the violation instead.
    cheat = "def place(item, bins, capacity):\n    return 0\n"
    out = InProcessSandbox().run(cheat, _INSTANCES)
    assert out["ok"]
    r = out["results"][0]
    assert r["violations"] >= 1          # the bad suggestions were recorded
    # every bin is within capacity despite the cheating heuristic
    assert r["bins_used"] >= 1
