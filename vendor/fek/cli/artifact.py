"""Build the reproducibility artifact manifest.

The artifact is a self-describing bundle that lets an external reviewer
reproduce the kernel's claims. Building it (re)generates the reports and writes
``artifact/artifact_manifest.json`` listing each tracked file with its content
hash and the current state root (integrity, law #15).
"""

from __future__ import annotations

from typing import Any

from fek.kernel.canonical import canonical_json, sha256_hex
from fek.kernel.context import Kernel


ARTIFACT_FILES = (
    "artifact/README.md",
    "artifact/INSTALL.md",
    "artifact/REPRODUCE.md",
    "artifact/CLAIMS.md",
    "artifact/EXPECTED_RESULTS.md",
    "artifact/run.sh",
    "reports/generated/evidence_report.md",
    "reports/generated/state_report.md",
    "reports/generated/overclaim_report.md",
    "reports/generated/trust_report.md",
)


def build_artifact(kernel: Kernel) -> dict[str, Any]:
    from fek.reports import generate_all

    gen = generate_all(kernel)
    state_root = gen["state_root"]

    entries: dict[str, str] = {}
    for rel in ARTIFACT_FILES:
        path = kernel.root / rel
        if path.exists():
            entries[rel] = "sha256:" + sha256_hex(path.read_text(encoding="utf-8"))

    manifest = {
        "artifact": "fractal-evidence-kernel",
        "state_root": state_root,
        "integrity_note": "hashes prove integrity, not correctness (law #15)",
        "self_audit_passed": gen["self_audit_passed"],
        "files": entries,
    }
    out_path = kernel.root / "artifact" / "artifact_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(canonical_json(manifest), encoding="utf-8")
    return {"manifest_path": str(out_path.relative_to(kernel.root)), "file_count": len(entries)}


__all__ = ["build_artifact", "ARTIFACT_FILES"]
