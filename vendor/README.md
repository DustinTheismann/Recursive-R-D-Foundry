# Vendored dependency: fractal-evidence-kernel

`vendor/fek/` is a **verbatim, pinned copy** of the `fek` package from
`fractal-evidence-kernel`, vendored so this repository's governance runs cold
(no external clone, no token, no network).

- upstream: DustinTheismann/fractal-evidence-kernel
- pinned commit: `2a286019d78ca68f6167ffaed46225ae0abf61cd`
- contents: the `fek` package only (standard library + optional PyYAML)
- license: MIT, see `vendor/FEK-LICENSE`

A pinned copy, not a fork. The governance bridge
(`rsi_foundry/governance/evidence_gate.py`) imports the evidence kernel from
here; nothing in `vendor/` is edited locally.
