"""First-class refutations.

Refutation is not an afterthought in this kernel -- it is a peer of evidence and
it *wins*. Law #2: refutation overrides promotion. A single valid refutation
collapses a claim's grade to ``EX_REFUTED`` and forces its status to
``refuted``, regardless of how much supporting evidence exists.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from fek.errors import RefutationError
from fek.kernel.canonical import content_id
from fek.kernel.context import Kernel
from fek.state.store import EventStore
from fek.types import ClaimStatus, RefutationType


@dataclass
class Refutation:
    refutation_id: str
    claim_id: str
    refutation_type: str
    source: str
    statement: str
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    status: str = "valid"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_refutation(data: dict[str, Any]) -> None:
    for key in ("claim_id", "refutation_type", "statement", "source"):
        if not data.get(key):
            raise RefutationError(f"refutation missing required field: {key!r}")
    if data["refutation_type"] not in {t.value for t in RefutationType}:
        raise RefutationError(f"unknown refutation_type: {data['refutation_type']!r}")


def create_refutation(
    kernel: Kernel,
    claim_id: str,
    refutation_type: str,
    statement: str,
    source: str,
    evidence: dict[str, Any] | None = None,
) -> Refutation:
    """Create a refutation, link it to the claim, and force ``refuted`` status.

    Emits ``refutation.created`` (refutation log) and ``claim.status_changed``
    (claims log) so both the grader and the replayed claim view reflect the
    override immediately.
    """

    data = {
        "claim_id": claim_id,
        "refutation_type": refutation_type,
        "statement": statement,
        "source": source,
        "evidence": evidence or {},
    }
    validate_refutation(data)
    rid = content_id("ref", {"claim_id": claim_id, "refutation_type": refutation_type, "statement": statement})
    refutation = Refutation(
        refutation_id=rid,
        claim_id=claim_id,
        refutation_type=refutation_type,
        source=source,
        statement=statement,
        evidence=evidence or {},
        created_at=kernel.now(),
        status="valid",
    )
    store = EventStore(kernel)
    store.append("refutation", "refutation.created", refutation.to_dict())
    # Law #2: force the claim to refuted in the canonical claim view.
    store.append(
        "claims",
        "claim.status_changed",
        {"claim_id": claim_id, "status": ClaimStatus.REFUTED.value, "reason": f"refuted by {rid}"},
    )
    return refutation


def load_refutations(kernel: Kernel) -> dict[str, dict[str, Any]]:
    """Replay the refutation log into a {refutation_id: record} map."""

    out: dict[str, dict[str, Any]] = {}
    for ev in EventStore(kernel).read("refutation"):
        if ev.type == "refutation.created":
            rec = ev.payload
            out[rec["refutation_id"]] = rec
        elif ev.type == "refutation.withdrawn":
            rid = ev.payload.get("refutation_id")
            if rid in out:
                out[rid] = {**out[rid], "status": "withdrawn"}
    return out


__all__ = ["Refutation", "create_refutation", "validate_refutation", "load_refutations", "RefutationType"]
