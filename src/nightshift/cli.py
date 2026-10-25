"""`nightshift run` command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from pathlib import Path

from nightshift.config import API_KEY_ENV, PROVIDER, Settings
from nightshift.llm import Budget, NemotronClient
from nightshift.pipeline.run import RunConfig, run_nightshift

# Implementations live in Jatin's workstream; see nightshift/sandbox/base.py for the contract.
SANDBOXES = {
    "docker": "nightshift.sandbox.docker:DockerSandbox",
    "nebius": "nightshift.sandbox.nebius:NebiusDockerSandbox",
}


def load_sandbox(name: str):
    module_name, _, cls_name = SANDBOXES[name].partition(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        sys.exit(f"sandbox {name!r} is not implemented yet ({SANDBOXES[name]}).")
    return getattr(module, cls_name)()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="nightshift")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="hunt for bugs in one library")
    run.add_argument("repo_url")
    run.add_argument("--package", required=True, help="import name, e.g. 'dateutil'")
    run.add_argument("--ref", default="main")
    run.add_argument("--library", default="", help="display name (defaults to the package)")
    run.add_argument("--max-targets", type=int, default=12)
    run.add_argument("--variants", type=int, default=2)
    run.add_argument("--budget", type=float, help="hard USD cap for this run")
    run.add_argument("--sandbox", choices=sorted(SANDBOXES), default="docker")
    run.add_argument("--mode", choices=("core", "baseline"), default="core")
    run.add_argument("--airgapped", action="store_true", help="disable external evidence and issue retrieval, including caches")
    run.add_argument("--online-lookup", action="store_true", help="enable bounded Tavily documentation/known-issue retrieval")
    run.add_argument("--tavily-credits", type=float, default=100, help="Tavily credit cap for this run (max 1000)")
    run.add_argument("--doc-path", action="append", help="approved documentation path inside the pinned checkout (repeatable)")
    run.add_argument("--max-examples", type=int, default=200)
    run.add_argument("--ultra-review", action="store_true", help="optional capped survivor review; never needed for a finding")
    run.add_argument("--ultra-budget", type=float, default=0.02)
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if not settings.api_key:
        sys.exit(f"{API_KEY_ENV[PROVIDER]} is not set (copy .env.example to .env).")
    budget = Budget(args.budget if args.budget is not None else settings.budget_usd)
    config = RunConfig(
        repo_url=args.repo_url,
        package=args.package,
        ref=args.ref,
        library=args.library,
        max_targets=args.max_targets,
        variants_per_target=args.variants,
        runs_dir=Path(settings.runs_dir),
        mode=args.mode,
        airgapped=args.airgapped,
        online_lookup=args.online_lookup,
        tavily_credits=args.tavily_credits,
        doc_paths=tuple(args.doc_path or ["README.md"]),
        max_examples=args.max_examples,
        ultra_review=args.ultra_review,
        ultra_budget_usd=args.ultra_budget,
    )

    async def go() -> dict:
        client = NemotronClient(settings, budget=budget)
        try:
            return await run_nightshift(config, client, load_sandbox(args.sandbox))
        finally:
            await client.aclose()

    report = asyncio.run(go())
    print(json.dumps(report["stats"], indent=2))
    if report["stopped_reason"]:
        print(f"stopped early: {report['stopped_reason']}", file=sys.stderr)


if __name__ == "__main__":
    main()
