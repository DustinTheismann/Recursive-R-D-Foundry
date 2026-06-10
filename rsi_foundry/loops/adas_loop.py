"""ADAS-style automated design of agentic systems.

Instead of searching only over candidates, ADAS searches over *designs* — here,
the search policy itself: how aggressively to mutate. It runs a UCB bandit over a
small archive of designs, allocates the next batch to the design with the best
upper-confidence estimate, and learns from which designs yield promotions. This
is the foundry improving the agent that improves the agents.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from rsi_foundry.core.types import Candidate
from rsi_foundry.loops.base import LoopContext


@dataclass
class Design:
    name: str
    scale: float
    pulls: int = 0
    reward: float = 0.0

    @property
    def mean(self) -> float:
        return self.reward / self.pulls if self.pulls else 0.0


class ADASLoop:
    name = "adas"

    def __init__(self, offspring: int = 3):
        self.offspring = offspring
        self.designs: list[Design] = [
            Design("conservative", 0.4),
            Design("balanced", 1.0),
            Design("aggressive", 2.0),
        ]
        self._total = 0
        self._last: str | None = None

    def _select(self) -> Design:
        self._total += 1
        for d in self.designs:
            if d.pulls == 0:
                return d
        c = 1.4
        return max(self.designs,
                   key=lambda d: d.mean + c * math.sqrt(math.log(self._total) / d.pulls))

    def generate(self, ctx: LoopContext) -> list[Candidate]:
        design = self._select()
        self._last = design.name
        design.pulls += 1
        scaled = {g: design.scale * ctx.priors.get(g, 1.0)
                  for g in ("w_residual", "w_remaining", "w_load", "w_tight", "new_bin_bias")}
        kids = ctx.proposer.propose(ctx.parents, ctx.rng, self.offspring,
                                    scaled, ctx.generation)
        for k in kids:
            k.meta["design"] = design.name
        return kids

    def reward(self, design_name: str, value: float) -> None:
        for d in self.designs:
            if d.name == design_name:
                d.reward += value

    def to_dict(self) -> dict:
        return {d.name: {"pulls": d.pulls, "mean": round(d.mean, 4)} for d in self.designs}
