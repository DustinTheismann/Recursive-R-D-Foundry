"""Darwin Gödel Machine-style self-editing loop.

The current champion proposes *edits to itself* as patches rather than mutating a
live system. Two patch families:
  * local self-edits — small perturbations of the champion genome, and
  * self-fusion      — the champion grafts a registered best-attribute gene from
                       another lineage onto itself.
Patches are evaluated and gated exactly like any other candidate; only governed
improvements are promoted, so self-editing never bypasses assurance.
"""
from __future__ import annotations

from rsi_foundry.core.types import Candidate
from rsi_foundry.loops.base import LoopContext
from rsi_foundry.proposers.base import build_candidate


class DGMLoop:
    name = "dgm"

    def __init__(self, patches: int = 3):
        self.patches = patches

    def generate(self, ctx: LoopContext) -> list[Candidate]:
        if ctx.champion is None:
            return []
        champ = ctx.champion
        kids = ctx.proposer.propose([champ], ctx.rng, self.patches,
                                    ctx.priors, ctx.generation)
        out: list[Candidate] = []
        for k in kids:
            # re-tag so lineage shows the self-edit explicitly
            out.append(build_candidate(k.genome, [champ.cid], self.name,
                                       ctx.generation))
        # one explicit self-fusion patch
        if ctx.registry is not None:
            g = ctx.registry.graft(dict(champ.genome), ctx.rng)
            out.append(build_candidate(g, [champ.cid], self.name + "+self_fuse",
                                       ctx.generation))
        return out
