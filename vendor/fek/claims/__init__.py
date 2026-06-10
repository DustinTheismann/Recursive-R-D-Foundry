"""The Claim model and its lifecycle helpers.

A *claim* is a typed assertion that wants to be believed. The kernel's job is to
refuse belief until evidence earns it (core invariant: *no output is trusted
because it was produced*). This module defines the claim record, deterministic
identity, normalization, hashing, and ingestion into the event log.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from fek.errors import ValidationError
from fek.kernel.canonical import content_id, sha256_hex, canonical_bytes
from fek.kernel.context import Kernel
from fek.state.store import EventStore
from fek.types import ClaimStatus, EvidenceClass


@dataclass
class Claim:
    """A typed claim awaiting evidence."""

    claim_id: str
    statement: str
    claim_type: str
    source: str
    producer: str
    created_at: str
    required_evidence: list[str] = field(default_factory=list)
    current_evidence: list[dict[str, Any]] = field(default_factory=list)
    status: str = ClaimStatus.RAW.value
    runpack_ids: list[str] = field(default_factory=list)
    refutation_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def hash(self) -> str:
        """Content hash of the *identity-bearing* fields of the claim."""

        return sha256_hex(canonical_bytes(_identity(self.statement, self.claim_type, self.source, self.producer)))


def _identity(statement: str, claim_type: str, source: str, producer: str) -> dict[str, str]:
    """Fields that define claim identity (NOT created_at -> idempotent re-ingest)."""

    return {
        "statement": statement.strip(),
        "claim_type": claim_type.strip(),
        "source": source.strip(),
        "producer": producer.strip(),
    }


def normalize_claim(data: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized copy: trimmed strings, defaulted collections."""

    out = dict(data)
    for key in ("statement", "claim_type", "source", "producer"):
        if key in out and isinstance(out[key], str):
            out[key] = out[key].strip()
    out.setdefault("required_evidence", [])
    out.setdefault("current_evidence", [])
    out.setdefault("runpack_ids", [])
    out.setdefault("refutation_ids", [])
    out.setdefault("metadata", {})
    out.setdefault("status", ClaimStatus.RAW.value)
    return out


def validate_claim(data: dict[str, Any]) -> None:
    """Structurally validate a claim dict. Raises :class:`ValidationError`."""

    required = ("statement", "claim_type", "source", "producer")
    for key in required:
        if not data.get(key):
            raise ValidationError(f"claim is missing required field: {key!r}")
    valid_classes = {e.value for e in EvidenceClass}
    for cls in data.get("required_evidence", []):
        if cls not in valid_classes:
            raise ValidationError(f"unknown required_evidence class: {cls!r}")
    status = data.get("status", ClaimStatus.RAW.value)
    if status not in {s.value for s in ClaimStatus}:
        raise ValidationError(f"unknown claim status: {status!r}")


def create_claim(data: dict[str, Any], created_at: str) -> Claim:
    """Validate + normalize + assign deterministic id, returning a Claim."""

    norm = normalize_claim(data)
    validate_claim(norm)
    claim_id = content_id("clm", _identity(norm["statement"], norm["claim_type"], norm["source"], norm["producer"]))
    norm["claim_id"] = claim_id
    norm["created_at"] = created_at
    return Claim.from_dict(norm)


def ingest_claim(kernel: Kernel, data: dict[str, Any]) -> Claim:
    """Create a claim and write a ``claim.ingested`` event (canonical truth)."""

    store = EventStore(kernel)
    claim = create_claim(data, created_at=kernel.now())
    store.append("claims", "claim.ingested", claim.to_dict())
    return claim


__all__ = [
    "Claim",
    "create_claim",
    "normalize_claim",
    "validate_claim",
    "ingest_claim",
]
