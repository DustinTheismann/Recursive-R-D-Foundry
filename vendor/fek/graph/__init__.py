"""Generic directed-graph helpers (cycle detection, topological export).

Shared by the layer graph and the namespace graph. Pure standard library: a
graph is just ``{node: [neighbours]}``.
"""

from __future__ import annotations

from typing import Any


def find_cycles(adjacency: dict[str, list[str]]) -> list[list[str]]:
    """Return a list of cycles (each as a node path). Empty if acyclic."""

    cycles: list[list[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adjacency}
    stack: list[str] = []

    def visit(node: str) -> None:
        color[node] = GRAY
        stack.append(node)
        for nbr in adjacency.get(node, []):
            if nbr not in color:
                color[nbr] = WHITE
            if color[nbr] == GRAY:
                idx = stack.index(nbr)
                cycles.append(stack[idx:] + [nbr])
            elif color[nbr] == WHITE:
                visit(nbr)
        stack.pop()
        color[node] = BLACK

    for node in list(adjacency):
        if color[node] == WHITE:
            visit(node)
    return cycles


def export_graph(nodes: dict[str, dict[str, Any]], adjacency: dict[str, list[str]]) -> dict[str, Any]:
    """Serialise a graph to a stable JSON-able structure."""

    return {
        "nodes": [{"id": nid, **attrs} for nid, attrs in sorted(nodes.items())],
        "edges": sorted(
            [{"from": src, "to": dst} for src, dsts in adjacency.items() for dst in dsts],
            key=lambda e: (e["from"], e["to"]),
        ),
    }


__all__ = ["find_cycles", "export_graph"]
