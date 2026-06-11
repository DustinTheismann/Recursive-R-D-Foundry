# Experiments

This directory holds **pre-registered** experiments. The discipline is the same
one the rest of the repo enforces on code, applied to claims:

1. **Register before running.** Each experiment ships a `PREREGISTRATION.md`
   with a locked hypothesis, fixed design (seeds, budget, arms), the exact
   metrics, and a decision rule that pre-commits the interpretation of *every*
   outcome — including the one where our own conjecture dies. The registration
   is committed *before* the run; its commit SHA is the registration timestamp.

2. **The experimenter is not the verifier.** Building and registering an
   experiment, and *running it for record*, are different roles (the producer ≠
   verifier rule, applied to ourselves). The apparatus here is built and
   smoke-tested for *mechanism* — that it executes and emits the metric schema —
   but the registered result runs are produced by an independent cold session
   and recorded as their own artifact. A harness author reporting their own
   headline numbers is exactly the self-attestation this project refuses.

3. **Honest ceiling.** At toy scale in one trusted process, even a clean result
   is a single strong study (CLASS 3). "Groundbreaking" is conferred by
   independent replication, never self-declared. That is why the benchmark
   (move 4) — packaging these as something others can plug their own mechanism
   into — is the load-bearing move, not optional polish.

## Index

| dir | move | claim | status |
|-----|------|-------|--------|
| `trait_quarantine/` | 2 | quarantined-trait recombination reaches honest improvement faster than discard, without raising false-promotion rate | **prereg v1.1** (amended pre-data after the §7 audit returned HOLD); apparatus fixed + smoke-validated; **re-audit + registered run pending cold session** (RUNBOOK.md) |
| `adaptive_adversary/` | 1 | the evidence gate holds against candidates that optimize against the gate itself (gate-aware attack) | registered; deterministic battery runnable; LLM arm is a seam, **run pending cold session** (RUNBOOK.md) |

## Apparatus runs ≠ apparatus measures (a finding in its own right)

This experiment has been saved twice, both times by checks `make verify` cannot
perform — green CI, broken inference:

1. **The liveness check** caught a rig that *couldn't promote*: the champion was
   frozen at the seed, every capability drift overwhelmed the HALF-LIFE budget,
   and all three arms would have "measured" a tie that was a deadlocked rig.
2. **The §7 faithfulness audit** (independent, cold) caught a rig that *would
   have promoted the wrong conclusion*: a budget leak granting GATED free compute
   proportional to its refutation count — indistinguishable, in a favorable
   result, from the hypothesis being true — plus a trait-bandwidth asymmetry
   confounding policy with bandwidth. Both fixed pre-data in v1.1; budget
   conservation is now enforced in code, not by review.

The lesson, twice demonstrated in one experiment: a test suite proves the
apparatus *executes*; only liveness checks and adversarial faithfulness audits
prove it *measures*. This paragraph belongs in any eventual writeup.

Moves 3 (real in-the-wild reward hacks) and 4 (the benchmark/leaderboard) grow
from whichever of 1–2 survives its cold run.

## Why these were registered now

The trait-quarantine claim (move 2) is *implicit in the repository's name and
description*. An unregistered central claim is a slow-motion caveat-laundering
risk: it accrues credibility from the framing while never exposing itself to
refutation. Registering it — including the decision rule under which we declare
it **false** — converts it from marketing into science.
