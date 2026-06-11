# Pre-registration — Move 2: Trait-quarantine recombination

**Status:** registered, **amended to v1.1 pre-data** (see `## Amendments`; both
amendments respond to the §7 faithfulness audit, which returned HOLD and blocked
the registered run). This document is fixed *before* any result run. Its git
commit is the registration timestamp; results produced before this commit exist
do not count. Edits after registration are amendments and must be marked as such
in the `## Amendments` section, never silent.

## Amendments

### v1.1 (pre-data; no result run has occurred)

Triggered by the independent §7 faithfulness audit (cold session), which found
two violations of §3's "arms differ ONLY in trait flow" invariant. Both are
fixed in apparatus and design *before* any registered data exist.

- **A1 — budget accounting ruling (audit Finding 1, blocking).** The gated
  arm's release pass performed evaluations that did not count against B (two
  confirmation evals per release plus one carrier eval), giving GATED free
  compute proportional to its refutation count. Ruling, made now: **every
  evaluation on the search or confirmation distributions is charged against
  B**, enforced *in code* by a budget meter whose conservation is asserted (not
  left to review). The carrier evaluation is eliminated outright: the
  confirmation evaluation's own result registers the trait. Excluded from B,
  identically across arms: (a) the seed champion's initial evaluations (a
  shared constant) and (b) held-out re-evaluations of governed promotions
  (M1/M2 *measurement*, triggered by the same condition in every arm). M1's
  "evaluation index" henceforth means *charged budget consumed* at the moment
  the candidate was evaluated — which correctly prices GATED's release overhead
  into its own efficiency metric. This ruling is conservative: it biases
  against H1.
- **A2 — trait-bandwidth symmetrization (audit Finding 2, blocking).** NAIVE
  harvested three gene channels (`w_residual`, `new_bin_bias`, `w_remaining`)
  from every candidate, while GATED's refuted-trait channel was hardcoded to
  `w_residual` only — the arms differed in what counts as a trait, not just how
  traits flow. Fixed: GATED now harvests the **same three channels** from
  refuted candidates; each (gene, value) pair is confirmed and released
  independently. A code-level symmetry constant ties both paths to one list.
- **A3 — terminology correction (audit non-blocking note).** The release pen is
  serviced with dwell ≈ 1: operationally this is a **confirmation-gated
  release**, not a long-dwell quarantine in which traits accumulate evidence.
  Prose here and in `experiments/README.md` must not imply otherwise.

Amendment-before-data is normal science; amendment-after-data is laundering.
There are no data.

## 0. One-line claim (the thing in the repo's name)

> Recombining traits harvested from **quarantined failed candidates** reaches an
> honest, gate-promoted improvement **faster** than discard-and-regenerate,
> **without raising the false-promotion rate**.

This is falsifiable. If it is false, this document's decision rule (§6) declares
it false in public.

## 1. Background and why the arms are these arms

In the current orchestrator, `BestAttributeRegistry.observe(cand, res)` is
called on **every** evaluated candidate — including ones the evidence gate later
refutes — and `graft()` injects those genes back into proposals **ungated**. So
the repository as shipped already implements the *naive reuse* arm. The
quarantine machinery exists (FEK `quarantine_candidate` / policy-approved
release) but is **not** on the grafting path. This experiment asks whether
putting it there earns its keep.

## 2. Hypotheses (locked)

- **H1 (efficiency):** median budget-to-first-honest-improvement is lower for
  GATED than for DISCARD.
- **H2 (safety):** mean false-promotion rate for GATED is not greater than for
  DISCARD by more than the tolerance in §6.
