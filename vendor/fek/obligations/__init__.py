"""Evidence obligations per claim type.

An *obligation* is the minimum honored evidence class a claim of a given type
must reach before it may be promoted to ``accepted``. This is the gate behind
law #1 (no claim promotes without evidence). A claim may also carry its own
``required_evidence`` list; the effective gate is the strictest of the two.
"""

from __future__ import annotations

from fek.types import EvidenceClass, evidence_rank

#: Default minimum evidence class required to promote a claim of each type.
DEFAULT_OBLIGATIONS: dict[str, EvidenceClass] = {
    "computational": EvidenceClass.E4_REPRODUCED,
    "empirical": EvidenceClass.E4_REPRODUCED,
    "mathematical": EvidenceClass.E7_FORMALLY_VERIFIED,
    "security": EvidenceClass.E10_ADVERSARIALLY_HARDENED,
    "documentation": EvidenceClass.E1_SOURCED,
    "metadata": EvidenceClass.E1_SOURCED,
}

#: Fallback when a claim_type is unknown -- demand reproduction.
FALLBACK_OBLIGATION = EvidenceClass.E4_REPRODUCED


def required_class_for(claim_type: str, claim_required: list[str] | None = None) -> EvidenceClass:
    """Return the effective minimum evidence class for promotion."""

    base = DEFAULT_OBLIGATIONS.get(claim_type, FALLBACK_OBLIGATION)
    best = base
    for raw in claim_required or []:
        try:
            cls = EvidenceClass(raw)
        except ValueError:
            continue
        if evidence_rank(cls) > evidence_rank(best):
            best = cls
    return best


__all__ = ["DEFAULT_OBLIGATIONS", "FALLBACK_OBLIGATION", "required_class_for"]
