"""On-disk layout of a kernel root.

A FEK "root" is a directory containing append-only event logs (canonical
truth), registries (typed definitions), and generated views (derived, never
source truth -- law #4). :class:`Paths` centralises every path so the rest of
the code never hard-codes a directory name.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Canonical event-log filenames. These are the *only* source of truth (law #5).
EVENT_LOGS: dict[str, str] = {
    "claims": "claims.events.jsonl",
    "state": "state.events.jsonl",
    "capability": "capability.events.jsonl",
    "runpack": "runpack.events.jsonl",
    "refutation": "refutation.events.jsonl",
    "quarantine": "quarantine.events.jsonl",
    "review": "review.events.jsonl",
    "publication": "publication.events.jsonl",
}


@dataclass(frozen=True)
class Paths:
    """Resolved paths for a kernel rooted at ``root``."""

    root: Path

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def events(self) -> Path:
        return self.data / "events"

    @property
    def runpacks(self) -> Path:
        return self.data / "runpacks"

    @property
    def attestations(self) -> Path:
        return self.data / "attestations"

    @property
    def generated(self) -> Path:
        return self.data / "generated"

    @property
    def snapshots(self) -> Path:
        return self.data / "snapshots"

    @property
    def registry(self) -> Path:
        return self.root / "registry"

    @property
    def layers(self) -> Path:
        return self.registry / "layers"

    @property
    def instances(self) -> Path:
        return self.registry / "instances"

    @property
    def capabilities(self) -> Path:
        return self.registry / "capabilities"

    @property
    def reports_generated(self) -> Path:
        return self.root / "reports" / "generated"

    @property
    def schemas(self) -> Path:
        return self.root / "schemas"

    def event_log(self, name: str) -> Path:
        """Path to a named event log (e.g. ``claims``)."""

        if name not in EVENT_LOGS:
            raise KeyError(f"unknown event log: {name!r}")
        return self.events / EVENT_LOGS[name]

    def ensure(self) -> None:
        """Create the writable directories a live kernel needs."""

        for d in (
            self.events,
            self.runpacks,
            self.attestations,
            self.generated,
            self.snapshots,
            self.instances,
            self.reports_generated,
        ):
            d.mkdir(parents=True, exist_ok=True)


__all__ = ["Paths", "EVENT_LOGS"]
