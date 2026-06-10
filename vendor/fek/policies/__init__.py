"""The policy engine.

Policies are the executable form of the constitution. Each policy is a pure
check that returns an explainable :class:`PolicyResult` (allowed + reason). The
engine is deny-by-default in spirit: a transition is allowed only if *every*
applicable policy allows it.

Policies implemented here map directly onto the hard constitutional laws:

* ``no_promotion_without_evidence``   -> law #1
* ``no_promotion_if_refuted``         -> law #2
* ``producers_are_not_verifiers``     -> law #3
* ``no_foundry_self_promotion``       -> law #13

Additional repo-wide policies (no edited generated views, no committed secrets,
no live layer without maturity, no public claim without source map) are checked
by the self-audit (:mod:`fek.reports.self_audit`) because they concern files,
not single transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fek.kernel.context import Kernel
from fek.obligations import required_class_for
from fek.types import EvidenceClass, TransitionAction, evidence_rank


@dataclass
class PolicyResult:
    policy_id: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, "allowed": self.allowed, "reason": self.reason}


@dataclass
class PolicyDecision:
    """Aggregate decision for a transition."""

    allowed: bool
    results: list[PolicyResult]

    @property
    def denials(self) -> list[PolicyResult]:
        return [r for r in self.results if not r.allowed]

    def explain(self) -> str:
        lines = [f"{'ALLOW' if r.allowed else 'DENY '} [{r.policy_id}] {r.reason}" for r in self.results]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "results": [r.to_dict() for r in self.results]}


# -- individual policies -------------------------------------------------
def _grade(kernel: Kernel, claim: dict[str, Any]):
    from fek.evidence.grader import grade_claim

    return grade_claim(kernel, claim, emit=False)


def no_promotion_if_refuted(kernel: Kernel, claim: dict[str, Any], action: str, proposed_by: str) -> PolicyResult:
    pid = "no_promotion_if_refuted"
    if action != TransitionAction.PROMOTE.value:
        return PolicyResult(pid, True, "not a promotion")
    g = _grade(kernel, claim)
    if g.refuted:
        return PolicyResult(pid, False, "claim has a valid refutation; promotion is forbidden (law #2)")
    return PolicyResult(pid, True, "no valid refutation present")


def no_promotion_without_evidence(kernel: Kernel, claim: dict[str, Any], action: str, proposed_by: str) -> PolicyResult:
    pid = "no_promotion_without_evidence"
    if action != TransitionAction.PROMOTE.value:
        return PolicyResult(pid, True, "not a promotion")
    required = required_class_for(claim.get("claim_type", ""), claim.get("required_evidence"))
    g = _grade(kernel, claim)
    if g.refuted:
        return PolicyResult(pid, False, "claim is refuted")
    actual = EvidenceClass(g.actual_grade)
    if evidence_rank(actual) >= evidence_rank(required):
        return PolicyResult(pid, True, f"honored grade {actual.value} >= required {required.value}")
    return PolicyResult(
        pid,
        False,
        f"honored grade {actual.value} < required {required.value}; insufficient evidence (law #1)",
    )


def producers_are_not_verifiers(kernel: Kernel, claim: dict[str, Any], action: str, proposed_by: str) -> PolicyResult:
    pid = "producers_are_not_verifiers"
    if action != TransitionAction.PROMOTE.value:
        return PolicyResult(pid, True, "not a promotion")
    producer = (claim.get("producer") or "").strip()
    independent = []
    for rec in claim.get("current_evidence", []):
        verifier = (rec.get("verifier") or "").strip()
        if verifier and verifier != producer:
            independent.append(verifier)
    if independent:
        return PolicyResult(pid, True, f"independent verifier(s) present: {sorted(set(independent))}")
    return PolicyResult(
        pid, False, "no evidence record verified by a party other than the producer (law #3)"
    )


def no_foundry_self_promotion(kernel: Kernel, claim: dict[str, Any], action: str, proposed_by: str) -> PolicyResult:
    pid = "no_foundry_self_promotion"
    if action != TransitionAction.PROMOTE.value:
        return PolicyResult(pid, True, "not a promotion")
    role = (claim.get("metadata", {}) or {}).get("producer_role", "")
    producer = (claim.get("producer") or "").strip()
    if role == "foundry" and proposed_by.strip() == producer:
        return PolicyResult(
            pid, False, "a foundry may propose but may not self-promote (law #13)"
        )
    return PolicyResult(pid, True, "not a foundry self-promotion")


TRANSITION_POLICIES: list[Callable[..., PolicyResult]] = [
    no_promotion_if_refuted,
    no_promotion_without_evidence,
    producers_are_not_verifiers,
    no_foundry_self_promotion,
]


def evaluate_transition(kernel: Kernel, claim: dict[str, Any], action: str, proposed_by: str) -> PolicyDecision:
    """Run all transition policies and aggregate (deny if any deny)."""

    results = [p(kernel, claim, action, proposed_by) for p in TRANSITION_POLICIES]
    allowed = all(r.allowed for r in results)
    return PolicyDecision(allowed=allowed, results=results)


__all__ = [
    "PolicyResult",
    "PolicyDecision",
    "evaluate_transition",
    "TRANSITION_POLICIES",
    "no_promotion_if_refuted",
    "no_promotion_without_evidence",
    "producers_are_not_verifiers",
    "no_foundry_self_promotion",
]
