"""POET-style environment coevolution.

The benchmark is not static. As successors get stronger, POET mutates the
problem distribution toward harder instances and admits a new environment only
if it satisfies a *minimal criterion*: the current champion must score inside a
band — hard enough to be interesting, not so hard as to be hopeless. This keeps
the evaluation ecology evolving with the agents and prevents overfitting a fixed
benchmark.
"""
from __future__ import annotations

import random
from typing import Any

from rsi_foundry.domain import binpack


class POET:
    def __init__(self, envs: list[binpack.EnvSpec], rng: random.Random,
                 min_score: float = 0.55, max_score: float = 0.9,
                 max_envs: int = 6):
        self.envs = list(envs)
        self.rng = rng
        self.min_score = min_score
        self.max_score = max_score
        self.max_envs = max_envs
        self._counter = 0

    def current(self) -> list[binpack.EnvSpec]:
        return list(self.envs)

    def _mutate_env(self, parent: binpack.EnvSpec) -> binpack.EnvSpec:
        self._counter += 1
        r = self.rng
        return binpack.EnvSpec(
            name=f"poet{self._counter}",
            capacity=parent.capacity,
            n_items=max(20, parent.n_items + r.choice([-10, 0, 10, 20])),
            size_lo=max(1, parent.size_lo + r.choice([-5, 0, 5])),
            size_hi=min(parent.capacity, parent.size_hi + r.choice([0, 5, 10])),
            bimodal=min(0.8, max(0.0, parent.bimodal + r.choice([0.0, 0.1, 0.2]))),
            large_lo=parent.large_lo,
            large_hi=min(parent.capacity, parent.large_hi + r.choice([0, 5])),
        )

    def step(self, score_env) -> dict[str, Any]:
        """Try to spawn one harder, minimally-criterion-satisfying environment.

        `score_env(env) -> float` is the champion's score on a fresh instance of
        `env` (supplied by the orchestrator).
        """
        info: dict[str, Any] = {"added": None, "tested": None, "score": None}
        if not self.envs:
            return info
        parent = self.rng.choice(self.envs)
        child = self._mutate_env(parent)
        score = score_env(child)
        info["tested"] = child.name
        info["score"] = round(score, 4)
        if self.min_score <= score <= self.max_score:
            self.envs.append(child)
            info["added"] = child.name
            if len(self.envs) > self.max_envs:
                # retire the easiest-named original-ish env to bound cost
                self.envs.pop(0)
        return info
