"""SEAL-style failure-mined self-training.

Every evaluated candidate — *especially the rejected ones* — becomes a training
example and updates the proposer's per-gene priors. Genes whose changes
correlate with improvement get explored more; genes whose changes correlate with
failure get explored less. Governance thereby becomes a *training signal*, not
just a blocker, and the generator improves recursively.

`training_examples()` exports the mined dataset (parent -> child edit, outcome,
narrative) in a shape ready for real preference/supervised fine-tuning when an
LLM proposer is wired in.
"""
from __future__ import annotations

from typing import Any

from rsi_foundry.domain.heuristics import GENES


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class SEALLoop:
    name = "seal"

    def __init__(self, lr: float = 0.3, k: float = 1.2):
        self.lr = lr
        self.k = k
        self.credit: dict[str, float] = {g: 0.0 for g in GENES}
        self.examples: list[dict[str, Any]] = []

    def observe(self, parent_genome: dict | None, child_genome: dict,
                parent_fit: float | None, child_fit: float, promoted: bool,
                cid: str) -> None:
        if parent_genome is None or parent_fit is None:
            return
        delta = child_fit - parent_fit
        changed = {g: abs(float(child_genome.get(g, 0)) - float(parent_genome.get(g, 0)))
                   for g in GENES}
        total = sum(changed.values()) or 1.0
        for g in GENES:
            attribution = changed[g] / total
            signal = attribution * delta + (0.05 * attribution if promoted else 0.0)
            self.credit[g] = (1 - self.lr) * self.credit[g] + self.lr * signal

        self.examples.append({
            "cid": cid,
            "edit": {g: round(float(child_genome.get(g, 0)) - float(parent_genome.get(g, 0)), 4)
                     for g in GENES if changed[g] > 1e-9},
            "delta": round(delta, 5),
            "label": "promote" if promoted else "reject",
            "narrative": (f"{'PROMOTED' if promoted else 'REJECTED'}: edit changed "
                          f"{[g for g in GENES if changed[g] > 1e-9]} for Δfitness={delta:+.4f}"),
        })

    def priors(self) -> dict[str, float]:
        return {g: round(_clip(1.0 + self.k * self.credit[g], 0.1, 2.0), 4)
                for g in GENES}

    def training_examples(self) -> list[dict[str, Any]]:
        return list(self.examples)

    def snapshot(self) -> dict[str, Any]:
        return {"credit": {g: round(v, 4) for g, v in self.credit.items()},
                "priors": self.priors(), "n_examples": len(self.examples)}
