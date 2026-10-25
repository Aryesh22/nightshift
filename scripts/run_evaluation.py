"""CLI entry point for the paired evaluation harness (Section 16.2 & 16.4).

Usage:
  # Deterministic offline self-test (0 API spend, runs in milliseconds):
  python scripts/run_evaluation.py --self-test

  # Full paired benchmark evaluation across a task manifest:
  python scripts/run_evaluation.py --manifest tasks.json --sandbox docker --output-md summary.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from nightshift.config import API_KEY_ENV, PROVIDER, Settings
from nightshift.eval import EvaluationResult, load_manifest, run_paired_evaluation, run_self_test
from nightshift.llm import Budget, NemotronClient


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_evaluation.py",
        description="Run paired Baseline vs. Nightshift Core evaluation under matched budgets and air-gapped Tavily.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run offline self-test against local toycodec fixtures with 0 API spend",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="path to task manifest JSON file",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="runs/evaluation/evaluation_report.json",
        help="path to write JSON results (default: runs/evaluation/evaluation_report.json)",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default="runs/evaluation/evaluation_report.md",
        help="path to write Markdown summary table (default: runs/evaluation/evaluation_report.md)",
    )
    parser.add_argument(
        "--sandbox",
        choices=("docker", "nebius", "local"),
        default="docker",
        help="sandbox execution environment (default: docker)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="total evaluation USD budget limit",
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default="runs/evaluation",
        help="directory for evaluation runs and task reports",
    )
    return parser.parse_args(argv)


def get_sandbox(name: str):
    if name == "local":
        from nightshift.sandbox.local import UnsafeLocalSandbox
        return UnsafeLocalSandbox()
    elif name == "docker":
        from nightshift.sandbox.docker import DockerSandbox
        return DockerSandbox()
    elif name == "nebius":
        from nightshift.sandbox.nebius import NebiusDockerSandbox
        return NebiusDockerSandbox()
    raise ValueError(f"unsupported sandbox: {name}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    if args.self_test or not args.manifest:
        if not args.self_test and not args.manifest:
            print("No manifest specified. Running in offline --self-test mode...\n", file=sys.stderr)
        result: EvaluationResult = run_self_test(out_dir=out_json.parent)
        # Ensure requested output filenames are written
        out_json.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
        out_md.write_text(result.to_markdown())
        print(result.to_markdown())
        print(f"Results written to:\n  JSON: {out_json}\n  Markdown: {out_md}")
        return 0

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        sys.exit(f"Manifest file not found: {manifest_path}")

    tasks = load_manifest(manifest_path)
    if not tasks:
        sys.exit(f"No tasks found in manifest: {manifest_path}")

    settings = Settings.from_env()
    if not settings.api_key:
        sys.exit(f"{API_KEY_ENV[PROVIDER]} is not set (copy .env.example to .env).")

    total_budget_usd = args.budget if args.budget is not None else settings.budget_usd
    budget = Budget(total_budget_usd)
    client = NemotronClient(settings, budget=budget)
    sandbox = get_sandbox(args.sandbox)

    async def go() -> EvaluationResult:
        try:
            return await run_paired_evaluation(
                tasks,
                client,
                sandbox,
                runs_dir=args.runs_dir,
                manifest_name=manifest_path.stem,
            )
        finally:
            await client.aclose()

    result = asyncio.run(go())
    out_json.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
    out_md.write_text(result.to_markdown())
    print(result.to_markdown())
    print(f"Results written to:\n  JSON: {out_json}\n  Markdown: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
