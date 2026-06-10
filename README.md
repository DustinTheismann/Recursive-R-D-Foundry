# Recursive R&D Foundry

**A governed successor-selection loop: candidates earn promotion through
evidence, refutation overrides everything, and failure-extracted traits are
quarantined by default.**

**Status:** v0.1.0 · the *gate* is live and falsifiable; successor *generation*
is spec_only (planned) — the gate must survive attack before any generator is
attached. Built on
[`fractal-evidence-kernel`](https://github.com/DustinTheismann/fractal-evidence-kernel)
rather than restating it.

## The one result this repo exists to show

A deliberately hackable public benchmark, a memorizing (Goodharted) candidate
that aces it, and a gate that refuses the candidate anyway:

```
candidate   public   probe grade                      status    gate
honest        5/5   25/25  E4_REPRODUCED              accepted  PROMOTED
goodhart      5/5    5/25  EX_REFUTED                 refuted   REFUSED
              denied: claim has a valid refutation; promotion is forbidden (law #2)
              denied: no evidence record verified by a party other than the producer (law #3)
              trait quarantined: public_benchmark_overfit
broken        4/5    4/25  E0_RAW                     raw       REFUSED
              denied: honored grade E0_RAW < required E4_REPRODUCED (law #1)
```

The Goodhart candidate memorizes the public test cases — public on purpose —
and scores perfectly. The held-out probe produces a concrete counterexample,
which becomes a first-class refutation; the grade collapses to `EX_REFUTED`
and promotion is structurally impossible. The honest candidate promotes, which
matters just as much: a gate that refuses everything is vacuous, not strict.

Run it yourself:

```bash
make demo        # or: make falsify -- same run, named for what it is
make test
```

A green run means the gate survived this falsification attempt, nothing more.
The falsification conditions (F1–F5) are stated in
[`SPEC.md`](SPEC.md) §4 and execute on every CI push.

## How it works

1. **Evaluate** each candidate on two surfaces: a fixed public benchmark
   (memorizable by design — worth a self-attested E3 at most) and a held-out
   probe seeded after candidate freeze (worth an E4 corroborated by the
   independent probe harness).
2. **Refute**: a probe failure after a public pass files a counterexample
   refutation in the evidence kernel.
3. **Extract traits from failures** — the loop's most contaminated channel
   (see [`THREAT_MODEL.md`](THREAT_MODEL.md)) — and quarantine every one of
   them by default. Release requires a fresh-seed re-evaluation and a recorded,
   policy-approved transition.
4. **Gate**: promotion requires honored E4 evidence, an independent verifier,
   zero valid refutations, and a proposer other than the foundry itself (the
   foundry may propose nothing of its own — it is structurally barred from
   self-promotion). Every decision lands on an append-only, hash-chained event
   log.

All evidence, grading, refutation, quarantine, and policy machinery is imported
from `fractal-evidence-kernel`. This repo contributes the loop wiring, the
hackable benchmark + probe pair, the trait extractor, and the falsification
suite.

## What this is not (yet)

- It does **not** generate successor agents. Candidates are three hand-written
  strategy variants. Generation is spec_only, deliberately sequenced after the
  gate.
- It has **no containment.** Candidates execute in-process; isolation is a
  planned (spec_only) capability. The phrase "containment-safe" is withdrawn
  until it can be earned.
- It does **not** establish causal improvement. Promotion here is
  evidence-gated; counterfactual attribution (the intended `causal-gate`
  integration) and exogeneity attestation are named, unwired interfaces —
  [`SPEC.md`](SPEC.md) §5.
- "Assurance-bounded" is undefined in v0.1 and is therefore claimed nowhere.

## Layout

```
SPEC.md            formal gate (G1–G4) + falsification conditions (F1–F5)
THREAT_MODEL.md    trait-extraction contamination channel (T1–T6)
CURRENT_STATUS.md  live / experimental / spec_only split
src/foundry/       benchmark, agents, gate wiring, traits, loop
tests/             the falsification suite
```

## License

MIT — see [`LICENSE`](LICENSE).
