"""Subprocess sandbox entrypoint.

Invoked as `python -m rsi_foundry.sandbox.runner`. Reads a JSON job from stdin,
applies OS-level resource limits (CPU time + address space), compiles the
candidate source under a *restricted* builtin namespace, runs every instance via
the trusted simulator, and writes JSON results to stdout.

This is the real containment boundary: a candidate that loops forever is killed
by the CPU rlimit / wall timeout; one that tries to allocate the universe hits
RLIMIT_AS; one that tries to import os/sockets fails because __import__ is absent.
"""
from __future__ import annotations

import json
import sys

from rsi_foundry.sandbox.simulate import run_instance

# A deliberately small allow-list of builtins available to candidate code.
_SAFE_BUILTINS = {
    "range": range, "len": len, "min": min, "max": max, "abs": abs,
    "float": float, "int": int, "bool": bool, "enumerate": enumerate,
    "sorted": sorted, "sum": sum, "round": round, "map": map, "filter": filter,
    "list": list, "tuple": tuple, "dict": dict, "set": set, "zip": zip,
    "True": True, "False": False, "None": None,
}


def _apply_limits(cpu_seconds: int, mem_bytes: int) -> None:
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        if mem_bytes > 0:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass  # non-POSIX or restricted; wall-clock timeout in parent still applies


def main() -> int:
    job = json.loads(sys.stdin.read())
    _apply_limits(int(job.get("cpu_seconds", 2)),
                  int(job.get("mem_mb", 256)) * 1024 * 1024)

    source = job["source"]
    instances = job["instances"]

    try:
        ns: dict = {"__builtins__": _SAFE_BUILTINS}
        compiled = compile(source, "<candidate>", "exec")
        exec(compiled, ns)  # noqa: S102 - sandboxed, restricted builtins
        place = ns.get("place")
        if not callable(place):
            raise ValueError("candidate defines no callable place()")
    except Exception as exc:  # compile/exec failure
        print(json.dumps({"ok": False, "error": f"load:{type(exc).__name__}:{exc}"}))
        return 0

    results = []
    try:
        for inst in instances:
            results.append(run_instance(place, inst["items"], inst["capacity"]))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"run:{type(exc).__name__}:{exc}"}))
        return 0

    print(json.dumps({"ok": True, "results": results}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
