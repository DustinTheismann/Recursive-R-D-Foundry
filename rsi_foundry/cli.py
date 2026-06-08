"""Command-line interface for the foundry.

    rsi-foundry run       [--config c.yaml] [--cycles N] [--seed S] [--out rp.yaml] [--dashboard d.html]
    rsi-foundry replay     <runpack>            # re-run from seed, verify reproducibility
    rsi-foundry dashboard  <runpack> [-o out.html]
    rsi-foundry report     <runpack>            # text summary
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import yaml

from rsi_foundry.core.orchestrator import Foundry
from rsi_foundry.core.runpack_exporter import (load_runpack, save_runpack,
                                               verify_replay)
from rsi_foundry.dashboard.render import save_dashboard


def _load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _print_report(rp: dict) -> None:
    reg = rp["successor_registry"]
    hl = rp["half_life"]["snapshot"]
    print("Recursive R&D Foundry — RunPack report")
    print(f"  lineage root : {rp['lineage_root']}")
    print(f"  seed         : {rp['root_seed']}   candidates: {rp['n_candidates']}")
    print(f"  champion     : {reg['champion']}  fitness={reg['champion_fitness']}")
    print(f"  promotions   : {reg['n_promotions']}")
    print(f"  HALF-LIFE    : {hl['state']}  assurance={hl['cumulative_assurance']} debt={hl['debt']}")
    print(f"  QD archive   : coverage={rp['qd_archive']['coverage']} score={rp['qd_archive']['qd_score']}")
    print(f"  SEAL examples: {rp['seal_training']['n_examples']}")
    print("  cycles:")
    for c in rp["cycles"]:
        print(f"    c{c['cycle']:>2}  promoted={len(c['promoted']):<2} state={c['half_life_state']:<5} "
              f"cap={c['capability_index']:<8} assur={c['assurance_index']:<8} "
              f"H={c['population_entropy']:<6} envs={c['environment']['envs']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rsi-foundry", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="run a recursive R&D session")
    pr.add_argument("--config"); pr.add_argument("--cycles", type=int)
    pr.add_argument("--seed", type=int)
    pr.add_argument("--out", default="runpacks/session.runpack.yaml")
    pr.add_argument("--dashboard")

    prp = sub.add_parser("replay", help="verify a runpack reproduces")
    prp.add_argument("runpack")

    pd = sub.add_parser("dashboard", help="render a runpack to HTML")
    pd.add_argument("runpack"); pd.add_argument("-o", "--out", default="dashboard.html")

    prt = sub.add_parser("report", help="print a text summary")
    prt.add_argument("runpack")

    args = p.parse_args(argv)

    if args.cmd == "run":
        cfg = _load_config(args.config)
        if args.cycles is not None:
            cfg["cycles"] = args.cycles
        if args.seed is not None:
            cfg["seed"] = args.seed
        foundry = Foundry(cfg)
        rp = foundry.run()
        save_runpack(rp, args.out)
        _print_report(rp)
        print(f"\nRunPack saved -> {args.out}")
        if args.dashboard:
            save_dashboard(rp, args.dashboard)
            print(f"Dashboard saved -> {args.dashboard}")
        return 0

    if args.cmd == "replay":
        v = verify_replay(args.runpack)
        print(f"reproducible      : {v['reproducible']}")
        print(f"  lineage match   : {v['lineage_root_match']}")
        print(f"  champion match  : {v['champion_match']}")
        print(f"  original root   : {v['original_root']}")
        print(f"  replay   root   : {v['replay_root']}")
        return 0 if v["reproducible"] else 1

    if args.cmd == "dashboard":
        rp = load_runpack(args.runpack)
        save_dashboard(rp, args.out)
        print(f"Dashboard saved -> {args.out}")
        return 0

    if args.cmd == "report":
        _print_report(load_runpack(args.runpack))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
