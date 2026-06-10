"""Shared fixtures. Locates fractal-evidence-kernel from a sibling checkout
when it is not installed (the CI workflow checks it out next to this repo)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    import fek  # noqa: F401
except ImportError:  # fall back to the sibling checkout
    sibling = REPO_ROOT.parent / "fractal-evidence-kernel" / "src"
    if sibling.exists():
        sys.path.insert(0, str(sibling))

from fek.kernel import Kernel  # noqa: E402


@pytest.fixture
def kernel(tmp_path) -> Kernel:
    k = Kernel(tmp_path)
    k.init()
    return k
