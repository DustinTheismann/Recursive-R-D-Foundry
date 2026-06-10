"""Prose claim extraction and overclaim scanning (law #11).

A lightweight, deterministic, **no-LLM** scanner. It walks public documentation,
finds sentences using strong-claim words ("verified", "proven", "E9",
"production-ready", ...), and flags each one that is neither marked speculative
nor backed by a source map.

This is a heuristic for v0.1 (maturity: live, but acknowledged as heuristic). It
catches the obvious overclaims that the constitution forbids; it is not a
natural-language understanding engine and does not pretend to be.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fek.kernel.context import Kernel
from fek.types import SPECULATIVE_MARKERS, STRONG_CLAIM_WORDS

#: Files/globs scanned for public claims.
SCAN_TARGETS = (
    "README.md",
    "CURRENT_STATUS.md",
    "docs/*.md",
    "examples/*/README.md",
)


def _compile(word: str) -> re.Pattern:
    """Word-boundary matcher so "secure" does not match "security".

    Boundaries are only required where the word edge is alphanumeric, so
    hyphenated phrases like ``production-ready`` still anchor correctly.
    """

    esc = re.escape(word)
    left = r"\b" if word[0].isalnum() else ""
    right = r"\b" if word[-1].isalnum() else ""
    return re.compile(left + esc + right, re.IGNORECASE)


_PATTERNS: list[tuple[str, re.Pattern]] = [(w, _compile(w)) for w in STRONG_CLAIM_WORDS]


@dataclass
class ProseSpan:
    file: str
    line: int
    word: str
    text: str
    speculative: bool
    has_source_map: bool

    @property
    def is_overclaim(self) -> bool:
        return not self.speculative and not self.has_source_map

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["is_overclaim"] = self.is_overclaim
        return d


def _iter_target_files(kernel: Kernel) -> list[Path]:
    files: list[Path] = []
    for pattern in SCAN_TARGETS:
        if "*" in pattern:
            files.extend(sorted(kernel.root.glob(pattern)))
        else:
            p = kernel.root / pattern
            if p.exists():
                files.append(p)
    return files


def _line_is_speculative(line: str) -> bool:
    low = line.lower()
    return any(marker in low for marker in SPECULATIVE_MARKERS)


def scan_prose(kernel: Kernel) -> list[ProseSpan]:
    """Scan target files and return every strong-claim span found."""

    from fek.source_maps import covering_map

    spans: list[ProseSpan] = []
    for path in _iter_target_files(kernel):
        rel = str(path.relative_to(kernel.root))
        in_fence = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                # Fenced code blocks are identifiers/commands, not public claims.
                continue
            speculative = _line_is_speculative(line)
            for word, pattern in _PATTERNS:
                if pattern.search(line):
                    has_map = covering_map(kernel, rel, lineno) is not None
                    spans.append(
                        ProseSpan(
                            file=rel,
                            line=lineno,
                            word=word,
                            text=line.strip()[:200],
                            speculative=speculative,
                            has_source_map=has_map,
                        )
                    )
    return spans


def overclaim_report(kernel: Kernel) -> dict[str, Any]:
    """Aggregate scan into overclaim / missing-source-map / unsupported reports."""

    spans = scan_prose(kernel)
    overclaims = [s for s in spans if s.is_overclaim]
    missing_maps = [s for s in spans if not s.has_source_map and not s.speculative]
    return {
        "total_spans": len(spans),
        "overclaim_count": len(overclaims),
        "spans": [s.to_dict() for s in spans],
        "overclaims": [s.to_dict() for s in overclaims],
        "missing_source_maps": [s.to_dict() for s in missing_maps],
        "unsupported_evidence_language": [
            s.to_dict() for s in overclaims if s.word.upper().startswith("E")
        ],
    }


__all__ = ["ProseSpan", "scan_prose", "overclaim_report", "SCAN_TARGETS"]
