"""Orchestrate one Nightshift run: read -> propose+run -> triage -> confirm -> report."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from nightshift.llm import BudgetExceeded, NemotronClient
from nightshift.pipeline.confirm import confirm
from nightshift.pipeline.propose import propose_and_run
from nightshift.pipeline.read import clone, extract_targets
from nightshift.pipeline.report import build_report, write_report
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


def _jsonl(path: Path, rows: list) -> None:
    path.write_text("".join(json.dumps(asdict(r)) + "\n" for r in rows))


async def run_nightshift(config: RunConfig, client: NemotronClient, sandbox: SandboxExecutor, router: Router | None = None) -> dict:
    router = router or Router()
    library = config.library or config.package
    run_id = f"{datetime.now(timezone.utc):%Y-%m-%d-%H%M}-{library}"
    run_dir = config.runs_dir / run_id
    (run_dir / "properties").mkdir(parents=True, exist_ok=True)

    stats = {"targets": 0, "properties_proposed": 0, "failures": 0, "triaged_real": 0}
    bugs: list[Bug] = []
    stopped: str | None = None
    lib_info = {"name": library, "repo": config.repo_url, "ref": config.ref}

    try:
        repo = await clone(config.repo_url, config.ref, config.runs_dir / "_src" / f"{library}-{config.ref}")
        targets, index, _ = await extract_targets(client, router, repo, config.package, library, config.max_targets)
        stats["targets"] = len(targets)
        (run_dir / "targets.json").write_text(json.dumps([asdict(t) for t in targets], indent=2))

        base_env = await sandbox.prepare(config.repo_url, config.ref, list(config.setup_cmds))
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
            _raise_budget(proposals)
            props: list[PropertyTest] = []
            failing: list[tuple[PropertyTest, Execution]] = []
            executions: list[Execution] = []
            for item in proposals:
                if isinstance(item, BaseException):
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

            verdicts = await asyncio.gather(
                *(triage(client, router, by_id[p.target_id], p, e) for p, e in failing),
                return_exceptions=True,
            )
            _raise_budget(verdicts)
            _jsonl(run_dir / "triage.jsonl", [v for v in verdicts if not isinstance(v, BaseException)])
            real = [
                (p, e, v)
                for (p, e), v in zip(failing, verdicts)
                if not isinstance(v, BaseException) and v.verdict == "real_bug"
            ]
            stats["triaged_real"] = len(real)

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
        finally:
            await sandbox.close(base_env)
    except BudgetExceeded as exc:
        stopped = f"budget: {exc}"

    report = build_report(run_id, lib_info, stats, client.budget.summary(), bugs, router.summary(), stopped)
    write_report(run_dir, report)
    return report


def _raise_budget(results: list) -> None:
    for r in results:
        if isinstance(r, BudgetExceeded):
            raise r
