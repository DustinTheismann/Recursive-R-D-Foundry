"""SEAL: failures become training signal that reshapes the proposer's priors."""
from rsi_foundry.training.seal_loop import SEALLoop


def _g(**kw):
    base = {"w_residual": 0.0, "w_remaining": 0.0, "w_load": 0.0, "w_tight": 0.0,
            "new_bin_bias": -1.0, "tie": "first"}
    base.update(kw)
    return base


def test_improving_edit_raises_that_genes_prior():
    seal = SEALLoop()
    seal.observe(_g(), _g(w_residual=1.0), parent_fit=0.7, child_fit=0.85,
                 promoted=True, cid="c1")
    priors = seal.priors()
    assert priors["w_residual"] > 1.0          # explore this gene more
    assert priors["w_load"] == 1.0             # untouched gene stays neutral


def test_failing_edit_lowers_that_genes_prior():
    seal = SEALLoop()
    seal.observe(_g(), _g(w_remaining=2.0), parent_fit=0.8, child_fit=0.6,
                 promoted=False, cid="c2")
    assert seal.priors()["w_remaining"] < 1.0


def test_every_observation_is_mined_as_an_example():
    seal = SEALLoop()
    seal.observe(_g(), _g(w_tight=0.5), 0.7, 0.72, True, "c1")
    seal.observe(_g(), _g(w_tight=0.9), 0.7, 0.65, False, "c2")
    ex = seal.training_examples()
    assert len(ex) == 2
    assert {e["label"] for e in ex} == {"promote", "reject"}
