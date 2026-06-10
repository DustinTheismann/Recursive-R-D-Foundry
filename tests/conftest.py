"""Shared fixtures. The evidence kernel is vendored under vendor/fek and added
to sys.path here, so the suite runs cold with no external checkout or install."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
for sub in ("src", "vendor"):
    p = REPO_ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fek.kernel import Kernel  # noqa: E402


@pytest.fixture
def kernel(tmp_path) -> Kernel:
    k = Kernel(tmp_path)
    k.init()
    return k
