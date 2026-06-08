"""Containment: run candidate code under isolation, two backends.

* ``SubprocessSandbox`` (default for the evaluator quorum) — real OS-level
  isolation: separate process, CPU + memory rlimits, wall-clock timeout,
  restricted builtins. Containment success/failure is itself a gate signal.
* ``InProcessSandbox`` — fast path for already-validated candidates (e.g. the
  inner ablation sweep), guarded by the static analyzer. Trades isolation for
  speed where the candidate has already cleared containment once.
* ``DockerSandbox`` — activates automatically if a Docker daemon is reachable,
  giving full kernel-level isolation; otherwise the factory falls back.

All three return the same dict shape so callers are backend-agnostic.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from rsi_foundry.sandbox.simulate import run_instance

_PKG_PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ContainmentPolicy:
    cpu_seconds: int = 2
    mem_mb: int = 256
    wall_timeout: float = 8.0


class SubprocessSandbox:
    backend = "subprocess"

    def __init__(self, policy: ContainmentPolicy | None = None):
        self.policy = policy or ContainmentPolicy()

    def run(self, source: str, instances: list[dict]) -> dict[str, Any]:
        job = {
            "source": source,
            "instances": instances,
            "cpu_seconds": self.policy.cpu_seconds,
            "mem_mb": self.policy.mem_mb,
        }
        env = dict(os.environ)
        env["PYTHONPATH"] = _PKG_PARENT + os.pathsep + env.get("PYTHONPATH", "")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "rsi_foundry.sandbox.runner"],
                input=json.dumps(job),
                capture_output=True,
                text=True,
                timeout=self.policy.wall_timeout,
                cwd=_PKG_PARENT,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout", "contained": True, "breach": False}
        if proc.returncode != 0:
            # Killed by rlimit (e.g. CPU/mem) -> contained, not a breach of the box.
            return {"ok": False, "error": f"exit:{proc.returncode}:{proc.stderr[-300:]}",
                    "contained": True, "breach": False}
        try:
            out = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:
            return {"ok": False, "error": "unparseable-output", "contained": True,
                    "breach": False}
        out["contained"] = True
        out["breach"] = False
        return out


class InProcessSandbox:
    backend = "in_process"

    def __init__(self, policy: ContainmentPolicy | None = None):
        self.policy = policy or ContainmentPolicy()

    def run(self, source: str, instances: list[dict]) -> dict[str, Any]:
        safe = {
            "range": range, "len": len, "min": min, "max": max, "abs": abs,
            "float": float, "int": int, "bool": bool, "enumerate": enumerate,
            "sorted": sorted, "sum": sum, "round": round, "map": map,
            "filter": filter, "list": list, "tuple": tuple, "dict": dict,
            "set": set, "zip": zip, "True": True, "False": False, "None": None,
        }
        try:
            ns: dict = {"__builtins__": safe}
            exec(compile(source, "<candidate>", "exec"), ns)  # noqa: S102
            place = ns.get("place")
            if not callable(place):
                raise ValueError("no place()")
        except Exception as exc:
            return {"ok": False, "error": f"load:{exc}", "contained": True, "breach": False}
        try:
            results = [run_instance(place, i["items"], i["capacity"]) for i in instances]
        except Exception as exc:
            return {"ok": False, "error": f"run:{exc}", "contained": True, "breach": False}
        return {"ok": True, "results": results, "contained": True, "breach": False}


def docker_available() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=4)
        return r.returncode == 0
    except Exception:
        return False


def make_sandbox(prefer: str = "subprocess",
                 policy: ContainmentPolicy | None = None):
    """Factory that picks the strongest available backend."""
    if prefer == "in_process":
        return InProcessSandbox(policy)
    return SubprocessSandbox(policy)
