"""Static analysis gate: reject unsafe or pathological candidate source.

Runs *before* execution. Blocks imports, attribute access to dunders, and the
usual escape hatches (exec/eval/open/compile/globals), and bounds AST size so a
candidate cannot smuggle in a fork bomb or a 10k-node monster. This is the
first vote in the evaluator quorum.
"""
from __future__ import annotations

import ast
from typing import Any

_FORBIDDEN_CALLS = {"exec", "eval", "open", "compile", "globals", "locals",
                    "__import__", "getattr", "setattr", "delattr", "vars",
                    "input", "exit", "quit", "breakpoint", "memoryview"}


def analyze(source: str, max_nodes: int = 400) -> dict[str, Any]:
    report: dict[str, Any] = {"ok": True, "issues": [], "nodes": 0, "defines_place": False}
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        report["ok"] = False
        report["issues"].append(f"syntax:{exc}")
        return report

    nodes = list(ast.walk(tree))
    report["nodes"] = len(nodes)
    if len(nodes) > max_nodes:
        report["ok"] = False
        report["issues"].append(f"too_complex:{len(nodes)}>{max_nodes}")

    for node in nodes:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            report["ok"] = False
            report["issues"].append("import_forbidden")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            report["ok"] = False
            report["issues"].append(f"dunder_attr:{node.attr}")
        elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_CALLS:
            report["ok"] = False
            report["issues"].append(f"forbidden:{node.id}")
        elif isinstance(node, ast.FunctionDef) and node.name == "place":
            report["defines_place"] = True

    if not report["defines_place"]:
        report["ok"] = False
        report["issues"].append("no_place_def")
    return report
