"""AlphaEvolve-style evolutionary loop.

The workhorse: generate many offspring from the quality-diversity parent pool and
let the gates + archive select. Occasionally fuse in a registered best-attribute
gene (recursive capability fusion) so good traits propagate across lineages.
"""
from __future__ import annotations

from rsi_foundry.core.types import Candidate
from rsi_foundry.loops.base import LoopContext
from rsi_foundry.proposers.base import build_candidate


class AlphaEvolveLoop:
    name = "alphaevolve"

    def __init__(self, offspring: int = 6):
        self.offspring = offspring

    def generate(self, ctx: LoopContext) -> list[Candidate]:
        kids = ctx.proposer.propose(ctx.parents, ctx.rng, self.offspring,
                                    ctx.priors, ctx.generation)
        # capability fusion: graft a proven gene into a fraction of offspring
        if ctx.registry is not None:
            fused: list[Candidate] = []
            for k in kids:
                if ctx.rng.random() < 0.25:
                    g = ctx.registry.graft(k.genome, ctx.rng)
                    fused.append(build_candidate(g, k.parents, self.name + "+fuse",
                                                 ctx.generation))
                else:
                    fused.append(k)
            kids = fused
        return kids
