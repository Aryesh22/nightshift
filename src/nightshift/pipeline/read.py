"""Stage 1: read the library and extract testable, grounded claims.

Source is read as text from a shallow host-side git clone; library code is never imported
or executed here.
"""

from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
from pathlib import Path

from nightshift.llm import NemotronClient
from nightshift.pipeline import prompts
from nightshift.pipeline.cascade import call_with_cascade
from nightshift.pipeline.router import Router, bucket
from nightshift.pipeline.types import RouteStep, Target

DOC_SUFFIXES = {".md", ".rst", ".txt"}
SKIP_DIRS = {"tests", "test", "testing", "benchmarks", "examples", ".git", "build", "dist", "node_modules"}


@dataclass
class SourceIndex:
    """Function sources by qualname, for prompts and complexity features."""

    functions: dict[str, tuple[str, str]]  # qualname -> (relative file path, source)

    def lookup(self, qualname: str) -> tuple[str, str]:
        if qualname in self.functions:
            return self.functions[qualname]
        # Re-exports: match on the trailing name if it is unique.
        tail = qualname.rsplit(".", 1)[-1]
        hits = [v for k, v in self.functions.items() if k.rsplit(".", 1)[-1] == tail]
        return hits[0] if len(hits) == 1 else ("", "")


async def clone(repo_url: str, ref: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", "--branch", ref, repo_url, str(dest),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {err.decode()[-500:]}")
    return dest


def _package_root(repo: Path, package: str) -> Path:
    for candidate in (repo / "src" / package, repo / package):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"package {package!r} not found under {repo} or {repo / 'src'}")


def index_functions(repo: Path, package: str) -> SourceIndex:
    root = _package_root(repo, package)
    functions: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*.py")):
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        text = path.read_text(errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        module = ".".join((package, *path.relative_to(root).with_suffix("").parts))
        module = module.removesuffix(".__init__")
        rel = str(path.relative_to(repo))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[f"{module}.{node.name}"] = (rel, ast.get_source_segment(text, node) or "")
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions[f"{module}.{node.name}.{item.name}"] = (
                            rel,
                            ast.get_source_segment(text, item) or "",
                        )
    return SourceIndex(functions)


def build_digest(repo: Path, package: str, max_chars: int) -> str:
    """Docs first (they hold the promises), then package source, cut at max_chars."""
    parts: list[str] = []
    docs = [p for p in sorted(repo.glob("*")) if p.suffix.lower() in DOC_SUFFIXES and p.is_file()]
    docs += sorted(p for p in (repo / "docs").rglob("*") if p.suffix.lower() in DOC_SUFFIXES) if (repo / "docs").is_dir() else []
    root = _package_root(repo, package)
    sources = [p for p in sorted(root.rglob("*.py")) if not SKIP_DIRS & set(p.relative_to(root).parts)]
    used = 0
    for path in docs + sources:
        text = path.read_text(errors="replace")
        block = f"\n===== {path.relative_to(repo)} =====\n{text}\n"
        if used + len(block) > max_chars:
            block = block[: max(0, max_chars - used)]
        parts.append(block)
        used += len(block)
        if used >= max_chars:
            break
    return "".join(parts)


def _valid_targets(payload: dict) -> list[dict]:
    targets = payload.get("targets")
    if not isinstance(targets, list):
        raise ValueError("missing 'targets' list")
    good = [t for t in targets if isinstance(t, dict) and t.get("qualname") and t.get("claim")]
    if not good:
        raise ValueError("no usable targets")
    return good


async def extract_targets(
    client: NemotronClient,
    router: Router,
    repo: Path,
    package: str,
    library: str,
    max_targets: int = 12,
    max_chars: int = 240_000,
) -> tuple[list[Target], SourceIndex, list[RouteStep]]:
    index = index_functions(repo, package)
    digest = build_digest(repo, package, max_chars)
    messages = [
        {"role": "system", "content": prompts.READ_SYSTEM},
        {"role": "user", "content": prompts.READ_USER.format(library=library, max_targets=max_targets, digest=digest)},
    ]
    raw, trace = await call_with_cascade(
        client, router, "read", bucket(), messages, parse=_valid_targets, max_tokens=4096
    )
    targets: list[Target] = []
    for i, t in enumerate(raw or []):
        _, source = index.lookup(t["qualname"])
        targets.append(
            Target(
                id=f"t{i + 1}",
                qualname=t["qualname"],
                signature=t.get("signature", ""),
                claim=t["claim"],
                kind=t.get("kind", "invariant"),
                evidence=t.get("evidence", ""),
                source=source,
            )
        )
    return targets[:max_targets], index, trace
