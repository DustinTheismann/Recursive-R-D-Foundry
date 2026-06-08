"""Content-addressed lineage as a Merkle DAG.

Each candidate's id is the hash of (canonical source + sorted genome + parent
ids). This makes lineage tamper-evident and gives a stable `lineage_hash` for
the promotion record — two foundries that evolve the same successor will agree
on its id, and any edit changes the id, so provenance cannot be silently
rewritten.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable


def candidate_id(source: str, genome: dict, parents: Iterable[str]) -> str:
    payload = json.dumps(
        {
            "source": source,
            "genome": genome,
            "parents": sorted(parents),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "c_" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def lineage_root(cids: Iterable[str]) -> str:
    """Merkle root over a set of candidate ids (used to fingerprint a RunPack)."""
    leaves = sorted(set(cids))
    if not leaves:
        return "0" * 64
    nodes = [hashlib.sha256(c.encode()).digest() for c in leaves]
    while len(nodes) > 1:
        nxt = []
        for i in range(0, len(nodes), 2):
            a = nodes[i]
            b = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            nxt.append(hashlib.sha256(a + b).digest())
        nodes = nxt
    return nodes[0].hex()


class LineageGraph:
    """Tracks parent/child edges and lets the dashboard render the DAG."""

    def __init__(self) -> None:
        self.edges: list[tuple[str, str]] = []   # (parent, child)
        self.nodes: dict[str, dict] = {}

    def add(self, cid: str, parents: list[str], attrs: dict | None = None) -> None:
        self.nodes.setdefault(cid, {})
        if attrs:
            self.nodes[cid].update(attrs)
        for p in parents:
            self.nodes.setdefault(p, {})
            self.edges.append((p, cid))

    def ancestors(self, cid: str) -> set[str]:
        parents = {p for (p, c) in self.edges if c == cid}
        seen: set[str] = set()
        frontier = set(parents)
        while frontier:
            n = frontier.pop()
            if n in seen:
                continue
            seen.add(n)
            frontier |= {p for (p, c) in self.edges if c == n}
        return seen

    def to_dict(self) -> dict:
        return {"nodes": self.nodes, "edges": self.edges}
