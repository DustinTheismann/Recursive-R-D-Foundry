"""Typed error hierarchy for the Fractal Evidence Kernel (FEK).

Every failure mode the kernel can produce is a subclass of :class:`FEKError`
so callers (CLI, CI guards, tests) can distinguish *why* an operation was
refused. This matters because the kernel is deny-by-default: a refusal is a
first-class, explainable outcome, not an accident.
"""

from __future__ import annotations


class FEKError(Exception):
    """Root of all kernel errors."""


class ValidationError(FEKError):
    """A typed object failed schema/structural validation."""


class SchemaError(FEKError):
    """A schema document itself is malformed or missing."""


class EvidenceError(FEKError):
    """An evidence record is malformed or grading is impossible."""


class VerifierError(FEKError):
    """A verifier refused an input (disallowed syntax, out-of-scope check)."""


class GradingError(FEKError):
    """The grader could not produce a defensible grade."""


class RunpackError(FEKError):
    """A runpack failed to seal, verify, or replay."""


class StateError(FEKError):
    """An append-only state operation was rejected."""


class PolicyViolation(FEKError):
    """A constitutional or operational policy denied an action.

    Carries the offending ``policy_id`` and a human-readable ``reason`` so the
    denial can be surfaced verbatim by the CLI and CI guards.
    """

    def __init__(self, policy_id: str, reason: str) -> None:
        self.policy_id = policy_id
        self.reason = reason
        super().__init__(f"[{policy_id}] {reason}")


class CapabilityDenied(FEKError):
    """A capability was invoked without an active grant (deny-by-default)."""


class RefutationError(FEKError):
    """A refutation is malformed or cannot be linked to a claim."""


class QuarantineError(FEKError):
    """A quarantine transition was rejected."""


class SelfAuditError(FEKError):
    """The root kernel failed to self-audit (law #12)."""


class OverclaimError(FEKError):
    """Prose makes a strong claim unsupported by evidence (law #11)."""


__all__ = [
    "FEKError",
    "ValidationError",
    "SchemaError",
    "EvidenceError",
    "VerifierError",
    "GradingError",
    "RunpackError",
    "StateError",
    "PolicyViolation",
    "CapabilityDenied",
    "RefutationError",
    "QuarantineError",
    "SelfAuditError",
    "OverclaimError",
]
