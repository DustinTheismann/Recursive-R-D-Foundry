"""Adapters: read-only ingestion of external repo-like systems.

Adapters turn an external thing (another repository, a paper, a dataset) into
raw (E0/E1) claims for grading. v0.1 ships one *experimental* adapter: a local
filesystem repo scanner that emits sourced claims about a directory. Network
adapters (GitHub API, arXiv) are ``spec_only`` -- they require capabilities and
must never carry committed credentials (law #8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fek.kernel.context import Kernel


def load_adapters(kernel: Kernel) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    d = kernel.paths.registry / "adapters"
    if not d.exists():
        return out
    for path in sorted(d.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        aid = doc.get("adapter_id")
        if aid:
            out[aid] = doc
    return out


def scan_local_repo(repo_path: str | Path, producer: str = "adapter:local_fs") -> list[dict[str, Any]]:
    """Experimental: emit E1_SOURCED claims describing a local directory.

    Returns claim *dicts* (not yet ingested). Each claim asserts a file exists
    and is sourced to its path -- nothing stronger. Higher grades must be earned
    by reproduction, not by scanning.
    """

    root = Path(repo_path)
    claims: list[dict[str, Any]] = []
    if not root.exists():
        return claims
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            rel = path.relative_to(root)
            claims.append(
                {
                    "statement": f"file {rel} exists in scanned repo",
                    "claim_type": "metadata",
                    "source": str(rel),
                    "producer": producer,
                    "required_evidence": ["E1_SOURCED"],
                    "current_evidence": [
                        {"evidence_class": "E1_SOURCED", "method": "fs_scan", "producer": producer, "verifier": ""}
                    ],
                    "metadata": {"adapter": "local_fs", "maturity": "experimental"},
                }
            )
    return claims


__all__ = ["load_adapters", "scan_local_repo"]
