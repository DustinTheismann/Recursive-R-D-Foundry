"""Fractal Evidence Kernel (FEK).

An evidence-governed substrate for computational institutions. The kernel
refuses to trust an output merely because it was produced: every claim,
capability, transition, report, and upgrade is trusted only according to what
evidence it survived.

See ``docs/ARCHITECTURE.md`` for the typed layer model and the event-sourcing
truth model, and ``GOVERNANCE.md`` for the fifteen hard constitutional laws.
"""

from __future__ import annotations

from fek.version import VERSION

__version__ = VERSION
__all__ = ["VERSION", "__version__"]
