"""Ported falsification suite: FEK governance as a supervening veto.

These tests prove the *delta* the evidence kernel adds over v0.2's internal
gate. v0.2 decides `promoted` about itself; FEK refuses to take its word for it.
Each condition is paired (bad refused / corrected promoted) and runs COLD from
the vendored kernel — no external clone, no network.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
for sub in (".", "vendor"):
    p = str(REPO_ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from fek.kernel import Kernel  # noqa: E402

from rsi_foundry.core.types import Candidate, EvalResult, GateReport  # noqa: E402
from rsi_foundry.governance.evidence_gate import EvidenceGate, FOUNDRY_ID, REVIEW_ID  # noqa: E402


@pytest.fixture
def gate():
    return EvidenceGate(Kernel(tempfile.mkdtemp(prefix="rsi-gov-test-")))


def _cand(cid="cand1"):
    return Candidate(cid=cid, source="def place(): ...", genome={}, origin="test")


def _report(**kw):
    base = dict(
        cid="cand1", fitness=0.9, fitness_delta=0.05, benchmark_pass=True,
        contained=True, contracts_pass=True, causal_pass=True, causal_effect=0.04,
        regression_failures=0, promoted=True,
    )
    base.update(kw)
    return GateReport(**base)


# PF1 -- self-attestation is not enough: producer != verifier (FEK law #3) -----
def test_self_attested_only_is_not_promoted(gate):
    # v0.2 promotes, but the only evidence is the foundry's own benchmark
    # (no independent causal verifier): FEK withholds promotion.
    report = gate.govern(_cand(), EvalResult(cid="cand1", valid=True, fitness=0.9),
                         _report(causal_pass=False, causal_effect=0.0))
    assert report.promoted is False
    assert report.fek_refutation_id is not None  # failed_reproduction filed
    # corrected: an independent ablation verifier yields E4 -> promoted
    report2 = gate.govern(_cand("cand2"), EvalResult(cid="cand2", valid=True, fitness=0.9),
                          _report(cid="cand2"))
    assert report2.promoted is True and report2.fek_grade == "E4_REPRODUCED"


# PF2 -- refutation supremacy: a regression vetoes regardless (law #2) ---------
def test_regression_refutes_even_if_v02_promoted(gate):
    # Force v0.2 to say promoted=True while a regression exists; FEK must refuse.
    report = gate.govern(_cand("r1"), EvalResult(cid="r1", valid=True, fitness=0.9),
                         _report(cid="r1", regression_failures=1, promoted=True))
    assert report.promoted is False
    assert report.fek_grade == "EX_REFUTED" and report.fek_refutation_id is not None
    # corrected: no regression -> promoted
    report2 = gate.govern(_cand("r2"), EvalResult(cid="r2", valid=True, fitness=0.9),
                          _report(cid="r2", regression_failures=0))
    assert report2.promoted is True


# PF3 -- containment breach refutes (law #2 via policy_violation) --------------
def test_containment_breach_refutes(gate):
    report = gate.govern(_cand("b1"), EvalResult(cid="b1", valid=True, fitness=0.9),
                         _report(cid="b1", contained=False, promoted=True))
    assert report.promoted is False and report.fek_grade == "EX_REFUTED"


# PF4 -- the foundry cannot self-promote (law #13) -----------------------------
def test_foundry_cannot_self_promote(gate):
    cand, res, report = _cand("s1"), EvalResult(cid="s1", valid=True, fitness=0.9), _report(cid="s1")
    # File the claim/evidence by governing once, then try a foundry-proposed promotion.
    gate.govern(cand, res, report)
    from fek.state import propose_transition, verify_transition

    txn = propose_transition(gate.kernel, report.fek_claim_id, "promote", proposed_by=FOUNDRY_ID)
    decision = verify_transition(gate.kernel, txn.transition_id)
    assert not decision["allowed"]
    assert any("self-promote" in r["reason"] for r in decision["results"] if not r["allowed"])


# PF5 -- v0.2 rejection is never overridden upward -----------------------------
def test_fek_never_promotes_what_v02_rejected(gate):
    report = gate.govern(_cand("n1"), EvalResult(cid="n1", valid=True, fitness=0.3),
                         _report(cid="n1", promoted=False, benchmark_pass=False))
    assert report.promoted is False
    assert report.fek_promoted is False


# Everything is on the append-only log -----------------------------------------
def test_decisions_are_recorded_on_the_event_log(gate):
    gate.govern(_cand("e1"), EvalResult(cid="e1", valid=True, fitness=0.9),
                _report(cid="e1", regression_failures=1))
    state = gate.state()
    assert state["claims"], "the governed claim is on the log"
    assert state["refutations"], "the regression refutation is on the log"
