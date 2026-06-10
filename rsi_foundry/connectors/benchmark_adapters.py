"""Benchmark adapters.

A benchmark turns a problem domain into (task_id -> instance) plus a scorer in
[0, 1]. The local bin-packing benchmark is fully offline and is what runs here.
The `BenchmarkAdapter` protocol is deliberately tiny so heavier external
benchmarks — SWE-bench Lite, MLE-Bench, a local-repo task set — can drop in
behind the same interface (stubs included, raising until their data/runners are
wired up).
"""
from __future__ import annotations

import random
from typing import Any, Protocol

from rsi_foundry.domain import binpack


class BenchmarkAdapter(Protocol):
    def tasks(self) -> list[tuple[str, dict]]: ...
    def score(self, task_id: str, result: dict) -> float: ...
    def total_items(self) -> int: ...


class LocalBinPackBenchmark:
    """Held-out suite of bin-packing instances drawn from a set of EnvSpecs."""

    def __init__(self, envs: list[binpack.EnvSpec], rng: random.Random,
                 per_env: int = 4):
        self._tasks: list[tuple[str, dict]] = []
        self._lb: dict[str, int] = {}
        for env in envs:
            for k in range(per_env):
                inst = binpack.make_instance(env, rng)
                tid = f"{env.name}#{k}"
                self._tasks.append((tid, {"capacity": inst.capacity, "items": inst.items}))
                self._lb[tid] = binpack.lower_bound(inst)

    def tasks(self) -> list[tuple[str, dict]]:
        return list(self._tasks)

    def total_items(self) -> int:
        return sum(len(t["items"]) for _, t in self._tasks)

    def score(self, task_id: str, result: dict) -> float:
        bins_used = result.get("bins_used", 0)
        if bins_used <= 0:
            return 0.0
        return self._lb[task_id] / bins_used


# --- External adapters (interface-compatible stubs) ----------------------------

class SWEBenchLiteAdapter:
    """Placeholder for a SWE-bench-Lite style code-repair benchmark.

    Wire `tasks()` to yield repo+issue fixtures and `score()` to run the project
    test suite inside the Docker containment backend. Same protocol as above.
    """

    def tasks(self) -> list[tuple[str, dict]]:
        raise NotImplementedError("SWE-bench adapter requires dataset + docker daemon")

    def score(self, task_id: str, result: dict) -> float:
        raise NotImplementedError

    def total_items(self) -> int:
        return 0


class MLEBenchAdapter:
    """Placeholder for an MLE-Bench style ML-engineering benchmark."""

    def tasks(self) -> list[tuple[str, dict]]:
        raise NotImplementedError("MLE-Bench adapter requires dataset + runners")

    def score(self, task_id: str, result: dict) -> float:
        raise NotImplementedError

    def total_items(self) -> int:
        return 0
