"""The append-only event store.

This is the heart of the kernel's truth model (laws #5, #6). Events are written
as JSON Lines, one canonical record per line. Nothing is ever updated in place.
The global Merkle root is computed over *all* events in a single, documented
canonical order so that any two checkouts of the same logs produce the same
state root.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from fek.errors import StateError
from fek.kernel.canonical import canonical_bytes, canonical_json, sha256_hex
from fek.kernel.context import Kernel
from fek.kernel.paths import EVENT_LOGS
from fek.state.events import GENESIS, Event
from fek.state.merkle import merkle_root


class EventStore:
    """Reads and appends canonical events for a kernel root."""

    def __init__(self, kernel: Kernel) -> None:
        self.kernel = kernel

    # -- writing ---------------------------------------------------------
    def append(self, log: str, event_type: str, payload: dict[str, Any], ts: str | None = None) -> Event:
        """Append one event to ``log`` and return it.

        ``seq`` is the next index in that log. The event is written as a single
        canonical JSON line; we never rewrite earlier lines (law #5).
        """

        path = self.kernel.paths.event_log(log)
        path.parent.mkdir(parents=True, exist_ok=True)
        records = self.read_records(log)
        seq = len(records)
        # Hash-chain: link to the leaf hash of the previous stored record.
        prev = sha256_hex(canonical_bytes(records[-1])) if records else GENESIS
        event = Event(seq=seq, type=event_type, ts=ts or self.kernel.now(), payload=payload, prev=prev)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(event.to_record()) + "\n")
        return event

    # -- reading ---------------------------------------------------------
    def read_records(self, log: str) -> list[dict[str, Any]]:
        """Raw stored records (including ``event_id``/``prev``), in write order."""

        path = self.kernel.paths.event_log(log)
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:  # pragma: no cover - corruption guard
                raise StateError(f"{log} line {lineno}: corrupt event JSON: {exc}") from exc
        return records

    def read(self, log: str) -> list[Event]:
        """All events in one log, in write order."""

        return [Event.from_record(rec) for rec in self.read_records(log)]

    def read_all(self) -> list[Event]:
        """Every event across every log, in canonical global order.

        Canonical order = (log name in the fixed ``EVENT_LOGS`` order, then seq
        within that log). This ordering is what the Merkle root commits to.
        """

        ordered: list[Event] = []
        for log in EVENT_LOGS:  # insertion-ordered dict = stable order
            ordered.extend(self.read(log))
        return ordered

    # -- integrity -------------------------------------------------------
    def verify_chain(self, log: str) -> str | None:
        """Validate one log's hash chain. Returns an error string or ``None``.

        Checks, per record: contiguous ``seq``, ``event_id`` matches the body
        hash, and ``prev`` matches the leaf hash of the preceding record. Any
        in-place edit, insertion, or deletion breaks at least one of these.
        Integrity only -- a perfect chain says nothing about claim correctness
        (law #15).
        """

        prev_leaf = GENESIS
        for i, rec in enumerate(self.read_records(log)):
            if rec.get("seq") != i:
                return f"{log}[{i}]: seq mismatch (stored {rec.get('seq')})"
            if rec.get("event_id") != Event.from_record(rec).event_id:
                return f"{log}[{i}]: event_id does not match body hash (tampered record)"
            if rec.get("prev", GENESIS) != prev_leaf:
                return f"{log}[{i}]: broken chain (prev does not match preceding leaf)"
            prev_leaf = sha256_hex(canonical_bytes(rec))
        return None

    def verify_chains(self) -> dict[str, str | None]:
        """Chain status for every log: ``{log: None | error string}``."""

        return {log: self.verify_chain(log) for log in EVENT_LOGS}

    def state_root(self) -> str:
        """Deterministic Merkle root over all events (integrity, not truth)."""

        leaves = [e.leaf_hash() for e in self.read_all()]
        return merkle_root(leaves)

    def counts(self) -> dict[str, int]:
        """Event count per log (for reports/audit)."""

        return {log: len(self.read(log)) for log in EVENT_LOGS}

    def total(self) -> int:
        return sum(self.counts().values())

    def iter_type(self, log: str, event_type: str) -> Iterable[Event]:
        """Yield events of a given type from a log, in order."""

        return (e for e in self.read(log) if e.type == event_type)


__all__ = ["EventStore"]
