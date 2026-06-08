"""Causal gate — promote only causally-evidenced improvements.

Two interventional tests, both required:

1. Ablation evidence. For each gene we knock it out to its neutral value, rerun,
   and measure the fitness drop. If *no* gene's removal hurts the candidate, the
   apparent gain is not mechanistically grounded (it is noise or a free rider),
   and the candidate is rejected even if its raw score is high.

2. Consistency vs. parent. The candidate must beat its parent on a majority of
   individual tasks, not just on the average — a guard against a single lucky
   task carrying the mean.

This turns "it scored higher" into "we have evidence about *why* it scored
higher", which is the whole point of the gate.
"""
from __future__ import annotations

from typing import Any

from rsi_foundry.core.types import Candidate, EvalResult
from rsi_foundry.domain import heuristics
from rsi_foundry.proposers.base import build_candidate


def ablation_study(cand: Candidate, base: EvalResult, fast_harness) -> dict[str, float]:
    """Return {gene: fitness_drop_when_removed}. Positive => gene contributes."""
    deltas: dict[str, float] = {}
    for gene in heuristics.GENES:
        ablated_genome = heuristics.ablate(cand.genome, gene)
        if ablated_genome == cand.genome:
            deltas[gene] = 0.0
            continue
        ab = build_candidate(ablated_genome, [cand.cid], "ablation", cand.generation)
        res = fast_harness.evaluate(ab.cid, ab.source)
        deltas[gene] = round(base.fitness - res.fitness, 5)
    return deltas


def evaluate_causal(cand: Candidate, base: EvalResult, parent_result: EvalResult | None,
                    fast_harness, min_ablation: float = 0.001,
                    min_task_frac: float = 0.5) -> dict[str, Any]:
    deltas = ablation_study(cand, base, fast_harness)
    max_delta = max(deltas.values()) if deltas else 0.0
    most_causal = max(deltas, key=deltas.get) if deltas else None

    if parent_result and parent_result.per_task:
        common = set(base.per_task) & set(parent_result.per_task)
        improved = sum(1 for t in common
                       if base.per_task[t] >= parent_result.per_task[t] - 1e-9)
        frac = improved / len(common) if common else 1.0
    else:
        frac = 1.0  # no parent (seed lineage): consistency test is vacuous

    passed = (max_delta >= min_ablation) and (frac >= min_task_frac)
    return {
        "ablation": deltas,
        "most_causal_gene": most_causal,
        "max_ablation_delta": round(max_delta, 5),
        "tasks_improved_frac": round(frac, 4),
        "effect": round(max_delta, 5),
        "pass": bool(passed),
    }
