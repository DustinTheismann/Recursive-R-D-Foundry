"""Novelty ledger + anti-collapse diversity tracking.

Implements behavioral novelty search: a candidate's novelty is its mean distance
to its k nearest neighbors in behavior space. The ledger also reports the
population's *occupancy entropy* over the behavior grid, which the orchestrator
watches as an anti-collapse signal — if entropy falls, novelty pressure is
raised so the search does not converge prematurely onto one lineage.
"""
from __future__ import annotations

import math
from typing import Any


def _dist(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class NoveltyLedger:
    def __init__(self, k: int = 5, grid: int = 8):
        self.k = k
        self.grid = grid
        self.behaviors: dict[str, list[float]] = {}
        self.records: dict[str, dict[str, Any]] = {}

    def novelty(self, behavior: list[float]) -> float:
        if not self.behaviors:
            return 1.0
        dists = sorted(_dist(behavior, b) for b in self.behaviors.values())
        kk = dists[: self.k]
        # behavior dims are in [0,1]; max pairwise dist ~ sqrt(dims). normalize.
        norm = math.sqrt(max(1, len(behavior)))
        return min(1.0, (sum(kk) / len(kk)) / norm) if kk else 1.0

    def add(self, cid: str, behavior: list[float], attrs: dict[str, Any] | None = None) -> None:
        self.behaviors[cid] = list(behavior)
        self.records[cid] = dict(attrs or {})

    def _cell(self, behavior: list[float]) -> tuple[int, ...]:
        return tuple(min(self.grid - 1, max(0, int(v * self.grid))) for v in behavior)

    def entropy(self) -> float:
        """Normalized Shannon entropy of behavior-grid occupancy, in [0, 1]."""
        if not self.behaviors:
            return 0.0
        counts: dict[tuple, int] = {}
        for b in self.behaviors.values():
            c = self._cell(b)
            counts[c] = counts.get(c, 0) + 1
        total = sum(counts.values())
        h = -sum((n / total) * math.log(n / total) for n in counts.values())
        hmax = math.log(min(len(self.behaviors), self.grid ** 2)) or 1.0
        return round(h / hmax, 4) if hmax else 0.0

    def size(self) -> int:
        return len(self.behaviors)
