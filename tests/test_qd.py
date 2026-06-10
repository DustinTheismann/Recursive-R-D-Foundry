"""Quality-diversity archive keeps the best candidate *per behavior niche*."""
from rsi_foundry.core.types import EvalResult
from rsi_foundry.loops.qd_archive import QDArchive
from rsi_foundry.proposers.base import build_candidate


def _cand(seed):
    return build_candidate(
        {"w_residual": float(seed), "w_remaining": 0.0, "w_load": 0.0,
         "w_tight": 0.0, "new_bin_bias": -1e9, "tie": "first"}, [], "t", 0)


def _res(cid, fitness, behavior):
    return EvalResult(cid=cid, valid=True, fitness=fitness, behavior=behavior)


def test_distinct_niches_are_both_retained():
    qd = QDArchive(grid=8)
    qd.add(_cand(1), _res("a", 0.8, [0.1, 0.1]))
    qd.add(_cand(2), _res("b", 0.7, [0.9, 0.9]))
    assert len(qd.elites()) == 2
    assert qd.coverage() > 0


def test_better_candidate_replaces_in_same_cell():
    qd = QDArchive(grid=8)
    c1, c2 = _cand(1), _cand(2)
    assert qd.add(c1, _res(c1.cid, 0.7, [0.5, 0.5])) is True
    assert qd.add(c2, _res(c2.cid, 0.9, [0.5, 0.5])) is True   # same cell, better
    assert len(qd.elites()) == 1
    assert qd.champion().result.fitness == 0.9


def test_worse_candidate_is_rejected_from_cell():
    qd = QDArchive(grid=8)
    c1, c2 = _cand(1), _cand(2)
    qd.add(c1, _res(c1.cid, 0.9, [0.5, 0.5]))
    assert qd.add(c2, _res(c2.cid, 0.6, [0.5, 0.5])) is False
    assert qd.champion().result.fitness == 0.9


def test_invalid_candidate_never_enters():
    qd = QDArchive(grid=8)
    c = _cand(1)
    bad = EvalResult(cid=c.cid, valid=False, fitness=0.99, behavior=[0.5, 0.5])
    assert qd.add(c, bad) is False
