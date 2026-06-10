"""Human review records (maturity: experimental).

Human reviewers are a distinct trust source (see ``docs/TRUST_TAXONOMY.md``): a
human review *rejection* is a valid refutation type, and a human approval is one
input to promotion. Reviews are appended to the review event log so they are
auditable, never editable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fek.kernel.canonical import content_id
from fek.kernel.context import Kernel
from fek.state.store import EventStore


@dataclass
class Review:
    review_id: str
    subject_ref: str
    reviewer: str
    decision: str  # "approve" | "reject" | "comment"
    notes: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_review(kernel: Kernel, subject_ref: str, reviewer: str, decision: str, notes: str = "") -> Review:
    if decision not in {"approve", "reject", "comment"}:
        raise ValueError(f"invalid review decision: {decision!r}")
    created_at = kernel.now()
    rid = content_id("rvw", {"subject_ref": subject_ref, "reviewer": reviewer, "created_at": created_at})
    review = Review(rid, subject_ref, reviewer, decision, notes, created_at)
    EventStore(kernel).append("review", "review.recorded", review.to_dict())
    return review


def load_reviews(kernel: Kernel) -> list[Review]:
    return [Review(**ev.payload) for ev in EventStore(kernel).read("review") if ev.type == "review.recorded"]


__all__ = ["Review", "record_review", "load_reviews"]
