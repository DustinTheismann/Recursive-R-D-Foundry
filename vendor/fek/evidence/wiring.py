"""The wiring oracle.

A claimed evidence class is only honored if the machinery that could *produce*
that class is actually wired and live. This is how the kernel refuses to take a
producer's word for it (law #3: producers are not verifiers) and how it stops
overclaiming (law #11): you cannot reach E7+ just by *writing* "E7" -- a real,
live verifier must exist.

In v0.1 the formal/numeric/symbolic verifiers are **stub / experimental**
(see ``registry/capabilities``), so anything above ``E4_REPRODUCED`` has no live
wiring and is downgraded by the grader. This is deliberate honesty, not a bug.
"""

from __future__ import annotations

from dataclasses import dataclass

from fek.kernel.context import Kernel
from fek.types import EvidenceClass, Maturity, evidence_rank

# Highest evidence class reachable with only the standard library (execution +
# reproduction). Everything at or below this rank needs no special capability.
MAX_STDLIB_CLASS = EvidenceClass.E4_REPRODUCED

# Evidence classes above stdlib map to a capability that must be LIVE to honor
# them. These capabilities are experimental/spec_only in v0.1.
WIRING_CAPABILITY: dict[EvidenceClass, str] = {
    EvidenceClass.E5_NUMERICALLY_SUPPORTED: "numeric_verifier",
    EvidenceClass.E6_SYMBOLICALLY_SUPPORTED: "symbolic_verifier",
    EvidenceClass.E7_FORMALLY_VERIFIED: "formal_verifier",
    EvidenceClass.E8_CROSS_FORMALLY_VERIFIED: "cross_formal_verifier",
    EvidenceClass.E9_MULTI_METHOD_VERIFIED: "multimethod_verifier",
    EvidenceClass.E10_ADVERSARIALLY_HARDENED: "adversarial_harness",
    EvidenceClass.E11_EXTERNALLY_VALIDATED: "external_validator",
}


@dataclass(frozen=True)
class WiringResult:
    supported: bool
    reason: str


def capability_maturity(kernel: Kernel, capability_id: str) -> Maturity | None:
    """Look up a capability's maturity from the registry, or ``None``."""

    from fek.capabilities import load_capabilities

    caps = load_capabilities(kernel)
    cap = caps.get(capability_id)
    if cap is None:
        return None
    try:
        return Maturity(cap.get("maturity", ""))
    except ValueError:
        return None


def check_wiring(kernel: Kernel, evidence_class: EvidenceClass) -> WiringResult:
    """Is ``evidence_class`` honorable given currently-live wiring?"""

    if evidence_rank(evidence_class) <= evidence_rank(MAX_STDLIB_CLASS):
        return WiringResult(True, "reachable with standard-library execution/reproduction")

    cap_id = WIRING_CAPABILITY.get(evidence_class)
    if cap_id is None:
        return WiringResult(False, f"no wiring defined for {evidence_class.value}")

    maturity = capability_maturity(kernel, cap_id)
    if maturity is None:
        return WiringResult(False, f"capability {cap_id!r} not registered")
    if maturity != Maturity.LIVE:
        return WiringResult(
            False,
            f"capability {cap_id!r} is {maturity.value}, not live -- {evidence_class.value} cannot be honored",
        )
    return WiringResult(True, f"capability {cap_id!r} is live")


__all__ = ["check_wiring", "WiringResult", "WIRING_CAPABILITY", "MAX_STDLIB_CLASS", "capability_maturity"]
