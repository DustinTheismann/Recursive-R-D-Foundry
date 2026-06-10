"""Deterministic state reconstruction (replay) and snapshots.

Current state is *never* stored as truth -- it is always derived by replaying
the append-only logs (laws #4, #5, #6). Two checkouts with the same logs replay
to byte-identical snapshots and the same state root.
"""

from __future__ import annotations

from typing import Any

from fek.kernel.canonical import canonical_json
from fek.kernel.context import Kernel
from fek.state.store import EventStore


def build_state(kernel: Kernel) -> dict[str, Any]:
    """Replay all logs into a structured current-state view."""

    store = EventStore(kernel)
    claims: dict[str, dict[str, Any]] = {}

    # Claims log: ingestion, grading, status changes.
    for ev in store.read("claims"):
        p = ev.payload
        if ev.type == "claim.ingested":
            claims[p["claim_id"]] = dict(p)
        elif ev.type == "claim.graded":
            cid = p.get("claim_id")
            if cid in claims:
                claims[cid]["grade"] = dict(p)
        elif ev.type == "claim.status_changed":
            cid = p.get("claim_id")
            if cid in claims:
                claims[cid]["status"] = p["status"]

    # State log: applied transitions are the authoritative status changes.
    transitions: dict[str, dict[str, Any]] = {}
    for ev in store.read("state"):
        p = ev.payload
        if ev.type == "transition.proposed":
            transitions[p["transition_id"]] = {**p, "status": "proposed"}
        elif ev.type == "transition.verified":
            tid = p.get("transition_id")
            if tid in transitions:
                transitions[tid]["status"] = "verified"
        elif ev.type == "transition.denied":
            tid = p.get("transition_id")
            if tid in transitions:
                transitions[tid]["status"] = "denied"
        elif ev.type == "transition.applied":
            tid = p.get("transition_id")
            if tid in transitions:
                transitions[tid]["status"] = "applied"
            cid = p.get("claim_id")
            if cid in claims:
                claims[cid]["status"] = p["new_status"]

    from fek.refutations import load_refutations
    from fek.quarantine import load_quarantine
    from fek.capabilities import active_grants

    refutations = load_refutations(kernel)
    # Law #2: refutation overrides promotion unconditionally, regardless of the
    # interleaving of events across logs. A valid refutation pins the claim to
    # refuted (a claim already retired stays retired).
    from fek.types import ClaimStatus

    for ref in refutations.values():
        if ref.get("status", "valid") == "withdrawn":
            continue
        cid = ref.get("claim_id")
        claim = claims.get(cid)
        if claim and claim.get("status") != ClaimStatus.RETIRED.value:
            claim["status"] = ClaimStatus.REFUTED.value

    return {
        "claims": claims,
        "transitions": transitions,
        "refutations": refutations,
        "quarantine": load_quarantine(kernel),
        "granted_capabilities": sorted(active_grants(kernel)),
        "state_root": store.state_root(),
        "event_counts": store.counts(),
    }


def status_counts(state: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in state["claims"].values():
        counts[claim.get("status", "raw")] = counts.get(claim.get("status", "raw"), 0) + 1
    return counts


def snapshot(kernel: Kernel) -> dict[str, Any]:
    """Return the deterministic snapshot dict (state + derived summaries)."""

    state = build_state(kernel)
    return {
        "state_root": state["state_root"],
        "event_counts": state["event_counts"],
        "status_counts": status_counts(state),
        "claims": state["claims"],
        "transitions": state["transitions"],
        "refutations": state["refutations"],
        "quarantine": state["quarantine"],
        "granted_capabilities": state["granted_capabilities"],
    }


def write_snapshot(kernel: Kernel) -> str:
    """Write the snapshot to ``data/snapshots/`` keyed by state root."""

    snap = snapshot(kernel)
    kernel.paths.snapshots.mkdir(parents=True, exist_ok=True)
    path = kernel.paths.snapshots / f"snapshot-{snap['state_root'][:16]}.json"
    path.write_text(canonical_json(snap), encoding="utf-8")
    latest = kernel.paths.snapshots / "latest.json"
    latest.write_text(canonical_json(snap), encoding="utf-8")
    return snap["state_root"]


__all__ = ["build_state", "snapshot", "write_snapshot", "status_counts"]
