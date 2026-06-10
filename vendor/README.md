# Vendored dependency: fractal-evidence-kernel

`vendor/fek/` is a **verbatim, pinned copy** of the `fek` package from
`fractal-evidence-kernel`. It is vendored so this repository runs cold — no
external clone, no PAT, no network — which is mandatory for a project whose
thesis is that verification must be externally replayable.

- upstream: DustinTheismann/fractal-evidence-kernel
- pinned commit: `2a286019d78ca68f6167ffaed46225ae0abf61cd`
- branch at vendor time: claude/fractal-evidence-kernel-TdJGs
- contents: the `fek` Python package only (standard library + optional PyYAML)
- license: MIT, see `vendor/FEK-LICENSE`

This is a pinned copy, not a fork: it is not edited here. To update, re-copy
`src/fek` from upstream at a new commit and bump the SHA above. The foundry's
exercised path (claim → grade → refute → quarantine → policy gate, plus the
overclaim scanner) requires only the Python standard library; PyYAML is needed
only if YAML registries/source-maps are present, which they are not in this repo.

Why vendor instead of `pip install`: a git/PyPI dependency on the kernel made
this repo's verification self-attested (unresolvable by any external reviewer).
Vendoring converts "trust my numbers" into "run it yourself".
