from __future__ import annotations

import ast
from typing import Any, Dict, Optional


class EvalError(Exception):
    pass


class ErrorValue:
    def __init__(self, message: str):
        self.error = True
        self.message = message

    def __repr__(self) -> str:
        return f"error(message={self.message!r})"


_ALLOWED_NODES = {
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.IfExp,
    ast.Compare,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.Attribute,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.Eq,
    ast.NotEq,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
}

_CODE_CACHE: dict[str, Any] = {}


def _validate_ast(node: ast.AST) -> None:
    for child in ast.walk(node):
        if type(child) not in _ALLOWED_NODES:
            raise EvalError(f"Unsupported expression node: {type(child).__name__}")


def eval_expr(
    expression: str,
    env: Dict[str, Any],
    item_ctx: Optional[Dict[str, Any]] = None,
    swallow_error: bool = False,
) -> Any:
    expression = expression.strip()
    if not expression:
        return None

    should_try = expression.endswith("?")
    if should_try:
        expression = expression[:-1].rstrip()

    try:
        code = _CODE_CACHE.get(expression)
        if code is None:
            tree = ast.parse(expression, mode="eval")
            _validate_ast(tree)
            code = compile(tree, "<pep-expr>", "eval")
            _CODE_CACHE[expression] = code

        names: Dict[str, Any] = {}
        names.update(_safe_builtins())
        names.update(env)
        if item_ctx:
            names.update(item_ctx)

        result = eval(code, {"__builtins__": {}}, names)
        return result
    except Exception as exc:  # noqa: BLE001
        if swallow_error or should_try:
            return ErrorValue(str(exc))
        raise EvalError(str(exc)) from exc


def _safe_builtins() -> Dict[str, Any]:
    return {
        "len": len,
        "sum": sum,
        "min": min,
        "max": max,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "range": range,
    }
