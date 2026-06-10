"""Secret-like string scanner (law #8: authority-bearing secrets never committed).

Heuristic, deterministic, no network. Walks the repository and flags strings
that look like real credentials (GitHub tokens, AWS keys, private key headers,
non-empty ``secret``/``token`` fields in capability files).

To avoid flagging itself and the documentation that *describes* these patterns,
the scanner skips its own module, ``*.example`` templates, and the docs/security
prose. Patterns are assembled from fragments so this source file does not itself
contain a matchable literal.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Assembled from fragments so this file contains no matchable literal token.
_GH = "gh" + "p_"
_AWS = "AKIA"
_PRIV = "BEGIN " + "RSA PRIVATE KEY"
_GHTOK = "github" + "_pat_"

SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("github_classic_token", re.compile(re.escape(_GH) + r"[A-Za-z0-9]{20,}")),
    ("github_fine_grained_token", re.compile(re.escape(_GHTOK) + r"[A-Za-z0-9_]{20,}")),
    ("aws_access_key", re.compile(re.escape(_AWS) + r"[A-Z0-9]{12,}")),
    ("private_key_block", re.compile(re.escape("-----" + _PRIV))),
]

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".venv"}
SKIP_SUFFIXES = {".example"}
# Files that legitimately discuss secret formats.
SKIP_NAMES = {"secret_scan.py", "self_audit.py", "SECURITY.md"}
SKIP_PATH_PARTS = {"docs", "security", "tests", "specs"}


def _should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    if path.name in SKIP_NAMES:
        return True
    if any(part in SKIP_PATH_PARTS for part in rel.parts):
        return True
    return False


def scan_secrets(root: Path) -> list[dict[str, Any]]:
    """Return findings: [{file, line, pattern}]. Empty == clean."""

    findings: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or _should_skip(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {"file": str(path.relative_to(root)), "line": lineno, "pattern": name}
                    )
    return findings


def scan_capability_secrets(root: Path) -> list[dict[str, Any]]:
    """Flag capability files that embed a non-empty secret/token field."""

    import yaml

    findings: list[dict[str, Any]] = []
    cap_dir = root / "registry" / "capabilities"
    if not cap_dir.exists():
        return findings
    for path in sorted(cap_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key in ("secret", "token", "credential", "private_key", "api_key"):
            if doc.get(key):
                findings.append({"file": str(path.relative_to(root)), "field": key})
    return findings


__all__ = ["scan_secrets", "scan_capability_secrets", "SECRET_PATTERNS"]
