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
| `trait_quarantine/` | 2 | quarantined-trait recombination reaches honest improvement faster than discard, without raising false-promotion rate | registered; apparatus built, smoke-validated; **run pending cold session** |
| `adaptive_adversary/` | 1 | the evidence gate holds against candidates that optimize against the gate itself (gate-aware attack) | registered; deterministic attack battery built + runnable; LLM arm is a seam, **run pending cold session** |

Moves 3 (real in-the-wild reward hacks) and 4 (the benchmark/leaderboard) grow
from whichever of 1–2 survives its cold run.

## Why these were registered now

The trait-quarantine claim (move 2) is *implicit in the repository's name and
description*. An unregistered central claim is a slow-motion caveat-laundering
risk: it accrues credibility from the framing while never exposing itself to
refutation. Registering it — including the decision rule under which we declare
it **false** — converts it from marketing into science.
