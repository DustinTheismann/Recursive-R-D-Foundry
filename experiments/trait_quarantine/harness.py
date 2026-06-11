"""Three-arm trait-quarantine apparatus (move 2).

DISCARD / NAIVE / GATED differ ONLY in trait flow (PREREGISTRATION §3); the gate
itself is the real one (`promotion.evaluate` + `causal_gate` + `EvidenceGate`),
not a reimplementation. This module is the apparatus; it PRODUCES NO HEADLINE
RESULT here. `--smoke` proves all three arms execute and emit the metric schema
on a tiny budget. The registered run (K=30 seeds, B=600) and the §7 faithfulness
audit are done by a separate cold session, which records RESULTS.md.

Metric schema per (arm, seed): {"m1": int, "promotions": int, "m2_false": int}.
  m1  = first evaluation index whose governed promotion survives the held-out
        re-eval (right-censored at B).
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
DEFAULT_BUDGET = 600
ARMS = ("discard", "naive", "gated")
ASSURANCE_PER_CHECK = 0.004  # mirrors orchestrator DEFAULTS (half-life accrual)


@dataclass
class ArmResult:
    arm: str
    seed: int
    m1: int
    promotions: int = 0
    m2_false: int = 0
    detail: dict[str, Any] = field(default_factory=dict)


def _benchmark(seed: int, floor: float = 0.5):
    sandbox = make_sandbox("in_process", ContainmentPolicy(cpu_seconds=2, mem_mb=256, wall_timeout=8.0))
    bench = LocalBinPackBenchmark(binpack.starter_envs(), random.Random(seed), per_env=3)
    return Harness(bench, sandbox, floor)


def _evaluate(h: Harness, cand: Candidate) -> EvalResult:
    return h.evaluate(cand.cid, cand.source)


def run_arm(arm: str, seed: int, budget: int = DEFAULT_BUDGET) -> ArmResult:
    """Run one arm on one search seed. The gate is identical across arms."""
    assert seed not in (HELD_OUT_SEED,) and seed < RELEASE_SEED_BASE, "search/holdout leakage"
    rng = random.Random(seed)
    harness = _benchmark(seed)
    fast = _benchmark(seed)            # ablation harness (same distribution)
    held = _benchmark(HELD_OUT_SEED)   # generalization check (unseen during search)
    proposer = MutationProposer()
    policy = PromotionPolicy()
    policy.novelty_min = 0.0
    half_life = HalfLifeController(safety_factor=2.0)
    gate = EvidenceGate(Kernel(tempfile.mkdtemp(prefix=f"tq-{arm}-{seed}-")))
    best_attr = BestAttributeRegistry() if arm in ("naive", "gated") else None
    quarantine_pen: list[tuple[str, Any]] = []  # (gene, value) awaiting release (gated)

    champ = build_candidate(heuristics.seed_genome(), [], "seed", 0)
    champ_res = _evaluate(harness, champ)
    champ_ho = _evaluate(held, champ)

    # Exploration is DECOUPLED from promotion (QD-style): a parent pool of the
    # best-fitness candidates drives the search so it can climb even while the
    # gate (correctly) promotes rarely. The champion is the promotion baseline
    # and advances only on a governed promotion.
    results: dict[str, EvalResult] = {champ.cid: champ_res}
    pool: list[Candidate] = [champ]
    POOL_K = 6

    evals = 0
    m1 = budget
    promotions = 0
    m2_false = 0
    gen = 0
    release_counter = 0

    while evals < budget:
        gen += 1
        # Re-anchor half-life to the current champion each generation and let
        # assurance accrue from contained-valid evals (mirrors the orchestrator,
        # orchestrator.py:187/234). Without this, every drift is measured from
        # zero with zero budget and HALF-LIFE blocks all promotions.
        half_life.set_baseline_capability(champ_res.fitness)
        contained_valid = 0
        children = proposer.propose(pool, rng, N_OFFSPRING, None, gen)
        for child in children:
            if evals >= budget:
                break
            # trait inflow: graft a released/registered best-gene (naive+gated)
            if best_attr is not None and best_attr.best:
                grafted = best_attr.graft(child.genome, rng)
                if grafted != child.genome:
                    child = build_candidate(grafted, child.parents, child.origin, gen)
            res = _evaluate(harness, child)
            evals += 1
            results[child.cid] = res
            if res.valid and res.quorum.get("contained"):
                contained_valid += 1
            # update the exploration pool (top-K by fitness, distinct)
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
                child_ho = _evaluate(held, child)
                survives = child_ho.fitness >= champ_ho.fitness - 1e-9
                if not survives:
                    m2_false += 1
                elif m1 == budget:
                    m1 = evals  # first held-out-surviving governed promotion
                if res.fitness > champ_res.fitness:
                    champ, champ_res, champ_ho = child, res, child_ho

            # trait outflow policy -- the ONLY difference between arms
            if arm == "naive":
                best_attr.observe(child, res)
            elif arm == "gated":
                if report.promoted:
                    best_attr.observe(child, res)           # accepted: trust directly
                elif report.fek_refutation_id:
                    # refuted candidate's trait -> quarantine, release only on
                    # fresh-seed confirmation (PREREGISTRATION §3)
                    gene = "w_residual"
                    quarantine_pen.append((gene, child.genome.get(gene)))
            # gated release pass
            if arm == "gated" and quarantine_pen:
                gene, val = quarantine_pen.pop(0)
                release_counter += 1
                fresh = _benchmark(RELEASE_SEED_BASE + release_counter)
                base_g = dict(champ.genome)
                test_g = dict(champ.genome); test_g[gene] = val
                base_f = _evaluate(fresh, build_candidate(base_g, [], "rel", 0)).fitness
                test_f = _evaluate(fresh, build_candidate(test_g, [], "rel", 0)).fitness
                if val is not None and test_f > base_f + 1e-9:
                    # released: synthesize a carrier candidate so observe() registers it
                    carrier = build_candidate(test_g, [champ.cid], "released", gen)
                    best_attr.observe(carrier, _evaluate(harness, carrier))

        # end of generation: accrue assurance from contained-valid evals
        half_life.add_assurance(ASSURANCE_PER_CHECK * contained_valid)

    return ArmResult(arm=arm, seed=seed, m1=m1, promotions=promotions, m2_false=m2_false,
                     detail={"final_champ_fitness": round(champ_res.fitness, 4),
                             "quarantined_unreleased": len(quarantine_pen)})


def run_experiment(seeds: list[int] | None = None, budget: int = DEFAULT_BUDGET) -> dict[str, Any]:
    seeds = seeds if seeds is not None else SEARCH_SEEDS
    out: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    for arm in ARMS:
        for seed in seeds:
            r = run_arm(arm, seed, budget)
            out[arm].append({"seed": r.seed, "m1": r.m1, "promotions": r.promotions,
                             "m2_false": r.m2_false, **r.detail})
    return {"budget": budget, "seeds": seeds, "arms": out}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--smoke" in argv:
        report = run_experiment(seeds=[1000], budget=24)
        ok = all(len(report["arms"][a]) == 1 and {"m1", "promotions", "m2_false"} <= report["arms"][a][0].keys()
                 for a in ARMS)
        print("apparatus smoke (NOT a result):")
        for a in ARMS:
            row = report["arms"][a][0]
            print(f"  {a:<8} m1={row['m1']} promotions={row['promotions']} m2_false={row['m2_false']} "
                  f"champ={row['final_champ_fitness']}")
        print(f"schema OK: {ok}")
        return 0 if ok else 1
    print("Refusing to run the registered experiment from this entrypoint.\n"
          "The K=30 / B=600 run + faithfulness audit are a cold session's job "
          "(PREREGISTRATION.md §7-8). Use --smoke to validate the apparatus.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
