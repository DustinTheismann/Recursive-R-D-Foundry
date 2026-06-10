"""Evidence governance bridge: subordinate v0.2's promotion to the kernel.

`promotion.evaluate()` produces a `GateReport` in which the foundry decides
`promoted` **about itself** — no external evidence record, no refutation
channel, no producer/verifier separation, no append-only log. That is precisely
the self-attestation the fractal-evidence-kernel (FEK) exists to refuse.

This bridge makes FEK a *supervening veto*. It can never promote what v0.2
rejected; it can refuse what v0.2 accepted. The governed decision is the
conjunction:

    governed_promoted = v0.2_promoted AND fek_promoted

What FEK adds that v0.2 had no notion of:

* **Producer is not verifier (FEK law #3).** v0.2's `benchmark_pass` is the
  foundry scoring itself -> a self-attested `E3_EXECUTABLE` record, which can
  never satisfy promotion alone. Only the causal/ablation study, run by a
  separate evaluation harness identity, yields an independently verified
  `E4_REPRODUCED` record.
* **Refutation supremacy (law #2).** A per-task regression, a containment
  breach, or an ablation that shows no real effect becomes a first-class
  refutation; the claim collapses to `EX_REFUTED` and promotion is forbidden
  regardless of every other gate.
* **No foundry self-promotion (law #13).** The claim is tagged
  `producer_role: foundry`; the promotion transition must be proposed by an
  independent review identity, not the foundry.
* **Append-only, hash-chained evidence.** Every decision is replayable from the
  kernel's event logs; none of it is the foundry's word.

Honest limitation (mirrors THREAT_MODEL T6 in the v0.1 lane): producer and
verifier are honest *labels* within one trusted process. Cryptographic identity
for evidence records is a spec_only interface, not a claim made here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from fek.claims import ingest_claim
from fek.evidence import grade_claim
from fek.kernel import Kernel
from fek.refutations import create_refutation
from fek.state import apply_transition, build_state, propose_transition, verify_transition

from rsi_foundry.core.types import Candidate, EvalResult, GateReport

FOUNDRY_ID = "rsi-foundry"
ABLATION_HARNESS_ID = "causal-ablation-harness"
REVIEW_ID = "governance-review"


@dataclass
class EvidenceVerdict:
    promoted: bool
    grade: str
    claim_id: str
    refutation_id: Optional[str] = None
    denials: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fek_promoted": self.promoted,
            "fek_grade": self.grade,
            "fek_claim_id": self.claim_id,
            "fek_refutation_id": self.refutation_id,
            "fek_denials": self.denials,
        }


class EvidenceGate:
    """Files a GateReport through FEK and returns a governed verdict."""

    def __init__(self, kernel: Kernel) -> None:
        self.kernel = kernel
        if not kernel.initialised():
            kernel.init()

    def _evidence(self, report: GateReport) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        # Self-attested execution: the foundry ran its own benchmark. E3 at best,
        # and it can never satisfy the independent-verifier policy on its own.
        if report.benchmark_pass:
            evidence.append(
                {
                    "evidence_class": "E3_EXECUTABLE",
                    "method": "self_benchmark",
                    "producer": FOUNDRY_ID,
                    "verifier": FOUNDRY_ID,
                    "detail": f"fitness={report.fitness}",
                }
            )
        # Independently verified reproduction: the ablation study is run by a
        # distinct evaluation harness identity and shows a real causal effect.
        if report.causal_pass and report.causal_effect > 0:
            evidence.append(
                {
                    "evidence_class": "E4_REPRODUCED",
                    "method": "ablation_study",
                    "producer": FOUNDRY_ID,
                    "verifier": ABLATION_HARNESS_ID,
                    "detail": f"causal_effect={report.causal_effect}",
                }
            )
        return evidence

    def govern(self, cand: Candidate, res: EvalResult, report: GateReport) -> GateReport:
        """Run FEK governance over a v0.2 GateReport; AND the two verdicts.

        Mutates and returns ``report`` with ``fek_*`` fields set and
        ``report.promoted`` reduced to the conjunction with FEK's decision.
        """

        v02_promoted = bool(report.promoted)

        claim = ingest_claim(
            self.kernel,
            {
                "statement": f"successor {cand.cid} is a governed improvement over the champion",
                "claim_type": "computational",
                "source": f"rsi_foundry/successor::{cand.cid}",
                "producer": FOUNDRY_ID,
                "required_evidence": ["E4_REPRODUCED"],
                "current_evidence": self._evidence(report),
                "metadata": {
                    "producer_role": "foundry",
                    "cid": cand.cid,
                    "origin": cand.origin,
                    "generation": cand.generation,
                },
            },
        )

        # Refutations -- any one collapses the claim to EX_REFUTED (law #2).
        refutation_id: Optional[str] = None
        if report.regression_failures > 0:
            ref = create_refutation(
                self.kernel, claim.claim_id, "counterexample",
                f"{report.regression_failures} per-task regression(s) vs champion",
                ABLATION_HARNESS_ID, evidence={"regression_failures": report.regression_failures},
            )
            refutation_id = ref.refutation_id
        elif not report.contained:
            ref = create_refutation(
                self.kernel, claim.claim_id, "policy_violation",
                "candidate was not contained (sandbox breach)", "containment-monitor",
            )
            refutation_id = ref.refutation_id
        elif v02_promoted and not (report.causal_pass and report.causal_effect > 0):
            # v0.2 wants to promote but the improvement is not reproduced under
            # ablation -- treat as a failed reproduction.
            ref = create_refutation(
                self.kernel, claim.claim_id, "failed_reproduction",
                "no causal effect under ablation; improvement not independently reproduced",
                ABLATION_HARNESS_ID,
            )
            refutation_id = ref.refutation_id

        grade = grade_claim(self.kernel, claim)

        # Promotion proposed by an INDEPENDENT review identity (law #13). The
        # foundry never proposes its own promotion.
        fek_promoted = False
        denials: list[str] = []
        if v02_promoted:
            txn = propose_transition(self.kernel, claim.claim_id, "promote", proposed_by=REVIEW_ID)
            decision = verify_transition(self.kernel, txn.transition_id)
            if decision["allowed"]:
                apply_transition(self.kernel, txn.transition_id)
                fek_promoted = True
            else:
                denials = [r["reason"] for r in decision["results"] if not r["allowed"]]
        else:
            denials = ["v0.2 gate did not promote; FEK not consulted for promotion"]

        verdict = EvidenceVerdict(
            promoted=fek_promoted, grade=grade.actual_grade,
            claim_id=claim.claim_id, refutation_id=refutation_id, denials=denials,
        )

        # Write FEK fields and reduce to the conjunction.
        report.fek_promoted = verdict.promoted
        report.fek_grade = verdict.grade
        report.fek_claim_id = verdict.claim_id
        report.fek_refutation_id = verdict.refutation_id
        report.fek_denials = verdict.denials
        report.promoted = bool(v02_promoted and verdict.promoted)
        if v02_promoted and not verdict.promoted:
            report.reasons = list(report.reasons) + ["fek_veto:" + ";".join(verdict.denials)]
        return report

    def state(self) -> dict[str, Any]:
        return build_state(self.kernel)


__all__ = ["EvidenceGate", "EvidenceVerdict", "FOUNDRY_ID", "ABLATION_HARNESS_ID", "REVIEW_ID"]
