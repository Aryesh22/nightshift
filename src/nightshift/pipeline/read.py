"""Stage 1: read the library and extract testable, grounded claims.

Source is read as text from a shallow host-side git clone; library code is never imported
or executed here.
"""

from __future__ import annotations

import ast
import asyncio
import re
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


async def _git(*args: str, cwd: Path | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=cwd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), 60)
    except (TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.wait()
        raise
    if proc.returncode != 0:
        raise RuntimeError(f"source Git operation failed: {err.decode()[-500:]}")
    return out.decode().strip()


def _origin_identity(url: str) -> str:
    if url.startswith("file://"):
        return str(Path(url[7:]).resolve())
    if "://" not in url and Path(url).exists():
        return str(Path(url).resolve())
    return url.rstrip("/").removesuffix(".git")


async def source_revision(repo: Path) -> str:
    return await _git("rev-parse", "--verify", "HEAD^{commit}", cwd=repo)


async def clone(repo_url: str, ref: str, dest: Path) -> Path:
    """Validate the origin and resolve one immutable revision on every cache reuse."""
    if not ref or ref.startswith("-"):
        raise ValueError("a non-option Git ref is required")
    if dest.exists():
        if not (dest / ".git").is_dir():
            raise ValueError("source cache is not a complete Git checkout")
        top = await _git("rev-parse", "--show-toplevel", cwd=dest)
        origin = await _git("remote", "get-url", "origin", cwd=dest)
        if Path(top).resolve() != dest.resolve() or _origin_identity(origin) != _origin_identity(repo_url):
            raise ValueError("source cache repository identity does not match the request")
        if await _git("status", "--porcelain", "--untracked-files=all", cwd=dest):
            raise ValueError("source cache is dirty or incomplete")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        await _git("clone", "--no-checkout", "--depth", "1", "--", repo_url, str(dest))
    if re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        revision = ref.lower()
    else:
        refs = await _git("ls-remote", "--exit-code", repo_url,
                          f"refs/heads/{ref}", f"refs/tags/{ref}", f"refs/tags/{ref}^{{}}")
        matches = {name: sha for sha, name in (line.split() for line in refs.splitlines())}
        revision = (matches.get(f"refs/heads/{ref}") or matches.get(f"refs/tags/{ref}^{{}}")
                    or matches.get(f"refs/tags/{ref}"))
        if not revision:
            raise ValueError("requested revision could not be resolved")
    await _git("fetch", "--depth", "1", "origin", revision, cwd=dest)
    await _git("checkout", "--detach", revision, cwd=dest)
    if await source_revision(dest) != revision:
        raise ValueError("source cache resolved to the wrong commit")
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
