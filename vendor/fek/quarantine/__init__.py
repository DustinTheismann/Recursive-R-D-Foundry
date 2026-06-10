"""Quarantine for generated / untrusted candidates.

Generated artifacts are never source truth (law #4). When an untrusted
candidate (a generated view, an unverified import, a suspicious claim) needs to
be held pending review, it goes into quarantine. Release is only possible
through a policy-approved transition -- it cannot be willed out by editing a
file.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from fek.errors import QuarantineError
from fek.kernel.canonical import content_id
from fek.kernel.context import Kernel
from fek.state.store import EventStore
from fek.types import QuarantineStatus


@dataclass
class QuarantineItem:
    quarantine_id: str
    object_type: str
    object_ref: str
    reason: str
    created_at: str
    status: str = QuarantineStatus.HELD.value
    release_conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def quarantine_candidate(
    kernel: Kernel,
    object_type: str,
    object_ref: str,
    reason: str,
    release_conditions: list[str] | None = None,
) -> QuarantineItem:
    qid = content_id("qtn", {"object_type": object_type, "object_ref": object_ref, "reason": reason})
    item = QuarantineItem(
        quarantine_id=qid,
        object_type=object_type,
        object_ref=object_ref,
        reason=reason,
        created_at=kernel.now(),
        status=QuarantineStatus.HELD.value,
        release_conditions=release_conditions or [],
    )
    EventStore(kernel).append("quarantine", "quarantine.created", item.to_dict())
    return item


def release_quarantine(kernel: Kernel, quarantine_id: str, approved_by: str, transition_id: str) -> None:
    """Release an item -- ONLY via a policy-approved transition reference."""

    items = load_quarantine(kernel)
    item = items.get(quarantine_id)
    if item is None:
        raise QuarantineError(f"unknown quarantine id: {quarantine_id}")
    if item["status"] != QuarantineStatus.HELD.value:
        raise QuarantineError(f"quarantine {quarantine_id} is {item['status']}, cannot release")
    if not transition_id:
        raise QuarantineError("release requires a policy-approved transition_id (law #4)")
    EventStore(kernel).append(
        "quarantine",
        "quarantine.released",
        {"quarantine_id": quarantine_id, "approved_by": approved_by, "transition_id": transition_id},
    )


def reject_quarantine(kernel: Kernel, quarantine_id: str, reason: str) -> None:
    items = load_quarantine(kernel)
    if quarantine_id not in items:
        raise QuarantineError(f"unknown quarantine id: {quarantine_id}")
    EventStore(kernel).append(
        "quarantine", "quarantine.rejected", {"quarantine_id": quarantine_id, "reason": reason}
    )


def load_quarantine(kernel: Kernel) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for ev in EventStore(kernel).read("quarantine"):
        rec = ev.payload
        qid = rec.get("quarantine_id")
        if ev.type == "quarantine.created":
            out[qid] = dict(rec)
        elif ev.type == "quarantine.released" and qid in out:
            out[qid]["status"] = QuarantineStatus.RELEASED.value
        elif ev.type == "quarantine.rejected" and qid in out:
            out[qid]["status"] = QuarantineStatus.REJECTED.value
    return out


__all__ = [
    "QuarantineItem",
    "quarantine_candidate",
    "release_quarantine",
    "reject_quarantine",
    "load_quarantine",
]
