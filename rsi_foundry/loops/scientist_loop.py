"""AI-Scientist loop: hypothesis -> experiment -> ablation -> review.

Turns improvement into knowledge. Each invocation forms a hypothesis about which
gene drives the champion's performance, runs an ablation experiment to test it,
records a structured review artifact (kept in the RunPack), and then proposes a
follow-up candidate that *amplifies the most causal gene* — an experiment-driven,
rather than random, proposal.
"""
from __future__ import annotations

from typing import Any

from rsi_foundry.core.types import Candidate
from rsi_foundry.governance.causal_gate import ablation_study
from rsi_foundry.loops.base import LoopContext
from rsi_foundry.proposers.base import build_candidate


class ScientistLoop:
    name = "scientist"

    def __init__(self) -> None:
        self.last_review: dict[str, Any] | None = None

    def generate(self, ctx: LoopContext) -> list[Candidate]:
        champ = ctx.champion
        if champ is None or ctx.champion_result is None or ctx.harness is None:
            return []

        deltas = ablation_study(champ, ctx.champion_result, ctx.harness)
        if not deltas:
            return []
        most_causal = max(deltas, key=deltas.get)
        effect = deltas[most_causal]

        review = {
            "hypothesis": f"gene '{most_causal}' is the primary driver of champion fitness",
            "champion": champ.cid,
            "champion_fitness": ctx.champion_result.fitness,
            "ablation": deltas,
            "conclusion": (
                f"supported (Δ={effect:+.4f})" if effect > 0
                else "not supported; champion robust to single-gene removal"
            ),
            "generation": ctx.generation,
        }
        self.last_review = review

        # experiment-driven proposal: amplify the most causal gene
        g = dict(champ.genome)
        if most_causal in ("w_residual", "w_remaining", "w_load", "w_tight"):
            g[most_causal] = round(float(g[most_causal]) * 1.5 + 0.1, 4)
        elif most_causal == "new_bin_bias":
            g[most_causal] = round(float(g[most_causal]) - 2.0, 4)
        return [build_candidate(g, [champ.cid], self.name, ctx.generation)]
