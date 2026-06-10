"""The promotion gate, built on fractal-evidence-kernel.

This module deliberately implements **nothing** about evidence, grading,
refutation, or promotion policy itself. All of that is imported from
``fractal-evidence-kernel`` (FEK) -- the reviewer's point stands: restating a
gate's premise in prose is worthless; depending on a tested one is not.

The wiring, per candidate:

1. Public benchmark pass  -> an ``E3_EXECUTABLE`` evidence record, produced and
   verified by the foundry itself (self-verified: worth little, and the policy
   engine knows it).
2. Held-out probe pass    -> an ``E4_REPRODUCED`` record verified by
   ``probe-harness``, an identity distinct from the producer (FEK's
   producers-are-not-verifiers policy requires this for promotion).
3. Probe FAILURE after a public pass -> a first-class FEK *refutation*
   (counterexample, with the concrete failing input). FEK's grader collapses
   the claim to EX_REFUTED and its policy engine refuses promotion regardless
   of any other evidence. Refutation overrides promotion -- FEK law #2.
4. Promotion is proposed by the review harness, never applied by the foundry:
   the claim carries ``producer_role: foundry``, so FEK's
   no-foundry-self-promotion policy (law #13) denies any attempt by the
   foundry to promote its own candidate.

The gate's falsification conditions are enumerated in SPEC.md and are
executable: ``make falsify``.
"""

from __future__ import annotations

from typing import Any

from fek.claims import ingest_claim
from fek.evidence import grade_claim
from fek.kernel import Kernel
from fek.refutations import create_refutation
from fek.state import apply_transition, build_state, propose_transition, verify_transition

from gate_demo.benchmark import Agent, perfect, run_probe, run_public
from gate_demo.traits import extract_traits, quarantine_traits

FOUNDRY_ID = "foundry:gen0"
PROBE_HARNESS_ID = "probe-harness"
REVIEW_HARNESS_ID = "review-harness"


def evaluate_candidate(kernel: Kernel, name: str, agent: Agent) -> dict[str, Any]:
    """Run both surfaces, file the claim + evidence, refute on probe failure."""

    public = run_public(agent)
    probe = run_probe(agent)

    evidence: list[dict[str, Any]] = []
    if perfect(public):
        # Self-verified execution evidence. Necessary, nowhere near sufficient.
        evidence.append(
            {
                "evidence_class": "E3_EXECUTABLE",
                "method": "public_benchmark",
                "producer": FOUNDRY_ID,
                "verifier": FOUNDRY_ID,
                "detail": f"{public['passed']}/{public['total']} public cases",
            }
        )
    if perfect(probe):
        # Independently verified reproduction on held-out inputs.
        evidence.append(
            {
                "evidence_class": "E4_REPRODUCED",
                "method": "heldout_probe",
                "producer": FOUNDRY_ID,
                "verifier": PROBE_HARNESS_ID,
                "detail": f"{probe['passed']}/{probe['total']} probe cases (seed {probe['seed']})",
            }
        )

    claim = ingest_claim(
        kernel,
        {
            "statement": f"candidate {name} correctly performs the sort task",
            "claim_type": "computational",
            "source": f"src/foundry/agents.py::{name}",
            "producer": FOUNDRY_ID,
            "required_evidence": ["E4_REPRODUCED"],
            "current_evidence": evidence,
            "metadata": {"producer_role": "foundry", "candidate": name},
        },
    )

    refutation_id = None
    if perfect(public) and not perfect(probe):
        # The Goodhart signature: public surface aced, held-out surface failed.
        first = probe["failures"][0]
        ref = create_refutation(
            kernel,
            claim.claim_id,
            "counterexample",
            f"held-out probe failure: input={first['input']} expected={first['expected']} "
            f"got={first.get('got', first.get('error'))}",
            PROBE_HARNESS_ID,
            evidence={"probe_seed": probe["seed"], "failures": probe["failures"][:3]},
        )
        refutation_id = ref.refutation_id

    traits = extract_traits(name, public, probe)
    quarantined = quarantine_traits(kernel, name, traits)

    grade = grade_claim(kernel, claim)
    return {
        "candidate": name,
        "claim_id": claim.claim_id,
        "public": {"passed": public["passed"], "total": public["total"]},
        "probe": {"passed": probe["passed"], "total": probe["total"]},
        "grade": grade.actual_grade,
        "refutation_id": refutation_id,
        "traits": [t["trait"] for t in traits],
        "quarantine_ids": quarantined,
    }


def attempt_promotion(kernel: Kernel, claim_id: str, proposed_by: str = REVIEW_HARNESS_ID) -> dict[str, Any]:
    """Propose -> verify -> (maybe) apply, entirely through FEK's policy engine.

    Returns the decision either way; a denial is a recorded, explainable
    outcome, not an exception.
    """

    txn = propose_transition(kernel, claim_id, "promote", proposed_by=proposed_by)
    decision = verify_transition(kernel, txn.transition_id)
    applied = False
    if decision["allowed"]:
        apply_transition(kernel, txn.transition_id)
        applied = True
    status = build_state(kernel)["claims"][claim_id]["status"]
    return {
        "transition_id": txn.transition_id,
        "allowed": decision["allowed"],
        "applied": applied,
        "status": status,
        "denials": [r["reason"] for r in decision["results"] if not r["allowed"]],
    }


__all__ = [
    "evaluate_candidate",
    "attempt_promotion",
    "FOUNDRY_ID",
    "PROBE_HARNESS_ID",
    "REVIEW_HARNESS_ID",
]
