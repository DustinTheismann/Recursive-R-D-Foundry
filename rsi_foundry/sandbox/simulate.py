"""Trusted bin-packing simulator.

Candidate code (`place`) is *advisory only*: it returns a bin index or -1. This
trusted function decides what that means and owns all accounting, so a candidate
can never overflow a bin, lose an item, or fabricate a score. Capacity-violating
suggestions are recorded as contract violations and overridden with a new bin.
"""
from __future__ import annotations

from typing import Any, Callable


def run_instance(place: Callable, items: list[int], capacity: int) -> dict[str, Any]:
    bins: list[int] = []
    violations = 0
    voluntary_open = 0
    for item in items:
        try:
            idx = place(item, list(bins), capacity)
        except Exception:
            idx = -1
        is_int = isinstance(idx, int) and not isinstance(idx, bool)
        if is_int and 0 <= idx < len(bins) and bins[idx] + item <= capacity:
            bins[idx] += item
        else:
            # The suggestion was unusable; the trusted simulator overrides it.
            if is_int and idx == -1:
                voluntary_open += 1            # legitimate "open a new bin"
            elif is_int and (idx < -1 or idx >= len(bins)):
                violations += 1                # out-of-range index: contract breach
            elif is_int and 0 <= idx < len(bins):
                violations += 1                # proposed an overflowing bin: breach
            bins.append(item)
    fullness = [b / capacity for b in bins] if bins else [0.0]
    mean_full = sum(fullness) / len(fullness)
    return {
        "bins_used": len(bins),
        "violations": violations,
        "voluntary_open": voluntary_open,
        "mean_fullness": mean_full,
        "n_items": len(items),
    }
