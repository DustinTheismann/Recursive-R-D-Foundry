"""Deterministic numeric check evaluator (E5 wiring). Maturity: live.

This is the engine that makes ``E5_NUMERICALLY_SUPPORTED`` *honorable*: an E5
evidence record must carry a ``check`` payload, and the grader only honors the
record if this verifier evaluates the check and it passes. Evidence becomes
executable, not declarative.

Scope (stated precisely, because honesty is the constitution):

* arithmetic expressions over numeric literals: ``+ - * / // % **``, unary
  ``+/-``, parentheses, and a small whitelist of math functions;
* evaluated by walking a parsed AST against an operator whitelist — there is no
  ``eval``, no name lookup, no attribute access, no imports;
* the result is compared to ``expected`` within an absolute ``tolerance``.

A passing check shows the stated arithmetic holds. It says nothing about
whether the *claim's interpretation* of that arithmetic is sound — that remains
the reviewer's job.
"""

from __future__ import annotations

import ast
import math
from typing import Any

from fek.errors import VerifierError

#: Whitelisted callable names -> implementations. Nothing else is callable.
ALLOWED_FUNCS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "log": math.log,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "abs": abs,
}

MAX_NODES = 200  # caps expression size
MAX_EXPONENT = 128  # caps ``**`` to keep evaluation bounded


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise VerifierError(f"non-numeric constant: {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        left, right = _eval(node.left), _eval(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            if right == 0:
                raise VerifierError("division by zero")
            return left / right
        if isinstance(op, ast.FloorDiv):
            if right == 0:
                raise VerifierError("division by zero")
            return left // right
        if isinstance(op, ast.Mod):
            if right == 0:
                raise VerifierError("modulo by zero")
            return left % right
        if isinstance(op, ast.Pow):
            if abs(right) > MAX_EXPONENT:
                raise VerifierError(f"exponent magnitude exceeds {MAX_EXPONENT}")
            return left**right
        raise VerifierError(f"disallowed operator: {type(op).__name__}")
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +_eval(node.operand)
        raise VerifierError(f"disallowed unary operator: {type(node.op).__name__}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
            raise VerifierError("only whitelisted functions are callable")
        if node.keywords:
            raise VerifierError("keyword arguments are not allowed")
        return ALLOWED_FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise VerifierError(f"disallowed syntax: {type(node).__name__}")


def verify(expression: str, expected: float, tolerance: float = 1e-9) -> dict[str, Any]:
    """Evaluate ``expression`` and compare to ``expected`` within ``tolerance``.

    Returns ``{"passed": bool, "value", "expected", "tolerance", "method", "reason"}``.
    Raises :class:`VerifierError` for out-of-scope or unsafe input.
    """

    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError as exc:
        raise VerifierError(f"unparseable expression: {exc}") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise VerifierError(f"expression exceeds {MAX_NODES} AST nodes")
    value = _eval(tree)
    expected_f = float(expected)
    tol = float(tolerance)
    passed = abs(value - expected_f) <= tol
    return {
        "passed": passed,
        "value": value,
        "expected": expected_f,
        "tolerance": tol,
        "method": "ast_whitelist_eval",
        "reason": f"value={value} vs expected={expected_f} (abs tolerance {tol})",
    }


__all__ = ["verify", "ALLOWED_FUNCS", "MAX_NODES", "MAX_EXPONENT"]
