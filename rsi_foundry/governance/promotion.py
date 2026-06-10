"""Composite promotion rule.

A successor advances only when ALL hold:

    contracts_pass        (capacity invariant + completeness)
    contained             (ran inside the sandbox, no breach)
    benchmark_pass        (fitness clears the floor)
    fitness_delta > min   (a real improvement over the current champion)
    novelty_score >= min  (dynamic; raised under anti-collapse pressure)
    causal_pass           (ablation evidence + per-task consistency)
    regression_failures==0 (no significant per-task regression vs champion)
    half_life allows       (capability drift absorbable by assurance)
    lineage_hash recorded

The HALF-LIFE controller is only consulted once the cheaper gates pass, so
assurance credit is never spent assessing candidates that fail for other reasons.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from rsi_foundry.core.types import Candidate, EvalResult, GateReport


@dataclass
class PromotionPolicy:
    fitness_delta_min: float = 0.001
    novelty_min: float = 0.0
    regression_tol: float = 0.02
    max_regressions: int = 0
    causal_min_ablation: float = 0.001
    causal_min_task_frac: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return vars(self).copy()


def _regressions(cand: EvalResult, champ: Optional[EvalResult], tol: float) -> int:
    if champ is None or not champ.per_task:
        return 0
    common = set(cand.per_task) & set(champ.per_task)
    return sum(1 for t in common if cand.per_task[t] < champ.per_task[t] - tol)


def evaluate(cand: Candidate, res: EvalResult, champion_result: Optional[EvalResult],
             parent_result: Optional[EvalResult], novelty_score: float,
             causal_result: dict[str, Any], half_life, policy: PromotionPolicy,
             lineage_hash: str) -> GateReport:

    champ_cap = champion_result.fitness if champion_result else 0.0
    fitness_delta = res.fitness - champ_cap

    report = GateReport(
        cid=cand.cid,
        fitness=res.fitness,
        fitness_delta=round(fitness_delta, 5),
        novelty_score=round(novelty_score, 5),
        causal_effect=causal_result.get("effect", 0.0),
        regression_failures=_regressions(res, champion_result, policy.regression_tol),
        contracts_pass=bool(res.quorum.get("contracts")),
        contained=bool(res.quorum.get("contained")),
        benchmark_pass=bool(res.quorum.get("benchmark")),
        lineage_hash=lineage_hash,
    )
    report.novelty_pass = novelty_score >= policy.novelty_min
    report.causal_pass = bool(causal_result.get("pass"))

    reasons: list[str] = []
    pre_gates_ok = True

    if not res.valid:
        pre_gates_ok = False
        reasons.append("invalid:" + (res.error or "quorum"))
    if not report.contracts_pass:
        pre_gates_ok = False; reasons.append("contracts_fail")
    if not report.contained:
        pre_gates_ok = False; reasons.append("not_contained")
    if not report.benchmark_pass:
        pre_gates_ok = False; reasons.append("benchmark_below_floor")
    if fitness_delta <= policy.fitness_delta_min:
        pre_gates_ok = False; reasons.append(f"fitness_delta<={policy.fitness_delta_min}")
    if not report.novelty_pass:
        pre_gates_ok = False; reasons.append(f"novelty<{policy.novelty_min}")
    if not report.causal_pass:
        pre_gates_ok = False; reasons.append("no_causal_evidence")
    if report.regression_failures > policy.max_regressions:
        pre_gates_ok = False
        reasons.append(f"regressions={report.regression_failures}")

    if not pre_gates_ok:
        report.half_life_state = half_life.state
        report.half_life_pass = False
        report.promoted = False
        report.reasons = reasons
        return report

    # Only now spend assurance budget on the HALF-LIFE assessment.
    decision = half_life.consider(res.fitness, report.contained)
    report.half_life_state = decision.state
    report.half_life_pass = decision.allow
    report.capability_drift = round(decision.drift, 5)
    report.assurance_renewal = round(decision.available_credit, 5)
    if not decision.allow:
        reasons.append(f"half_life:{decision.state}:{decision.reason}")

    report.promoted = bool(pre_gates_ok and decision.allow)
    report.reasons = reasons or ["all_gates_passed"]
    return report
