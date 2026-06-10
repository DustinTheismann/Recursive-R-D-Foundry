"""The :class:`Kernel` run context.

A :class:`Kernel` binds a root directory to its :class:`Paths` and provides a
clock. Components (event store, grader, policy engine) take a ``Kernel`` so
they share one root and one notion of "now". The clock is injectable so tests
can produce byte-identical event logs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fek.kernel.paths import Paths


def _utc_now() -> str:
    """ISO-8601 UTC timestamp with second precision (stable across machines)."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Kernel:
    """Root context: where things live and what time it is."""

    def __init__(self, root: str | Path, clock: Callable[[], str] | None = None) -> None:
        self.paths = Paths(Path(root).resolve())
        self._clock = clock or _utc_now

    @property
    def root(self) -> Path:
        return self.paths.root

    def now(self) -> str:
        """Current timestamp string (injectable for determinism in tests)."""

        return self._clock()

    def initialised(self) -> bool:
        """True if the writable event directory exists."""

        return self.paths.events.exists()

    def init(self) -> None:
        """Create the writable directory skeleton and empty event logs."""

        self.paths.ensure()
        from fek.kernel.paths import EVENT_LOGS

        for name in EVENT_LOGS:
            log = self.paths.event_log(name)
            if not log.exists():
                log.touch()


__all__ = ["Kernel"]
