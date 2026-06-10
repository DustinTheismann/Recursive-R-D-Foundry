"""Runpack re-execution (maturity: experimental).

Re-runs a sealed runpack's command log via subprocess and compares each
command's stdout hash against the expectations sealed inside the runpack. This
upgrades replay from "the files exist and the seal matches" to "the commands
actually reproduce the recorded outputs".

Honesty notes:

* This is **process re-execution, not an isolation sandbox**. Commands run as
  the invoking user with a scrubbed environment and a timeout; they are not
  containerized. True sandboxed execution (Wasm) remains spec_only.
* Because spawning processes is authority-bearing, execution is gated by the
  ``runpack_executor`` capability: no active grant, no execution (law #7).
  Every run is audited to the capability event log.
* Matching output hashes prove the bundle reproduces -- integrity of the
  reproduction, not correctness of the science (law #15).
"""

from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any

from fek.errors import CapabilityDenied, RunpackError
from fek.kernel.canonical import sha256_hex
from fek.kernel.context import Kernel

CAPABILITY_ID = "runpack_executor"
DEFAULT_TIMEOUT = 60  # seconds per command


def _require_grant(kernel: Kernel) -> None:
    from fek.capabilities import active_grants, load_capabilities

    if CAPABILITY_ID not in load_capabilities(kernel):
        raise CapabilityDenied(f"capability {CAPABILITY_ID!r} is not registered (deny-by-default)")
    if CAPABILITY_ID not in active_grants(kernel):
        raise CapabilityDenied(
            f"runpack re-execution requires an active {CAPABILITY_ID!r} grant (deny-by-default, law #7)"
        )


def execute_runpack(kernel: Kernel, runpack, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Re-execute a sealed runpack's commands and check output hashes.

    Requires an active ``runpack_executor`` grant. Verifies the seal first, then
    runs each command with a scrubbed environment (``PATH`` only) from the
    kernel root. If the runpack declares ``outputs`` (command index -> sha256 of
    stdout), each must match. Emits ``runpack.replayed`` on success and
    ``runpack.replay_failed`` on mismatch/failure.
    """

    from fek.runpacks import verify_runpack
    from fek.state.store import EventStore

    _require_grant(kernel)
    verify_runpack(kernel, runpack, emit=False)

    store = EventStore(kernel)
    results: list[dict[str, Any]] = []
    try:
        for i, cmd in enumerate(runpack.command_log):
            argv = shlex.split(cmd)
            if not argv:
                raise RunpackError(f"runpack {runpack.runpack_id}: empty command at index {i}")
            try:
                proc = subprocess.run(
                    argv,
                    cwd=kernel.root,
                    capture_output=True,
                    timeout=timeout,
                    env={"PATH": os.environ.get("PATH", "")},
                )
            except FileNotFoundError as exc:
                raise RunpackError(f"command not found: {argv[0]!r}") from exc
            except subprocess.TimeoutExpired as exc:
                raise RunpackError(f"command timed out after {timeout}s: {cmd!r}") from exc
            if proc.returncode != 0:
                raise RunpackError(
                    f"command failed (exit {proc.returncode}): {cmd!r}: {proc.stderr.decode(errors='replace')[:200]}"
                )
            stdout_hash = "sha256:" + sha256_hex(proc.stdout)
            expected = runpack.outputs.get(str(i), "")
            if expected and expected != stdout_hash:
                raise RunpackError(
                    f"output mismatch at command {i} ({cmd!r}): expected {expected}, got {stdout_hash}"
                )
            results.append({"index": i, "command": cmd, "stdout_hash": stdout_hash, "matched": bool(expected)})
    except RunpackError as exc:
        store.append(
            "runpack",
            "runpack.replay_failed",
            {"runpack_id": runpack.runpack_id, "claim_id": runpack.claim_id, "error": str(exc)},
        )
        raise

    report = {
        "runpack_id": runpack.runpack_id,
        "claim_id": runpack.claim_id,
        "commands_run": len(results),
        "outputs_checked": sum(1 for r in results if r["matched"]),
        "results": results,
        "trust_boundary": "local-subprocess-no-isolation",
        "note": "re-execution proves the bundle reproduces; it is not an isolation sandbox (law #15)",
    }
    store.append(
        "runpack",
        "runpack.replayed",
        {k: report[k] for k in ("runpack_id", "claim_id", "commands_run", "outputs_checked")},
    )
    store.append(
        "capability",
        "capability.invoked",
        {"capability_id": CAPABILITY_ID, "trust_boundary": "local-subprocess-no-isolation",
         "maturity": "experimental", "result_status": "ok"},
    )
    return report


__all__ = ["execute_runpack", "CAPABILITY_ID", "DEFAULT_TIMEOUT"]
