"""Structural smoke for the pre-registered experiment apparatus.

These assert the apparatus *runs and emits the registered schema* — they assert
NOTHING about which arm wins or whether the gate holds against the LLM arm.
Those are results, produced by a cold session, not by this suite.
"""

from __future__ import annotations

from experiments.adaptive_adversary.attack_harness import run_battery
from experiments.trait_quarantine.harness import ARMS, run_experiment


def test_adversary_battery_runs_and_control_holds():
    # Apparatus contract only: the honest control is promoted and the static
    # memorizer is not. (This is the gate's F1/F2 contract on the attack lane,
    # not the headline adaptive-adversary result, which is the LLM arm.)
    report = run_battery(rounds=1)
    assert report["verdict"] in {"HOLD", "BREAK"}  # not VACUOUS
    r0 = report["detail"][0]["outcomes"]
    assert r0["honest_sorter"]["promoted"] is True
    assert r0["memorize_public"]["promoted"] is False


def test_trait_apparatus_runs_all_three_arms_and_emits_schema():
    report = run_experiment(seeds=[1000], budget=24)
    for arm in ARMS:
        assert len(report["arms"][arm]) == 1
        row = report["arms"][arm][0]
        assert {"m1", "promotions", "m2_false"} <= row.keys()
        assert isinstance(row["m1"], int) and row["m1"] >= 1


def test_seed_isolation_constants_are_disjoint():
    # Held-out / release seeds must never collide with search seeds (§7).
    from experiments.trait_quarantine.harness import (
        HELD_OUT_SEED,
        RELEASE_SEED_BASE,
        SEARCH_SEEDS,
    )

    assert HELD_OUT_SEED not in SEARCH_SEEDS
    assert all(s < RELEASE_SEED_BASE for s in SEARCH_SEEDS)