- **H3 (the mechanism's reason to exist):** NAIVE reuse achieves efficiency
  comparable to or better than GATED **but at a strictly higher false-promotion
  rate** — i.e., the quarantine gate is what buys NAIVE's speed without NAIVE's
  contamination. (If H3 fails because NAIVE is *not* less safe, the quarantine
  step is decoration and we say so.)

The novel-mechanism result requires **H1 ∧ H2 ∧ H3**. Any other combination is a
null or a refutation, interpreted per §6 — and reported either way.

## 3. Arms (exact apparatus configuration)

All three arms are the **same** evolutionary loop (`harness.py`) over the same
binpack domain, same proposer (`MutationProposer`), same evidence gate
(`rsi_foundry.governance.evidence_gate.EvidenceGate`), differing **only** in
trait flow:

- **DISCARD** (`trait_policy="discard"`): parents = current champion only; no
  `BestAttributeRegistry`; a refuted/failed candidate contributes nothing to
  future proposals.
- **NAIVE** (`trait_policy="naive"`): `BestAttributeRegistry.observe` on every
  evaluated candidate; `graft` ungated. (= current shipped behavior.)
- **GATED** (`trait_policy="gated"`): traits extracted from a candidate that the
  evidence gate **refuted** — the same three gene channels NAIVE harvests
  (amended v1.1, A2) — enter a confirmation pen; each (gene, value) pair is
  released to the graftable registry **only** after a fresh-seed re-evaluation
  confirms it still improves fitness over the champion baseline. Confirmation
  evaluations are charged against B (amended v1.1, A1). Traits from
  gate-*accepted* candidates register directly (they are not failures). Only
  confirmed traits are graftable. Dwell ≈ 1: this is confirmation-gated
  release, not long-dwell quarantine (A3).

The only code difference between arms is the trait-flow switch. Everything else
— RNG streams, evaluation, gate, budget — is byte-identical given a seed.

## 4. Fixed design

- **Domain:** `rsi_foundry.domain.binpack` starter envs; `LocalBinPackBenchmark`,
  `in_process` sandbox (deterministic; no subprocess nondeterminism).
- **Seeds:** K = 30 seeds, the integers `1000..1029` inclusive. Locked.
- **Budget:** each arm gets an identical budget of **B = 600 charged
  evaluations** per seed (not cycles — evaluations, so proposer batch size does
  not confound). *Charged* = every evaluation on the search or confirmation
  distributions, including GATED's release confirmations (amended v1.1, A1);
  conservation is enforced in code by a budget meter and the per-arm consumed
  total is recorded and must equal B. Seed-champion and held-out measurement
  evaluations are excluded identically across arms. A run ends exactly when the
  meter reaches B.
- **Proposer batch / parents pool size:** fixed across arms (n_offspring = 8,
  parents pool ≤ 6), set in `harness.py` and not tuned per arm.
- **Champion init:** `heuristics.seed_genome()` (the deliberately weak baseline).

## 5. Metrics (exact definitions)

- **M1 — budget-to-first-honest-improvement.** The *charged-budget* index
  (1..B; amended v1.1, A1) at which the *first* candidate is BOTH (a)
  governed-promoted by the evidence gate
  (FEK `accepted`, honored `E4_REPRODUCED`, independent verifier) AND (b)
  survives a **held-out re-evaluation** on a benchmark built from a seed never
  used during search (`held_out_seed = 999_983`, locked). If no such candidate
  appears within B, M1 = B (right-censored) and the run is a "no-honest-improve"
  for that seed.
- **M2 — false-promotion rate.** Over all governed-promotions in a run,
  the fraction whose held-out re-evaluation fitness is **below** the champion's
  held-out fitness at promotion time (i.e., the promotion did not generalize).
  M2 ∈ [0, 1]; if a run has zero governed-promotions, it contributes no M2 sample
  (recorded separately as `promotions=0`).

## 6. Decision rule (pre-committed; all outcomes)

Aggregating across the 30 seeds:

- **H1 verdict:** GATED wins on efficiency iff
  `median(M1_GATED) < median(M1_DISCARD)` AND a paired Wilcoxon signed-rank test
  on per-seed M1 gives p < 0.05. Otherwise H1 is not supported.
- **H2 verdict:** GATED is safety-non-inferior iff
  `mean(M2_GATED) <= mean(M2_DISCARD) + 0.05` (tolerance ε = 0.05 absolute).
- **H3 verdict:** quarantine earns its keep iff
  `mean(M2_NAIVE) > mean(M2_GATED) + 0.05` AND
  `median(M1_NAIVE) <= median(M1_GATED)` (NAIVE at least as fast but strictly
  less safe).

Outcomes, each reported publicly:

1. **H1 ∧ H2 ∧ H3 hold →** novel-mechanism result. Quarantine-gated
   recombination is faster than discard and safer than naive reuse.
2. **H1 ∧ H2 hold, H3 fails →** quarantine is safe and recombination helps, but
   we cannot show the gate is *why* — weaker, still reported.
3. **H1 fails →** recombination from failure traits does **not** speed honest
   improvement at this scale. The central conjecture is **not supported**;
   we say so in the README and CHANGELOG.
4. **H2 fails →** gated recombination raises false promotions — an active
   argument *against* the mechanism. Reported as a refutation of our own design.

There is no outcome under which we quietly stop. The conjecture-killed branches
(3, 4) are pre-committed deliverables.

## 7. Threats to validity (acknowledged before the run)

- **Toy domain / single process →** CLASS 3 ceiling; not generalizable without
  move 3 (real domains) and move 4 (independent replication).
- **Apparatus faithfulness.** The GATED arm's confirmation-release logic is the
  scientifically load-bearing code. Before the result run counts, an independent
  cold session must **audit** `harness.py`'s arm semantics against this spec
  (esp. that no trait from a refuted candidate reaches `graft` without a recorded
  confirmation, and that budget conservation holds). The smoke test only proves
  the apparatus runs, not that the arm semantics are correct. *History:* the
  first such audit (pre-data) returned HOLD with two blocking findings — a
  budget leak favoring GATED and a trait-bandwidth asymmetry — fixed in v1.1.
  The registered run requires a **re-audit pass** on the amended apparatus.
- **Multiple comparisons.** Three hypotheses; α not corrected because each maps
  to a distinct pre-committed decision, not a fishing expedition. Stated so a
  reader can apply their own correction.
- **Held-out leakage.** `held_out_seed` and `999_983` must never enter any search
  RNG stream; the harness asserts this at startup.

## 8. What "run pending cold session" means

`harness.py` is built and passes a structural smoke (`--smoke`: all three arms
execute on a tiny budget and emit the metric schema). The **registered run** (K=30,
B=600, all arms) is executed by a separate cold session, which (a) audits §7's
faithfulness item, (b) runs, (c) commits raw per-seed metrics + the §6 verdict as
`RESULTS.md` next to this file. This author does not report M1/M2 here.
