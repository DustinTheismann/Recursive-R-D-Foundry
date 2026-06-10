# Threat Model — failure-trait extraction and the selection loop

Scope: the v0.1 loop (evaluate → refute/quarantine → propose → gate). The
trait-extraction step gets primary attention because harvesting traits from
*failed* candidates is the most contaminated channel in the architecture: it is
a pipe from adversarial output back toward future generation.

## Assets

- **A1.** The integrity of the promotion decision (no Goodharted candidate
  accepted).
- **A2.** The future generation channel (no adversarial trait re-enters
  candidate construction unreviewed).
- **A3.** The audit trail (every decision replayable from append-only logs).

## Threats and mitigations

### T1 — Goodhart propagation through selection
A candidate optimizes the public benchmark rather than the task, and selection
amplifies it.

*Mitigation (live):* the public surface is capped at self-verified E3 and can
never satisfy the gate alone (G1+G2 require the held-out probe). A probe
failure after a public pass files a first-class refutation; refutation
overrides all accumulated evidence (G3). Demonstrated negatively in F1.

*Residual risk:* a candidate that generalizes to the probe distribution while
still gaming the underlying objective. One toy task cannot exhibit this;
treated in §Limits.

### T2 — Trait laundering (the channel this document exists for)
A trait extracted from a failed candidate encodes the hack itself — e.g. a
"useful heuristic" that is actually memorized benchmark answers — and re-enters
generation as curated knowledge.

*Mitigation (live):* traits are quarantined **by default** with `held` status.
Release requires a policy-approved transition recorded on the event log; the
release conditions require re-evaluation on a **freshly seeded** probe (the one
test a memorized artifact cannot pass — `test_fresh_seed_still_catches_memorization`)
plus recorded human review. Nothing in the loop reads quarantined traits.
Falsification condition F3.

*Residual risk:* a reviewer releases a laundered trait. The log makes the
release attributable; it cannot make the reviewer wise.

### T3 — Benchmark leakage (deliberate, by construction)
`PUBLIC_CASES` is visible to candidate construction. This is not a flaw to fix
but the experimental condition: the demo exists to show the gate holding
*despite* full leakage of the public surface.

*Mitigation (live):* evidence-class asymmetry (E3 public vs E4 probe), G2.

### T4 — In-process execution (the honest red box)
Candidates run as ordinary Python callables in the host process. **There is no
containment in v0.1.** A malicious candidate could do anything the process can.

*Mitigation (live):* none beyond policy — the candidate set is committed,
reviewed source, and this repo must not be pointed at untrusted candidate code.
*Planned (spec_only):* isolated execution behind FEK's deny-by-default
capability router. Until that exists, "containment-safe" appears in no live
claim of this project.

### T5 — Audit-trail tampering
Doctoring the record of what was evaluated, refuted, or promoted.

*Mitigation (live, inherited from FEK):* append-only JSONL logs, per-log hash
chains, deterministic Merkle state root; hand-edits to generated views and
broken chains fail FEK's self-audit. Integrity only — a perfect chain proves
nothing about correctness.

### T6 — Verifier identity spoofing
The foundry labels its own evidence with the probe harness's identity to fake
G2.

*Mitigation (partial, live):* in v0.1 producer/verifier identities are honest
strings within one trusted process; the gate enforces the *distinctness rule*
(G2, G4) and the demo's tests pin the wiring. Cryptographic identity for
evidence records is spec_only (attestation interface, SPEC §5).

## Limits

This threat model covers a toy task with three committed candidates inside one
trusted process. It does not cover: deceptive candidates that behave well under
all evaluation, multi-step reward hacking, collusion between candidates and
extraction rules, or any threat requiring real isolation. Those are the reasons
T4's mitigation ships before any generator does.
