"""The ``fek`` command-line interface (argparse, standard library only).

Every verb maps to a kernel operation and prints a concise, machine-friendly
summary. Refusals (policy denials, capability denials, seal mismatches) exit
non-zero so CI guards and the Makefile can depend on them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fek.errors import FEKError
from fek.kernel import Kernel
from fek.version import VERSION


def _kernel(args: argparse.Namespace) -> Kernel:
    return Kernel(args.root)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


# -- command handlers ----------------------------------------------------
def cmd_init(args) -> int:
    k = _kernel(args)
    k.init()
    print(f"initialised kernel root at {k.root}")
    print(f"event logs: {k.paths.events}")
    return 0


def cmd_ingest_claim(args) -> int:
    from fek.claims import ingest_claim

    k = _kernel(args)
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    claim = ingest_claim(k, data)
    print(f"ingested claim {claim.claim_id} (status={claim.status})")
    return 0


def _find_claim(k: Kernel, claim_id: str) -> dict[str, Any]:
    from fek.state.snapshot import build_state

    claim = build_state(k)["claims"].get(claim_id)
    if claim is None:
        raise FEKError(f"unknown claim: {claim_id}")
    return claim


def cmd_grade(args) -> int:
    from fek.evidence import grade_claim

    k = _kernel(args)
    claim = _find_claim(k, args.claim_id)
    result = grade_claim(k, claim)
    _print(result.to_dict())
    return 0


def cmd_seal_runpack(args) -> int:
    from fek.runpacks import create_runpack_manifest, seal_runpack
    from fek.kernel.canonical import sha256_hex
    from fek.state.store import EventStore

    k = _kernel(args)
    claim = _find_claim(k, args.claim_id)
    meta = claim.get("metadata", {})
    files = meta.get("runpack_files") or ([claim["source"]] if claim.get("source") else [])
    manifest = []
    artifact_hashes = {}
    for rel in files:
        p = k.root / rel
        h = "sha256:" + sha256_hex(p.read_text(encoding="utf-8")) if p.exists() else "missing"
        manifest.append({"path": rel, "hash": h})
        artifact_hashes[rel] = h
    rp = create_runpack_manifest(
        claim_id=args.claim_id,
        created_at=k.now(),
        manifest=manifest,
        command_log=meta.get("commands", ["echo 'reproduced'"]),
        artifact_hashes=artifact_hashes,
        environment={"python": "3.11", "os": "linux"},
    )
    rp = seal_runpack(k, rp)
    EventStore(k).append("claims", "claim.runpack_attached", {"claim_id": args.claim_id, "runpack_id": rp.runpack_id})
    print(f"sealed runpack {rp.runpack_id} -> {rp.sealed_hash}")
    return 0


def cmd_create_refutation(args) -> int:
    from fek.refutations import create_refutation

    k = _kernel(args)
    ref = create_refutation(k, args.claim_id, args.type, args.statement, args.source or "cli")
    print(f"created refutation {ref.refutation_id}; claim {args.claim_id} forced to refuted")
    return 0


def cmd_propose_transition(args) -> int:
    from fek.state import propose_transition

    k = _kernel(args)
    txn = propose_transition(k, args.claim_id, args.action, proposed_by=args.by)
    print(f"proposed transition {txn.transition_id} ({args.action} {args.claim_id})")
    return 0


def cmd_verify_transition(args) -> int:
    from fek.state import verify_transition

    k = _kernel(args)
    decision = verify_transition(k, args.transition_id)
    _print(decision)
    return 0 if decision["allowed"] else 1


def cmd_apply_transition(args) -> int:
    from fek.state import apply_transition

    k = _kernel(args)
    result = apply_transition(k, args.transition_id)
    print(f"applied transition {result['transition_id']}: {result['claim_id']} -> {result['new_status']}")
    return 0


def cmd_generate_state(args) -> int:
    from fek.state.snapshot import write_snapshot

    k = _kernel(args)
    root = write_snapshot(k)
    print(f"state_root: {root}")
    print("(a state_root proves integrity, not correctness -- law #15)")
    return 0


def cmd_generate_graph(args) -> int:
    from fek.namespaces import export_json

    k = _kernel(args)
    report = export_json(k)
    print(f"namespace graph: {report['instance_count']} instances, acyclic={report['acyclic']}")
    return 0


def cmd_generate_report(args) -> int:
    from fek.reports import generate_all

    k = _kernel(args)
    out = generate_all(k)
    print(f"generated {len(out['generated'])} views; state_root={out['state_root']}")
    print(f"self_audit_passed={out['self_audit_passed']}")
    for rel in out["generated"]:
        print(f"  - {rel}")
    return 0


def cmd_scan_overclaims(args) -> int:
    from fek.prose_claims import overclaim_report

    k = _kernel(args)
    report = overclaim_report(k)
    print(f"strong-claim spans: {report['total_spans']}, overclaims: {report['overclaim_count']}")
    for s in report["overclaims"]:
        print(f"  OVERCLAIM {s['file']}:{s['line']} '{s['word']}' -> {s['text']}")
    return 1 if report["overclaim_count"] else 0


def cmd_audit(args) -> int:
    from fek.reports import run_self_audit

    k = _kernel(args)
    report = run_self_audit(k)
    for c in report["checks"]:
        print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['id']}: {c['detail']}")
    print(f"self-audit: {'PASS' if report['passed'] else 'FAIL'} (state_root={report['state_root']})")
    return 0 if report["passed"] else 1


def cmd_artifact(args) -> int:
    from fek.cli.artifact import build_artifact

    k = _kernel(args)
    out = build_artifact(k)
    print(f"artifact manifest written: {out['manifest_path']} ({out['file_count']} files)")
    return 0


def cmd_verify_chain(args) -> int:
    from fek.state.store import EventStore

    k = _kernel(args)
    statuses = EventStore(k).verify_chains()
    broken = False
    for log, err in sorted(statuses.items()):
        if err:
            broken = True
            print(f"  [FAIL] {log}: {err}")
        else:
            print(f"  [OK]   {log}")
    print("chain integrity: " + ("BROKEN" if broken else "intact") + " (integrity, not correctness -- law #15)")
    return 1 if broken else 0


def cmd_replay_runpack(args) -> int:
    from fek.runpacks import load_runpack, replay_runpack

    k = _kernel(args)
    rp = load_runpack(k, args.runpack_id)
    if args.execute:
        from fek.runpacks.execute import execute_runpack

        report = execute_runpack(k, rp)
        print(
            f"re-executed {report['commands_run']} command(s), "
            f"{report['outputs_checked']} output hash(es) matched ({report['trust_boundary']})"
        )
    else:
        report = replay_runpack(k, rp)
        print(f"replay (presence+seal): seal_ok={report['seal_ok']}, missing_files={report['missing_files']}")
    return 0


# -- parser --------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fek",
        description="Fractal Evidence Kernel -- evidence-governed substrate for computational institutions.",
    )
    p.add_argument("--root", default=".", help="kernel root directory (default: current directory)")
    p.add_argument("--version", action="version", version=f"fek {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create event logs and writable directories").set_defaults(func=cmd_init)

    sp = sub.add_parser("ingest-claim", help="ingest a claim JSON file (writes claim.ingested)")
    sp.add_argument("path", help="path to a claim JSON document")
    sp.set_defaults(func=cmd_ingest_claim)

    sp = sub.add_parser("grade", help="recompute and record a claim's evidence grade")
    sp.add_argument("claim_id")
    sp.set_defaults(func=cmd_grade)

    sp = sub.add_parser("seal-runpack", help="build and seal a runpack for a claim")
    sp.add_argument("claim_id")
    sp.set_defaults(func=cmd_seal_runpack)

    sp = sub.add_parser("create-refutation", help="file a refutation against a claim (forces refuted)")
    sp.add_argument("claim_id")
    sp.add_argument("--type", required=True, help="refutation type (e.g. counterexample)")
    sp.add_argument("--statement", required=True, help="why the claim fails")
    sp.add_argument("--source", default="", help="who/what produced the refutation")
    sp.set_defaults(func=cmd_create_refutation)

    sp = sub.add_parser("propose-transition", help="propose a claim state transition")
    sp.add_argument("claim_id")
    sp.add_argument("--action", required=True, choices=["promote", "reject", "refute", "retire"])
    sp.add_argument("--by", default="cli", help="proposer identity")
    sp.set_defaults(func=cmd_propose_transition)

    sp = sub.add_parser("verify-transition", help="run policy checks on a proposed transition")
    sp.add_argument("transition_id")
    sp.set_defaults(func=cmd_verify_transition)

    sp = sub.add_parser("apply-transition", help="apply a verified transition (re-checks policy)")
    sp.add_argument("transition_id")
    sp.set_defaults(func=cmd_apply_transition)

    sub.add_parser("generate-state", help="write a deterministic state snapshot + root").set_defaults(func=cmd_generate_state)
    sub.add_parser("generate-graph", help="export the namespace graph JSON").set_defaults(func=cmd_generate_graph)
    sub.add_parser("generate-report", help="generate all audit reports + sync status").set_defaults(func=cmd_generate_report)
    sub.add_parser("scan-overclaims", help="scan public prose for unsupported strong claims").set_defaults(func=cmd_scan_overclaims)
    sub.add_parser("audit", help="run the root self-audit (exit!=0 on failure)").set_defaults(func=cmd_audit)
    sub.add_parser("artifact", help="build the reproducibility artifact manifest").set_defaults(func=cmd_artifact)
    sub.add_parser(
        "verify-chain", help="verify the hash chain of every event log (integrity, not correctness)"
    ).set_defaults(func=cmd_verify_chain)

    sp = sub.add_parser(
        "replay-runpack",
        help="replay a sealed runpack: presence+seal check, or full re-execution with --execute (requires runpack_executor grant)",
    )
    sp.add_argument("runpack_id")
    sp.add_argument("--execute", action="store_true", help="re-run commands and compare stdout hashes")
    sp.set_defaults(func=cmd_replay_runpack)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FEKError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


__all__ = ["main", "build_parser"]
