"""Orchestrate one Nightshift run: read -> propose+run -> triage -> confirm -> report."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Literal
import math

from nightshift.llm import BudgetExceeded, NemotronClient
from nightshift.pipeline.confirm import confirm
from nightshift.pipeline.propose import propose_and_run
from nightshift.pipeline.read import clone, extract_targets, source_revision
from nightshift.report import build_campaign_report, write_campaign_report
from nightshift.pipeline.router import Router
from nightshift.pipeline.triage import triage
from nightshift.pipeline.types import Bug, Execution, PropertyTest, Target
from nightshift.sandbox import SandboxExecutor

SETUP_CMDS = ["python -m pip install -q -e . hypothesis pytest"]


@dataclass
class RunConfig:
    repo_url: str
    package: str
    ref: str = "main"
    library: str = ""
    max_targets: int = 12
    variants_per_target: int = 2
    runs_dir: Path = Path("runs")
    setup_cmds: tuple[str, ...] = tuple(SETUP_CMDS)
    # Compatibility for callers predating dual-mode campaigns. The CLI explicitly
    # selects Core by default; new API callers select mode="core" here or below.
    mode: Literal["core", "baseline"] = "baseline"
    airgapped: bool = False
    online_lookup: bool = False
    tavily_credits: float = 1000
    doc_paths: tuple[str, ...] = ("README.md",)
    max_examples: int = 200
    campaign_timeout_s: float = 120
    python: str = "python"
    cache_namespace: str = ""
    ultra_review: bool = False
    ultra_budget_usd: float = 0.02
    ultra_max_survivors: int = 2

    def __post_init__(self):
        if self.mode not in {"core", "baseline"}:
            raise ValueError("mode must be core or baseline")
        if not math.isfinite(self.tavily_credits) or not 0 <= self.tavily_credits <= 1000:
            raise ValueError("Tavily credit allowance must be between 0 and 1000")
        if not math.isfinite(self.ultra_budget_usd) or self.ultra_budget_usd < 0:
            raise ValueError("Ultra allowance must be finite and nonnegative")
        if not 1 <= self.max_examples <= 10_000 or not 1 <= self.variants_per_target <= 10:
            raise ValueError("invalid bounded campaign profile")
        if not 0 <= self.ultra_max_survivors <= 10 or not 1 <= self.max_targets <= 128:
            raise ValueError("invalid survivor/contract limit")
        if not 0 < self.campaign_timeout_s <= 600:
            raise ValueError("campaign timeout must be between 0 and 600 seconds")


def _jsonl(path: Path, rows: list) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(asdict(r)) + "\n" for r in rows))
    temporary.replace(path)


async def run_nightshift(config: RunConfig, client: NemotronClient, sandbox: SandboxExecutor,
                         router: Router | None = None, *, mode: Literal["core", "baseline"] | None = None,
                         tavily=None) -> dict:
    selected = config.mode if mode is None else mode
    if selected not in {"core", "baseline"}:
        raise ValueError("mode must be core or baseline")
    if selected == "core":
        from nightshift.pipeline.core import run_core
        return await run_core(config, client, sandbox, tavily=tavily)
    router = router or Router()
    library = config.library or config.package
    run_id = f"{datetime.now(timezone.utc):%Y-%m-%d-%H%M%S}-{uuid4().hex[:8]}-{library}"
    run_dir = config.runs_dir / run_id
    (run_dir / "properties").mkdir(parents=True, exist_ok=True)

    stats = {"targets": 0, "properties_proposed": 0, "failures": 0, "triaged_real": 0}
    bugs: list[Bug] = []
    stopped: str | None = None
    lib_info = {"name": library, "repo": config.repo_url, "ref": config.ref}
    targets = []
    failing = []
    completed_verdicts = []
    errors: list[dict] = []

    try:
        repo = await clone(config.repo_url, config.ref, config.runs_dir / "_src" / f"{library}-{config.ref}")
        revision = await source_revision(repo)
        lib_info["version"] = revision
        (run_dir / "source.json").write_text(json.dumps({**lib_info, "commit": revision}, indent=2))
        targets, index, _ = await extract_targets(client, router, repo, config.package, library, config.max_targets)
        stats["targets"] = len(targets)
        (run_dir / "targets.json").write_text(json.dumps([asdict(t) for t in targets], indent=2))

        base_env = await sandbox.prepare(config.repo_url, revision, list(config.setup_cmds))
        try:
            by_id: dict[str, Target] = {t.id: t for t in targets}
            proposals = await asyncio.gather(
                *(
                    propose_and_run(client, router, sandbox, base_env, t, v)
                    for t in targets
                    for v in range(config.variants_per_target)
                ),
                return_exceptions=True,
            )
            props: list[PropertyTest] = []
            failing: list[tuple[PropertyTest, Execution]] = []
            executions: list[Execution] = []
            for item in proposals:
                if isinstance(item, BaseException):
                    errors.append({"stage": "propose", "error": type(item).__name__, "message": str(item)})
                    continue
                prop, execution, _ = item
                if execution:
                    executions.append(execution)
                if prop and execution:
                    props.append(prop)
                    (run_dir / "properties" / f"test_{prop.id}.py").write_text(prop.code)
                    if execution.status in ("fail", "timeout"):
                        failing.append((prop, execution))
            stats["properties_proposed"] = len(props)
            stats["failures"] = len(failing)
            _jsonl(run_dir / "executions.jsonl", executions)
            (run_dir / "errors.json").write_text(json.dumps(errors, indent=2))
            _raise_budget(proposals)

            verdicts = await asyncio.gather(
                *(triage(client, router, by_id[p.target_id], p, e) for p, e in failing),
                return_exceptions=True,
            )
            _jsonl(run_dir / "triage.jsonl", [v for v in verdicts if not isinstance(v, BaseException)])
            completed_verdicts = [v for v in verdicts if not isinstance(v, BaseException)]
            real = [
                (p, e, v)
                for (p, e), v in zip(failing, verdicts)
                if not isinstance(v, BaseException) and v.verdict == "real_bug"
            ]
            stats["triaged_real"] = len(real)
            errors.extend({"stage": "triage", "error": type(v).__name__, "message": str(v)}
                          for v in verdicts if isinstance(v, BaseException))
            (run_dir / "errors.json").write_text(json.dumps(errors, indent=2))
            _raise_budget(verdicts)

            # Several properties often hit one root cause: confirm one failure per target.
            seen: set[str] = set()
            for p, e, v in real:
                if p.target_id in seen:
                    continue
                target = by_id[p.target_id]
                source_path, _ = index.lookup(target.qualname)
                file_source = (repo / source_path).read_text(errors="replace") if source_path else ""
                bug = await confirm(
                    client, router, sandbox, base_env, target, source_path, file_source, p, e, v,
                    bug_id=f"b{len(bugs) + 1}",
                )
                if bug:
                    bugs.append(bug)
                    seen.add(p.target_id)
                    bundle = run_dir / "findings" / bug.id
                    bundle.mkdir(parents=True, exist_ok=True)
                    (bundle / "repro.py").write_text(bug.repro)
                    (bundle / "discovery.py").write_text(p.code)
                    (bundle / "verification.json").write_text(json.dumps(bug.verification, indent=2))
                    if bug.patch_diff:
                        (bundle / "candidate.patch").write_text(bug.patch_diff)
        finally:
            await sandbox.close(base_env)
    except BudgetExceeded as exc:
        stopped = f"budget: {exc}"
    except Exception as exc:
        stopped = f"infrastructure: {type(exc).__name__}: {exc}"
        errors.append({"stage": "controller", "error": type(exc).__name__, "message": str(exc)})
        (run_dir / "errors.json").write_text(json.dumps(errors, indent=2))

    report = build_campaign_report(run_id, lib_info, stats, client.budget.summary(), bugs, router.summary(), stopped,
                                   targets=targets, verdicts=completed_verdicts, failures=failing)
    report["mode"] = "baseline"
    write_campaign_report(run_dir, report)
    return report


def _raise_budget(results: list) -> None:
    for r in results:
        if isinstance(r, BudgetExceeded):
            raise r
