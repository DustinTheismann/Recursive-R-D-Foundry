"""Live, deterministic, in-process evidence checkers.

These engines turn E5/E6 from *declarative* evidence classes into *executable*
ones: the grader will not honor an E5/E6 evidence record unless the record's
``check`` payload actually passes the corresponding verifier here.

Trust note (see docs/TRUST_TAXONOMY.md): these are pure in-process functions —
no I/O, no network, no subprocess, no authority. That is why grading may call
them directly rather than through the capability router. Authority-bearing
operations (e.g. runpack re-execution) DO go through deny-by-default grants.

Scope honesty: ``numeric`` evaluates whitelisted arithmetic; ``symbolic`` proves
univariate polynomial identities exactly and refuses everything else. Neither is
a proof assistant; machine-checked proof (E7+) remains spec_only.
"""

from __future__ import annotations

from fek.verifiers import numeric, symbolic

__all__ = ["numeric", "symbolic"]
