"""Three-arm trait-quarantine apparatus (move 2) — prereg v1.1.

DISCARD / NAIVE / GATED differ ONLY in trait flow (PREREGISTRATION §3); the gate
itself is the real one (`promotion.evaluate` + `causal_gate` + `EvidenceGate`),
not a reimplementation. This module is the apparatus; it PRODUCES NO HEADLINE
RESULT here. `--smoke` proves all three arms execute and emit the metric schema
on a tiny budget. The registered run (K=30 seeds, B=600) requires the v1.1
re-audit and is done by a separate cold session (see RUNBOOK.md), which records
RESULTS.md.

v1.1 amendments implemented here (see PREREGISTRATION `## Amendments`):

* **A1 (budget conservation, in code).** Every evaluation on the search or
  confirmation distributions is charged against B through :class:`BudgetMeter`;
  the loop terminates exactly at B and the consumed total is recorded per arm
  (`evals_used`). GATED's confirmation evals are charged; the old carrier eval
  is eliminated (the confirmation result itself registers the trait). Excluded
  identically across arms: the seed champion's initial evaluations and held-out
  *measurement* evaluations of governed promotions.
* **A2 (trait-bandwidth symmetry).** GATED harvests the same three gene
  channels from refuted candidates that NAIVE's ``observe`` tracks
  (:data:`TRAIT_GENES`); arms differ only in flow.

Metric schema per (arm, seed): {"m1": int, "promotions": int, "m2_false": int,
"evals_used": int}.
  m1  = first charged-budget index whose governed promotion survives the
        held-out re-eval (right-censored at B).
  m2  = m2_false / promotions  (computed downstream over seeds).
"""

from __future__ import annotations

import random
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any

from fek.kernel import Kernel

from rsi_foundry.connectors.benchmark_adapters import LocalBinPackBenchmark
from rsi_foundry.core.types import Candidate, EvalResult
from rsi_foundry.domain import binpack, heuristics
from rsi_foundry.evals.harness import Harness
from rsi_foundry.governance import causal_gate, promotion
from rsi_foundry.governance.evidence_gate import EvidenceGate
from rsi_foundry.governance.half_life import HalfLifeController
from rsi_foundry.governance.promotion import PromotionPolicy
from rsi_foundry.loops.best_attribute_registry import BestAttributeRegistry
from rsi_foundry.proposers.base import build_candidate
from rsi_foundry.proposers.mutation_proposer import MutationProposer
from rsi_foundry.sandbox.containment import ContainmentPolicy, make_sandbox

# Locked seeds (PREREGISTRATION §4, §5). Reserved ranges must never enter search.
SEARCH_SEEDS = list(range(1000, 1030))     # K = 30
HELD_OUT_SEED = 999_983                     # final generalization check
RELEASE_SEED_BASE = 888_000                 # fresh seeds for gated trait release
N_OFFSPRING = 8
POOL_K = 6
DEFAULT_BUDGET = 600
ASSURANCE_PER_CHECK = 0.004  # mirrors orchestrator DEFAULTS (half-life accrual)
ARMS = ("discard", "naive", "gated")

# A2: the single symmetry constant. NAIVE's BestAttributeRegistry.observe tracks
# exactly these three gene channels; GATED's refuted-trait harvest uses the SAME
# list, so the arms cannot drift apart in trait bandwidth.
TRAIT_GENES = ("w_residual", "new_bin_bias", "w_remaining")


class BudgetExhausted(Exception):
    pass


@dataclass
class BudgetMeter:
    """A1: in-code budget conservation. Every charged eval goes through here."""

    limit: int
    used: int = 0

    def can(self, n: int = 1) -> bool:
        return self.used + n <= self.limit

    def charge(self, n: int = 1) -> None:
        if not self.can(n):
            raise BudgetExhausted(f"budget exceeded: used={self.used} +{n} > limit={self.limit}")
        self.used += n


@dataclass
class ArmResult:
    arm: str
    seed: int
    m1: int
    promotions: int = 0
    m2_false: int = 0
    evals_used: int = 0
    detail: dict[str, Any] = field(default_factory=dict)


