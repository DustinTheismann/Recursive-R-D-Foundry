"""Report generation and self-audit.

This package produces the generated audit trail (``reports/generated/*.md`` and
``data/generated/*``) and runs the root self-audit. Everything it writes is a
derived view, never source truth (law #4), and is reproducible from the event
logs (law #6).
"""

from __future__ import annotations

from fek.reports.generate import generate_all, load_manifest
from fek.reports.self_audit import run_self_audit
from fek.reports.secret_scan import scan_capability_secrets, scan_secrets

__all__ = ["generate_all", "load_manifest", "run_self_audit", "scan_secrets", "scan_capability_secrets"]
