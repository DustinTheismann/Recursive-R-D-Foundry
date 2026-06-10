"""Failure-trait extraction -- the most contaminated channel in the loop.

THREAT_MODEL.md treats this step as adversarial input, because it is: traits
harvested from failed candidates are exactly where Goodhart artifacts and
deceptive behaviours would re-enter a generation loop. Accordingly:

* extraction is rule-based and labelled **experimental** -- two transparent
  signatures, no learned components, nothing clever to hide in;
* every extracted trait is **quarantined by default** in FEK. Nothing here can
  release a trait; release requires a policy-approved transition recorded in
  the event log (FEK law #4 applied to traits), and the release conditions
  demand evaluation on *fresh* probe seeds -- the one test a memorized artifact
  cannot pass.

A trait in quarantine is data about a failure. It is not knowledge, and the
loop never treats it as knowledge.
"""

from __future__ import annotations

from typing import Any

from fek.kernel import Kernel
from fek.quarantine import quarantine_candidate

from gate_demo.benchmark import perfect

#: Release conditions every extracted trait carries into quarantine.
RELEASE_CONDITIONS = [
    "re-evaluated against a freshly seeded probe set (seed unseen at extraction time)",
    "independent human review recorded in the review log",
    "released only via a policy-approved transition (never by editing state)",
]


def extract_traits(name: str, public: dict[str, Any], probe: dict[str, Any]) -> list[dict[str, Any]]:
    """Rule-based failure-trait extraction (experimental).

    Two signatures only:

    * ``public_benchmark_overfit`` -- perfect public score, imperfect probe.
      The Goodhart signature; the single most dangerous trait to ever feed
      back into generation.
    * ``fails_public_benchmark`` -- ordinary incapability.
    """

    traits: list[dict[str, Any]] = []
    if perfect(public) and not perfect(probe):
        traits.append(
            {
                "trait": "public_benchmark_overfit",
                "candidate": name,
                "signal": f"public {public['passed']}/{public['total']} vs probe {probe['passed']}/{probe['total']}",
                "hazard": "memorization/Goodhart artifact; must never re-enter generation unreviewed",
            }
        )
    if not perfect(public):
        traits.append(
            {
                "trait": "fails_public_benchmark",
                "candidate": name,
                "signal": f"public {public['passed']}/{public['total']}",
                "hazard": "ordinary incapability",
            }
        )
    return traits


def quarantine_traits(kernel: Kernel, name: str, traits: list[dict[str, Any]]) -> list[str]:
    """Quarantine every extracted trait. Returns quarantine ids."""

    ids = []
    for trait in traits:
        item = quarantine_candidate(
            kernel,
            object_type="trait",
            object_ref=f"{name}:{trait['trait']}",
            reason=f"failure-extracted trait ({trait['hazard']})",
            release_conditions=RELEASE_CONDITIONS,
        )
        ids.append(item.quarantine_id)
    return ids


__all__ = ["extract_traits", "quarantine_traits", "RELEASE_CONDITIONS"]
