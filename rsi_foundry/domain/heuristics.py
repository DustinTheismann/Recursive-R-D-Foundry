"""Genome <-> source for bin-packing heuristics.

A genome is a structured set of feature weights that *compiles to real Python
source* for a `place(item, bins, capacity)` function. The weight family spans
the classic heuristics and everything between them:

    * all weights 0, tie="first", strongly negative new-bin bias  -> FIRST-FIT
    * w_residual < 0 (prefer the snuggest bin)                    -> BEST-FIT
    * w_remaining > 0 (prefer the emptiest bin)                   -> WORST-FIT

Because the genome is structured, we can do three things cleanly:
  1. generate/crossover/mutate candidates (evolution),
  2. compile to genuine code that runs in the sandbox (real execution), and
  3. *ablate one gene at a time* to measure its causal contribution (causal gate).
"""
from __future__ import annotations

import random
from typing import Any

GENES = ("w_residual", "w_remaining", "w_load", "w_tight", "new_bin_bias")


def seed_genome() -> dict[str, Any]:
    """Deliberately weak baseline: a worst-fit-ish heuristic that opens new bins
    too eagerly (high new_bin_bias) and so wastes space (~0.77 fitness). This
    leaves real headroom for the loop to discover best-fit-like packing
    (~0.95) — the recursive climb is genuine, not cosmetic."""
    return {
        "w_residual": 0.0,
        "w_remaining": 1.0,       # prefers emptier bins (worst-fit flavor)
        "w_load": 0.0,
        "w_tight": 0.0,
        "new_bin_bias": 40.0,     # opens a fresh bin even when one could fit
        "tie": "first",
    }


def random_genome(rng: random.Random) -> dict[str, Any]:
    return {
        "w_residual": round(rng.uniform(-3, 3), 4),
        "w_remaining": round(rng.uniform(-3, 3), 4),
        "w_load": round(rng.uniform(-2, 2), 4),
        "w_tight": round(rng.uniform(-2, 2), 4),
        "new_bin_bias": round(rng.uniform(-50, 5), 4),
        "tie": rng.choice(["first", "last"]),
    }


def mutate_genome(genome: dict[str, Any], rng: random.Random,
                  scale: float = 1.0) -> dict[str, Any]:
    g = dict(genome)
    # perturb a random subset of weight genes (Gaussian creep)
    for gene in GENES:
        if rng.random() < 0.5:
            sigma = (0.6 if gene != "new_bin_bias" else 8.0) * scale
            g[gene] = round(float(g[gene]) + rng.gauss(0, sigma), 4)
    if rng.random() < 0.15:
        g["tie"] = "last" if g.get("tie") == "first" else "first"
    return g


def crossover(a: dict[str, Any], b: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    g: dict[str, Any] = {}
    for gene in GENES:
        # blended (arithmetic) crossover keeps the space continuous
        t = rng.random()
        g[gene] = round(t * float(a[gene]) + (1 - t) * float(b[gene]), 4)
    g["tie"] = rng.choice([a.get("tie", "first"), b.get("tie", "first")])
    return g


def ablate(genome: dict[str, Any], gene: str) -> dict[str, Any]:
    """Knock out a single gene to its neutral value (for causal ablation)."""
    g = dict(genome)
    if gene in ("w_residual", "w_remaining", "w_load", "w_tight"):
        g[gene] = 0.0
    elif gene == "new_bin_bias":
        g[gene] = -1.0e9
    return g


def compile_source(genome: dict[str, Any]) -> str:
    """Compile a genome into real, sandbox-executable Python source."""
    wr = float(genome.get("w_residual", 0.0))
    wm = float(genome.get("w_remaining", 0.0))
    wl = float(genome.get("w_load", 0.0))
    wt = float(genome.get("w_tight", 0.0))
    nb = float(genome.get("new_bin_bias", -1.0e9))
    cmp_op = ">" if genome.get("tie", "first") == "first" else ">="
    return f'''def place(item, bins, capacity):
    best_idx = -1
    best_score = -1e18
    for i in range(len(bins)):
        load = bins[i]
        residual = capacity - (load + item)
        if residual < 0:
            continue
        score = ({wr!r}) * (-residual) \\
              + ({wm!r}) * (capacity - load) \\
              + ({wl!r}) * load \\
              + ({wt!r}) * ((load + item) / capacity)
        if score {cmp_op} best_score:
            best_score = score
            best_idx = i
    if best_idx == -1 or best_score < ({nb!r}):
        return -1
    return best_idx
'''
