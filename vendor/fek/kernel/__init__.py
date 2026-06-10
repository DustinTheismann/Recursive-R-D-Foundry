"""The root kernel: canonicalization, hashing, paths, and the run context.

This package holds the primitives that *everything else* depends on:

* deterministic canonical JSON encoding (so hashes and Merkle roots are stable),
* content hashing,
* the on-disk layout (where event logs, registries, and generated views live),
* a :class:`Kernel` context object that binds a root directory to those paths.

These primitives encode law #6 (generated views must be reproducible) and
law #15 (Merkle roots prove integrity, not correctness) at the lowest level.
"""

from __future__ import annotations

from fek.kernel.canonical import canonical_bytes, canonical_json, sha256_hex
from fek.kernel.context import Kernel
from fek.kernel.paths import Paths

__all__ = ["canonical_json", "canonical_bytes", "sha256_hex", "Kernel", "Paths"]
