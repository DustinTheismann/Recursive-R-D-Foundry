"""Attestations: who vouched for what.

An attestation is a recorded statement by a named party about a subject (a
claim, a grade, a runpack). It is content-hashed for integrity. v0.1 does
**not** do cryptographic signatures -- real signing keys are a ``spec_only``
capability (law #8: authority-bearing secrets are never committed). We do not
claim attestations are cryptographically signed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fek.kernel.canonical import canonical_bytes, canonical_json, content_id, sha256_hex
from fek.kernel.context import Kernel


@dataclass
class Attestation:
    attestation_id: str
    subject_type: str
    subject_ref: str
    attestor: str
    statement: str
    created_at: str
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def _body(self) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "subject_ref": self.subject_ref,
            "attestor": self.attestor,
            "statement": self.statement,
            "created_at": self.created_at,
        }

    def compute_hash(self) -> str:
        return "sha256:" + sha256_hex(canonical_bytes(self._body()))


def create_attestation(
    kernel: Kernel, subject_type: str, subject_ref: str, attestor: str, statement: str
) -> Attestation:
    created_at = kernel.now()
    aid = content_id("att", {"subject_ref": subject_ref, "attestor": attestor, "statement": statement})
    att = Attestation(aid, subject_type, subject_ref, attestor, statement, created_at)
    att.content_hash = att.compute_hash()
    kernel.paths.attestations.mkdir(parents=True, exist_ok=True)
    (kernel.paths.attestations / f"{aid}.json").write_text(canonical_json(att.to_dict()), encoding="utf-8")
    return att


def verify_attestation(att: Attestation) -> bool:
    return att.content_hash == att.compute_hash()


def load_attestations(kernel: Kernel) -> list[Attestation]:
    out: list[Attestation] = []
    d = kernel.paths.attestations
    if not d.exists():
        return out
    import json

    for path in sorted(d.glob("*.json")):
        out.append(Attestation(**json.loads(path.read_text(encoding="utf-8"))))
    return out


__all__ = ["Attestation", "create_attestation", "verify_attestation", "load_attestations"]
