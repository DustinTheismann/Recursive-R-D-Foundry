"""Governed orchestrator demo that witnesses BOTH halves of the gate.

A gate that is only ever seen to refuse is indistinguishable from one that is
stuck shut (the F2 principle). This run asserts the gate both SHUTS (refutations
structurally block promotion) and OPENS (an honest improvement clears E4 and is
promoted) on the default branch, cold. Exits non-zero if either half is absent.
"""
from __future__ import annotations

import sys

from rsi_foundry.core.orchestrator import Foundry

CYCLES, SEED = 8, 7


def main() -> int:
    f = Foundry({"cycles": CYCLES, "seed": SEED})
    f.run()
    state = f.evidence_gate.state()
    claims = state["claims"]
    accepted = [c for c in claims.values() if c["status"] == "accepted"]
    refuted = [c for c in claims.values() if c["status"] == "refuted"]
    events = sum(state["event_counts"].values())
    print(f"governed orchestrator (cycles={CYCLES}, seed={SEED}):")
    print(f"  claims={len(claims)} accepted={len(accepted)} refuted={len(refuted)} events={events}")
    if accepted:
        print(f"  sample promoted grade: {accepted[0].get('grade', {}).get('actual_grade')}")
    # Both halves must be witnessed.
    if not refuted:
        print("WITNESS FAILED: no refutation blocked promotion (gate never shut)", file=sys.stderr)
        return 1
    if not accepted:
        print("WITNESS FAILED: no honest candidate was promoted (gate never opened)", file=sys.stderr)
        return 1
    print("  both halves witnessed: gate opens (promotion) AND shuts (refutation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
