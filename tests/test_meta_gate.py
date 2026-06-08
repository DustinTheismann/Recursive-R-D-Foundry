"""Meta-gate: governance is recursively improvable but monotone-safe."""
from rsi_foundry.governance.half_life import HalfLifeController
from rsi_foundry.governance.meta_gate import MetaGate
from rsi_foundry.governance.promotion import PromotionPolicy


def test_tightening_is_always_allowed():
    pol = PromotionPolicy()
    before = pol.fitness_delta_min
    MetaGate(pol, HalfLifeController()).on_breach_or_regression("containment")
    assert pol.fitness_delta_min > before


def test_loosening_requires_earned_assurance():
    pol = PromotionPolicy()
    hl = HalfLifeController()
    hl.add_assurance(1.0)                      # assurance has been earned
    mg = MetaGate(pol, hl, loosen_assurance_margin=0.5, drought_cycles=2)
    before = pol.fitness_delta_min
    assert mg.on_cycle_end(0) is None          # not enough drought yet
    entry = mg.on_cycle_end(0)                  # drought reached
    assert entry is not None and entry["allowed"] is True
    assert pol.fitness_delta_min < before


def test_loosening_blocked_when_assurance_not_earned():
    pol = PromotionPolicy()
    hl = HalfLifeController()
    hl.add_assurance(0.1)                       # below the margin
    mg = MetaGate(pol, hl, loosen_assurance_margin=10.0, drought_cycles=1)
    entry = mg.on_cycle_end(0)
    assert entry is not None and entry["allowed"] is False
    assert entry["blocked_reason"] == "assurance_not_earned"
