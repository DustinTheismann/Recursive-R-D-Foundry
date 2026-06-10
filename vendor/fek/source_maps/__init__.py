"""Source maps: binding public prose to evidence.

A *source map* says "lines X..Y of file F assert claim C, which is backed by
evidence record E (and optionally runpack R)." Law #11 requires that every
public strong claim either maps to evidence or is explicitly marked
speculative. Source maps are how the first half of that disjunction is proven.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fek.errors import ValidationError
from fek.kernel.context import Kernel

#: Where source maps live (a plain config file, version-controlled source truth).
SOURCE_MAP_FILE = "configs/source_maps.yaml"


@dataclass
class SourceMap:
    source_file: str
    line_start: int
    line_end: int
    claim_id: str
    evidence_record_id: str
    runpack_id: str = ""
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def covers(self, source_file: str, line: int) -> bool:
        return self.source_file == source_file and self.line_start <= line <= self.line_end


def load_source_maps(kernel: Kernel) -> list[SourceMap]:
    path = kernel.root / SOURCE_MAP_FILE
    if not path.exists():
        return []
    # Lazy import: the overclaim-scan / grading paths must run on the standard
    # library alone (no PyYAML) unless a source-map file actually exists.
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [SourceMap(**entry) for entry in doc.get("source_maps", [])]


def validate_source_maps(kernel: Kernel) -> list[str]:
    """Validate each source map references a known claim. Returns errors."""

    from fek.state.snapshot import build_state

    errors: list[str] = []
    claims = build_state(kernel)["claims"]
    for sm in load_source_maps(kernel):
        if sm.line_start > sm.line_end:
            errors.append(f"{sm.source_file}: line_start > line_end")
        if sm.claim_id not in claims:
            errors.append(f"{sm.source_file}:{sm.line_start} maps to unknown claim {sm.claim_id!r}")
        if not sm.evidence_record_id:
            errors.append(f"{sm.source_file}:{sm.line_start} has no evidence_record_id")
    return errors


def covering_map(kernel: Kernel, source_file: str, line: int) -> SourceMap | None:
    for sm in load_source_maps(kernel):
        if sm.status == "active" and sm.covers(source_file, line):
            return sm
    return None


__all__ = ["SourceMap", "load_source_maps", "validate_source_maps", "covering_map", "SOURCE_MAP_FILE"]
