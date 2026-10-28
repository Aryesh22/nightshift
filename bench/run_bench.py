#!/usr/bin/env python3
"""PBT-Bench Automated Benchmark Runner (Nightshift Core vs. Baseline).

Interleaves execution across 10 matched tasks under a strict $10.00 total budget cap.
Logs full stdout/stderr, report.json, wall-time, and evaluator verdicts into bench/results.jsonl.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BENCH_DIR = Path(__file__).parent
CONFIG_PATH = BENCH_DIR / "config.json"
RESULTS_DIR = BENCH_DIR / "results"
RESULTS_JSONL = BENCH_DIR / "results.jsonl"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config at {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text())


def get_cumulative_spend() -> float:
    if not RESULTS_JSONL.exists():
        return 0.0
    total = 0.0
    for line in RESULTS_JSONL.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            total += row.get("cost_confirmed", 0.0) + row.get("cost_pending", 0.0)
    return total


def run_campaign(task: dict, mode: str, config: dict, is_rerun: bool = False) -> dict:
    task_id = task["task_id"]
    level = task["level"]
    package = task["package"]
    target_dir = RESULTS_DIR / f"{task_id}_{mode}"
    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "nightshift.cli", "run",
        task["repo"],
        "--package", package,
        "--mode", mode,
        "--airgapped",
        "--budget", str(config["budget"]["per_run_cap_usd"]),
    ]

    start_time = time.time()
    status = "completed"
    failure_reason = None
    cost_confirmed = 0.0
    cost_pending = 0.0
    findings_total = 0
    findings_rejected = 0
    findings_unresolved = 0
    evaluator_detected = False

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config["runtime"]["timeout_seconds"],
        )
        wall_seconds = round(time.time() - start_time, 2)
        (target_dir / "stdout.log").write_text(proc.stdout)
        (target_dir / "stderr.log").write_text(proc.stderr)

        if proc.returncode != 0:
            status = "failed"
            failure_reason = f"Process exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        wall_seconds = round(time.time() - start_time, 2)
        status = "timeout"
        failure_reason = f"Timeout exceeded ({config['runtime']['timeout_seconds']}s)"
    except Exception as e:
        wall_seconds = round(time.time() - start_time, 2)
        status = "failed"
        failure_reason = str(e)

    # Check generated report.json if present
    run_report_path = Path("runs") / task_id / "report.json"
    if run_report_path.exists():
        try:
            report_data = json.loads(run_report_path.read_text())
            (target_dir / "report.json").write_text(json.dumps(report_data, indent=2))
            cost_confirmed = report_data.get("stats", {}).get("cost_usd", 0.0)
            cost_pending = report_data.get("stats", {}).get("pending_cost_usd", 0.0)
            findings = report_data.get("findings", [])
            findings_total = len(findings)
            findings_rejected = sum(1 for f in findings if f.get("status") == "rejected")
            findings_unresolved = sum(1 for f in findings if f.get("status") == "unresolved")
            # If any finding survived to ai_reviewed or human_validated, check evaluator
            evaluator_detected = any(f.get("status") in ("ai_reviewed", "human_validated") for f in findings)
        except Exception as e:
            print(f"Warning parsing report for {task_id}_{mode}: {e}")

    result_row = {
        "task_id": task_id,
        "level": level,
        "mode": mode,
        "is_rerun": is_rerun,
        "status": status,
        "failure_reason": failure_reason,
        "cost_confirmed": cost_confirmed,
        "cost_pending": cost_pending,
        "wall_seconds": wall_seconds,
        "findings_total": findings_total,
        "findings_rejected": findings_rejected,
        "findings_unresolved": findings_unresolved,
        "evaluator_detected": evaluator_detected,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with open(RESULTS_JSONL, "a") as f:
        f.write(json.dumps(result_row) + "\n")

    return result_row


def main():
    config = load_config()
    stop_threshold = config["budget"]["stop_threshold_usd"]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("🌙 Nightshift PBT-Bench 20-Campaign Benchmark Runner")
    print(f"Tasks: {len(config['tasks'])} | Total Cap: ${config['budget']['total_cap_usd']:.2f}")
    print(f"Budget Stop Limit: ${stop_threshold:.2f}")
    print("==================================================\n")

    for idx, task in enumerate(config["tasks"]):
        # Interleave execution variant order
        modes = ["baseline", "core"] if idx % 2 == 0 else ["core", "baseline"]

        for mode in modes:
            spent = get_cumulative_spend()
            print(f"Current Cumulative Spend: ${spent:.4f}")

            if spent >= stop_threshold:
                print(f"🚨 BUDGET LIMIT REACHED (${spent:.2f} >= ${stop_threshold:.2f}). Skipping remaining.")
                with open(RESULTS_JSONL, "a") as f:
                    f.write(json.dumps({
                        "task_id": task["task_id"],
                        "level": task["level"],
                        "mode": mode,
                        "status": "not_run",
                        "failure_reason": "Budget limit reached ($9.00 ceiling)",
                    }) + "\n")
                continue

            print(f"▶️ Running {task['task_id']} ({task['level']}) in [{mode}] mode...")
            row = run_campaign(task, mode, config)
            print(f"  Result: {row['status']} | Detected: {row['evaluator_detected']} | Cost: ${row['cost_confirmed']:.4f} | Time: {row['wall_seconds']}s")

    print("\n✅ Benchmark execution complete! Output saved in bench/results.jsonl")


if __name__ == "__main__":
    main()

