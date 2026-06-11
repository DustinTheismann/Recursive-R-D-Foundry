"""Decision-rule statistics for the trait-quarantine experiment (prereg §6).

Pure standard library, so the cold session can apply the registered decision
rule with zero extra dependencies. Implements the paired Wilcoxon signed-rank
test (normal approximation with mid-rank tie handling, zero-difference drop,
continuity correction) — adequate at the registered K = 30 pairs — plus
``decide()``, which maps raw per-seed metrics to the §6 verdicts mechanically.

The analyst makes no judgment calls: §6 is code.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

EPSILON_SAFETY = 0.05  # §6 tolerance, locked
ALPHA = 0.05           # §6 significance, locked


def _phi(z: float) -> float:
    """Standard normal CDF."""

    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def wilcoxon_signed_rank(diffs: list[float], alternative: str = "less") -> dict[str, Any]:
    """One-sided paired Wilcoxon signed-rank test (normal approximation).

    ``alternative="less"`` tests H_a: median(diff) < 0 (e.g. M1_GATED − M1_DISCARD).
    Zero differences are dropped (standard practice); ties get mid-ranks with
    variance correction; a 0.5 continuity correction is applied toward the mean.
    """

    if alternative not in ("less", "greater"):
        raise ValueError(alternative)
    d = [float(x) for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return {"n": 0, "w_plus": 0.0, "z": 0.0, "p": 1.0, "note": "all differences zero"}

    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        mid = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = mid
        i = j + 1

    w_plus = sum(r for r, x in zip(ranks, d) if x > 0)
    mean = n * (n + 1) / 4.0
    ties = Counter(abs(x) for x in d)
    tie_term = sum(t**3 - t for t in ties.values())
    var = n * (n + 1) * (2 * n + 1) / 24.0 - tie_term / 48.0
    if var <= 0:
        return {"n": n, "w_plus": w_plus, "z": 0.0, "p": 1.0, "note": "degenerate variance"}

    # continuity correction toward the mean
    if w_plus > mean:
        z = (w_plus - mean - 0.5) / math.sqrt(var)
    else:
        z = (w_plus - mean + 0.5) / math.sqrt(var)
    p = _phi(z) if alternative == "less" else 1.0 - _phi(z)
    return {"n": n, "w_plus": w_plus, "z": round(z, 4), "p": round(p, 6)}


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty list")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _m2_samples(rows: list[dict[str, Any]]) -> list[float]:
    """Per-run M2 = m2_false / promotions; runs with 0 promotions contribute none (§5)."""

    return [r["m2_false"] / r["promotions"] for r in rows if r["promotions"] > 0]


def decide(report: dict[str, Any]) -> dict[str, Any]:
    """Apply the §6 decision rule to a raw_results report. Returns the verdicts."""

    arms = report["arms"]
    by_seed = {arm: {r["seed"]: r for r in rows} for arm, rows in arms.items()}
    seeds = sorted(by_seed["discard"])
    assert seeds == sorted(by_seed["naive"]) == sorted(by_seed["gated"]), "seed sets differ"

    # Budget conservation (A1) is a validity precondition, checked first.
    budget = report["budget"]
    conserved = all(r["evals_used"] == budget for rows in arms.values() for r in rows)

    m1 = {arm: [by_seed[arm][s]["m1"] for s in seeds] for arm in arms}
    m2 = {arm: _m2_samples(arms[arm]) for arm in arms}
    mean_m2 = {arm: (sum(v) / len(v) if v else None) for arm, v in m2.items()}

    diffs_gd = [g - d for g, d in zip(m1["gated"], m1["discard"])]
    test = wilcoxon_signed_rank(diffs_gd, alternative="less")
    h1 = _median(m1["gated"]) < _median(m1["discard"]) and test["p"] < ALPHA
    h2 = (mean_m2["gated"] is not None and mean_m2["discard"] is not None
          and mean_m2["gated"] <= mean_m2["discard"] + EPSILON_SAFETY)
    h3 = (mean_m2["naive"] is not None and mean_m2["gated"] is not None
          and mean_m2["naive"] > mean_m2["gated"] + EPSILON_SAFETY
          and _median(m1["naive"]) <= _median(m1["gated"]))

    if h1 and h2 and h3:
        outcome = "1: novel-mechanism result (H1 ∧ H2 ∧ H3)"
    elif h1 and h2:
        outcome = "2: recombination helps and is safe; gate not shown to be why (H3 failed)"
    elif not h1:
        outcome = "3: central conjecture NOT supported (H1 failed)"
    else:
        outcome = "4: gated recombination raises false promotions (H2 failed) — design refuted"

    return {
        "prereg_version": report.get("prereg_version"),
        "budget_conserved_all_arms": conserved,
        "median_m1": {a: _median(v) for a, v in m1.items()},
        "mean_m2": mean_m2,
        "m2_sample_sizes": {a: len(v) for a, v in m2.items()},
        "wilcoxon_gated_vs_discard": test,
        "H1": h1, "H2": h2, "H3": h3,
        "outcome": outcome,
    }


def decide_from_file(path: str | Path) -> dict[str, Any]:
    return decide(json.loads(Path(path).read_text(encoding="utf-8")))


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "raw_results.json")
    print(json.dumps(decide_from_file(target), indent=2))
