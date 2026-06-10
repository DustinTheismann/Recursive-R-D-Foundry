"""Stable programmatic facade (maturity: experimental).

A thin re-export layer so embedders can drive the kernel without importing deep
module paths. The surface is intentionally small and mirrors the CLI verbs.
"""

from __future__ import annotations

from fek.claims import ingest_claim
from fek.evidence import grade_claim
from fek.kernel import Kernel
from fek.namespaces import graph_report
from fek.prose_claims import overclaim_report
from fek.reports import generate_all, run_self_audit
from fek.runpacks import create_runpack_manifest, seal_runpack, verify_runpack
from fek.state import (
    apply_transition,
    build_state,
    propose_transition,
    snapshot,
    verify_transition,
)

__all__ = [
    "Kernel",
    "ingest_claim",
    "grade_claim",
    "create_runpack_manifest",
    "seal_runpack",
    "verify_runpack",
    "propose_transition",
    "verify_transition",
    "apply_transition",
    "build_state",
    "snapshot",
    "graph_report",
    "overclaim_report",
    "generate_all",
    "run_self_audit",
]
