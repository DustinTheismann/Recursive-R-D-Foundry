"""Deterministic symbolic identity checker (E6 wiring). Maturity: live.

Makes ``E6_SYMBOLICALLY_SUPPORTED`` honorable for a precisely bounded class of
claims: **univariate polynomial identities** over the integers.

Method — and exactly why it is sound for this scope:

* Both sides are parsed into ASTs restricted to ``+ - *``, ``**`` with a
  constant integer exponent, integer literals, and the single declared variable.
* The degree of each side is bounded structurally from the AST.
* Both sides are evaluated at ``d+1`` integer points (``0..d``, where ``d`` is
  the larger degree bound) using exact :class:`fractions.Fraction` arithmetic —
  no floating point.
* Two univariate polynomials of degree at most ``d`` that agree on ``d+1``
  distinct points are identical. So within this scope the check is sound *and*
  complete: a pass is a proof of the identity, a fail produces a concrete
  counterexample point.

Anything outside this scope (multivariate input, division, non-integer
constants, transcendental functions) is **refused**, not approximated. Refusal
keeps the E6 grade meaning something. A full computer-algebra system remains
future work (spec_only).
"""

from __future__ import annotations

import ast
from fractions import Fraction
from typing import Any

from fek.errors import VerifierError

MAX_NODES = 200
MAX_DEGREE = 64


def _parse(text: str) -> ast.Expression:
    try:
        tree = ast.parse(str(text), mode="eval")
    except SyntaxError as exc:
        raise VerifierError(f"unparseable expression: {exc}") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise VerifierError(f"expression exceeds {MAX_NODES} AST nodes")
    return tree


def _degree(node: ast.AST, var: str) -> int:
    """Structural upper bound on polynomial degree (exact for this grammar)."""

    if isinstance(node, ast.Expression):
        return _degree(node.body, var)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int):
            raise VerifierError(f"only integer constants allowed, got {node.value!r}")
        return 0
    if isinstance(node, ast.Name):
        if node.id != var:
            raise VerifierError(f"unknown name {node.id!r} (declared variable is {var!r})")
        return 1
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return max(_degree(node.left, var), _degree(node.right, var))
        if isinstance(node.op, ast.Mult):
            return _degree(node.left, var) + _degree(node.right, var)
        if isinstance(node.op, ast.Pow):
            if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, int)):
                raise VerifierError("exponent must be a constant integer")
            if node.right.value < 0:
                raise VerifierError("negative exponents are out of scope (not a polynomial)")
            return _degree(node.left, var) * node.right.value
        raise VerifierError(f"disallowed operator: {type(node.op).__name__} (polynomials only)")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _degree(node.operand, var)
    raise VerifierError(f"disallowed syntax: {type(node).__name__}")


def _eval(node: ast.AST, var: str, x: Fraction) -> Fraction:
    if isinstance(node, ast.Expression):
        return _eval(node.body, var, x)
    if isinstance(node, ast.Constant):
        return Fraction(node.value)
    if isinstance(node, ast.Name):
        return x
    if isinstance(node, ast.BinOp):
        left, right_node = node.left, node.right
        if isinstance(node.op, ast.Add):
            return _eval(left, var, x) + _eval(right_node, var, x)
        if isinstance(node.op, ast.Sub):
            return _eval(left, var, x) - _eval(right_node, var, x)
        if isinstance(node.op, ast.Mult):
            return _eval(left, var, x) * _eval(right_node, var, x)
        if isinstance(node.op, ast.Pow):
            return _eval(left, var, x) ** right_node.value  # type: ignore[attr-defined]
    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand, var, x)
        return -operand if isinstance(node.op, ast.USub) else operand
    raise VerifierError(f"disallowed syntax: {type(node).__name__}")  # pragma: no cover - guarded by _degree


def verify(lhs: str, rhs: str, variable: str = "x") -> dict[str, Any]:
    """Check the univariate polynomial identity ``lhs == rhs`` exactly.

    Returns ``{"passed", "method", "degree", "points", "reason"}``. A failing
    result includes a concrete counterexample point. Raises
    :class:`VerifierError` for out-of-scope input (refusal, not approximation).
    """

    lt, rt = _parse(lhs), _parse(rhs)
    degree = max(_degree(lt, variable), _degree(rt, variable))
    if degree > MAX_DEGREE:
        raise VerifierError(f"degree bound {degree} exceeds maximum {MAX_DEGREE}")
    points = degree + 1
    for i in range(points):
        x = Fraction(i)
        lv, rv = _eval(lt, variable, x), _eval(rt, variable, x)
        if lv != rv:
            return {
                "passed": False,
                "method": "univariate_polynomial_identity",
                "degree": degree,
                "points": points,
                "reason": f"counterexample at {variable}={i}: lhs={lv} != rhs={rv}",
            }
    return {
        "passed": True,
        "method": "univariate_polynomial_identity",
        "degree": degree,
        "points": points,
        "reason": (
            f"agree at {points} points with exact rational arithmetic; "
            f"identical for univariate polynomials of degree <= {degree}"
        ),
    }


__all__ = ["verify", "MAX_NODES", "MAX_DEGREE"]
