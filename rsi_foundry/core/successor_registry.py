"""Registry of governed promotions.

Only candidates that clear every gate land here. The registry tracks the current
champion (highest fitness on the canonical benchmark) and the full promotion
record for audit and RunPack export.
"""
from __future__ import annotations

from typing import Any, Optional

from rsi_foundry.core.types import Candidate, EvalResult, GateReport


class SuccessorRegistry:
    def __init__(self) -> None:
        self.promotions: list[dict[str, Any]] = []
        self._champion: Optional[tuple[Candidate, EvalResult]] = None

    def seed(self, cand: Candidate, res: EvalResult) -> None:
        self._champion = (cand, res)
        self.promotions.append({"candidate": cand.to_dict(), "result": res.to_dict(),
                                "report": None, "kind": "seed"})

    def promote(self, cand: Candidate, res: EvalResult, report: GateReport) -> None:
        self.promotions.append({"candidate": cand.to_dict(), "result": res.to_dict(),
                                "report": report.to_dict(), "kind": "promotion"})
        if self._champion is None or res.fitness > self._champion[1].fitness:
            self._champion = (cand, res)

    def champion(self) -> Optional[tuple[Candidate, EvalResult]]:
        return self._champion

    def champion_candidate(self) -> Optional[Candidate]:
        return self._champion[0] if self._champion else None

    def champion_result(self) -> Optional[EvalResult]:
        return self._champion[1] if self._champion else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "champion": self._champion[0].cid if self._champion else None,
            "champion_fitness": self._champion[1].fitness if self._champion else None,
            "n_promotions": len([p for p in self.promotions if p["kind"] == "promotion"]),
            "promotions": self.promotions,
        }
