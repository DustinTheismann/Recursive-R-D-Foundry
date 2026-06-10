"""Toolchain registry (maturity: experimental).

Declares external toolchains (proof checkers, SAT solvers, numeric harnesses)
the kernel *could* route to. In v0.1 these are declarations only -- the actual
integrations are ``spec_only`` (see ``specs/future``). The wiring oracle reads
their maturity to decide whether high evidence classes may be honored.
"""

from __future__ import annotations

from typing import Any

import yaml

from fek.kernel.context import Kernel


def load_toolchains(kernel: Kernel) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    d = kernel.paths.registry / "toolchains"
    if not d.exists():
        return out
    for path in sorted(d.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        tid = doc.get("toolchain_id")
        if tid:
            out[tid] = doc
    return out


def live_toolchains(kernel: Kernel) -> list[str]:
    return [tid for tid, doc in load_toolchains(kernel).items() if doc.get("maturity") == "live"]


__all__ = ["load_toolchains", "live_toolchains"]
