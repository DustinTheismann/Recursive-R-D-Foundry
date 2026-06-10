# Recursive R&D Foundry

**A governed successor-evolution lab.** The foundry generates successor
*programs*, sandboxes them, benchmarks them, checks contracts, gathers causal
evidence, mines failures into training signal, archives diversity, and promotes
only candidates that clear its internal gates **and** an external evidence gate
(the fractal-evidence-kernel) enforcing producer≠verifier, refutation supremacy,
and no self-promotion on an append-only log.

> **Status / honesty note.** "Recursive self-improvement", an "assurance bound",
> and "proof" are **not** claimed as achieved. The internal HALF-LIFE controller
> is a heuristic throttle, not a guaranteed bound; "causal" here means
> interventional ablation evidence, not a formal causal proof. What is live and externally
> checkable is the *governance* — see **Governance (evidence-gated)** below, and
> reproduce it cold yourself.

The viable path to recursive self-improvement is not *“one AI mutates itself
freely.”* It is a **recursive AI R&D factory**:

```
generate successors → sandbox → benchmark → prove / ablate → extract traits
→ train future proposers on failures → promote only governed improvements → repeat
```

This is **v0.2: a working recursive agent lab** — not a scaffold of stubs. It
runs fully offline and deterministically, evolving real, sandbox-executed
programs, with real LLM and Docker backends as pluggable seams that activate
when present.

---

## What it actually does

It evolves **online bin-packing heuristics** — a real, well-studied optimization
problem where heuristic quality genuinely matters. A genome of feature weights
**compiles to real Python source** that is executed under containment; fitness,
contracts, behavior descriptors, and gene-level ablations are all measured on
actual program behavior.

A typical 8-cycle run (`examples/run_minimal_cycle.py`):

```
seed capability     : 0.798        # deliberately weak baseline (eager-open)
champion fitness    : 0.926        # loop discovers best-fit-like packing
governed promotions : 3            # only gate-passing improvements
HALF-LIFE final     : GREEN        # capability stayed within assurance budget
assurance / debt    : 0.50 / 0.0
QD coverage / score : 0.19 / 8.81  # diverse elites, not a single winner
SEAL examples mined : 108          # failures turned into training signal
reproducible replay : True         # same lineage Merkle root on re-run
```

## Quickstart

```bash
pip install pyyaml            # only hard dependency (pytest for tests)

# run a governed recursive session + write a RunPack and an HTML dashboard
python -m rsi_foundry.cli run --config configs/policy.yaml \
    --out runpacks/session.runpack.yaml --dashboard dashboard.html

# verify a RunPack replays bit-for-bit (reproducibility is an assurance property)
python -m rsi_foundry.cli replay runpacks/session.runpack.yaml

# text summary / re-render dashboard
python -m rsi_foundry.cli report    runpacks/session.runpack.yaml
python -m rsi_foundry.cli dashboard runpacks/session.runpack.yaml -o dashboard.html

# smallest complete demonstration
python examples/run_minimal_cycle.py

# tests
pytest -q                    # 30 passing
```

## The loop, mapped to the research

| Layer | Research basis | Role |
|---|---|---|
| **DGM loop** | Darwin Gödel / self-improving coding agents | champion proposes *edits to itself* as patches, not live mutation |
| **AlphaEvolve loop** | evolutionary coding agent + evaluators | many offspring from the QD parent pool, selected by fitness |
| **ADAS loop** | Automated Design of Agentic Systems | UCB bandit over *search designs* (the agent that designs agents) |
| **SEAL loop** | Self-Adapting LMs | rejected candidates become training data + reshape proposer priors |
| **AI-Scientist loop** | automated scientific workflow | hypothesis → ablation → review artifact → experiment-driven proposal |
| **Benchmark layer** | MLE/RE/SWE-style tasks | real fitness on executed code (local; SWE/MLE adapters stubbed) |
| **Contract layer** | proof-carrying gates | capacity invariant + completeness (Lean/typed seam) |
| **HALF-LIFE control plane** | assurance framework | blocks capability expanding faster than assurance can absorb it |

## The novel synthesis

Most systems select the single best candidate. This one does more — it improves
the **generator, the agent design, the training data, the evaluation ecology,
the verification layer, and the governance layer at the same time**:

- **Quality-Diversity (MAP-Elites)** archive — keep the best *different*
  candidates per behavior niche, not one winner. Anti-fixation.
- **Anti-collapse novelty pressure** — occupancy-entropy of the behavior grid is
  watched; if diversity falls, the novelty threshold rises automatically.
- **POET environment coevolution** — the benchmark gets harder as successors
  improve; new environments are admitted only under a minimal-criterion band.
- **Failure-mined self-training (SEAL)** — governance becomes a *training
  signal*, not just a blocker.
