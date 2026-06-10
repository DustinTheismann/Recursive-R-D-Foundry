"""HALF-LIFE assurance control plane.

The core safety invariant: *capability must not expand faster than assurance can
absorb, test, and constrain it.* We model this as an assurance-credit ledger.

  * Assurance-producing work each cycle (contracts proven, ablations run,
    containment checks passed, behavior-space coverage gained) mints assurance
    credit.
  * Promoting a candidate that raises capability by `drift` *spends*
    `drift / safety_factor` credit. If there is not enough credit, the promotion
    is blocked and the unmet amount is booked as assurance debt.

Operational states, escalating with stress:

  GREEN  — capability expansion comfortably within the assurance budget
  AMBER  — budget tight; expansion allowed but flagged
  RED    — assurance cannot absorb the proposed drift; promotion frozen
  BLACK  — containment breach or sustained RED; the loop halts

This is the gate that makes the difference between "one AI mutating itself
freely" and "a governed recursive R&D factory".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HalfLifeDecision:
    state: str
    allow: bool
    capability: float
    drift: float
    required_credit: float
    available_credit: float
    debt: float
    reason: str


class HalfLifeController:
    def __init__(self, safety_factor: float = 2.0, amber_util: float = 0.5,
                 black_strikes_to_halt: int = 3):
        self.safety_factor = safety_factor
        self.amber_util = amber_util
        self.black_strikes_to_halt = black_strikes_to_halt
        self.capability = 0.0
        self.assurance_credit = 0.0
        self.cumulative_assurance = 0.0
        self.debt = 0.0
        self.state = "GREEN"
        self.black_strikes = 0
        self.history: list[dict[str, Any]] = []

    # ---- assurance accrual --------------------------------------------------
    def add_assurance(self, renewal: float) -> None:
        renewal = max(0.0, float(renewal))
        self.assurance_credit += renewal
        self.cumulative_assurance += renewal

    def set_baseline_capability(self, cap: float) -> None:
        self.capability = float(cap)

    # ---- promotion decision -------------------------------------------------
    def consider(self, fitness: float, contained: bool) -> HalfLifeDecision:
        drift = max(0.0, float(fitness) - self.capability)
        required = drift / self.safety_factor if self.safety_factor > 0 else float("inf")

        if not contained:
            self.black_strikes += 1
            self.state = "BLACK"
            d = HalfLifeDecision("BLACK", False, self.capability, drift, required,
                                 self.assurance_credit, self.debt,
                                 "containment breach")
            self._log(d)
            return d

        if drift <= 1e-12:
            d = HalfLifeDecision("GREEN", True, self.capability, 0.0, 0.0,
                                 self.assurance_credit, self.debt,
                                 "no capability drift (lateral/diversity)")
            self._log(d)
            return d

        if self.assurance_credit + 1e-12 >= required:
            self.assurance_credit -= required
            self.capability = fitness
            util = required / (required + self.assurance_credit + 1e-9)
            self.state = "AMBER" if util > self.amber_util else "GREEN"
            self.black_strikes = 0
            d = HalfLifeDecision(self.state, True, self.capability, drift, required,
                                 self.assurance_credit, self.debt,
                                 "drift absorbed by assurance budget")
            self._log(d)
            return d

        # insufficient assurance to absorb this expansion
        self.debt += (required - self.assurance_credit)
        self.state = "RED"
        d = HalfLifeDecision("RED", False, self.capability, drift, required,
                             self.assurance_credit, self.debt,
                             "assurance cannot yet absorb capability drift")
        self._log(d)
        return d

    def should_halt(self) -> bool:
        return self.black_strikes >= self.black_strikes_to_halt

    def _log(self, d: HalfLifeDecision) -> None:
        self.history.append({
            "state": d.state, "allow": d.allow, "capability": round(d.capability, 5),
            "drift": round(d.drift, 5), "required": round(d.required_credit, 5),
            "available": round(d.available_credit, 5), "debt": round(self.debt, 5),
            "reason": d.reason,
        })

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state, "capability": round(self.capability, 5),
            "assurance_credit": round(self.assurance_credit, 5),
            "cumulative_assurance": round(self.cumulative_assurance, 5),
            "debt": round(self.debt, 5), "black_strikes": self.black_strikes,
        }
