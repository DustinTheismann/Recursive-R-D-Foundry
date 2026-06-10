"""Evidence ladder, wiring oracle, and grader.

The evidence ladder (``E0``..``E11`` plus the terminal ``EX_REFUTED``) lives in
:mod:`fek.types`. This package adds the two behaviours that make the ladder
mean something:

* the **wiring oracle** (:mod:`fek.evidence.wiring`) -- which classes are
  actually honorable given what is live;
* the **grader** (:mod:`fek.evidence.grader`) -- recomputing a claim's grade
  from its evidence, never from its producer's say-so.
"""

from __future__ import annotations

from fek.evidence.grader import GradeResult, grade_claim
from fek.evidence.wiring import WiringResult, check_wiring
from fek.types import EVIDENCE_ORDER, EvidenceClass, evidence_rank

#: Human-readable description of each rung, used in reports/docs.
LADDER_DESCRIPTIONS: dict[str, str] = {
    "E0_RAW": "raw, unsourced assertion",
    "E1_SOURCED": "attached to an identifiable source",
    "E2_PARSED": "source machine-parsed into structured form",
    "E3_EXECUTABLE": "an executable artifact exists",
    "E4_REPRODUCED": "independently re-run with matching output",
    "E5_NUMERICALLY_SUPPORTED": "numerical evidence (needs live numeric wiring)",
    "E6_SYMBOLICALLY_SUPPORTED": "symbolic evidence (needs live symbolic wiring)",
    "E7_FORMALLY_VERIFIED": "machine-checked proof (needs live proof checker)",
    "E8_CROSS_FORMALLY_VERIFIED": "proof checked by two independent checkers",
    "E9_MULTI_METHOD_VERIFIED": "agreement across independent methods",
    "E10_ADVERSARIALLY_HARDENED": "survived adversarial attack attempts",
    "E11_EXTERNALLY_VALIDATED": "validated by an independent external party",
    "EX_REFUTED": "collapsed by a valid refutation (terminal)",
}

__all__ = [
    "grade_claim",
    "GradeResult",
    "check_wiring",
    "WiringResult",
    "EvidenceClass",
    "EVIDENCE_ORDER",
    "evidence_rank",
    "LADDER_DESCRIPTIONS",
]
