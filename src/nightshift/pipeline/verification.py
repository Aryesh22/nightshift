"""Controller-owned semantic replay and the deliberately narrow patch policy."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import shlex
from pathlib import PurePosixPath

REPRO_PATH = "nightshift_repro.py"
VERIFIER_PATH = "nightshift_verify.py"
DISCOVERY_PATH = "nightshift_tests/test_discovery.py"
MARKER = "NIGHTSHIFT_REPLAY "
FORBIDDEN_ERRORS = {"ImportError", "ModuleNotFoundError", "SyntaxError", "NameError"}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def assertion_lines(property_source: str, repro: str, target: str) -> list[int]:
    """Match assertions with the discovery inputs substituted consistently.

    Preserve API paths, operators, fixed expected values and repeated-input equality.
    This first-release policy requires direct assertion expressions; reduction into
    helper-based or unrelated assertions is unresolved rather than silently accepted.
    """
    def parse(source):
        tree = ast.parse(source)
        aliases = {target.rsplit(".", 1)[-1]: target}
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                aliases.update({a.asname or a.name: f"{n.module}.{a.name}" for a in n.names})
            elif isinstance(n, ast.Import):
                aliases.update({a.asname or a.name.split(".")[0]: a.name if a.asname else a.name.split(".")[0]
                                for a in n.names})

        class Canonical(ast.NodeTransformer):
            def visit_Name(self, node):
                return ast.Name(id=aliases.get(node.id, node.id), ctx=ast.Load())

            def visit_Attribute(self, node):
                value = self.visit(node.value)
                if isinstance(value, ast.Name):
                    return ast.Name(id=f"{value.id}.{node.attr}", ctx=ast.Load())
                return node

        assertions = [(n.lineno, Canonical().visit(copy.deepcopy(n.test)))
                      for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        parameters = {a.arg for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                      for a in (*n.args.posonlyargs, *n.args.args, *n.args.kwonlyargs)}
        return assertions, parameters

    def contains_target(node):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == target
                   for n in ast.walk(node))

    def matches(pattern, actual, variables, bindings):
        if isinstance(pattern, ast.Name) and pattern.id in variables:
            value = ast.dump(actual, include_attributes=False)
            previous = bindings.setdefault(pattern.id, value)
            return value == previous
        if type(pattern) is not type(actual):
            return False
        if isinstance(pattern, ast.AST):
            return all(matches(getattr(pattern, f), getattr(actual, f), variables, bindings)
                       for f in pattern._fields)
        if isinstance(pattern, list):
            return len(pattern) == len(actual) and all(matches(p, a, variables, bindings)
                                                       for p, a in zip(pattern, actual))
        return pattern == actual

    patterns, variables = parse(property_source)
    assertions, _ = parse(repro)
    return [line for line, actual in assertions if contains_target(actual) and
            any(contains_target(pattern) and matches(pattern, actual, variables, {}) for _, pattern in patterns)]


_REPLAY = '''
import functools, hashlib, importlib, inspect, json, sys, traceback
from pathlib import Path

receipt = {"target": TARGET, "repro_sha256": EXPECTED_SHA, "target_calls": 0,
           "call_lines": [], "matched": False, "passed": False}
target_errors = []
code = 2
try:
    source = Path("nightshift_repro.py").read_text()
    if hashlib.sha256(source.encode()).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("protected repro hash changed")
    parts = TARGET.split(".")
    for i in range(len(parts) - 1, 0, -1):
        try:
            owner = importlib.import_module(".".join(parts[:i]))
            break
        except ModuleNotFoundError as exc:
            if exc.name != ".".join(parts[:i]):
                raise
    else:
        raise ImportError("target module could not be loaded")
    for name in parts[i:-1]:
        owner = getattr(owner, name)
    name = parts[-1]
    static = inspect.getattr_static(owner, name)
    original = static.__func__ if isinstance(static, (staticmethod, classmethod)) else getattr(owner, name)

    @functools.wraps(original)
    def tracked(*args, **kwargs):
        receipt["target_calls"] += 1
        frame = sys._getframe(1)
        while frame:
            if frame.f_code.co_filename == "nightshift_repro.py":
                receipt["call_lines"].append(frame.f_lineno)
                break
            frame = frame.f_back
        try:
            return original(*args, **kwargs)
        except BaseException as exc:
            target_errors.append(exc)
            raise

    setattr(owner, name, type(static)(tracked) if isinstance(static, (staticmethod, classmethod)) else tracked)
    try:
        exec(compile(source, "nightshift_repro.py", "exec"), {"__name__": "__main__"})
    except BaseException as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["traceback"] = traceback.format_exc()
        lines = [tb.lineno for tb in traceback.extract_tb(exc.__traceback__)
                 if tb.filename == "nightshift_repro.py"]
        line = lines[-1] if lines else None
        reached = line in APPROVED_LINES and line in receipt["call_lines"]
        assertion = isinstance(exc, AssertionError) and FAILURE_KIND == "assertion" and reached
        crash = (FAILURE_KIND == "crash" and type(exc).__name__ == EXPECTED_ERROR and
                 any(exc is error for error in target_errors) and reached)
        receipt["matched"] = (assertion or crash) and type(exc).__name__ not in FORBIDDEN_ERRORS
        code = 1 if receipt["matched"] else 2
    else:
        receipt["passed"] = any(line in APPROVED_LINES for line in receipt["call_lines"])
        code = 0 if receipt["passed"] else 2
except BaseException as exc:
    receipt.update(error_type=type(exc).__name__, traceback=traceback.format_exc())
print("NIGHTSHIFT_REPLAY " + json.dumps(receipt), flush=True)
sys.exit(code)
'''


def replay_program(repro: str, prop: str, target: str, failure_kind: str, discovery_output: str) -> str:
    lines = assertion_lines(prop, repro, target)
    if not lines:
        raise ValueError("repro does not preserve a discovery assertion involving the target API")
    errors = re.findall(r"\b([A-Za-z_]\w*(?:Error|Exception)):", discovery_output)
    expected_error = errors[-1] if errors else None
    if failure_kind not in {"assertion", "crash"} or (failure_kind == "crash" and not expected_error):
        raise ValueError("discovery has no supported semantic failure signature")
    values = {"TARGET": target, "EXPECTED_SHA": sha256(repro), "APPROVED_LINES": lines,
              "FAILURE_KIND": failure_kind, "EXPECTED_ERROR": expected_error,
              "FORBIDDEN_ERRORS": FORBIDDEN_ERRORS}
    return "\n".join(f"{k} = {v!r}" for k, v in values.items()) + "\n" + _REPLAY


def replay_receipt(result, repro: str, target: str) -> dict | None:
    if result.timed_out:
        return None
    for line in reversed(result.stdout.splitlines()):
        if line.startswith(MARKER):
            try:
                receipt = json.loads(line[len(MARKER):])
                if receipt["target"] == target and receipt["repro_sha256"] == sha256(repro):
                    return receipt
            except (ValueError, KeyError, TypeError):
                return None
    return None


def patch_paths(diff: str, source_path: str) -> set[str]:
    """Only plain text library changes; no tests, controller artifacts or path escapes."""
    source = PurePosixPath(source_path)
    root = str(source.parent) if str(source.parent) != "." else source_path
    paths = set()
    for line in diff.splitlines():
        if line.startswith(("rename ", "copy ", "GIT binary patch", "Binary files ")):
            raise ValueError("renames, copies and binary patches are unsupported")
        if line.startswith(("--- ", "+++ ")):
            pieces = shlex.split(line[4:].split("\t", 1)[0])
            if len(pieces) != 1:
                raise ValueError("unsupported diff path")
            path = pieces[0]
            if path == "/dev/null":
                continue
            if path.startswith(("a/", "b/")):
                path = path[2:]
            pure = PurePosixPath(path)
            if (pure.is_absolute() or ".." in pure.parts or "\\" in path or
                any(p in {"test", "tests", ".git", "nightshift_tests"} for p in pure.parts) or
                any(p.startswith(("test_", "nightshift_")) or p.endswith("_test.py") for p in pure.parts)):
                raise ValueError(f"patch touches a protected path: {path}")
            if not source_path or not (path == root or path.startswith(root + "/")):
                raise ValueError(f"patch is outside the target library: {path}")
            paths.add(path)
    if not paths:
        raise ValueError("patch contains no supported library changes")
    return paths


def hash_guard(repro: str, prop: str) -> str:
    hashes = {REPRO_PATH: sha256(repro), DISCOVERY_PATH: sha256(prop)}
    script = ("import hashlib; from pathlib import Path; "
              f"expected={hashes!r}; "
              "assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in expected.items()), "
              "'protected test hash changed'")
    return "python -c " + shlex.quote(script)
