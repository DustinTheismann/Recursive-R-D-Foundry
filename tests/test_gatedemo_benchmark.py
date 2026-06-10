"""The benchmark must be genuinely hackable, and the probe must genuinely catch it.

If either half fails, the demo proves nothing: a Goodhart-proof public
benchmark makes the rejection trivial, and a leaky probe makes it false.
"""

from __future__ import annotations

from gate_demo.agents import broken, goodhart, honest
from gate_demo.benchmark import PROBE_SEED, perfect, probe_cases, run_probe, run_public


def test_public_surface_is_hackable():
    # The Goodhart agent does not sort, yet aces the public benchmark.
    assert perfect(run_public(goodhart))
    assert goodhart([9, 7, 8]) == [9, 7, 8]  # proof it does not sort


def test_probe_catches_the_hack():
    result = run_probe(goodhart)
    assert not perfect(result)
    assert result["failures"], "probe must produce concrete counterexamples"


def test_honest_passes_both_surfaces():
    assert perfect(run_public(honest))
    assert perfect(run_probe(honest))


def test_broken_fails_probe():
    assert not perfect(run_probe(broken))


def test_probe_is_deterministic_per_seed():
    assert probe_cases(PROBE_SEED) == probe_cases(PROBE_SEED)
    assert probe_cases(PROBE_SEED) != probe_cases(PROBE_SEED + 1)


def test_fresh_seed_still_catches_memorization():
    # Release conditions for quarantined traits demand fresh seeds; a fresh
    # seed must still catch the memorizer.
    assert not perfect(run_probe(goodhart, seed=PROBE_SEED + 1))
