"""MAP-Elites quality-diversity archive.

Instead of keeping only the single best candidate, we keep the best candidate in
each cell of a discretized behavior space. This is the core anti-fixation move:
the search retains high-performing *and different* solutions, which gives the
proposers a diverse, non-collapsing parent pool and lets the foundry harvest
specialists for different niches.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from rsi_foundry.core.types import Candidate, EvalResult


@dataclass
class Elite:
    candidate: Candidate
    result: EvalResult


class QDArchive:
    def __init__(self, grid: int = 8, dims: int = 2):
        self.grid = grid
        self.dims = dims
        self.cells: dict[tuple[int, ...], Elite] = {}

    def _cell(self, behavior: list[float]) -> tuple[int, ...]:
        b = (behavior + [0.0] * self.dims)[: self.dims]
        return tuple(min(self.grid - 1, max(0, int(v * self.grid))) for v in b)

    def add(self, candidate: Candidate, result: EvalResult) -> bool:
        """Insert if the cell is empty or this beats the incumbent. Returns True if it entered."""
        if not result.valid:
            return False
        cell = self._cell(result.behavior)
        cur = self.cells.get(cell)
        if cur is None or result.fitness > cur.result.fitness:
            self.cells[cell] = Elite(candidate, result)
            return True
        return False

    def elites(self) -> list[Elite]:
        return list(self.cells.values())

    def parents(self, rng, n: int) -> list[Candidate]:
        elites = self.elites()
        if not elites:
            return []
        # Diverse parent selection: sample elites, lightly biased toward fitness.
        weights = [max(1e-6, e.result.fitness) for e in elites]
        chosen = rng.choices(elites, weights=weights, k=min(n, max(1, len(elites) * 2)))
        return [e.candidate for e in chosen[:n]]

    def champion(self) -> Optional[Elite]:
        elites = self.elites()
        return max(elites, key=lambda e: e.result.fitness) if elites else None

    def coverage(self) -> float:
        return round(len(self.cells) / (self.grid ** self.dims), 4)

    def qd_score(self) -> float:
        return round(sum(e.result.fitness for e in self.cells.values()), 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grid": self.grid, "dims": self.dims, "coverage": self.coverage(),
            "qd_score": self.qd_score(),
            "cells": {
                ",".join(map(str, k)): {
                    "cid": e.candidate.cid, "fitness": e.result.fitness,
                    "behavior": e.result.behavior, "origin": e.candidate.origin,
                }
                for k, e in self.cells.items()
            },
        }