- **Best Attribute Registry** — harvest high-performing genes from *losing*
  candidates and graft them across lineages (recursive capability fusion).
- **Causal gate** — promotion requires interventional ablation evidence that the
  gain is mechanistically real, plus per-task consistency vs. the parent.
- **Proof-carrying contracts** — candidates must satisfy machine-checkable
  invariants before they can be considered correct.
- **HALF-LIFE assurance-debt ledger** — capability may only expand as fast as
  assurance is minted; states **GREEN → AMBER → RED → BLACK** throttle or halt.
- **Meta-gate (recursive governance)** — the gates themselves are improvable, but
  *monotone by construction*: tighten freely; loosen only when assurance has been
  earned.

## Promotion rule

A successor advances only when **all** hold:

```
contracts_pass · contained · benchmark_pass
fitness_delta > threshold
novelty_score >= threshold            (raised under anti-collapse pressure)
causal evidence exists                (ablation + per-task consistency)
regression_failures == 0
capability_drift  <=  assurance_renewal × safety_factor      (HALF-LIFE)
lineage_hash recorded                 (content-addressed Merkle DAG)
```

...**and then it must clear the external evidence gate below.** The rule above
is the foundry judging itself. The next section is the part that does not take
the foundry's word for it.

## Governance (evidence-gated)

Every internal decision above is *self-attested*: the foundry computes its own
`promoted` flag. That is exactly the failure mode the
[`fractal-evidence-kernel`](https://github.com/DustinTheismann/fractal-evidence-kernel)
(FEK) refuses. v0.2 now routes every promotion through FEK as a **supervening
veto** (`rsi_foundry/governance/evidence_gate.py`):

```
governed_promoted = internal_gates_pass  AND  fek_gate_pass
```

FEK can never promote what the internal gates rejected; it can refuse what they
accepted. What it adds, that the internal gate had no notion of:

- **Producer ≠ verifier.** A self-run benchmark is at most a self-attested
  `E3_EXECUTABLE` record and can never satisfy promotion alone. Only the
  ablation study, run by a separate harness identity, yields an independently
  corroborated `E4_REPRODUCED` record.
- **Refutation supremacy.** A per-task regression, a containment breach, or an
  ablation showing no real effect becomes a first-class refutation that
  collapses the claim to `EX_REFUTED` — promotion forbidden regardless of every
  other gate.
- **No self-promotion.** The claim is tagged `producer_role: foundry`; the
  promotion transition must be proposed by an independent review identity.
- **Append-only, hash-chained evidence.** Every decision is replayable from the
  kernel's event logs, not asserted in prose.

Honest limit: producer and verifier are honest *labels* within one trusted
process; cryptographic identity for evidence records is a spec_only interface,
not a claim made here.

## Reproduce cold

The evidence kernel is **vendored** under [`vendor/fek`](vendor/README.md) at a
pinned commit, so governance runs with no external clone, no token, and no
network:

```bash
pip install pytest          # the only thing not vendored
make verify                 # internal tests + ported falsification suite + overclaim scan
```

The ported falsification suite (`tests/test_evidence_gate.py`, PF1–PF5) proves
the veto's added value: a self-attested-only successor is **not** promoted; a
regression or breach **refutes**; the foundry **cannot** self-promote; and FEK
**never** promotes what the internal gate rejected.

## Layout

```
rsi_foundry/
├── core/          orchestrator, types, RNG hub, lineage DAG, registry, RunPack
├── domain/        bin-packing problem + genome⇄source compiler (real code-gen)
├── proposers/     mutation engine (always on) + Claude proposer (pluggable)
├── loops/         alphaevolve · dgm · adas · scientist · novelty · qd · poet · best-attr
├── training/      seal (failure-mined self-training)
├── governance/    half_life · causal_gate · promotion · meta_gate
├── verification/  static analyzer · proof-carrying contracts
├── sandbox/       trusted simulator + subprocess/in-process/docker containment
├── evals/         evaluator quorum
├── connectors/    benchmark adapters (local + SWE/MLE stubs)
└── dashboard/     dependency-free HTML+SVG report
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

## Pluggable seams (path to bigger capability)

- **LLM proposer** — set `use_llm: true`; activates with `anthropic` +
  `ANTHROPIC_API_KEY`, otherwise falls back to the mutation engine.
- **Docker containment** — kernel-level isolation when a daemon is reachable.
- **SWE-bench / MLE-Bench adapters** — same `BenchmarkAdapter` protocol as the
  local benchmark.
- **Lean / typed contracts** — drop in behind `verification/contracts.py`.

## Built the way it works

The artifact was built the way it operates: each capability was proposed,
executed, and gated; two defects were caught and treated exactly as the foundry
treats them before anything was “promoted” — a runaway meta-gate (a governance
misfire, corrected to fire only on real containment breaches) and a wall-clock
dependency that broke reproducible replay (an assurance violation, removed).
