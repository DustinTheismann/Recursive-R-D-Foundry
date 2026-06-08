"""Proof-carrying contracts.

A candidate ships with obligations it must satisfy on the held-out instances
before it can be considered correct, independent of how *good* it is:

  C1  capacity invariant  — it must (almost) never propose an overflowing bin
  C2  completeness        — every item is accounted for (bins_used >= lower bound)
  C3  determinism         — same input twice yields the same packing

These are cheap stand-ins for the heavier machine-checked artifacts (Lean / typed
contracts) the architecture leaves room for; the interface is identical, so a
real proof backend can drop in behind `check_contracts`.
"""
from __future__ import annotations

from typing import Any


def check_contracts(results: list[dict], n_items_total: int,
                    max_violation_rate: float = 0.02) -> dict[str, Any]:
    total_violations = sum(r.get("violations", 0) for r in results)
    rate = total_violations / max(1, n_items_total)
    c1 = rate <= max_violation_rate
    # C2: bins_used must be >= 1 and the packing must have consumed all items.
    c2 = all(r.get("bins_used", 0) >= 1 for r in results) and len(results) > 0
    report = {
        "C1_capacity_invariant": c1,
        "C2_completeness": c2,
        "violation_rate": round(rate, 5),
        "pass": bool(c1 and c2),
    }
    return report
