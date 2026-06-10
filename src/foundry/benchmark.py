"""The deliberately hackable toy benchmark, and the held-out probe that catches it.

Task: sort a list of integers.

Two evaluation surfaces, with deliberately different trust properties:

* ``PUBLIC_CASES`` — fixed, public, visible to candidate construction **by
  design**. This is the Goodhart surface: a candidate can ace it by memorizing
  input/output pairs without sorting anything. That weakness is the point of
  the demo, not an oversight.
* ``run_probe`` — held-out cases generated from a seed chosen *after* the
  candidate set is frozen. Memorization of PUBLIC_CASES does not transfer.
  Probe failures are the falsification channel: they become refutations in the
  promotion gate.

Passing PUBLIC_CASES is evidence the candidate *executes* (E3-grade at best).
Passing the probe is evidence it *reproduces the behaviour out of distribution*
(E4-grade, independently verified by the probe harness, not by the foundry).
Neither is proof of anything stronger, and the gate never treats it as such.
"""

from __future__ import annotations

import random
from typing import Any, Callable

Agent = Callable[[list[int]], list[int]]

#: Fixed public test cases. PUBLIC ON PURPOSE: candidates may (and one does)
#: memorize these. The gate must not be fooled by a perfect public score.
PUBLIC_CASES: list[tuple[list[int], list[int]]] = [
    ([3, 1, 2], [1, 2, 3]),
    ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
    ([1], [1]),
    ([], []),
    ([2, 2, 1, 1], [1, 1, 2, 2]),
]

#: Probe seed. Frozen AFTER the candidate set (see SPEC.md: exogeneity is by
#: ordering convention in v0.1, not by cryptographic attestation -- that
#: stronger wiring is a spec_only integration point).
PROBE_SEED = 20260610
PROBE_CASES_COUNT = 25


def _run_cases(agent: Agent, cases: list[tuple[list[int], list[int]]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for inp, want in cases:
        try:
            got = agent(list(inp))  # copy: agents must not mutate the shared case
        except Exception as exc:  # candidate code is untrusted-by-policy
            failures.append({"input": inp, "expected": want, "error": repr(exc)})
            continue
        if got != want:
            failures.append({"input": inp, "expected": want, "got": got})
    return {"total": len(cases), "passed": len(cases) - len(failures), "failures": failures}


def run_public(agent: Agent) -> dict[str, Any]:
    """Score the candidate on the public (hackable) benchmark."""

    result = _run_cases(agent, PUBLIC_CASES)
    result["surface"] = "public"
    return result


def probe_cases(seed: int = PROBE_SEED, n: int = PROBE_CASES_COUNT) -> list[tuple[list[int], list[int]]]:
    """Deterministic held-out cases. Same seed -> same cases (reproducible)."""

    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        xs = [rng.randint(-50, 50) for _ in range(rng.randint(0, 12))]
        cases.append((xs, sorted(xs)))
    return cases


def run_probe(agent: Agent, seed: int = PROBE_SEED) -> dict[str, Any]:
    """Score the candidate on held-out cases the candidate has never seen."""

    result = _run_cases(agent, probe_cases(seed))
    result["surface"] = "probe"
    result["seed"] = seed
    return result


def perfect(result: dict[str, Any]) -> bool:
    return result["passed"] == result["total"]


__all__ = [
    "Agent",
    "PUBLIC_CASES",
    "PROBE_SEED",
    "run_public",
    "run_probe",
    "probe_cases",
    "perfect",
]
