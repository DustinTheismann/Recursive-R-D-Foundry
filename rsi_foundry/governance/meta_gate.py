"""Meta-gate: recursive governance of the gates themselves.

The promotion thresholds are treated as a successor lineage that the foundry can
improve — but under a strict monotonicity invariant so governance can never
quietly weaken itself:

  * TIGHTENING a threshold is always allowed (more caution is free).
  * LOOSENING a threshold is allowed ONLY if cumulative assurance has grown by a
    margin since the last loosening — i.e. the system has *earned* the right to
    take more risk. You may never loosen faster than assurance accrues.

Triggers:
  * A containment breach or a post-promotion regression -> tighten immediately.
  * A prolonged drought of promotions while HALF-LIFE is GREEN and debt is zero
    -> the gates may be too strict; propose a small, assurance-backed loosening.

This is "improve the governance layer" made safe: the same HALF-LIFE logic that
governs capability also governs how the governor may relax.
"""
from __future__ import annotations

from typing import Any

from rsi_foundry.governance.promotion import PromotionPolicy


class MetaGate:
    def __init__(self, policy: PromotionPolicy, half_life,
                 loosen_assurance_margin: float = 0.5,
                 drought_cycles: int = 4):
        self.policy = policy
        self.half_life = half_life
        self.loosen_assurance_margin = loosen_assurance_margin
        self.drought_cycles = drought_cycles
        self._assurance_at_last_loosen = 0.0
        self._dry_cycles = 0
        self.log: list[dict[str, Any]] = []

    def on_breach_or_regression(self, kind: str) -> None:
        """Always-allowed tightening."""
        before = self.policy.fitness_delta_min
        self.policy.fitness_delta_min = round(before * 1.5 + 1e-4, 6)
        self.policy.causal_min_ablation = round(self.policy.causal_min_ablation * 1.5 + 1e-5, 6)
        self.log.append({"action": "tighten", "trigger": kind,
                         "fitness_delta_min": self.policy.fitness_delta_min,
                         "allowed": True})

    def on_cycle_end(self, promoted_this_cycle: int) -> dict[str, Any] | None:
        """Maybe propose an assurance-backed loosening after a promotion drought."""
        if promoted_this_cycle > 0:
            self._dry_cycles = 0
            return None
        self._dry_cycles += 1
        if self._dry_cycles < self.drought_cycles:
            return None

        healthy = (self.half_life.state == "GREEN" and self.half_life.debt <= 1e-9)
        assurance_growth = self.half_life.cumulative_assurance - self._assurance_at_last_loosen
        earned = assurance_growth >= self.loosen_assurance_margin

        if healthy and earned:
            self.policy.fitness_delta_min = round(max(1e-5, self.policy.fitness_delta_min * 0.6), 6)
            self._assurance_at_last_loosen = self.half_life.cumulative_assurance
            self._dry_cycles = 0
            entry = {"action": "loosen", "trigger": "promotion_drought",
                     "fitness_delta_min": self.policy.fitness_delta_min,
                     "assurance_growth": round(assurance_growth, 4), "allowed": True}
        else:
            entry = {"action": "loosen", "trigger": "promotion_drought",
                     "blocked_reason": ("unhealthy" if not healthy else "assurance_not_earned"),
                     "assurance_growth": round(assurance_growth, 4), "allowed": False}
        self.log.append(entry)
        return entry
