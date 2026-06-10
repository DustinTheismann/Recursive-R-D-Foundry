"""Deterministic Merkle root over canonicalized events.

A Merkle root is a fingerprint of an ordered set of events. If a single byte of
any event changes, or events are reordered, the root changes.

LAW #15 (stated here because this is where people are tempted to forget it):
**A Merkle root proves integrity, not correctness.** It says "these exact
events, in this exact order, have not been tampered with." It says *nothing*
about whether the claims inside those events are true. Correctness comes only
from surviving evidence gates -- never from a hash.
"""

from __future__ import annotations

from fek.kernel.canonical import sha256_hex

# Root of an empty log. A fixed, documented constant so "no events" still has a
# stable, reproducible fingerprint.
EMPTY_ROOT = sha256_hex(b"fek:empty-merkle-root:v1")


def merkle_root(leaf_hashes: list[str]) -> str:
    """Compute a Merkle root from pre-hashed leaves (hex strings).

    Odd levels duplicate the final node (Bitcoin-style). Order is significant
    and is the caller's responsibility -- see :func:`fek.state.store` for the
    canonical event ordering.
    """

    if not leaf_hashes:
        return EMPTY_ROOT

    level = list(leaf_hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])  # duplicate last to pair it
        nxt: list[str] = []
        for i in range(0, len(level), 2):
            nxt.append(sha256_hex(level[i] + level[i + 1]))
        level = nxt
    return level[0]


__all__ = ["merkle_root", "EMPTY_ROOT"]
