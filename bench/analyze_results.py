#!/usr/bin/env python3
"""PBT-Bench Results Aggregator & Dashboard Exporter.

Reads bench/results.jsonl and bench/config.json, calculates denominators,
and compiles the final structured JSON for dashboard/data/benchmark/results.json.
"""

from __future__ import annotations

import json
from pathlib import Path

BENCH_DIR = Path(__file__).parent
CONFIG_PATH = BENCH_DIR / "config.json"
RESULTS_JSONL = BENCH_DIR / "results.jsonl"
OUTPUT_JSON = Path("dashboard") / "data" / "benchmark" / "results.json"


def analyze():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config at {CONFIG_PATH}")
    config = json.loads(CONFIG_PATH.read_text())

    if not RESULTS_JSONL.exists():
        print(f"No results.jsonl found at {RESULTS_JSONL}. Nothing to analyze.")
        return

    rows = [json.loads(line) for line in RESULTS_JSONL.read_text().splitlines() if line.strip()]

    # Map by task_id and mode
    task_map: dict[str, dict[str, dict]] = {}
    for r in rows:
        tid = r["task_id"]
        mode = r["mode"]
        if tid not in task_map:
            task_map[tid] = {}
        task_map[tid][mode] = r

    tasks_output = []
    baseline_detected = 0
    core_detected = 0
    baseline_cost = 0.0
    core_cost = 0.0
    baseline_failures = 0
    core_failures = 0
    baseline_time = 0.0
    core_time = 0.0

    for task_info in config["tasks"]:
        tid = task_info["task_id"]
        level = task_info["level"]
        t_results = task_map.get(tid, {})

        b = t_results.get("baseline", {
            "status": "not_run",
            "evaluator_detected": False,
            "findings_total": 0,
            "cost_confirmed": 0.0,
            "wall_seconds": 0.0,
        })
        c = t_results.get("core", {
            "status": "not_run",
            "evaluator_detected": False,
            "findings_total": 0,
            "findings_rejected": 0,
            "findings_unresolved": 0,
            "cost_confirmed": 0.0,
            "wall_seconds": 0.0,
        })

        if b.get("evaluator_detected"):
            baseline_detected += 1
        if c.get("evaluator_detected"):
            core_detected += 1

        baseline_cost += b.get("cost_confirmed", 0.0)
        core_cost += c.get("cost_confirmed", 0.0)

        if b.get("status") in ("failed", "timeout", "not_run"):
            baseline_failures += 1
        if c.get("status") in ("failed", "timeout", "not_run"):
            core_failures += 1

        baseline_time += b.get("wall_seconds", 0.0)
        core_time += c.get("wall_seconds", 0.0)

        tasks_output.append({
            "taskId": tid,
            "level": level,
            "baseline": {
                "status": b.get("status", "completed"),
                "evaluatorDetected": b.get("evaluator_detected", False),
                "findingsTotal": b.get("findings_total", 0),
                "costUsd": b.get("cost_confirmed", 0.0),
                "wallSeconds": b.get("wall_seconds", 0.0),
                "failureReason": b.get("failure_reason"),
            },
            "nightshiftCore": {
                "status": c.get("status", "completed"),
                "evaluatorDetected": c.get("evaluator_detected", False),
                "findingsTotal": c.get("findings_total", 0),
                "findingsRejected": c.get("findings_rejected", 0),
                "findingsUnresolved": c.get("findings_unresolved", 0),
                "costUsd": c.get("cost_confirmed", 0.0),
                "wallSeconds": c.get("wall_seconds", 0.0),
                "failureReason": c.get("failure_reason"),
            },
        })

    n_tasks = len(config["tasks"])
    final_output = {
        "config": {
            "commitSha": config.get("git_commit", "unknown"),
            "totalRuns": len(rows),
            "budgetCapTotal": config["budget"]["total_cap_usd"],
            "perRunBudgetCap": config["budget"]["per_run_cap_usd"],
            "models": {
                "lightning": config["models"]["lightning"],
                "super": config["models"]["super"],
                "ultra": "disabled (ultra-review off)",
            },
            "selectionRulesSeed": config.get("seed", 42),
            "frozenDate": config.get("frozen_at", "2026-10-27T22:30:00Z"),
            "asymmetryNote": config.get("methodology_asymmetry_disclosure", ""),
        },
        "summary": {
            "baselineDetectedRatio": f"{baseline_detected}/{n_tasks}",
            "coreDetectedRatio": f"{core_detected}/{n_tasks}",
            "baselineTotalCost": round(baseline_cost, 2),
            "coreTotalCost": round(core_cost, 2),
            "baselineFailures": baseline_failures,
            "coreFailures": core_failures,
            "meanTimeBaselineSec": round(baseline_time / n_tasks, 1) if n_tasks else 0,
            "meanTimeCoreSec": round(core_time / n_tasks, 1) if n_tasks else 0,
        },
        "tasks": tasks_output,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(final_output, indent=2) + "\n")
    print(f"✅ Exported benchmark analysis to {OUTPUT_JSON}")
    print(f"Summary: Core {baseline_detected}/{n_tasks} vs Baseline {core_detected}/{n_tasks} | Cost: ${core_cost:.2f} vs ${baseline_cost:.2f}")


if __name__ == "__main__":
    analyze()

