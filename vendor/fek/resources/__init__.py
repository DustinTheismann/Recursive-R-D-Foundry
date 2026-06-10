"""Resource accounting (maturity: spec_only).

Metering compute/credentials/quotas for a federated evidence substrate
(layer 10) is future work. Declared here so the architecture is represented in
typed code, not invented folders. Not wired (law #14).
"""

from __future__ import annotations

MATURITY = "spec_only"


def account(*_args, **_kwargs):  # pragma: no cover - spec_only stub
    raise NotImplementedError("resource accounting is spec_only in v0.1 (see specs/future)")


__all__ = ["MATURITY", "account"]
