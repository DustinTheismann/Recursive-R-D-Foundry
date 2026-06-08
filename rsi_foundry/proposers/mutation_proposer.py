"""Deterministic mutation proposer (the always-available code generator).

Generates successor source by mutating/recombining parent genomes. It consumes
*priors* produced by the SEAL failure-mining loop: a per-gene weight that biases
which genes to perturb. Genes that historically led to failures are perturbed
less; genes correlated with promotion are perturbed more. That makes the
generator itself a thing that improves over time — the foundry improving its
own proposer.
"""
from __future__ import annotations

from typing import Any

from rsi_foundry.core.types import Candidate
from rsi_foundry.domain import heuristics
from rsi_foundry.proposers.base import build_candidate


class MutationProposer:
    name = "mutation"

    def propose(self, parents: list[Candidate], rng, n: int,
                priors: dict[str, float] | None = None,
                generation: int = 0) -> list[Candidate]:
        priors = priors or {}
        out: list[Candidate] = []
        for _ in range(n):
            if not parents:
                g = heuristics.random_genome(rng)
                out.append(build_candidate(g, [], self.name, generation))
                continue
            if len(parents) >= 2 and rng.random() < 0.4:
                a, b = rng.sample(parents, 2)
                child = heuristics.crossover(a.genome, b.genome, rng)
                child = self._guided_mutate(child, rng, priors)
                out.append(build_candidate(child, [a.cid, b.cid], self.name, generation))
            else:
                p = rng.choice(parents)
                child = self._guided_mutate(p.genome, rng, priors)
                out.append(build_candidate(child, [p.cid], self.name, generation))
        return out

    def _guided_mutate(self, genome: dict[str, Any], rng,
                       priors: dict[str, float]) -> dict[str, Any]:
        g = dict(genome)
        for gene in heuristics.GENES:
            # prior in (0, 2): >1 perturb more, <1 perturb less. Default 1.
            w = max(0.05, float(priors.get(gene, 1.0)))
            if rng.random() < min(0.95, 0.5 * w):
                sigma = (0.6 if gene != "new_bin_bias" else 8.0) * w
                g[gene] = round(float(g[gene]) + rng.gauss(0, sigma), 4)
        if rng.random() < 0.15:
            g["tie"] = "last" if g.get("tie") == "first" else "first"
        return g
