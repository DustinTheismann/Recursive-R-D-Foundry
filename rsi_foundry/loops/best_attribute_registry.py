"""Best Attribute Registry — recursive capability fusion.

Losing candidates are not discarded. For each tracked metric (peak fitness, low
violation rate, fast runtime, best score on a specific niche) we remember which
*gene values* achieved it. New candidates can then be "grafted" with a proven
gene from a different lineage — partial breakthroughs are harvested even when the
whole candidate is rejected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rsi_foundry.core.types import Candidate, EvalResult
from rsi_foundry.domain import heuristics


@dataclass
class Attribute:
    metric: str
    value: float
    gene: str
    gene_value: Any
    cid: str


class BestAttributeRegistry:
    def __init__(self) -> None:
        self.best: dict[str, Attribute] = {}

    def observe(self, cand: Candidate, res: EvalResult) -> list[str]:
        """Record any metric records this candidate set. Returns updated metrics.

        Only *deterministic* signals are tracked — never wall-clock runtime —
        because the registry feeds `graft`, which is on the search path, and the
        search must replay bit-for-bit.
        """
        updated: list[str] = []
        candidates = {
            "fitness": res.fitness,
            "low_violation": 1.0 - res.violation_rate,
            "tightness": res.behavior[0] if res.behavior else 0.0,
        }
        # the gene most responsible for "snug" packing is w_residual; track it
        # for fitness, new_bin_bias for the low-violation niche, w_remaining for
        # the tightness (behavior) niche.
        gene_for = {"fitness": "w_residual", "low_violation": "new_bin_bias",
                    "tightness": "w_remaining"}
        for metric, value in candidates.items():
            cur = self.best.get(metric)
            if cur is None or value > cur.value:
                gene = gene_for[metric]
                self.best[metric] = Attribute(metric, value, gene,
                                              cand.genome.get(gene), cand.cid)
                updated.append(metric)
        return updated

    def graft(self, genome: dict[str, Any], rng) -> dict[str, Any]:
        """Inject one registered best-gene value into a genome (trait fusion)."""
        if not self.best:
            return genome
        g = dict(genome)
        attr = rng.choice(list(self.best.values()))
        if attr.gene_value is not None and attr.gene in heuristics.GENES:
            g[attr.gene] = attr.gene_value
        return g

    def to_dict(self) -> dict[str, Any]:
        return {m: vars(a) for m, a in self.best.items()}
