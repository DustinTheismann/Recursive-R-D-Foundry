"""Deny-by-default capability registry and router (law #7).

Nothing in the kernel may *do* anything privileged without an explicit, active
grant. Capabilities are declared in ``registry/capabilities/*.yaml`` with a
trust boundary and maturity label (law #9, law #10). The router records every
invocation -- allowed or denied -- to the capability event log (audit).

Authority-bearing secrets are never stored here (law #8); capability files
declare *what* is permitted, never the credential that permits it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from fek.errors import CapabilityDenied
from fek.kernel.context import Kernel
from fek.state.store import EventStore


def load_capabilities(kernel: Kernel) -> dict[str, dict[str, Any]]:
    """Load all capability definitions keyed by ``capability_id``."""

    out: dict[str, dict[str, Any]] = {}
    cap_dir = kernel.paths.capabilities
    if not cap_dir.exists():
        return out
    for path in sorted(cap_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cid = doc.get("capability_id")
        if cid:
            out[cid] = doc
    return out


def active_grants(kernel: Kernel) -> set[str]:
    """Capability ids that are currently granted (replayed from the log)."""

    granted: set[str] = set()
    for ev in EventStore(kernel).read("capability"):
        cid = ev.payload.get("capability_id")
        if ev.type == "capability.granted":
            granted.add(cid)
        elif ev.type == "capability.revoked":
            granted.discard(cid)
    return granted


def request_capability(kernel: Kernel, capability_id: str, requester: str) -> None:
    _require_registered(kernel, capability_id)
    EventStore(kernel).append(
        "capability", "capability.requested", {"capability_id": capability_id, "requester": requester}
    )


def grant_capability(kernel: Kernel, capability_id: str, grantor: str) -> None:
    _require_registered(kernel, capability_id)
    EventStore(kernel).append(
        "capability", "capability.granted", {"capability_id": capability_id, "grantor": grantor}
    )


def revoke_capability(kernel: Kernel, capability_id: str, revoker: str) -> None:
    EventStore(kernel).append(
        "capability", "capability.revoked", {"capability_id": capability_id, "revoker": revoker}
    )


def invoke_capability(kernel: Kernel, capability_id: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Invoke a capability IFF it is granted. Deny + audit otherwise.

    Every outcome is written to the capability event log (the ``audit_event_type``
    declared by the capability), satisfying law #9's "all live capabilities must
    have trust boundaries" by making each crossing observable.
    """

    args = args or {}
    caps = load_capabilities(kernel)
    cap = caps.get(capability_id)
    store = EventStore(kernel)

    if cap is None:
        store.append("capability", "capability.denied", {"capability_id": capability_id, "reason": "unregistered"})
        raise CapabilityDenied(f"capability {capability_id!r} is not registered (deny-by-default)")

    if capability_id not in active_grants(kernel):
        store.append(
            "capability",
            "capability.denied",
            {"capability_id": capability_id, "reason": "no active grant", "trust_boundary": cap.get("trust_boundary")},
        )
        raise CapabilityDenied(f"capability {capability_id!r} invoked without an active grant (deny-by-default)")

    # Granted: dispatch (or stub for non-live maturities) and audit.
    result = _dispatch(cap, args)
    store.append(
        "capability",
        cap.get("audit_event_type", "capability.invoked"),
        {
            "capability_id": capability_id,
            "trust_boundary": cap.get("trust_boundary"),
            "maturity": cap.get("maturity"),
            "result_status": result.get("status"),
        },
    )
    return result


def _dispatch(cap: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """Call the implementation if live and importable; otherwise return a stub."""

    if cap.get("maturity") != "live":
        return {"status": "stub", "maturity": cap.get("maturity"), "capability_id": cap.get("capability_id")}
    module = cap.get("implementation_module")
    func = cap.get("implementation_function")
    if not module or not func:
        return {"status": "stub", "reason": "no implementation wired"}
    import importlib

    try:
        mod = importlib.import_module(module)
        fn = getattr(mod, func)
    except (ImportError, AttributeError) as exc:
        return {"status": "error", "reason": f"implementation unavailable: {exc}"}
    return {"status": "ok", "value": fn(**args)}


def _require_registered(kernel: Kernel, capability_id: str) -> None:
    if capability_id not in load_capabilities(kernel):
        raise CapabilityDenied(f"capability {capability_id!r} is not registered")


__all__ = [
    "load_capabilities",
    "active_grants",
    "request_capability",
    "grant_capability",
    "revoke_capability",
    "invoke_capability",
]
