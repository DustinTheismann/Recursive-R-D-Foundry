# RESULTS — trait-quarantine registered run (prereg v1.1)

**Status:** REGISTERED RESULT. Produced by a cold run session per
PREREGISTRATION.md §7–8 and RUNBOOK.md, against commit `eb0de6e` on `main`,
after a passing re-audit of the v1.1 amendments. Independently re-verified by
the committing session (see "Independent verification" below) before entering
the public record.

## Verdict (mechanical, `stats.decide()`, §6 — no analyst judgment)

**Outcome 3: central conjecture NOT supported (H1 failed).**

| Hypothesis | Verdict | Registered criterion |
|---|---|---|
| H1 (efficiency) | **FAIL** | median(M1_GATED)=37.0 vs median(M1_DISCARD)=14.0; paired Wilcoxon n=30, z=4.7754, p≈0.999999 — GATED significantly *slower*, opposite direction |
| H2 (safety) | **HOLD** | mean(M2_GATED)=0.000 ≤ mean(M2_DISCARD)=0.0289 + ε(0.05) |
| H3 (gating necessity) | **FAIL** | requires NAIVE strictly less safe than GATED beyond ε and ≥ as fast; not met (mean M2_NAIVE=0.0083, within ε of GATED) |

Recombination from confirmation-gated failure traits did **not** speed
budget-to-first-honest-improvement under the registered conditions. With the
confirmation machinery priced into its own budget (amendment A1), the GATED arm
was ~2.6× slower at the median than plain discard. The hypothesis implicit in
this repository's name is refuted, exactly as the pre-registration committed to
reporting.

## Registered observations (within §6 scope)

- GATED recorded **0 false promotions across all 30 seeds** — the only arm at
  zero (DISCARD: 3, NAIVE: 1). H2 holds with margin. The *safety* property
  survives; the *efficiency* claim dies.
- Budget conservation held in code on every cell: `evals_used == 600` for all
  90 (arm, seed) runs.

## Per-arm summary (K=30 seeds 1000–1029, B=600 charged evaluations)

| arm | median(M1) | total promotions | total false promotions |
|---|---|---|---|
| discard | 14.0 | 98 | 3 |
| naive | 15.0 | 87 | 1 |
| gated | 37.0 | 86 | 0 |

Raw per-seed metrics: `raw_results.json` (`prereg_version: "1.1"`).

## Verbatim machine verdict (`stats.decide(raw_results.json)`)

```json
{
  "prereg_version": "1.1",
  "budget_conserved_all_arms": true,
  "median_m1": {"discard": 14.0, "gated": 37.0, "naive": 15.0},
  "mean_m2": {"discard": 0.02888888888888889, "gated": 0.0, "naive": 0.008333333333333333},
  "m2_sample_sizes": {"discard": 30, "gated": 30, "naive": 30},
  "wilcoxon_gated_vs_discard": {"n": 30, "w_plus": 465.0, "z": 4.7754, "p": 0.999999},
  "H1": false,
  "H2": true,
  "H3": false,
  "outcome": "3: central conjecture NOT supported (H1 failed)"
}
```

## Deviations from RUNBOOK.md (documented, pre-analysis)

1. **Chunked execution.** The monolithic `--registered` entrypoint exceeds the
   sandbox's per-call wall-clock. The identical code path (`run_arm`, same
   seeds, same budget, same module) was executed via a resumable chunked driver
   writing per-cell rows. Equivalence rests on §5 determinism and was checked
   empirically by the run session (6 cells, all arms, both ends of the seed
   range; PASS) and again by the committing session (see below).
2. No other deviations. No interim §6 statistics were computed before the matrix
   was complete.

## Independent verification (committing session)

Before committing, the registered numbers were re-derived from
`raw_results.json` with the committed `stats.py` — the verdict above is that
recomputation verbatim, not a transcription. A second determinism spot-check
re-ran four cells through the committed `harness.run_arm` at B=600 and matched
the stored rows exactly, including the load-bearing GATED arm:

| cell | m1 | promotions | final_champ_fitness | extra |
|---|---|---|---|---|
| discard/1000 | 18 | 2 | 0.9351 | — |
| naive/1000 | 17 | 3 | 0.9351 | — |
| discard/1029 | 11 | 4 | 0.9135 | — |
| gated/1000 | 63 | 2 | 0.9351 | confirmations=191, released=1 |

Producer ≠ verifier applies to the act of committing a result, not only to
producing it.

## Audit trail

- §7 faithfulness audit v1.0: **HOLD** — two blocking findings (budget leak
  favoring GATED; trait-bandwidth asymmetry). Both fixed pre-data in v1.1
  (amendments A1–A3).
- §7 re-audit v1.1: **PASS** (BudgetMeter coverage, carrier eval eliminated,
  TRAIT_GENES symmetry, in-code budget assertion, `evals_used==600` exact).
- Note for the writeup: the original (pre-A1) apparatus did not charge
  confirmation evaluations; under that accounting GATED's measured efficiency
  would have been subsidized. Whether the leak alone would have flipped H1 is
  **not established here** (no unregistered reanalysis was run) — but the
  direction of the bias matched the direction of the conjecture, which is
  precisely why the audit ruling preceded the data. The §7 audit did not only
  protect this result's validity; it may have determined its sign.

## Exploratory note (NOT a registered result)

The H2 margin (0 false promotions in the only arm with confirmation-gated
release) suggests a successor hypothesis worth its own pre-registration:
quarantine-gating as a *safety* mechanism with an explicit, accepted efficiency
cost — the opposite framing from the one that died. Any such claim requires a
new registration with safety as the primary endpoint; it is **not** supported
by this one, and must not resurrect the dead efficiency conjecture inside it.

## Ceiling

Single strong study at toy scale in one trusted process (CLASS 3). The
refutation generalizes no further than the binpack domain and these conditions
until independent replication (move 4) says otherwise.
