"""Shared fixtures for the v0.2 test suite.

The evidence kernel is vendored under vendor/fek and resolved via pyproject's
pythonpath (".", "vendor"); this conftest only supplies the `kernel` fixture the
ported gate-demo falsification tests expect.
"""
from __future__ import annotations

import pytest

from fek.kernel import Kernel


@pytest.fixture
def kernel(tmp_path) -> Kernel:
    k = Kernel(tmp_path)
    k.init()
    return k
