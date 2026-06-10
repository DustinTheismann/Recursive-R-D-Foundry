"""The evidence grader.

The grader answers one question: *given the evidence actually attached to a
claim, and given what wiring is actually live, what grade does this claim
deserve right now?*

It enforces three constitutional laws directly:

* law #2 -- a single valid refutation collapses the grade to ``EX_REFUTED``;
* law #3 -- a producer's *asserted* grade is never trusted; it is recomputed;
* law #11 -- evidence above live wiring is downgraded, not honored.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fek.errors import EvidenceError, VerifierError
from fek.kernel.context import Kernel
from fek.state.store import EventStore
from fek.types import EvidenceClass, evidence_rank
from fek.evidence.wiring import check_wiring

#: Evidence classes whose records must carry an executable ``check`` payload.
#: The record is honored only if the live verifier runs the check and it passes.
#: This is what makes evidence executable rather than declarative.
CHECKED_CLASSES: dict[EvidenceClass, str] = {
    EvidenceClass.E5_NUMERICALLY_SUPPORTED: "numeric",
    EvidenceClass.E6_SYMBOLICALLY_SUPPORTED: "symbolic",
}


def _run_evidence_check(cls: EvidenceClass, rec: dict) -> tuple[bool, str]:
    """Execute the record's check with the matching verifier. (passed, reason)."""

    check = rec.get("check")
    if not isinstance(check, dict) or not check:
        return False, "no executable check payload attached"
    from fek.verifiers import numeric, symbolic

    engine = numeric if CHECKED_CLASSES[cls] == "numeric" else symbolic
    try:
        result = engine.verify(**check)
    except VerifierError as exc:
        return False, f"verifier refused the check: {exc}"
    except TypeError as exc:
        return False, f"malformed check payload: {exc}"
    return bool(result["passed"]), f"{result['method']}: {result['reason']}"


@dataclass
class GradeResult:
    """Outcome of grading a claim."""

    claim_id: str
    actual_grade: str
    refuted: bool
    claimed_grade: str | None
    downgraded: bool
    honored_classes: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "actual_grade": self.actual_grade,
            "refuted": self.refuted,
            "claimed_grade": self.claimed_grade,
            "downgraded": self.downgraded,
            "honored_classes": self.honored_classes,
            "reasons": self.reasons,
        }


def _valid_refutations(kernel: Kernel, claim_id: str) -> list[str]:
    """Refutation ids that currently bind to ``claim_id`` and are not withdrawn."""

    from fek.refutations import load_refutations

    out = []
    for ref in load_refutations(kernel).values():
        if ref.get("claim_id") == claim_id and ref.get("status", "valid") != "withdrawn":
            out.append(ref.get("refutation_id", "?"))
    return out


def grade_claim(kernel: Kernel, claim, emit: bool = True) -> GradeResult:
    """Compute and (optionally) record the grade for ``claim``.

    ``claim`` may be a :class:`fek.claims.Claim` or a plain dict.
    """

    claim_dict = claim.to_dict() if hasattr(claim, "to_dict") else dict(claim)
    claim_id = claim_dict["claim_id"]
    claimed_grade = claim_dict.get("metadata", {}).get("claimed_grade")
    reasons: list[str] = []

    # Law #2: refutation overrides everything.
    refs = _valid_refutations(kernel, claim_id)
    if refs:
        result = GradeResult(
            claim_id=claim_id,
            actual_grade=EvidenceClass.EX_REFUTED.value,
            refuted=True,
            claimed_grade=claimed_grade,
            downgraded=claimed_grade not in (None, EvidenceClass.EX_REFUTED.value),
            honored_classes=[],
            reasons=[f"valid refutation(s) present: {', '.join(refs)} -> EX_REFUTED"],
        )
        if emit:
            EventStore(kernel).append("claims", "claim.graded", result.to_dict())
        return result

    # Honor each evidence record only if its class has live wiring (law #11).
    honored: list[EvidenceClass] = []
    for rec in claim_dict.get("current_evidence", []):
        raw_cls = rec.get("evidence_class")
        try:
            cls = EvidenceClass(raw_cls)
        except (ValueError, TypeError) as exc:
            raise EvidenceError(f"evidence record has invalid class: {raw_cls!r}") from exc
        if cls == EvidenceClass.EX_REFUTED:
            continue
        wiring = check_wiring(kernel, cls)
        if not wiring.supported:
            reasons.append(f"DOWNGRADED {cls.value}: {wiring.reason}")
            continue
        if cls in CHECKED_CLASSES:
            # Executable evidence: the live verifier must actually run the
            # attached check, and it must pass. Declaring E5/E6 is not enough.
            passed, why = _run_evidence_check(cls, rec)
            if passed:
                honored.append(cls)
                reasons.append(f"honored {cls.value}: check passed -- {why}")
            else:
                reasons.append(f"NOT HONORED {cls.value}: {why}")
            continue
        honored.append(cls)
        reasons.append(f"honored {cls.value}: {wiring.reason}")

    if honored:
        actual = max(honored, key=evidence_rank)
    else:
        actual = EvidenceClass.E0_RAW
        reasons.append("no evidence honored -> E0_RAW")

    downgraded = False
    if claimed_grade and claimed_grade != EvidenceClass.EX_REFUTED.value:
        try:
            claimed_cls = EvidenceClass(claimed_grade)
            if evidence_rank(claimed_cls) > evidence_rank(actual):
                downgraded = True
                reasons.append(
                    f"producer asserted {claimed_grade} but only {actual.value} is supported -- assertion rejected (law #3)"
                )
        except ValueError:
            reasons.append(f"ignored unknown claimed_grade {claimed_grade!r}")

    result = GradeResult(
        claim_id=claim_id,
        actual_grade=actual.value,
        refuted=False,
        claimed_grade=claimed_grade,
        downgraded=downgraded,
        honored_classes=[c.value for c in honored],
        reasons=reasons,
    )
    if emit:
        EventStore(kernel).append("claims", "claim.graded", result.to_dict())
    return result


__all__ = ["grade_claim", "GradeResult"]
