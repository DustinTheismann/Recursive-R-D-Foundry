"""HALF-LIFE: capability may expand only as fast as assurance can absorb it."""
from rsi_foundry.governance.half_life import HalfLifeController


def test_absorbable_drift_is_allowed():
    c = HalfLifeController(safety_factor=2.0)
    c.set_baseline_capability(0.80)
    c.add_assurance(0.01)
    d = c.consider(0.82, contained=True)   # drift 0.02 -> required 0.01
    assert d.allow is True
    assert c.capability == 0.82
    assert d.state in ("GREEN", "AMBER")


def test_unabsorbable_drift_goes_RED_and_books_debt():
    c = HalfLifeController(safety_factor=2.0)
    c.set_baseline_capability(0.80)
    # no assurance minted; a large jump cannot be absorbed
    d = c.consider(0.95, contained=True)
    assert d.allow is False
    assert d.state == "RED"
    assert c.debt > 0


def test_lateral_diversity_has_no_cost():
    c = HalfLifeController()
    c.set_baseline_capability(0.80)
    d = c.consider(0.80, contained=True)   # no capability drift
    assert d.allow is True
    assert d.drift == 0.0


def test_containment_breach_is_BLACK_and_halts():
    c = HalfLifeController(black_strikes_to_halt=3)
    c.set_baseline_capability(0.80)
    for _ in range(3):
        d = c.consider(0.81, contained=False)
        assert d.state == "BLACK" and d.allow is False
    assert c.should_halt() is True
