"""LLM proposer (pluggable, optional).

If the `anthropic` SDK and an API key are present, this proposer asks Claude to
read the parent heuristic plus a digest of recent *failures* and emit an improved
genome as JSON. Otherwise it transparently falls back to the mutation proposer,
so the loop is identical whether or not a model is wired in.

This is the seam where "simulated proposer" becomes "real code generation": the
prompt carries the current best source and the failure ledger, exactly the
self-editing-coding-agent / SEAL pattern.
"""
from __future__ import annotations

import json
import os
from typing import Any

from rsi_foundry.core.types import Candidate
from rsi_foundry.domain import heuristics
from rsi_foundry.proposers.base import build_candidate
from rsi_foundry.proposers.mutation_proposer import MutationProposer

_SYSTEM = (
    "You improve an online bin-packing heuristic. You are given a parent genome "
    "(feature weights for choosing a bin) and a digest of recent failures. "
    "Return ONLY a JSON object with keys w_residual, w_remaining, w_load, "
    "w_tight, new_bin_bias (floats) and tie ('first'|'last'). Prefer snug "
    "(best-fit-like) packing; avoid proposing overflowing bins."
)


class LLMProposer:
    name = "llm"

    def __init__(self, model: str = "claude-opus-4-8"):
        self.model = model
        self._fallback = MutationProposer()
        self._client = self._maybe_client()

    @staticmethod
    def _maybe_client():
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None
        try:
            import anthropic  # type: ignore
            return anthropic.Anthropic()
        except Exception:
            return None

    @property
    def active(self) -> bool:
        return self._client is not None

    def propose(self, parents: list[Candidate], rng, n: int,
                priors: dict[str, float] | None = None,
                generation: int = 0) -> list[Candidate]:
        if not self.active or not parents:
            return self._fallback.propose(parents, rng, n, priors, generation)
        out: list[Candidate] = []
        for _ in range(n):
            parent = rng.choice(parents)
            genome = self._ask(parent, parents)
            if genome is None:
                out.extend(self._fallback.propose([parent], rng, 1, priors, generation))
            else:
                out.append(build_candidate(genome, [parent.cid], self.name, generation))
        return out

    def _ask(self, parent: Candidate, parents: list[Candidate]) -> dict[str, Any] | None:
        digest = "; ".join(
            f"{p.origin}:fit={p.meta.get('fitness', '?')}" for p in parents[:5]
        )
        prompt = (
            f"Parent genome: {json.dumps(parent.genome)}\n"
            f"Recent population digest: {digest}\n"
            "Return improved genome JSON only."
        )
        try:
            msg = self._client.messages.create(
                model=self.model, max_tokens=512, system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(getattr(b, "text", "") for b in msg.content)
            start, end = text.find("{"), text.rfind("}")
            genome = json.loads(text[start:end + 1])
            # validate / coerce
            for k in heuristics.GENES:
                genome[k] = float(genome[k])
            genome["tie"] = "last" if str(genome.get("tie")) == "last" else "first"
            return genome
        except Exception:
            return None
