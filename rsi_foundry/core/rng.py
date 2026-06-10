"""Deterministic, hierarchical RNG.

Reproducibility is a first-class assurance property: a RunPack must replay
bit-for-bit. We derive every stream from a single root seed via stable hashing
so that independent components (proposer, POET, ablation sampling) never share
state yet always reproduce.
"""
from __future__ import annotations

import hashlib
import random


def _derive_seed(root: int, label: str) -> int:
    h = hashlib.sha256(f"{root}:{label}".encode()).digest()
    return int.from_bytes(h[:8], "big")


class RNGHub:
    """Spawns named, independent, reproducible random streams from one seed."""

    def __init__(self, root_seed: int):
        self.root_seed = int(root_seed)
        self._streams: dict[str, random.Random] = {}

    def stream(self, label: str) -> random.Random:
        if label not in self._streams:
            self._streams[label] = random.Random(_derive_seed(self.root_seed, label))
        return self._streams[label]

    def fork(self, label: str) -> "RNGHub":
        return RNGHub(_derive_seed(self.root_seed, "fork:" + label))
