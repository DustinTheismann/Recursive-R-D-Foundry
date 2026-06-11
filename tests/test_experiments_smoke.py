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
        assert {"m1", "promotions", "m2_false", "evals_used"} <= row.keys()
        assert isinstance(row["m1"], int) and row["m1"] >= 1


def test_budget_conservation_enforced_and_equal_across_arms():
    # Audit Finding 1 (A1): every arm consumes EXACTLY the budget, so GATED's
    # confirmation evals cannot grant it free compute. Enforced in code.
    budget = 24
    report = run_experiment(seeds=[1000], budget=budget)
    for arm in ARMS:
        assert report["arms"][arm][0]["evals_used"] == budget


def test_trait_bandwidth_symmetry_constant():
    # Audit Finding 2 (A2): GATED's refuted-trait channels equal NAIVE's tracked
    # channels -- arms differ only in flow, not in what counts as a trait.
    from experiments.trait_quarantine.harness import TRAIT_GENES

    assert set(TRAIT_GENES) == {"w_residual", "new_bin_bias", "w_remaining"}


def test_stats_decision_rule_is_mechanical():
    # stats.py IS prereg §6: synthetic report where GATED is faster than DISCARD
    # and NAIVE is less safe -> outcome 1, with no analyst judgment.
    from experiments.trait_quarantine import stats

    def rows(m1, m2f, promo, b=600):
        return [{"seed": 1000 + i, "m1": m1, "m2_false": m2f, "promotions": promo,
                 "evals_used": b} for i in range(30)]

    synthetic = {
        "budget": 600, "prereg_version": "1.1",
        "arms": {
            "discard": rows(500, 0, 4),
            "naive": rows(100, 3, 4),    # fast but unsafe (3/4 false)
            "gated": rows(120, 0, 4),    # nearly as fast, safe
        },
    }
    verdict = stats.decide(synthetic)
    assert verdict["budget_conserved_all_arms"] is True
    assert verdict["H1"] and verdict["H2"] and verdict["H3"]
    assert verdict["outcome"].startswith("1")


def test_seed_isolation_constants_are_disjoint():
    # Held-out / release seeds must never collide with search seeds (§7).
    from experiments.trait_quarantine.harness import (
        HELD_OUT_SEED,
        RELEASE_SEED_BASE,
        SEARCH_SEEDS,
    )

    assert HELD_OUT_SEED not in SEARCH_SEEDS
    assert all(s < RELEASE_SEED_BASE for s in SEARCH_SEEDS)
