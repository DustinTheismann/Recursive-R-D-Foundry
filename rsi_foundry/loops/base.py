"""Shared loop context.

Every generative loop receives the same context and returns candidates, so the
orchestrator can compose them freely. Loops may also emit a `review` artifact
(the AI-Scientist loop does) which is recorded into the RunPack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from rsi_foundry.core.types import Candidate


@dataclass
class LoopContext:
    rng: Any
    generation: int
    proposer: Any
    parents: list[Candidate] = field(default_factory=list)
    champion: Optional[Candidate] = None
    champion_result: Any = None
    priors: dict[str, float] = field(default_factory=dict)
    registry: Any = None
    harness: Any = None
    sandbox: Any = None
    benchmark: Any = None
    config: dict[str, Any] = field(default_factory=dict)
