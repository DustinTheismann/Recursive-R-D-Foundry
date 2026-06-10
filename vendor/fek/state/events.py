"""The Event type.

An event is the atomic unit of canonical truth (law #5). Events are immutable
once written; state changes by *appending* a new event, never by editing an old
one.

Two integrity mechanisms cover every event (both prove integrity, never
correctness -- law #15):

* ``event_id`` is the content hash of the event body, so each record is
  self-describing;
* ``prev`` is the leaf hash of the previous record in the same log (or
  ``"genesis"``), forming a hash chain: editing or removing any line breaks the
  linkage of every line after it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fek.kernel.canonical import canonical_bytes, sha256_hex

GENESIS = "genesis"


@dataclass(frozen=True)
class Event:
    """An append-only, hash-chained event record."""

    seq: int
    type: str
    ts: str
    payload: dict[str, Any]
    prev: str = GENESIS

    @property
    def event_id(self) -> str:
        """Content hash of the event body (``ev_<16 hex>``)."""

        return "ev_" + sha256_hex(canonical_bytes(self._body()))[:16]

    def _body(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "type": self.type,
            "ts": self.ts,
            "payload": self.payload,
            "prev": self.prev,
        }

    def to_record(self) -> dict[str, Any]:
        """Full on-disk record, including the derived id."""

        rec = self._body()
        rec["event_id"] = self.event_id
        return rec

    def leaf_hash(self) -> str:
        """Hash used as a Merkle leaf and as the next event's ``prev``."""

        return sha256_hex(canonical_bytes(self.to_record()))

    @classmethod
    def from_record(cls, rec: dict[str, Any]) -> "Event":
        return cls(
            seq=rec["seq"],
            type=rec["type"],
            ts=rec["ts"],
            payload=rec["payload"],
            prev=rec.get("prev", GENESIS),
        )


__all__ = ["Event", "GENESIS"]