def _benchmark(seed: int, floor: float = 0.5):
    sandbox = make_sandbox("in_process", ContainmentPolicy(cpu_seconds=2, mem_mb=256, wall_timeout=8.0))
    bench = LocalBinPackBenchmark(binpack.starter_envs(), random.Random(seed), per_env=3)
    return Harness(bench, sandbox, floor)


def _eval_charged(meter: BudgetMeter, h: Harness, cand: Candidate) -> EvalResult:
    """A1: the ONLY way the search/confirmation distributions are evaluated."""

    meter.charge(1)
    return h.evaluate(cand.cid, cand.source)


def _eval_measurement(h: Harness, cand: Candidate) -> EvalResult:
    """Held-out measurement evals: uncharged, identical trigger in every arm."""

    return h.evaluate(cand.cid, cand.source)


def run_arm(arm: str, seed: int, budget: int = DEFAULT_BUDGET) -> ArmResult:
    """Run one arm on one search seed. The gate is identical across arms."""

    assert arm in ARMS, arm
    assert seed != HELD_OUT_SEED and seed < RELEASE_SEED_BASE, "search/holdout leakage"
    rng = random.Random(seed)
    meter = BudgetMeter(limit=budget)
    harness = _benchmark(seed)
    fast = _benchmark(seed)            # ablation harness (same distribution)
    held = _benchmark(HELD_OUT_SEED)   # generalization check (unseen during search)
    proposer = MutationProposer()
    policy = PromotionPolicy()
    policy.novelty_min = 0.0
    half_life = HalfLifeController(safety_factor=2.0)
    gate = EvidenceGate(Kernel(tempfile.mkdtemp(prefix=f"tq-{arm}-{seed}-")))
    best_attr = BestAttributeRegistry() if arm in ("naive", "gated") else None
    pen: list[tuple[str, Any]] = []  # (gene, value) awaiting confirmation (gated)

    # Seed champion: shared constant across arms, excluded from B (A1).
    champ = build_candidate(heuristics.seed_genome(), [], "seed", 0)
    champ_res = harness.evaluate(champ.cid, champ.source)
    champ_ho = _eval_measurement(held, champ)

    # Exploration is DECOUPLED from promotion (QD-style): a top-K parent pool
    # drives the search so it can climb while the gate promotes rarely. The
    # champion is the promotion baseline and advances only on a governed
    # promotion.
    results: dict[str, EvalResult] = {champ.cid: champ_res}
    pool: list[Candidate] = [champ]

    m1 = budget
    promotions = 0
    m2_false = 0
    confirmations = 0
    released = 0
    gen = 0

    while meter.used < budget:
        gen += 1
        # Re-anchor half-life to the current champion each generation and accrue
        # assurance from contained-valid evals (mirrors orchestrator.py:187/234).
        half_life.set_baseline_capability(champ_res.fitness)
        contained_valid = 0
        children = proposer.propose(pool, rng, N_OFFSPRING, None, gen)
        for child in children:
            if not meter.can(1):
                break
            # trait inflow: graft a registered best-gene (naive + gated)
            if best_attr is not None and best_attr.best:
                grafted = best_attr.graft(child.genome, rng)
                if grafted != child.genome:
                    child = build_candidate(grafted, child.parents, child.origin, gen)
            res = _eval_charged(meter, harness, child)
            results[child.cid] = res
            if res.valid and res.quorum.get("contained"):
                contained_valid += 1
            pool.append(child)
            pool = sorted(pool, key=lambda c: results[c.cid].fitness, reverse=True)[:POOL_K]

            parent_res = results.get(child.parents[0]) if child.parents else champ_res
            causal = causal_gate.evaluate_causal(child, res, parent_res or champ_res, fast,
                                                 min_ablation=policy.causal_min_ablation,
                                                 min_task_frac=policy.causal_min_task_frac)
            report = promotion.evaluate(child, res, champ_res, parent_res, 1.0,
                                        causal, half_life, policy, child.cid)
            report = gate.govern(child, res, report)

            if report.promoted:
                promotions += 1
                child_ho = _eval_measurement(held, child)  # uncharged (A1)
                survives = child_ho.fitness >= champ_ho.fitness - 1e-9
                if not survives:
                    m2_false += 1
                elif m1 == budget:
                    m1 = meter.used  # charged-budget index (A1)
                if res.fitness > champ_res.fitness:
                    champ, champ_res, champ_ho = child, res, child_ho

            # trait outflow policy -- the ONLY difference between arms (§3)
            if arm == "naive":
                best_attr.observe(child, res)
            elif arm == "gated":
                if report.promoted:
                    best_attr.observe(child, res)  # accepted: trust directly
                elif report.fek_refutation_id:
                    # A2: harvest the SAME channels NAIVE tracks, into the pen.
                    for gene in TRAIT_GENES:
                        pen.append((gene, child.genome.get(gene)))

            # gated confirmation-release pass (dwell ~1; A3). Two charged evals
            # per confirmation (A1); skipped (deferred) if budget cannot cover it.
            if arm == "gated" and pen and meter.can(2):
                gene, val = pen.pop(0)
                confirmations += 1
                fresh = _benchmark(RELEASE_SEED_BASE + (seed * 1000 + confirmations))
                base_g = dict(champ.genome)
                test_g = dict(champ.genome)
                test_g[gene] = val
                base_res = _eval_charged(meter, fresh, build_candidate(base_g, [], "confirm", gen))
                test_cand = build_candidate(test_g, [champ.cid], "released", gen)
                test_res = _eval_charged(meter, fresh, test_cand)
                if val is not None and test_res.fitness > base_res.fitness + 1e-9:
                    # A1: register with the confirmation result -- no carrier eval.
                    best_attr.observe(test_cand, test_res)
                    released += 1

        half_life.add_assurance(ASSURANCE_PER_CHECK * contained_valid)

    assert meter.used <= budget, "budget conservation violated"
    return ArmResult(
        arm=arm, seed=seed, m1=m1, promotions=promotions, m2_false=m2_false,
        evals_used=meter.used,
        detail={
            "final_champ_fitness": round(champ_res.fitness, 4),
            "confirmations": confirmations,
            "released": released,
            "pen_unconfirmed": len(pen),
        },
    )


