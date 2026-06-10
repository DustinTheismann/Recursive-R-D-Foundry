"""Static analysis + proof-carrying contracts."""
from rsi_foundry.verification import contracts, static_analyzer


def test_static_rejects_imports_and_dunders():
    assert static_analyzer.analyze("import os\ndef place(i,b,c):\n return -1")["ok"] is False
    assert static_analyzer.analyze("def place(i,b,c):\n return i.__class__")["ok"] is False


def test_static_requires_place():
    assert static_analyzer.analyze("def other(i,b,c):\n return -1")["ok"] is False


def test_static_accepts_clean_heuristic():
    src = "def place(item, bins, capacity):\n    return -1\n"
    assert static_analyzer.analyze(src)["ok"] is True


def test_contracts_flag_capacity_violations():
    clean = [{"violations": 0, "bins_used": 5}, {"violations": 0, "bins_used": 4}]
    assert contracts.check_contracts(clean, n_items_total=100)["pass"] is True

    dirty = [{"violations": 40, "bins_used": 5}]
    assert contracts.check_contracts(dirty, n_items_total=50)["pass"] is False
