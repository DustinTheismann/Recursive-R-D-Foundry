"""Append-only state engine: events, store, Merkle integrity, transitions.

This package is the canonical truth layer (laws #4, #5, #6, #15). Everything
the kernel "knows" is a replay of the event logs here. Generated views and
snapshots are derived and disposable; the logs are not.
"""

from __future__ import annotations

from fek.state.events import Event
from fek.state.merkle import EMPTY_ROOT, merkle_root
from fek.state.snapshot import build_state, snapshot, status_counts, write_snapshot
from fek.state.store import EventStore
from fek.state.transitions import (
    Transition,
    apply_transition,
    propose_transition,
    verify_transition,
)

__all__ = [
    "Event",
    "EventStore",
    "merkle_root",
    "EMPTY_ROOT",
    "build_state",
    "snapshot",
    "write_snapshot",
    "status_counts",
    "Transition",
    "propose_transition",
    "verify_transition",
    "apply_transition",
]
