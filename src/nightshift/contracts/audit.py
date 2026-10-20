"""Deterministic checks on model-written harness code before it is allowed to run.

Catches the cheap ways an adapter or strategy can hide a bug: swallowing failures,
skipping checks, asserting on its own, or reaching into the controller. It is a filter,
not a proof of semantic fidelity; ambiguous mappings still go to a reviewer.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

BANNED_CALLS = {"exec", "eval", "compile", "globals", "locals", "vars", "__import__", "breakpoint"}
BANNED_ATTRS = {
    ("sys", "exit"), ("os", "_exit"), ("sys", "modules"), ("sys", "_getframe"),
    ("inspect", "currentframe"), ("hypothesis", "assume"), ("pytest", "skip"),
}
BANNED_MODULES = {"builtins", "gc", "ctypes", "pytest", "unittest"}
BROAD_EXCEPTIONS = {"Exception", "BaseException", "AssertionError"}


@dataclass(frozen=True)
class AuditResult:
    ok: bool
    problems: tuple[str, ...]


def audit_source(source: str, *, required: tuple[str, ...], kind: str) -> AuditResult:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return AuditResult(False, (f"{kind}: syntax error: {e}",))

    problems: list[str] = []
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    for name in required:
        if name not in defined:
            problems.append(f"{kind}: missing top-level function `{name}`")

    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Assert):
            problems.append(f"{kind}:{line}: `assert` is not allowed; the controller owns assertions")
        elif isinstance(node, ast.ExceptHandler):
            caught = _exception_names(node.type)
            if node.type is None or caught & BROAD_EXCEPTIONS:
                problems.append(f"{kind}:{line}: broad `except` can swallow the failure we test for")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for mod in mods:
                if mod.split(".")[0] in BANNED_MODULES or (kind == "adapter" and mod.startswith("hypothesis")):
                    problems.append(f"{kind}:{line}: import of `{mod}` is not allowed")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            problems.append(f"{kind}:{line}: call to `{node.func.id}` is not allowed")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if (node.value.id, node.attr) in BANNED_ATTRS:
                problems.append(f"{kind}:{line}: `{node.value.id}.{node.attr}` is not allowed")
        elif isinstance(node, ast.Name) and node.id.startswith("_STATS"):
            problems.append(f"{kind}:{line}: touching controller state is not allowed")
        elif isinstance(node, ast.Name) and node.id in {"assume", "reject"} and kind == "strategy":
            problems.append(f"{kind}:{line}: filtering with `{node.id}` hides inputs; use constructive strategies")
    return AuditResult(not problems, tuple(problems))


def _exception_names(node: ast.expr | None) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Tuple):
        return set().union(*(_exception_names(e) for e in node.elts))
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    return set()
