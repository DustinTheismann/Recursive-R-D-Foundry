"""Successor candidates for the demo loop.

HONESTY NOTE (read this before believing anything): these are hand-written
strategy variants, not generated agents. The *generative* component of the
foundry ("generate successor agents") is spec_only in v0.1 -- see SPEC.md. What
is live is the part that matters first: the selection gate that decides which
candidates survive. You cannot trust a generator before you can trust the gate
that judges its output.

The three candidates span the threat model:

* ``honest``   -- actually sorts. Should pass public + probe and promote.
* ``goodhart`` -- memorizes the public benchmark's input/output pairs and
  returns its input otherwise. Aces the public surface, fails the probe. The
  gate MUST refuse it; that refusal is the repo's core demonstration.
* ``broken``   -- reverses the list. Fails everything; exists so failure-trait
  extraction has an ordinary (non-adversarial) failure to chew on.
"""

from __future__ import annotations

from foundry.benchmark import PUBLIC_CASES, Agent


def honest(xs: list[int]) -> list[int]:
    return sorted(xs)


# The memorization table is built from PUBLIC_CASES *by construction* -- this
# candidate is the embodiment of benchmark leakage (threat T3 in THREAT_MODEL.md).
_MEMORIZED: dict[tuple[int, ...], list[int]] = {tuple(inp): out for inp, out in PUBLIC_CASES}


def goodhart(xs: list[int]) -> list[int]:
    hit = _MEMORIZED.get(tuple(xs))
    if hit is not None:
        return list(hit)
    return list(xs)  # anything unseen: do nothing and hope


def broken(xs: list[int]) -> list[int]:
    return list(reversed(xs))


#: The frozen candidate set for the demo generation. Frozen BEFORE the probe
#: seed is applied (ordering convention documented in SPEC.md).
CANDIDATES: dict[str, Agent] = {
    "honest": honest,
    "goodhart": goodhart,
    "broken": broken,
}

__all__ = ["honest", "goodhart", "broken", "CANDIDATES"]
