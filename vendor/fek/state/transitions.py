"""State-transition proposal / verification / application.

A transition is a *proposed* change to a claim's status. It moves through three
recorded stages -- proposed -> verified -> applied -- and every stage is an
appended event (law #5). Verification runs the policy engine; application
re-runs it (defense in depth) before writing the new status. A denied
transition is itself recorded, so refusals are auditable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from fek.errors import StateError, PolicyViolation
from fek.kernel.canonical import content_id
from fek.kernel.context import Kernel
from fek.policies import evaluate_transition
from fek.state.store import EventStore
from fek.types import ClaimStatus, TransitionAction

ACTION_TO_STATUS: dict[str, str] = {
    TransitionAction.PROMOTE.value: ClaimStatus.ACCEPTED.value,
    TransitionAction.REJECT.value: ClaimStatus.REJECTED.value,
    TransitionAction.REFUTE.value: ClaimStatus.REFUTED.value,
    TransitionAction.RETIRE.value: ClaimStatus.RETIRED.value,
}


@dataclass
class Transition:
    transition_id: str
    claim_id: str
    action: str
    proposed_by: str
    created_at: str
    status: str = "proposed"
    new_status: str = ""
    policy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_claim(kernel: Kernel, claim_id: str) -> dict[str, Any]:
    from fek.state.snapshot import build_state

    claim = build_state(kernel)["claims"].get(claim_id)
    if claim is None:
        raise StateError(f"unknown claim: {claim_id}")
    return claim


def _load_transition(kernel: Kernel, transition_id: str) -> dict[str, Any]:
    from fek.state.snapshot import build_state

    txn = build_state(kernel)["transitions"].get(transition_id)
    if txn is None:
        raise StateError(f"unknown transition: {transition_id}")
    return txn


def propose_transition(kernel: Kernel, claim_id: str, action: str, proposed_by: str) -> Transition:
    if action not in ACTION_TO_STATUS:
        raise StateError(f"unknown transition action: {action!r}")
    _load_claim(kernel, claim_id)  # ensure claim exists
    created_at = kernel.now()
    tid = content_id("txn", {"claim_id": claim_id, "action": action, "created_at": created_at, "by": proposed_by})
    txn = Transition(
        transition_id=tid,
        claim_id=claim_id,
        action=action,
        proposed_by=proposed_by,
        created_at=created_at,
        status="proposed",
        new_status=ACTION_TO_STATUS[action],
    )
    EventStore(kernel).append("state", "transition.proposed", txn.to_dict())
    return txn


def verify_transition(kernel: Kernel, transition_id: str) -> dict[str, Any]:
    """Run policies for a proposed transition; record verified or denied."""

    txn = _load_transition(kernel, transition_id)
    claim = _load_claim(kernel, txn["claim_id"])
    decision = evaluate_transition(kernel, claim, txn["action"], txn["proposed_by"])
    store = EventStore(kernel)
    if decision.allowed:
        store.append(
            "state",
            "transition.verified",
            {"transition_id": transition_id, "claim_id": txn["claim_id"], "policy": decision.to_dict()},
        )
    else:
        store.append(
            "state",
            "transition.denied",
            {"transition_id": transition_id, "claim_id": txn["claim_id"], "policy": decision.to_dict()},
        )
    return decision.to_dict()


def apply_transition(kernel: Kernel, transition_id: str) -> dict[str, Any]:
    """Apply a verified transition after re-checking policy (defense in depth)."""

    txn = _load_transition(kernel, transition_id)
    if txn.get("status") != "verified":
        raise StateError(
            f"transition {transition_id} is {txn.get('status')!r}; must be verified before apply"
        )
    claim = _load_claim(kernel, txn["claim_id"])
    decision = evaluate_transition(kernel, claim, txn["action"], txn["proposed_by"])
    if not decision.allowed:
        # Something changed between verify and apply (e.g. a refutation landed).
        raise PolicyViolation(
            decision.denials[0].policy_id,
            f"transition {transition_id} no longer passes policy: {decision.denials[0].reason}",
        )
    new_status = ACTION_TO_STATUS[txn["action"]]
    store = EventStore(kernel)
    store.append(
        "state",
        "transition.applied",
        {"transition_id": transition_id, "claim_id": txn["claim_id"], "new_status": new_status},
    )
    store.append(
        "claims",
        "claim.status_changed",
        {"claim_id": txn["claim_id"], "status": new_status, "reason": f"transition {transition_id}"},
    )
    return {"transition_id": transition_id, "claim_id": txn["claim_id"], "new_status": new_status}


__all__ = [
    "Transition",
    "propose_transition",
    "verify_transition",
    "apply_transition",
    "ACTION_TO_STATUS",
]
