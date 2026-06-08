"""Minimal end-to-end recursive cycle.

Runs a short governed session, prints the champion trajectory, verifies the
RunPack replays deterministically, and writes a dashboard. This is the smallest
complete demonstration of the loop:

    generate -> sandbox -> quorum -> causal -> novelty -> HALF-LIFE -> promote
    -> learn (SEAL / Best-Attribute / ADAS) -> coevolve (POET) -> repeat.

    python examples/run_minimal_cycle.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rsi_foundry.core.orchestrator import Foundry
from rsi_foundry.core.runpack_exporter import save_runpack, verify_replay
from rsi_foundry.dashboard.render import save_dashboard


def main() -> None:
    foundry = Foundry({"seed": 7, "cycles": 8})
    rp = foundry.run()

    reg = rp["successor_registry"]
    seed_fit = rp["cycles"][0]["capability_index"]
    print(f"seed capability     : {seed_fit}")
    print(f"champion fitness    : {reg['champion_fitness']}")
    print(f"governed promotions : {reg['n_promotions']}")
    print(f"HALF-LIFE final     : {rp['half_life']['snapshot']['state']}")
    print(f"assurance / debt    : {rp['half_life']['snapshot']['cumulative_assurance']}"
          f" / {rp['half_life']['snapshot']['debt']}")
    print(f"QD coverage / score : {rp['qd_archive']['coverage']} / {rp['qd_archive']['qd_score']}")
    print(f"SEAL examples mined : {rp['seal_training']['n_examples']}")

    out = save_runpack(rp, "runpacks/minimal_cycle.runpack.yaml")
    print(f"\nRunPack -> {out}")

    v = verify_replay(out)
    print(f"reproducible replay : {v['reproducible']} (lineage root {v['replay_root'][:16]}…)")

    dash = save_dashboard(rp, "runpacks/minimal_cycle.dashboard.html")
    print(f"Dashboard -> {dash}")


if __name__ == "__main__":
    main()
