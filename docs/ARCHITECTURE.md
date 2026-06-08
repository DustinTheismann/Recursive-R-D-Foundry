# Architecture — Recursive R&D Foundry v0.2

The foundry is a **governed recursive self-improvement factory**. It does not let
one model mutate itself freely. Instead it runs a disciplined loop that generates
successor *programs*, executes them under containment, proves contracts, gathers
causal evidence, mines failures into training signal, preserves diversity, and
promotes only improvements that assurance can absorb.

```
                              ┌─────────────────────────────────────────┐
                              │              ORCHESTRATOR                 │
                              │  (rsi_foundry/core/orchestrator.py)       │
                              └─────────────────────────────────────────┘
   generate            evaluate            gate                 learn / coevolve
 ┌──────────┐     ┌───────────────┐   ┌────────────────┐    ┌────────────────────┐
 │AlphaEvolve│──▶ │ containment   │──▶│ novelty ledger │──▶ │ SEAL self-training │
 │DGM (self- │    │ (subprocess)  │   │ causal gate    │    │ Best-Attr registry │
 │  editing) │    │ static check  │   │ regression     │    │ ADAS design bandit │
 │ADAS (meta)│    │ contracts     │   │ HALF-LIFE      │    │ POET env coevolve  │
 │Scientist  │    │ benchmark     │   │ meta-gate      │    │ QD archive (elites)│
 └──────────┘     └───────────────┘   └────────────────┘    └────────────────────┘
        ▲                                       │                         │
        └───────────────── parents (QD elites) ─┴── promotions ──────────┘
```

## The domain (so it is *real*, not simulated)

`rsi_foundry/domain` evolves **online bin-packing heuristics**. A genome of
feature weights compiles to genuine Python source for `place(item, bins,
capacity)` (`heuristics.compile_source`). The weight family spans first-fit,
best-fit, worst-fit and every interpolation, so it is richly evolvable,
crossover-able, and — crucially — **ablatable gene by gene** for the causal gate.

Candidate code is *advisory only*: the trusted simulator
(`sandbox/simulate.py`) owns all accounting, so a candidate can never overflow a
bin, lose an item, or fabricate a score — it can only score poorly.

This domain needs no network or GPU and is fully deterministic, which is what
makes reproducible replay an enforceable assurance property.

## Generation loops (`rsi_foundry/loops`)

| Loop          | Research basis                       | Role |
|---------------|--------------------------------------|------|
| AlphaEvolve   | evolutionary coding agent + evaluators | many offspring from the QD parent pool, selected by fitness |
| DGM           | Darwin Gödel / self-editing agents   | the champion proposes *edits to itself* as patches (+ self-fusion) |
| ADAS          | Automated Design of Agentic Systems  | a UCB bandit over *search designs* (how aggressively to mutate) |
| Scientist     | automated scientific workflow        | hypothesis → ablation → review artifact → experiment-driven proposal |

## Evaluation (`rsi_foundry/evals`, `sandbox`, `verification`)

A four-voter **quorum**, no single signal can promote:

1. **static** — AST safety + complexity bound (`verification/static_analyzer.py`)
2. **contained** — ran inside the resource-limited subprocess sandbox without breach
3. **contracts** — capacity invariant + completeness (`verification/contracts.py`)
4. **benchmark** — composite fitness clears a floor

Containment has two backends: a real `SubprocessSandbox` (CPU/memory rlimits,
wall timeout, restricted builtins) used for the quorum, and a fast
`InProcessSandbox` used for the inner ablation sweep on already-validated
candidates. A `DockerSandbox` seam activates if a daemon is reachable.

## Governance (`rsi_foundry/governance`)

**Causal gate.** Promotion requires *interventional* evidence: ablating the
candidate's genes one at a time must show that at least one gene's removal hurts
fitness (the gain is mechanistically grounded), and the candidate must beat its
parent on a *majority of individual tasks* (not just on the average).

**HALF-LIFE control plane.** The core invariant: *capability must not expand
faster than assurance can absorb it.* Modeled as an assurance-credit ledger —
verification work mints credit; promoting a candidate that raises capability by
`drift` spends `drift / safety_factor` credit. States escalate **GREEN → AMBER →
RED → BLACK**; RED freezes promotion, BLACK (containment breach or sustained RED)
halts the loop. Unabsorbed expansion is booked as **assurance debt**.

**Promotion rule** (`governance/promotion.py`) — a successor advances only when:
contracts pass · contained · benchmark pass · `fitness_delta > min` ·
`novelty ≥ min` (dynamic) · causal evidence exists · `regressions == 0` ·
HALF-LIFE allows · lineage hash recorded.

**Meta-gate (recursive governance).** The thresholds are themselves an
improvable lineage — but *monotone-safe*: tightening is always allowed; loosening
is allowed **only** when cumulative assurance has grown by a margin since the last
loosening. The governor may never relax faster than assurance accrues.

## Learning & anti-collapse

* **SEAL** (`training/seal_loop.py`) — every evaluated candidate, *especially
  failures*, becomes a training example and updates per-gene exploration priors,
  so the generator improves recursively. Mined examples export in a shape ready
  for real preference/SFT fine-tuning of an LLM proposer.
* **QD archive / MAP-Elites** — keeps the best candidate per behavior cell, not a
  single winner, giving diverse non-collapsing parents.
* **Novelty ledger** — behavioral novelty + occupancy-entropy anti-collapse: if
  diversity falls, novelty pressure rises.
* **Best Attribute Registry** — harvests proven gene values from losing
  candidates and grafts them across lineages (recursive capability fusion).
* **POET** — coevolves the benchmark: harder environments are admitted only if
  the champion scores inside a minimal-criterion band.

## Reproducibility (`core/rng.py`, `core/lineage.py`, `core/runpack_exporter.py`)

All randomness derives from one root seed via a hierarchical `RNGHub`. Candidate
ids are content-addressed (Merkle DAG). A **RunPack** records config, seed,
lineage DAG + Merkle root, every cycle, all promotions, the SEAL dataset, the QD
archive, and the full HALF-LIFE / meta-gate history. `verify_replay` re-runs from
the seed and confirms the lineage root and champion match — *a RunPack that does
not replay is treated as a governance failure.*

## Acting the way it works

The build itself followed the loop it implements: each capability was proposed,
executed, and gated; two issues were caught and treated as the system would treat
them — a runaway meta-gate (a governance misfire, corrected) and a wall-clock
dependency that broke replay (an assurance violation, removed) — before anything
was "promoted".

## Pluggable seams (the path to bigger capability)

* `proposers/llm_proposer.py` — Claude-backed proposal (activates with API key).
* `connectors/benchmark_adapters.py` — SWE-bench-Lite / MLE-Bench adapters behind
  the same protocol as the local benchmark.
* `sandbox/containment.py` — Docker backend for kernel-level isolation.
* `verification/contracts.py` — drop-in for machine-checked (Lean/typed) proofs.
