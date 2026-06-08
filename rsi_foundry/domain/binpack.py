"""The benchmark domain: online bin-packing heuristic evolution.

Why this domain: it is a real, well-studied online optimization problem where
heuristics (next-fit, first-fit, best-fit, ...) have genuinely different
performance. That gives us (a) real code to generate and execute, (b) a smooth
continuous fitness, (c) machine-checkable contracts (never overflow a bin), (d)
natural behavior descriptors for quality-diversity, and (e) a difficulty axis
POET can coevolve. No network, no GPU, fully deterministic.

The *simulator* that actually runs candidate code lives in
`rsi_foundry.sandbox.simulate` (trusted code), so a buggy or adversarial
candidate can never corrupt the bin accounting — it only ever returns a bin
index, and the trusted simulator decides what that means.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvSpec:
    """A POET environment: the distribution that generates problem instances."""

    name: str
    capacity: int = 100
    n_items: int = 60
    size_lo: int = 10
    size_hi: int = 70
    # difficulty knobs POET can push on:
    bimodal: float = 0.0     # 0..1 fraction of items drawn from a large-size mode
    large_lo: int = 60
    large_hi: int = 95

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "capacity": self.capacity, "n_items": self.n_items,
            "size_lo": self.size_lo, "size_hi": self.size_hi, "bimodal": self.bimodal,
            "large_lo": self.large_lo, "large_hi": self.large_hi,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EnvSpec":
        return cls(**d)


@dataclass
class Instance:
    capacity: int
    items: list[int]


def make_instance(spec: EnvSpec, rng: random.Random) -> Instance:
    items: list[int] = []
    for _ in range(spec.n_items):
        if rng.random() < spec.bimodal:
            items.append(rng.randint(spec.large_lo, min(spec.large_hi, spec.capacity)))
        else:
            items.append(rng.randint(spec.size_lo, min(spec.size_hi, spec.capacity)))
    return Instance(capacity=spec.capacity, items=items)


def make_suite(spec: EnvSpec, rng: random.Random, n: int) -> list[Instance]:
    return [make_instance(spec, rng) for _ in range(n)]


def lower_bound(inst: Instance) -> int:
    """Optimal number of bins is at least total / capacity (ceil)."""
    return max(1, math.ceil(sum(inst.items) / inst.capacity))


def instance_score(inst: Instance, bins_used: int) -> float:
    """1.0 == provably optimal; lower is worse."""
    if bins_used <= 0:
        return 0.0
    return lower_bound(inst) / bins_used


def default_env() -> EnvSpec:
    return EnvSpec(name="baseline")


def starter_envs() -> list[EnvSpec]:
    """Initial POET niche population — easy → mixed."""
    return [
        EnvSpec(name="easy", n_items=40, size_lo=5, size_hi=40),
        EnvSpec(name="baseline"),
        EnvSpec(name="mixed", n_items=60, size_lo=10, size_hi=70, bimodal=0.25),
    ]
