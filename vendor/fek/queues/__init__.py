"""Work queues (maturity: spec_only).

A future capability fabric (layer 8) needs durable, evidence-aware work queues
to route grading/verification jobs. v0.1 does NOT implement a real queue
backend. This module exposes the intended interface as a thin, in-memory stub so
callers can be written against it, but it is marked ``spec_only`` (law #14) and
must never be reported as live.
"""

from __future__ import annotations

MATURITY = "spec_only"


def enqueue(*_args, **_kwargs):  # pragma: no cover - spec_only stub
    raise NotImplementedError("work queues are spec_only in v0.1 (see specs/future)")


__all__ = ["MATURITY", "enqueue"]
