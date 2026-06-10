"""Root self-audit (law #12: the root kernel must self-audit).

Runs a fixed battery of constitutional checks against the live repository and
returns a structured report. ``fek audit`` exits non-zero if any check fails, so
CI can enforce the constitution. Each check maps to one or more hard laws.
"""

from __future__ import annotations

from typing import Any

from fek.kernel.context import Kernel
from fek.kernel.canonical import sha256_hex


def _check(checks: list[dict[str, Any]], cid: str, passed: bool, detail: str) -> None:
    checks.append({"id": cid, "passed": bool(passed), "detail": detail})


def run_self_audit(kernel: Kernel) -> dict[str, Any]:
    """Return ``{"passed": bool, "checks": [...]}``."""

    from fek.layers import load_layers, validate_layers
    from fek.state.snapshot import build_state
    from fek.evidence.grader import grade_claim
    from fek.obligations import required_class_for
    from fek.prose_claims import overclaim_report
    from fek.source_maps import validate_source_maps
    from fek.reports.secret_scan import scan_secrets, scan_capability_secrets
    from fek.reports.generate import load_manifest, current_block_hash, STATUS_START, STATUS_END
    from fek.types import EvidenceClass, evidence_rank

    checks: list[dict[str, Any]] = []
    state = build_state(kernel)
    claims = state["claims"]

    # 1. Layers valid (maturity present, no dup index) -- laws #10, #14.
    layer_errors = validate_layers(kernel)
    _check(checks, "layers_valid", not layer_errors, "; ".join(layer_errors) or "all layer defs valid")

    # 2. No live layer missing a maturity label (law #10).
    no_maturity = [l.id for l in load_layers(kernel) if not l.maturity]
    _check(checks, "no_live_layer_without_maturity", not no_maturity, str(no_maturity) or "all layers labelled")

    # 3. No spec_only layer advertised as live (law #14).
    bad_spec = [l.id for l in load_layers(kernel) if l.maturity == "spec_only" and l.status == "live"]
    _check(checks, "no_spec_only_advertised_live", not bad_spec, str(bad_spec) or "spec_only kept honest")

    # 4. Generated views unmodified (law #6).
    manifest = load_manifest(kernel)
    drift: list[str] = []
    for rel, recorded in manifest.items():
        if rel.endswith("#generated_block"):
            actual = current_block_hash(kernel)
        else:
            path = kernel.root / rel
            actual = sha256_hex(path.read_text(encoding="utf-8")) if path.exists() else None
        if actual != recorded:
            drift.append(rel)
    _check(checks, "generated_views_unmodified", not drift, str(drift) or "no manifest drift")

    # 5. No committed secrets (law #8).
    secrets = scan_secrets(kernel.root) + scan_capability_secrets(kernel.root)
    _check(checks, "no_committed_secrets", not secrets, str(secrets) or "no secret-like strings")

    # 6. No authority-bearing .cap files committed (law #8).
    cap_files = [str(p.relative_to(kernel.root)) for p in kernel.root.rglob("*.cap") if ".example" not in p.suffixes]
    _check(checks, "no_authority_cap_files", not cap_files, str(cap_files) or "no committed .cap files")

    # 7. Every accepted claim has sufficient honored evidence (law #1).
    weak_accepted: list[str] = []
    for cid, claim in claims.items():
        if claim.get("status") == "accepted":
            g = grade_claim(kernel, claim, emit=False)
            req = required_class_for(claim.get("claim_type", ""), claim.get("required_evidence"))
            if g.refuted or evidence_rank(EvidenceClass(g.actual_grade)) < evidence_rank(req):
                weak_accepted.append(cid)
    _check(checks, "accepted_claims_have_evidence", not weak_accepted, str(weak_accepted) or "all accepted claims backed")

    # 8. No refuted claim sitting in the accepted view (law #2).
    refuted_accepted: list[str] = []
    for cid, claim in claims.items():
        if claim.get("status") == "accepted":
            if grade_claim(kernel, claim, emit=False).refuted:
                refuted_accepted.append(cid)
    _check(checks, "no_refuted_in_accepted", not refuted_accepted, str(refuted_accepted) or "no refuted claim accepted")

    # 9. CURRENT_STATUS generated block not stale (law #6).
    stale = _status_block_stale(kernel, state["state_root"], STATUS_START, STATUS_END)
    _check(checks, "current_status_not_stale", not stale, "stale generated block" if stale else "status block fresh")

    # 10. No unsupported strong public claims (law #11).
    over = overclaim_report(kernel)
    _check(checks, "no_overclaims", over["overclaim_count"] == 0, f"{over['overclaim_count']} overclaim(s)")

    # 11. Source maps valid (law #11).
    sm_errors = validate_source_maps(kernel)
    _check(checks, "source_maps_valid", not sm_errors, "; ".join(sm_errors) or "source maps valid")

    # 12. No ZK/Wasm/etc. future tech marked live unless implemented (law #14).
    future_live = _future_tech_marked_live(kernel)
    _check(checks, "no_future_tech_live", not future_live, str(future_live) or "future tech kept spec_only")

    # 13. Every live capability declares a trust boundary (law #9).
    from fek.capabilities import load_capabilities

    unbounded = [
        cid
        for cid, cap in load_capabilities(kernel).items()
        if cap.get("maturity") == "live" and not str(cap.get("trust_boundary", "")).strip()
    ]
    _check(checks, "live_capabilities_have_trust_boundary", not unbounded, str(unbounded) or "all live capabilities bounded")

    # 14. Event-log hash chains intact (laws #5, #15 -- integrity only).
    from fek.state.store import EventStore

    chain_errors = [err for err in EventStore(kernel).verify_chains().values() if err]
    _check(checks, "event_chains_intact", not chain_errors, "; ".join(chain_errors) or "all log chains intact")

    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "checks": checks, "state_root": state["state_root"]}


def _status_block_stale(kernel: Kernel, state_root: str, start: str, end: str) -> bool:
    import re

    path = kernel.root / "CURRENT_STATUS.md"
    if not path.exists():
        return False
    m = re.search(re.escape(start) + r".*?" + re.escape(end), path.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        return False  # no generated block yet -> not stale, just absent
    return state_root not in m.group(0)


def _future_tech_marked_live(kernel: Kernel) -> list[str]:
    from fek.layers import load_layers
    from fek.capabilities import load_capabilities
    from fek.tools import load_toolchains

    needles = ("zk", "zero-knowledge", "wasm", "webassembly", "solidity", "rego")
    bad: list[str] = []
    for l in load_layers(kernel):
        blob = (l.name + " " + l.description).lower()
        if l.maturity == "live" and any(n in blob for n in needles):
            bad.append(f"layer:{l.id}")
    for cid, cap in load_capabilities(kernel).items():
        blob = (cid + " " + str(cap.get("description", ""))).lower()
        if cap.get("maturity") == "live" and any(n in blob for n in needles):
            bad.append(f"capability:{cid}")
    for tid, tc in load_toolchains(kernel).items():
        blob = (tid + " " + str(tc.get("description", ""))).lower()
        if tc.get("maturity") == "live" and any(n in blob for n in needles):
            bad.append(f"toolchain:{tid}")
    return bad


__all__ = ["run_self_audit"]
