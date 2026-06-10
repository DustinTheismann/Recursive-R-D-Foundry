# SPEC — Recursive R&D Foundry v0.1

This document states the promotion gate formally, enumerates the falsification
conditions for the gate itself, and draws the line between what is **live**
(implemented, tested, falsifiable today) and what is **spec_only** (named
interface, not wired — and not claimed).

## 1. The object under governance

A *candidate* is a successor strategy for a task. In v0.1 candidates are
hand-written variants (`src/foundry/agents.py`); **successor generation is
spec_only**. This ordering is deliberate: a generator is only as trustworthy as
the gate that judges its output, so the gate ships first and must survive
falsification before any generator is attached.

## 2. The promotion gate (live, formal statement)

The gate is not implemented here. It is imported from
[`fractal-evidence-kernel`](https://github.com/DustinTheismann/fractal-evidence-kernel)
(FEK) — its claim model, evidence grader, refutation engine, quarantine engine,
and policy engine. The foundry contributes only the wiring (`src/foundry/gate.py`).

A candidate `c` with claim `K(c)` is **promoted** iff all of the following hold
at apply time (re-checked, not cached):

- **G1 (evidence floor).** The *honored* grade of `K(c)` is at least
  `E4_REPRODUCED`. Honored means recomputed by FEK's grader from the attached
  evidence and currently-live wiring — never taken from the producer's
  assertion. In v0.1 the E4 record is earned exclusively by a perfect score on
  the held-out probe.
- **G2 (independent verification).** At least one honored evidence record names
  a verifier distinct from the producer. The public benchmark is self-verified
  by the foundry (E3 at best) and can never satisfy G2; only the probe harness
  can.
- **G3 (refutation supremacy).** Zero valid refutations exist against `K(c)`.
  A single probe counterexample collapses the grade to `EX_REFUTED` and G3
  fails *regardless of G1/G2*. Refutation overrides promotion.
- **G4 (no self-promotion).** `K(c)` carries `producer_role: foundry`; FEK's
  policy denies any promotion proposed by the producer itself. Promotion must
  be proposed by an independent identity (the review harness).

Every gate decision — allow or deny, with per-policy reasons — is appended to
FEK's event logs and is replayable.

### What the gate does *not* claim

The v0.1 gate establishes **evidence-gated** promotion, not **causally proven**
improvement. The original one-line README overclaimed this; the claim is
withdrawn until the machinery exists (§5).

## 3. Evaluation surfaces and exogeneity (live, with stated limits)

- **Public benchmark** (`PUBLIC_CASES`): fixed, public, *deliberately
  memorizable*. Worth at most a self-verified E3.
- **Held-out probe** (`run_probe`): cases generated from `PROBE_SEED`, with the
  convention that the candidate set is frozen **before** the seed applies.

Exogeneity status, honestly: in v0.1 this ordering is a **convention enforced
by repo structure** (candidates are committed source; the seed is a constant),
not a cryptographically attested protocol. Attested seed-after-freeze records
are a spec_only integration point (§5). The fresh-seed test
(`test_fresh_seed_still_catches_memorization`) demonstrates the catch is not an
artifact of the particular seed.

## 4. Falsification conditions (live — run `make falsify`)

The gate itself ships with the conditions under which it must be declared
broken. Each is an executable check; CI runs them on every push.

| id | the gate is falsified if... | executable location |
|----|------------------------------|---------------------|
| F1 | a candidate that fails the held-out probe ends `accepted` | `tests/test_gate.py::test_f1_goodharted_successor_is_refused`, `foundry.loop.main` |
| F2 | the honest candidate is not promoted (a gate that refuses everything is vacuous, not safe) | `tests/test_gate.py::test_f2_honest_successor_is_promoted`, `foundry.loop.main` |
| F3 | any failure-extracted trait exists outside quarantine without a policy-approved release transition | `tests/test_gate.py::test_f3_extracted_traits_are_quarantined_held`, `foundry.loop.main` |
| F4 | a foundry-proposed promotion of its own candidate is allowed | `tests/test_gate.py::test_f4_foundry_self_promotion_denied_even_for_honest_candidate` |
| F5 | a candidate with no honored E4 evidence is promoted | `tests/test_gate.py::test_f5_broken_candidate_lacks_evidence` |

A green falsification run means the gate **survived another attempt** — it is
not a proof of the gate. The demo's Goodhart candidate is one attacker; the
benchmark is one toy task. Scaling the attacker set is the v0.2 work item.

## 5. spec_only interfaces (named, not wired, not claimed)

- **Causal attribution** — the intended integration with `causal-gate`
  (mechanism-attribution rejection): promotion would additionally require a
  paired counterfactual comparison — predecessor vs successor on identical
  probe seeds — with the improvement attributed to the candidate's mechanism
  rather than to evaluation noise. Interface point: an additional FEK evidence
  record class on `K(c)` produced by the attribution harness. **Not wired; no
  causal language is used in live claims.**
- **Exogeneity attestation** — OutcomePack-style attested records proving the
  probe seed was drawn after candidate freeze. Interface point: an FEK
  attestation bound to the probe evidence record. **Not wired.**
- **Containment** — candidates currently execute in-process (see
  THREAT_MODEL.md T4). Real isolation is a planned capability behind FEK's
  deny-by-default router. **Not wired; "containment-safe" is withdrawn from
  all live claims.**
- **Assurance bounds** — a quantitative bound on promotion confidence as a
  function of evidence class and probe size. **Undefined in v0.1 and therefore
  not claimed anywhere.**
- **Successor generation** — any generative component. Gated on the above.

## 6. Shipping rule conformance

Nothing in this repo ships without a stated falsification condition: the gate's
are §4; the benchmark's hackability and the probe's catch are
`tests/test_benchmark.py`; trait extraction's containment condition is F3.
Prose claims in this repo are checked against the kernel's overclaim scanner in
CI (`make audit`).

### 6.1 External reproducibility (non-negotiable for this project)

A project whose thesis is that self-reported verification does not count cannot
report self-attested results behind an unresolvable dependency. Therefore the
evidence kernel is **vendored** under `vendor/fek` at a pinned commit
(`vendor/README.md`), and `make verify` (test + demo + audit) runs with no
external clone, no token, and no network — only the standard library plus
`pytest`. The exercised gate path imports no third-party package at all.

Falsification of *this* property: if `make verify` cannot be run from a fresh
clone of this repository alone, the reproducibility claim is broken and must be
treated as such — exactly as the gate would treat any claim lacking independent
evidence.
