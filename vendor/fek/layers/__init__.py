"""The typed layer registry.

The ten-rung hierarchy (Repo -> ... -> Federated Evidence Substrate) is NOT a
folder tree. It is a set of typed *layer definitions* in
``registry/layers/*.yaml``. Each definition carries a maturity label (law #10);
this module refuses to report a ``spec_only`` layer as ``live`` (law #14).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from fek.errors import ValidationError
from fek.kernel.context import Kernel
from fek.types import Maturity

REQUIRED_FIELDS = (
    "id",
    "name",
    "layer_index",
    "maturity",
    "status",
    "description",
    "required_fields",
    "canonical_events",
    "must_not",
    "spec",
)


@dataclass
class Layer:
    id: str
    name: str
    layer_index: int
    maturity: str
    status: str
    description: str
    required_fields: list[str]
    canonical_events: list[str]
    must_not: list[str]
    spec: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Layer":
        return cls(
            id=data["id"],
            name=data["name"],
            layer_index=int(data["layer_index"]),
            maturity=data["maturity"],
            status=data["status"],
            description=data["description"],
            required_fields=list(data.get("required_fields", [])),
            canonical_events=list(data.get("canonical_events", [])),
            must_not=list(data.get("must_not", [])),
            spec=data.get("spec", ""),
        )

    @property
    def is_live(self) -> bool:
        return self.maturity == Maturity.LIVE.value


def load_layers(kernel: Kernel) -> list[Layer]:
    """Load and order all layer definitions by ``layer_index``."""

    layers: list[Layer] = []
    for path in sorted(kernel.paths.layers.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        layers.append(Layer.from_dict(doc))
    return sorted(layers, key=lambda layer_obj: layer_obj.layer_index)


def validate_layers(kernel: Kernel) -> list[str]:
    """Validate every layer definition. Returns a list of error strings."""

    errors: list[str] = []
    seen_index: dict[int, str] = {}
    valid_maturities = {m.value for m in Maturity}
    for path in sorted(kernel.paths.layers.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        name = path.name
        for fld in REQUIRED_FIELDS:
            if fld not in doc:
                errors.append(f"{name}: missing required field {fld!r}")
        mat = doc.get("maturity")
        if mat not in valid_maturities:
            errors.append(f"{name}: invalid maturity {mat!r} (law #10)")
        idx = doc.get("layer_index")
        if idx in seen_index:
            errors.append(f"{name}: duplicate layer_index {idx} (also {seen_index[idx]})")
        elif isinstance(idx, int):
            seen_index[idx] = name
        # Law #14: spec_only layers must not advertise live status.
        if mat == Maturity.SPEC_ONLY.value and doc.get("status") == "live":
            errors.append(f"{name}: spec_only layer advertised as live status (law #14)")
    return errors


def instantiate_layer(kernel: Kernel, layer_id: str) -> Layer:
    """Return the typed :class:`Layer` for ``layer_id``."""

    for layer in load_layers(kernel):
        if layer.id == layer_id:
            return layer
    raise ValidationError(f"unknown layer id: {layer_id!r}")


def live_layers(kernel: Kernel) -> list[Layer]:
    """Only layers whose maturity is ``live`` (never spec_only -- law #14)."""

    return [layer for layer in load_layers(kernel) if layer.is_live]


def layer_graph(kernel: Kernel) -> dict[str, Any]:
    """Build a linear containment graph over the ordered layers."""

    from fek.graph import export_graph

    layers = load_layers(kernel)
    nodes = {
        layer.id: {
            "name": layer.name,
            "layer_index": layer.layer_index,
            "maturity": layer.maturity,
            "status": layer.status,
        }
        for layer in layers
    }
    adjacency: dict[str, list[str]] = {layer.id: [] for layer in layers}
    for lower, higher in zip(layers, layers[1:]):
        adjacency[lower.id].append(higher.id)  # each layer is contained by the next
    return export_graph(nodes, adjacency)


def maturity_summary(kernel: Kernel) -> dict[str, int]:
    summary: dict[str, int] = {}
    for layer in load_layers(kernel):
        summary[layer.maturity] = summary.get(layer.maturity, 0) + 1
    return summary


__all__ = [
    "Layer",
    "load_layers",
    "validate_layers",
    "instantiate_layer",
    "live_layers",
    "layer_graph",
    "maturity_summary",
    "REQUIRED_FIELDS",
]
