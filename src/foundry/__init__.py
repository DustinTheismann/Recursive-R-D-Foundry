"""Recursive R&D Foundry -- a governed successor-selection loop (v0.1).

What is live: the promotion gate (built entirely on fractal-evidence-kernel),
a deliberately hackable public benchmark plus a held-out probe, rule-based
failure-trait extraction with quarantine-by-default, and an executable
falsification run (`python -m foundry`).

What is NOT here yet (spec_only, see SPEC.md): successor generation,
containment/sandboxing, causal attribution, assurance bounds.
"""

from foundry.loop import main, run_demo

__version__ = "0.1.0"
__all__ = ["run_demo", "main", "__version__"]
