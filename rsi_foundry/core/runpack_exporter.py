"""RunPack export + replay.

A RunPack is the reproducible record of a recursive run: config, root seed,
lineage DAG (with its Merkle root), every cycle, all promotions, the mined SEAL
training set, the QD archive, and the full HALF-LIFE / meta-gate history.

Reproducibility is an assurance property, so `verify_replay` re-runs the foundry
from the recorded seed+config and checks that the lineage Merkle root and final
champion match — a RunPack that does not replay is a governance failure.
"""
from __future__ import annotations

import json
import os
from typing import Any

import yaml

from rsi_foundry.core.lineage import lineage_root


def build_runpack(config: dict, root_seed: int, cycles: list[dict],
                  registry: dict, qd: dict, seal: dict, half_life: dict,
                  meta_gate_log: list, lineage: dict, reviews: list,
                  all_cids: list[str]) -> dict[str, Any]:
    return {
        "runpack_version": "0.2",
        "config": config,
        "root_seed": root_seed,
        "lineage_root": lineage_root(all_cids),
        "n_candidates": len(set(all_cids)),
        "cycles": cycles,
        "successor_registry": registry,
        "qd_archive": qd,
        "seal_training": seal,
        "half_life": half_life,
        "meta_gate_log": meta_gate_log,
        "scientist_reviews": reviews,
        "lineage_graph": lineage,
    }


def save_runpack(runpack: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if path.endswith((".yaml", ".yml")):
        with open(path, "w") as f:
            yaml.safe_dump(runpack, f, sort_keys=False, default_flow_style=False)
    else:
        with open(path, "w") as f:
            json.dump(runpack, f, indent=2)
    return path


def load_runpack(path: str) -> dict[str, Any]:
    with open(path) as f:
        if path.endswith((".yaml", ".yml")):
            return yaml.safe_load(f)
        return json.load(f)


def verify_replay(path: str) -> dict[str, Any]:
    """Re-run from the recorded seed+config; confirm lineage root + champion match."""
    from rsi_foundry.core.orchestrator import Foundry  # late import (avoid cycle)

    original = load_runpack(path)
    cfg = dict(original["config"])
    cfg["seed"] = original["root_seed"]
    foundry = Foundry(cfg)
    replay = foundry.run(cfg.get("cycles", len(original["cycles"])))
    match_root = replay["lineage_root"] == original["lineage_root"]
    match_champ = (replay["successor_registry"]["champion"]
                   == original["successor_registry"]["champion"])
    return {
        "lineage_root_match": match_root,
        "champion_match": match_champ,
        "reproducible": bool(match_root and match_champ),
        "original_root": original["lineage_root"],
        "replay_root": replay["lineage_root"],
        "original_champion": original["successor_registry"]["champion"],
        "replay_champion": replay["successor_registry"]["champion"],
    }
