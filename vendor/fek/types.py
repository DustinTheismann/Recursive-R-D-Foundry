"""Core enumerations and shared vocabulary for the kernel.

These types are the *constitutional vocabulary*: claim statuses, the evidence
ladder, maturity labels, and the allowed public-language words. Keeping them in
one module means every other component agrees on the meaning of "accepted",
"E9", or "spec_only".
"""

from __future__ import annotations

from enum import Enum


class ClaimStatus(str, Enum):
    """Lifecycle of a claim. Transitions are append-only (law #5)."""

    RAW = "raw"
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REFUTED = "refuted"
    STALE = "stale"
    DISPUTED = "disputed"
    RETIRED = "retired"


class EvidenceClass(str, Enum):
    """The evidence ladder.

    Higher classes require strictly more wiring. ``EX_REFUTED`` is terminal and
    overrides everything: a single valid refutation collapses a claim to it
    (law #2).
    """

    E0_RAW = "E0_RAW"
    E1_SOURCED = "E1_SOURCED"
    E2_PARSED = "E2_PARSED"
    E3_EXECUTABLE = "E3_EXECUTABLE"
    E4_REPRODUCED = "E4_REPRODUCED"
    E5_NUMERICALLY_SUPPORTED = "E5_NUMERICALLY_SUPPORTED"
    E6_SYMBOLICALLY_SUPPORTED = "E6_SYMBOLICALLY_SUPPORTED"
    E7_FORMALLY_VERIFIED = "E7_FORMALLY_VERIFIED"
    E8_CROSS_FORMALLY_VERIFIED = "E8_CROSS_FORMALLY_VERIFIED"
    E9_MULTI_METHOD_VERIFIED = "E9_MULTI_METHOD_VERIFIED"
    E10_ADVERSARIALLY_HARDENED = "E10_ADVERSARIALLY_HARDENED"
    E11_EXTERNALLY_VALIDATED = "E11_EXTERNALLY_VALIDATED"
    EX_REFUTED = "EX_REFUTED"


# Monotone ordering of the ladder (EX_REFUTED is handled out-of-band, it is
# not "greater" than anything -- it is a collapse).
EVIDENCE_ORDER: list[EvidenceClass] = [
    EvidenceClass.E0_RAW,
    EvidenceClass.E1_SOURCED,
    EvidenceClass.E2_PARSED,
    EvidenceClass.E3_EXECUTABLE,
    EvidenceClass.E4_REPRODUCED,
    EvidenceClass.E5_NUMERICALLY_SUPPORTED,
    EvidenceClass.E6_SYMBOLICALLY_SUPPORTED,
    EvidenceClass.E7_FORMALLY_VERIFIED,
    EvidenceClass.E8_CROSS_FORMALLY_VERIFIED,
    EvidenceClass.E9_MULTI_METHOD_VERIFIED,
    EvidenceClass.E10_ADVERSARIALLY_HARDENED,
    EvidenceClass.E11_EXTERNALLY_VALIDATED,
]


def evidence_rank(cls: EvidenceClass) -> int:
    """Return the integer rank of an evidence class.

    ``EX_REFUTED`` returns ``-1`` because it is a collapse, never a promotion.
    """

    if cls == EvidenceClass.EX_REFUTED:
        return -1
    return EVIDENCE_ORDER.index(cls)


class Maturity(str, Enum):
    """Maturity labels. The only words allowed to describe a layer/capability.

    ``LIVE`` means wired and exercised by tests. ``EXPERIMENTAL`` means present
    but not trustworthy for promotion. ``SPEC_ONLY`` means described but not
    wired (law #14). ``DEPRECATED`` / ``RETIRED`` are end-of-life states.
    """

    LIVE = "live"
    EXPERIMENTAL = "experimental"
    SPEC_ONLY = "spec_only"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class TransitionAction(str, Enum):
    """Allowed state-transition verbs against a claim."""

    PROMOTE = "promote"
    REJECT = "reject"
    REFUTE = "refute"
    RETIRE = "retire"


class RefutationType(str, Enum):
    """Kinds of refutation the kernel recognises (law #2)."""

    COUNTEREXAMPLE = "counterexample"
    FAILED_REPRODUCTION = "failed_reproduction"
    PROOF_FAILURE = "proof_failure"
    CHECKER_DISAGREEMENT = "checker_disagreement"
    INVALID_SOURCE_MAP = "invalid_source_map"
    BROKEN_RUNPACK = "broken_runpack"
    POLICY_VIOLATION = "policy_violation"
    HUMAN_REVIEW_REJECTION = "human_review_rejection"


class QuarantineStatus(str, Enum):
    """Quarantine lifecycle states."""

    HELD = "held"
    RELEASED = "released"
    REJECTED = "rejected"


# Strong public-language words that MUST map to evidence or be marked
# speculative (law #11). Used by the prose scanner.
STRONG_CLAIM_WORDS: tuple[str, ...] = (
    "verified",
    "proven",
    "proved",
    "demonstrated",
    "formally verified",
    "production-ready",
    "production ready",
    "secure",
    "safe",
    "complete",
    "fully built",
    "E7",
    "E8",
    "E9",
)

# Marker that downgrades a strong sentence to allowed speculative language.
SPECULATIVE_MARKERS: tuple[str, ...] = (
    "spec_only",
    "speculative",
    "aspirational",
    "planned",
    "future",
    "not yet",
    "intended to",
)


__all__ = [
    "ClaimStatus",
    "EvidenceClass",
    "EVIDENCE_ORDER",
    "evidence_rank",
    "Maturity",
    "TransitionAction",
    "RefutationType",
    "QuarantineStatus",
    "STRONG_CLAIM_WORDS",
    "SPECULATIVE_MARKERS",
]
