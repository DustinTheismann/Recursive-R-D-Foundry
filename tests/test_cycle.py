"""End-to-end recursive cycle: the loop runs, improves, and stays governed."""
from rsi_foundry.core.orchestrator import Foundry


def test_cycle_runs_and_exports():
    rp = Foundry({"seed": 7, "cycles": 5}).run()
    assert rp["n_candidates"] > 10
    assert rp["successor_registry"]["champion"] is not None
    assert len(rp["cycles"]) == 5
    # lineage merkle root is recorded
    assert len(rp["lineage_root"]) == 64


def test_recursive_improvement_over_seed():
    rp = Foundry({"seed": 7, "cycles": 8}).run()
    seed_capability = rp["cycles"][0]["capability_index"]
    champion = rp["successor_registry"]["champion_fitness"]
    # the foundry discovers a genuinely better heuristic than the weak seed
    assert champion > seed_capability
    assert rp["successor_registry"]["n_promotions"] >= 1


def test_every_promotion_passed_all_gates():
    rp = Foundry({"seed": 11, "cycles": 6}).run()
    for p in rp["successor_registry"]["promotions"]:
        rep = p.get("report")
        if rep is None:  # seed entry
            continue
        assert rep["promoted"] is True
        assert rep["contracts_pass"] and rep["contained"] and rep["benchmark_pass"]
        assert rep["causal_pass"] is True
        assert rep["half_life_pass"] is True
        assert rep["regression_failures"] == 0
        assert rep["lineage_hash"]


def test_anti_collapse_keeps_diversity():
    rp = Foundry({"seed": 7, "cycles": 8}).run()
    # the QD archive holds more than one elite; diversity does not collapse to 1
    assert rp["qd_archive"]["coverage"] > 0.0
    assert len(rp["qd_archive"]["cells"]) >= 2
