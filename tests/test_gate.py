"""The gate's falsification conditions (SPEC.md §4), as executable tests.

Each test is paired where it matters: the gate must refuse the bad candidate
AND accept the honest one, or it proves nothing.
"""

from __future__ import annotations

from fek.quarantine import load_quarantine
from fek.state import build_state

from foundry.agents import broken, goodhart, honest
from foundry.gate import FOUNDRY_ID, attempt_promotion, evaluate_candidate
from foundry.loop import run_demo


# F1 -- the core negative demonstration ------------------------------------
def test_f1_goodharted_successor_is_refused(kernel):
    result = evaluate_candidate(kernel, "goodhart", goodhart)
    assert result["grade"] == "EX_REFUTED"
    assert result["refutation_id"] is not None
    promo = attempt_promotion(kernel, result["claim_id"])
    assert not promo["allowed"] and promo["status"] == "refuted"
    # the refutation override is among the recorded denial reasons
    assert any("refutation" in d for d in promo["denials"])


# F2 -- the gate must not be vacuous ----------------------------------------
def test_f2_honest_successor_is_promoted(kernel):
    result = evaluate_candidate(kernel, "honest", honest)
    assert result["grade"] == "E4_REPRODUCED"
    promo = attempt_promotion(kernel, result["claim_id"])
    assert promo["applied"] and promo["status"] == "accepted"


# F3 -- the contamination channel stays closed -------------------------------
def test_f3_extracted_traits_are_quarantined_held(kernel):
    evaluate_candidate(kernel, "goodhart", goodhart)
    evaluate_candidate(kernel, "broken", broken)
    quarantine = load_quarantine(kernel)
    assert quarantine, "failure traits must be extracted and quarantined"
    assert all(q["status"] == "held" for q in quarantine.values())
    assert any("public_benchmark_overfit" in q["object_ref"] for q in quarantine.values())


# F4 -- the foundry may propose but never self-promote ------------------------
def test_f4_foundry_self_promotion_denied_even_for_honest_candidate(kernel):
    result = evaluate_candidate(kernel, "honest", honest)
    promo = attempt_promotion(kernel, result["claim_id"], proposed_by=FOUNDRY_ID)
    assert not promo["allowed"]
    assert any("self-promote" in d for d in promo["denials"])
    # corrected case: an independent proposer succeeds
    promo2 = attempt_promotion(kernel, result["claim_id"])
    assert promo2["applied"]


# F5 -- mere incapability is refused for lack of evidence, not refuted ---------
def test_f5_broken_candidate_lacks_evidence(kernel):
    result = evaluate_candidate(kernel, "broken", broken)
    assert result["grade"] == "E0_RAW"
    assert result["refutation_id"] is None  # ordinary failure, not Goodhart
    promo = attempt_promotion(kernel, result["claim_id"])
    assert not promo["allowed"]
    assert any("insufficient evidence" in d for d in promo["denials"])


# The full loop, end to end ---------------------------------------------------
def test_demo_loop_holds_all_falsification_conditions(tmp_path):
    demo = run_demo(tmp_path)
    out = demo["outcomes"]
    assert out["goodhart"]["promotion"]["status"] == "refuted"
    assert out["honest"]["promotion"]["status"] == "accepted"
    assert out["broken"]["promotion"]["status"] == "raw"
    assert demo["all_traits_held"]


def test_everything_is_on_the_event_log(kernel):
    # No silent state: every decision in the loop is replayable from events.
    result = evaluate_candidate(kernel, "goodhart", goodhart)
    attempt_promotion(kernel, result["claim_id"])
    state = build_state(kernel)
    assert result["claim_id"] in state["claims"]
    assert state["refutations"], "the probe counterexample is on the log"
    assert state["transitions"], "the denied promotion is on the log"
