"""Deterministic canonical JSON + content hashing.

Reproducibility (law #6) and integrity (law #15) both rest on a single rule:
*any two processes that serialize the same logical object must produce the
exact same bytes.* We achieve that with sorted keys, compact separators, and
UTF-8 without ASCII escaping.

Nothing here proves a claim is *correct*. A hash proves only that bytes did not
change. That distinction is the entire point of law #15.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Return the canonical JSON *string* for ``obj``.

    Rules: keys sorted, no insignificant whitespace, UTF-8 preserved. This is
    the only serialization used for hashing and for writing event payloads, so
    that re-serialization is byte-identical.
    """

    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def canonical_bytes(obj: Any) -> bytes:
    """Canonical JSON encoded as UTF-8 bytes."""

    return canonical_json(obj).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    """SHA-256 hex digest of bytes or text.

    Returned with a ``sha256:`` prefix is *not* done here on purpose: callers
    that build Merkle trees need the raw hex. Use :func:`content_id` when you
    want a namespaced identifier.
    """

    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def content_id(prefix: str, obj: Any) -> str:
    """Deterministic, namespaced content identifier, e.g. ``clm_ab12...``.

    The id is derived purely from the canonical content, so the same logical
    object always gets the same id (idempotent ingestion).
    """

    digest = sha256_hex(canonical_bytes(obj))
    return f"{prefix}_{digest[:16]}"


__all__ = ["canonical_json", "canonical_bytes", "sha256_hex", "content_id"]
