"""Core data model for the foundry.

Everything that flows through the recursive loop is one of these immutable-ish
records. They are plain dataclasses so they serialize cleanly into RunPacks and
replay deterministically.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Candidate:
    """A successor program proposed by some loop/proposer."""

    cid: str                                   # content-addressed lineage id
    source: str                                # real Python source for `place`
    genome: dict[str, Any]                     # structured params generating the source
    parents: list[str] = field(default_factory=list)
    generation: int = 0
    origin: str = "seed"                       # which loop/proposer produced it
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Candidate":
        return cls(**d)


@dataclass
class EvalResult:
    """Outcome of running a candidate through the evaluator quorum."""

    cid: str
    valid: bool                                # contracts satisfied
    fitness: float                             # composite benchmark score in [0, 1]
    per_task: dict[str, float] = field(default_factory=dict)
    runtime_ms: float = 0.0
    behavior: list[float] = field(default_factory=list)   # MAP-Elites descriptors
    violation_rate: float = 0.0
    static_ok: bool = True
    static_report: dict[str, Any] = field(default_factory=dict)
    quorum: dict[str, bool] = field(default_factory=dict)  # evaluator -> vote
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateReport:
    """Full record of why a candidate was (or was not) promoted."""

    cid: str
    fitness: float = 0.0
    fitness_delta: float = 0.0
    novelty_score: float = 0.0
    novelty_pass: bool = False
    causal_effect: float = 0.0
    causal_pass: bool = False
    regression_failures: int = 0
    benchmark_pass: bool = False
    contained: bool = False
    contracts_pass: bool = False
    capability_drift: float = 0.0
    assurance_renewal: float = 0.0
    half_life_state: str = "GREEN"
    half_life_pass: bool = False
    promoted: bool = False
    lineage_hash: str = ""
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CycleRecord:
    """One full recursive cycle's worth of activity."""

    cycle: int
    proposed: list[str] = field(default_factory=list)
    promoted: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    gate_reports: list[dict[str, Any]] = field(default_factory=list)
    half_life_state: str = "GREEN"
    capability_index: float = 0.0
    assurance_index: float = 0.0
    population_entropy: float = 0.0
    environment: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
