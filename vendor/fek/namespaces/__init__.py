"""Namespace graph built from registry instances.

Active instances of layers (a specific repo, substrate, institution, ...) live
in ``registry/instances/*.yaml`` and reference each other and a layer type.
This module loads them, validates their references, builds a graph, detects
illegal cycles, and exports a report. Instances are *typed namespaces*, not
folders.
"""

from __future__ import annotations

from typing import Any

import yaml

from fek.errors import ValidationError
from fek.kernel.context import Kernel
from fek.graph import export_graph, find_cycles


def load_instances(kernel: Kernel) -> dict[str, dict[str, Any]]:
    """Load instance definitions keyed by instance id."""

    out: dict[str, dict[str, Any]] = {}
    inst_dir = kernel.paths.instances
    if not inst_dir.exists():
        return out
    for path in sorted(inst_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        iid = doc.get("id")
        if iid:
            out[iid] = doc
    return out


def validate_refs(kernel: Kernel) -> list[str]:
    """Check that every parent/child/layer reference resolves."""

    from fek.layers import load_layers

    errors: list[str] = []
    instances = load_instances(kernel)
    layer_ids = {layer.id for layer in load_layers(kernel)}
    for iid, inst in instances.items():
        layer_ref = inst.get("layer")
        if layer_ref and layer_ref not in layer_ids:
            errors.append(f"instance {iid}: references unknown layer {layer_ref!r}")
        for parent in inst.get("parents", []):
            if parent not in instances:
                errors.append(f"instance {iid}: references unknown parent {parent!r}")
    return errors


def build_adjacency(kernel: Kernel) -> dict[str, list[str]]:
    instances = load_instances(kernel)
    adjacency: dict[str, list[str]] = {iid: [] for iid in instances}
    for iid, inst in instances.items():
        for parent in inst.get("parents", []):
            adjacency.setdefault(parent, [])
            adjacency[parent].append(iid)  # parent -> child
    return adjacency


def build_graph(kernel: Kernel) -> dict[str, Any]:
    instances = load_instances(kernel)
    nodes = {
        iid: {"name": inst.get("name", iid), "layer": inst.get("layer"), "maturity": inst.get("maturity")}
        for iid, inst in instances.items()
    }
    return export_graph(nodes, build_adjacency(kernel))


def detect_cycles(kernel: Kernel) -> list[list[str]]:
    """Containment graphs must be acyclic; return any cycles found."""

    return find_cycles(build_adjacency(kernel))


def graph_report(kernel: Kernel) -> dict[str, Any]:
    instances = load_instances(kernel)
    cycles = detect_cycles(kernel)
    ref_errors = validate_refs(kernel)
    return {
        "instance_count": len(instances),
        "ref_errors": ref_errors,
        "cycles": cycles,
        "acyclic": not cycles,
        "graph": build_graph(kernel),
    }


def export_json(kernel: Kernel) -> dict[str, Any]:
    """Write the namespace graph to ``data/generated/namespace_graph.json``."""

    from fek.kernel.canonical import canonical_json

    report = graph_report(kernel)
    kernel.paths.generated.mkdir(parents=True, exist_ok=True)
    path = kernel.paths.generated / "namespace_graph.json"
    path.write_text(canonical_json(report), encoding="utf-8")
    return report


__all__ = [
    "load_instances",
    "validate_refs",
    "build_graph",
    "build_adjacency",
    "detect_cycles",
    "graph_report",
    "export_json",
]
