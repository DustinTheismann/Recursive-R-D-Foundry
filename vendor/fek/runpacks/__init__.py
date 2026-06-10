"""Runpacks: sealed, replayable evidence bundles.

A *runpack* records exactly how a computational claim was produced: the
manifest of files, the command log, artifact hashes, and the environment. It is
sealed by hashing its canonical JSON. The seal proves the bundle has not
changed (integrity, law #15) -- it does **not** prove the computation was
correct.

v0.1 ships a *replay stub*: it validates that the referenced files and command
log exist and that the seal still matches. It does not re-execute arbitrary
commands (that requires the sandbox capability, which is ``spec_only``). We do
not pretend otherwise (law #14, implementation honesty).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fek.errors import RunpackError
from fek.kernel.canonical import canonical_bytes, content_id, sha256_hex
from fek.kernel.context import Kernel
from fek.state.store import EventStore


@dataclass
class Runpack:
    """A sealed (or unsealed) runpack."""

    runpack_id: str
    claim_id: str
    manifest: list[dict[str, Any]]
    command_log: list[str]
    artifact_hashes: dict[str, str]
    environment: dict[str, str]
    created_at: str
    # Optional expected stdout hashes per command index ("0" -> "sha256:..."),
    # checked by the experimental re-execution engine (fek.runpacks.execute).
    outputs: dict[str, str] = field(default_factory=dict)
    sealed_hash: str = ""
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Runpack":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def _sealable_body(self) -> dict[str, Any]:
        """The fields that the seal commits to (everything but the seal/status)."""

        return {
            "runpack_id": self.runpack_id,
            "claim_id": self.claim_id,
            "manifest": self.manifest,
            "command_log": self.command_log,
            "artifact_hashes": self.artifact_hashes,
            "environment": self.environment,
            "created_at": self.created_at,
            "outputs": self.outputs,
        }

    def compute_seal(self) -> str:
        return "sha256:" + sha256_hex(canonical_bytes(self._sealable_body()))


def create_runpack_manifest(
    claim_id: str,
    created_at: str,
    manifest: list[dict[str, Any]] | None = None,
    command_log: list[str] | None = None,
    artifact_hashes: dict[str, str] | None = None,
    environment: dict[str, str] | None = None,
    outputs: dict[str, str] | None = None,
) -> Runpack:
    """Build an unsealed runpack with a deterministic id."""

    body = {
        "claim_id": claim_id,
        "manifest": manifest or [],
        "command_log": command_log or [],
        "artifact_hashes": artifact_hashes or {},
        "environment": environment or {},
        "outputs": outputs or {},
    }
    rid = content_id("rpk", body)
    return Runpack(
        runpack_id=rid,
        claim_id=claim_id,
        manifest=body["manifest"],
        command_log=body["command_log"],
        artifact_hashes=body["artifact_hashes"],
        environment=body["environment"],
        created_at=created_at,
        outputs=body["outputs"],
        status="draft",
    )


def seal_runpack(kernel: Kernel, runpack: Runpack, persist: bool = True) -> Runpack:
    """Seal a runpack by hashing its canonical body and record the event."""

    runpack.sealed_hash = runpack.compute_seal()
    runpack.status = "sealed"
    if persist:
        _write(kernel, runpack)
        EventStore(kernel).append(
            "runpack",
            "runpack.sealed",
            {"runpack_id": runpack.runpack_id, "claim_id": runpack.claim_id, "sealed_hash": runpack.sealed_hash},
        )
    return runpack


def verify_runpack(kernel: Kernel, runpack: Runpack, emit: bool = True) -> bool:
    """Recompute the seal and compare. Emits ``runpack.verified``."""

    expected = runpack.compute_seal()
    ok = bool(runpack.sealed_hash) and runpack.sealed_hash == expected
    if emit:
        EventStore(kernel).append(
            "runpack",
            "runpack.verified",
            {
                "runpack_id": runpack.runpack_id,
                "claim_id": runpack.claim_id,
                "ok": ok,
                "expected": expected,
                "stored": runpack.sealed_hash,
            },
        )
    if not ok:
        raise RunpackError(
            f"runpack {runpack.runpack_id} seal mismatch: stored={runpack.sealed_hash!r} expected={expected!r}"
        )
    return True


def replay_runpack(kernel: Kernel, runpack: Runpack) -> dict[str, Any]:
    """Stub replay: validate seal + that referenced files/command log exist.

    Returns a report dict. This is intentionally *not* a re-execution engine in
    v0.1 (see module docstring).
    """

    verify_runpack(kernel, runpack, emit=False)
    missing: list[str] = []
    for entry in runpack.manifest:
        rel = entry.get("path")
        if not rel:
            continue
        if not (kernel.root / rel).exists():
            missing.append(rel)
    report = {
        "runpack_id": runpack.runpack_id,
        "seal_ok": True,
        "command_log_present": bool(runpack.command_log),
        "missing_files": missing,
        "maturity": "experimental",
        "note": "replay validates presence + seal only; execution is spec_only",
    }
    if missing:
        raise RunpackError(f"runpack {runpack.runpack_id} references missing files: {missing}")
    if not runpack.command_log:
        raise RunpackError(f"runpack {runpack.runpack_id} has an empty command log")
    return report


def _write(kernel: Kernel, runpack: Runpack) -> Path:
    kernel.paths.runpacks.mkdir(parents=True, exist_ok=True)
    path = kernel.paths.runpacks / f"{runpack.runpack_id}.json"
    from fek.kernel.canonical import canonical_json

    path.write_text(canonical_json(runpack.to_dict()), encoding="utf-8")
    return path


def load_runpack(kernel: Kernel, runpack_id: str) -> Runpack:
    path = kernel.paths.runpacks / f"{runpack_id}.json"
    if not path.exists():
        raise RunpackError(f"runpack not found: {runpack_id}")
    import json

    return Runpack.from_dict(json.loads(path.read_text(encoding="utf-8")))


__all__ = [
    "Runpack",
    "create_runpack_manifest",
    "seal_runpack",
    "verify_runpack",
    "replay_runpack",
    "load_runpack",
]
