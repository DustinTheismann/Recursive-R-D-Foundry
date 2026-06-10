"""Evaluator quorum.

A candidate is scored by four independent voters; promotion later requires the
mandatory ones to agree, so no single metric (and no single gameable signal) can
push a candidate through:

  vote 1  static    — source is safe & bounded (verification.static_analyzer)
  vote 2  contained — it ran inside the sandbox without breaching it
  vote 3  contracts — capacity invariant + completeness (verification.contracts)
  vote 4  benchmark — composite fitness clears a floor

`evaluate` returns a full EvalResult including MAP-Elites behavior descriptors.
"""
from __future__ import annotations

import time
from typing import Any

from rsi_foundry.core.types import EvalResult
from rsi_foundry.verification import contracts, static_analyzer


class Harness:
    def __init__(self, benchmark, sandbox, benchmark_floor: float = 0.50):
        self.benchmark = benchmark
        self.sandbox = sandbox
        self.benchmark_floor = benchmark_floor

    def evaluate(self, cid: str, source: str) -> EvalResult:
        # vote 1 — static analysis (pre-execution)
        sreport = static_analyzer.analyze(source)
        if not sreport["ok"]:
            return EvalResult(cid=cid, valid=False, fitness=0.0, static_ok=False,
                              static_report=sreport, quorum={"static": False},
                              error="static:" + ";".join(sreport["issues"]))

        tasks = self.benchmark.tasks()
        instances = [t for _, t in tasks]
        t0 = time.time()
        out = self.sandbox.run(source, instances)
        runtime_ms = (time.time() - t0) * 1000.0

        contained = bool(out.get("contained", False)) and not out.get("breach", True)
        if not out.get("ok"):
            return EvalResult(cid=cid, valid=False, fitness=0.0, static_ok=True,
                              static_report=sreport, runtime_ms=runtime_ms,
                              quorum={"static": True, "contained": contained,
                                      "contracts": False, "benchmark": False},
                              error=out.get("error", "run-failed"))

        results = out["results"]
        per_task: dict[str, float] = {}
        fullness_acc = 0.0
        openness_acc = 0.0
        for (tid, task), r in zip(tasks, results):
            per_task[tid] = self.benchmark.score(tid, r)
            fullness_acc += r.get("mean_fullness", 0.0)
            openness_acc += r.get("voluntary_open", 0) / max(1, r.get("n_items", 1))

        n = max(1, len(results))
        creport = contracts.check_contracts(results, self.benchmark.total_items())
        violation_rate = creport["violation_rate"]
        raw = sum(per_task.values()) / n
        fitness = max(0.0, min(1.0, raw * (1.0 - 0.5 * violation_rate)))

        # MAP-Elites behavior descriptors (deterministic, derived from the suite)
        behavior = [
            round(fullness_acc / n, 4),   # bd0: packing tightness
            round(openness_acc / n, 4),   # bd1: openness (voluntary new bins)
        ]

        quorum = {
            "static": True,
            "contained": contained,
            "contracts": creport["pass"],
            "benchmark": fitness >= self.benchmark_floor,
        }
        valid = quorum["static"] and quorum["contained"] and quorum["contracts"]

        return EvalResult(
            cid=cid, valid=valid, fitness=round(fitness, 5), per_task=per_task,
            runtime_ms=round(runtime_ms, 2), behavior=behavior,
            violation_rate=violation_rate, static_ok=True, static_report=sreport,
            quorum=quorum, error=None,
        )
