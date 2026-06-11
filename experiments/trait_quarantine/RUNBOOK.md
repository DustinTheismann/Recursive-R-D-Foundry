# Run-book — trait-quarantine registered run (prereg v1.1)

For the **cold session** that produces the registered result. The apparatus
author does not run this. Work top to bottom; if any gate fails, STOP and file
findings instead of running.

## 0. Preconditions

```bash
git clone <repo> && cd Recursive-R-D-Foundry
pip install pytest
make verify              # must be green before anything else
make experiments-smoke   # apparatus executes + schema + budget equality
```

## 1. Re-audit checklist (v1.1; the first audit's findings, now code-checked)

Each item must PASS before the run counts. Record pass/fail per item in
RESULTS.md.

1. **Gate identity.** All three arms call the production path
   `causal_gate.evaluate_causal → promotion.evaluate → EvidenceGate.govern`
   unconditionally — no arm-conditional gate logic anywhere in `run_arm`.
2. **Budget conservation (audit Finding 1).** `_eval_charged` is the ONLY call
   site that evaluates the search/confirmation distributions:
   `grep -n "harness.evaluate\|fresh\b.*evaluate\|\.evaluate(" experiments/trait_quarantine/harness.py`
   — every hit must be inside `_eval_charged`, `_eval_measurement` (held-out
   only), or the seed-champion block. Then confirm `evals_used == B` for every
   (arm, seed) row in the raw output.
3. **Trait-bandwidth symmetry (audit Finding 2).** `TRAIT_GENES` is the single
   constant feeding GATED's refuted-trait harvest, and it equals the three
   channels `BestAttributeRegistry.observe` tracks (`w_residual`,
   `new_bin_bias`, `w_remaining`).
4. **Seed isolation.** `SEARCH_SEEDS` ∩ {`HELD_OUT_SEED`} = ∅ and all search
   seeds < `RELEASE_SEED_BASE`; no other RNG consumes the held-out seed.
5. **M1 definition.** Code records M1 at the charged-budget index of the first
   governed promotion that survives the held-out re-eval — matches prereg §5
   as amended (A1).
6. **No data contamination.** `experiments/trait_quarantine/raw_results.json`
   and `RESULTS.md` do not already exist in the tree.

## 2. The registered run

```bash
PYTHONPATH=.:vendor python3 experiments/trait_quarantine/harness.py --registered
# K=30 seeds x 3 arms x B=600 charged evals; writes raw_results.json
```

Estimated wall time: minutes-to-tens-of-minutes scale (in-process sandbox).
Do not tune, re-seed, or re-run on dislike of the numbers: one run, as
registered. A crash is a finding, not a do-over.

## 3. Apply the §6 decision rule (mechanical)

```bash
PYTHONPATH=.:vendor python3 experiments/trait_quarantine/stats.py
```

`stats.py` IS §6: medians, paired one-sided Wilcoxon (normal approximation),
the ε = 0.05 safety tolerance, and the four pre-committed outcomes. No analyst
judgment enters.

## 4. Record

Commit, in one commit: `raw_results.json` + `RESULTS.md` containing:

- re-audit checklist outcomes (item-by-item),
- the `stats.py` JSON verdict verbatim,
- the pre-committed §6 outcome sentence (1/2/3/4) stated plainly — including
  outcomes 3/4 ("conjecture not supported" / "design refuted") with the same
  prominence a positive result would get,
- environment: Python version, OS, repo commit SHA,
- the CLASS-3 ceiling note: single strong study; replication is move 4.

Do not edit PREREGISTRATION.md in the same commit as results.
