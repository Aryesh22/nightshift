"""`nightshift run` command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from pathlib import Path

from nightshift.config import Settings
from nightshift.llm import Budget, NemotronClient
from nightshift.pipeline.run import RunConfig, run_nightshift

# Implementations live in Jatin's workstream; see nightshift/sandbox/base.py for the contract.
SANDBOXES = {
    "docker": "nightshift.sandbox.docker:DockerSandbox",
    "nebius": "nightshift.sandbox.nebius:NebiusContreeSandbox",
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
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if not settings.api_key:
        sys.exit("NEBIUS_API_KEY is not set (copy .env.example to .env).")
    budget = Budget(args.budget if args.budget is not None else settings.budget_usd)
    config = RunConfig(
        repo_url=args.repo_url,
        package=args.package,
        ref=args.ref,
        library=args.library,
        max_targets=args.max_targets,
        variants_per_target=args.variants,
        runs_dir=Path(settings.runs_dir),
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
