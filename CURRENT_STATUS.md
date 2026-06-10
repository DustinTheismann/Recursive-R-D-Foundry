# Current Status

## Live (wired and exercised by the falsification suite)

- **Cold-reproducible:** the evidence kernel is vendored under `vendor/fek` at a
  pinned commit, so `make verify` (test + demo + audit) runs from a fresh clone
  with no external dependency, token, or network. Results are replayable, not
  self-attested.
- Promotion gate wiring on the vendored evidence kernel: evidence floor (E4),
  independent-verifier requirement, refutation supremacy, no foundry
  self-promotion (SPEC.md G1–G4).
- Deliberately hackable public benchmark + deterministic held-out probe.
- Counterexample refutations filed automatically on probe failure.
- Quarantine-by-default for failure-extracted traits, with fresh-seed release
  conditions.
- Executable falsification run (`make falsify`, F1–F5) and 13-test suite.

## Experimental (present, not promotion-grade)

- Rule-based trait extraction (two signatures: public_benchmark_overfit,
  fails_public_benchmark). Transparent on purpose; no learned components.

## spec_only (named interfaces, not wired — claimed nowhere)

- Successor generation (gated on the gate itself surviving attack).
- Containment / isolated execution of candidates (currently in-process;
  see THREAT_MODEL.md T4).
- Causal attribution via causal-gate (counterfactual predecessor/successor
  comparison on identical probe seeds).
- Exogeneity attestation for probe seeds (OutcomePack-style records).
- Assurance bounds (undefined in v0.1).

## Known limitations

- One toy task, three committed candidates, one trusted process. The threat
  model's Limits section lists what this cannot show.
- Probe exogeneity is an ordering convention in v0.1, not an attested protocol.
