"""Causal gate: promotion needs interventional ablation evidence."""
import random

from rsi_foundry.connectors.benchmark_adapters import LocalBinPackBenchmark
from rsi_foundry.domain import binpack, heuristics
from rsi_foundry.evals.harness import Harness
from rsi_foundry.governance import causal_gate
from rsi_foundry.proposers.base import build_candidate
from rsi_foundry.sandbox.containment import InProcessSandbox


def _harness():
    bench = LocalBinPackBenchmark(binpack.starter_envs(), random.Random(3), per_env=3)
    return Harness(bench, InProcessSandbox())


def test_meaningful_gene_shows_causal_effect():
    h = _harness()
    best_fit = build_candidate(
        {"w_residual": 2.0, "w_remaining": 0.0, "w_load": 0.0, "w_tight": 0.0,
         "new_bin_bias": -1e9, "tie": "first"}, [], "test", 0)
    res = h.evaluate(best_fit.cid, best_fit.source)
    out = causal_gate.evaluate_causal(best_fit, res, None, h)
    assert out["max_ablation_delta"] > 0       # removing a gene hurts
    assert out["pass"] is True


def test_no_active_genes_means_no_causal_evidence():
    h = _harness()
    first_fit = build_candidate(
        {"w_residual": 0.0, "w_remaining": 0.0, "w_load": 0.0, "w_tight": 0.0,
         "new_bin_bias": -1e9, "tie": "first"}, [], "test", 0)
    res = h.evaluate(first_fit.cid, first_fit.source)
    out = causal_gate.evaluate_causal(first_fit, res, None, h)
    # all weights are already neutral, so ablation changes nothing
    assert out["max_ablation_delta"] == 0.0
    assert out["pass"] is False
