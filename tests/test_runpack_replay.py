"""Reproducibility is an assurance property: a RunPack must replay bit-for-bit."""
import os
import tempfile

from rsi_foundry.core.orchestrator import Foundry
from rsi_foundry.core.runpack_exporter import (load_runpack, save_runpack,
                                               verify_replay)


def test_runs_are_deterministic():
    a = Foundry({"seed": 5, "cycles": 5}).run()
    b = Foundry({"seed": 5, "cycles": 5}).run()
    assert a["lineage_root"] == b["lineage_root"]
    assert a["successor_registry"]["champion"] == b["successor_registry"]["champion"]


def test_different_seeds_explore_differently():
    a = Foundry({"seed": 1, "cycles": 5}).run()
    b = Foundry({"seed": 2, "cycles": 5}).run()
    assert a["lineage_root"] != b["lineage_root"]


def test_runpack_roundtrip_and_replay():
    rp = Foundry({"seed": 7, "cycles": 5}).run()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "rp.yaml")
        save_runpack(rp, path)
        loaded = load_runpack(path)
        assert loaded["lineage_root"] == rp["lineage_root"]
        v = verify_replay(path)
        assert v["reproducible"] is True
