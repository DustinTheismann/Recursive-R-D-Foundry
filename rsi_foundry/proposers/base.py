"""Proposer interface + candidate construction helper.

A proposer turns parent candidates (and learned priors) into new successor
candidates. Every proposer goes through `build_candidate` so lineage ids stay
content-addressed and consistent regardless of who proposed them.
"""
from __future__ import annotations

from typing import Any, Protocol

from rsi_foundry.core.lineage import candidate_id
from rsi_foundry.core.types import Candidate
from rsi_foundry.domain.heuristics import compile_source


def build_candidate(genome: dict[str, Any], parents: list[str], origin: str,
                    generation: int) -> Candidate:
    source = compile_source(genome)
    cid = candidate_id(source, genome, parents)
    return Candidate(cid=cid, source=source, genome=genome,
                     parents=list(parents), generation=generation, origin=origin)


class Proposer(Protocol):
    name: str

    def propose(self, parents: list[Candidate], rng, n: int,
                priors: dict[str, float] | None, generation: int) -> list[Candidate]:
        ...