def run_experiment(seeds: list[int] | None = None, budget: int = DEFAULT_BUDGET) -> dict[str, Any]:
    seeds = seeds if seeds is not None else SEARCH_SEEDS
    out: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    for arm in ARMS:
        for seed in seeds:
            r = run_arm(arm, seed, budget)
            out[arm].append({"seed": r.seed, "m1": r.m1, "promotions": r.promotions,
                             "m2_false": r.m2_false, "evals_used": r.evals_used, **r.detail})
    return {"budget": budget, "seeds": seeds, "prereg_version": "1.1", "arms": out}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--smoke" in argv:
        report = run_experiment(seeds=[1000], budget=24)
        rows = {a: report["arms"][a][0] for a in ARMS}
        schema_ok = all({"m1", "promotions", "m2_false", "evals_used"} <= r.keys() for r in rows.values())
        budget_ok = all(r["evals_used"] == 24 for r in rows.values())
        print("apparatus smoke (NOT a result):")
        for a, r in rows.items():
            print(f"  {a:<8} m1={r['m1']} promotions={r['promotions']} m2_false={r['m2_false']} "
                  f"evals_used={r['evals_used']} champ={r['final_champ_fitness']}")
        print(f"schema OK: {schema_ok}; budget conserved & equal across arms: {budget_ok}")
        return 0 if (schema_ok and budget_ok) else 1
    if "--registered" in argv:
        # Cold-session entrypoint (RUNBOOK.md). Refuses unless explicitly invoked.
        import json
        from pathlib import Path

        out = Path(__file__).parent / "raw_results.json"
        report = run_experiment()
        out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"registered run complete; raw per-seed metrics written to {out}")
        print("now apply the §6 decision rule (stats.py) and commit RESULTS.md per RUNBOOK.md")
        return 0
    print("Refusing to run the registered experiment from this entrypoint.\n"
          "The K=30 / B=600 run requires the v1.1 re-audit and is a cold session's "
          "job (PREREGISTRATION.md §7-8, RUNBOOK.md). Use --smoke to validate the "
          "apparatus, or --registered from a cold session.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
