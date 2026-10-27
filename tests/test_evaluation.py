"""Tests for the paired evaluation harness, metric calculations, and offline self-test."""

import json
from pathlib import Path

import pytest

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nightshift.eval import (
    EvalTask, EvaluationResult, SystemMetrics, compute_metrics, load_manifest, run_self_test,
)
from scripts.run_evaluation import main


def test_compute_metrics_cost_per_validated_is_none_with_zero_findings():
    task = EvalTask(
        task_id="empty-task",
        repo_url="https://example.com/repo",
        package="empty",
        known_defects=("some_bug",),
        hard_negatives=(),
    )
    report = {
        "run_id": "r1",
        "mode": "core",
        "stats": {"cost_usd": 0.50, "tavily_credits": 0.0},
        "findings": [],
    }
    metrics = compute_metrics("core", [report], [task])
    assert metrics.validated_findings == 0
    assert metrics.cost_per_validated_finding is None
    assert metrics.report_precision == 0.0
    assert metrics.known_defect_recall == 0.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.tavily_credits == 0.0
    assert metrics.total_spend_usd == 0.50


def test_compute_metrics_detects_false_positives_and_recalls():
    task = EvalTask(
        task_id="t1",
        repo_url="https://example.com/repo",
        package="pkg",
        known_defects=("planted_leak", "buffer_overflow"),
        hard_negatives=("invalid_domain_input",),
    )
    # System report finding 1 real bug and 1 hard negative incorrectly accepted
    report = {
        "run_id": "r1",
        "mode": "baseline",
        "stats": {"cost_usd": 1.20, "tavily_credits": 0.0},
        "findings": [
            {
                "id": "f1",
                "title": "planted_leak detected",
                "status": "ai_reviewed",
                "expected": "memory does not leak",
                "repro": "leak_test()",
            },
            {
                "id": "f2",
                "title": "invalid_domain_input crashes",
                "status": "ai_reviewed",
                "expected": "graceful handling",
                "repro": "call_invalid()",
            },
        ],
        "campaigns": [{"reach_rate": 0.60}, {"reach_rate": 0.80}],
    }
    metrics = compute_metrics("baseline", [report], [task])
    assert metrics.total_findings == 2
    assert metrics.validated_findings == 1  # only planted_leak, since invalid_domain_input was a hard negative
    assert metrics.report_precision == 0.5  # 1 / 2
    assert metrics.known_defect_recall == 0.5  # 1 / 2 known defects exposed
    assert metrics.false_positive_rate == 1.0  # 1 / 1 hard negatives incorrectly retained
    assert metrics.cost_per_validated_finding == 1.20
    assert metrics.valid_input_rate == 0.70  # average reach_rate (0.6 + 0.8) / 2


def test_self_test_runs_deterministically_offline(tmp_path):
    result = run_self_test(out_dir=tmp_path)
    assert isinstance(result, EvaluationResult)
    assert result.manifest_name == "toycodec-offline-selftest"
    assert result.task_ids == ["toycodec-selftest"]

    # Core must outperform Baseline on precision, recall, and false positive rate
    assert result.core.report_precision == 1.0
    assert result.baseline.report_precision == 0.5
    assert result.core.known_defect_recall == 1.0
    assert result.baseline.known_defect_recall == 0.5
    assert result.core.false_positive_rate == 0.0
    assert result.baseline.false_positive_rate == 1.0

    # Tavily credits must be 0 in airgapped evaluation
    assert result.core.tavily_credits == 0.0
    assert result.baseline.tavily_credits == 0.0

    # Cost per validated finding is lower for core
    assert result.core.cost_per_validated_finding == 0.05
    assert result.baseline.cost_per_validated_finding == 0.15

    # Check written outputs
    json_path = tmp_path / "evaluation_report.json"
    md_path = tmp_path / "evaluation_report.md"
    assert json_path.exists()
    assert md_path.exists()

    d = json.loads(json_path.read_text())
    assert d["manifest_name"] == "toycodec-offline-selftest"
    assert "baseline" in d and "core" in d and "comparison" in d
    assert d["comparison"]["precision_delta"] == 0.5
    assert d["comparison"]["recall_delta"] == 0.5
    assert d["comparison"]["fpr_delta"] == -1.0

    md = md_path.read_text()
    assert "# Paired Evaluation Summary: toycodec-offline-selftest" in md
    assert "Report precision" in md
    assert "Known-defect recall" in md
    assert "False-positive rate" in md
    assert "Cost per validated finding" in md
    assert "Airgapped mode verified: 0 external Tavily credits consumed" in md


def test_load_manifest_parses_json(tmp_path):
    manifest_data = {
        "manifest": "pbt-bench-subset",
        "tasks": [
            {
                "task_id": "task-01",
                "repo_url": "https://github.com/example/lib",
                "package": "lib",
                "ref": "v1.0",
                "known_defects": ["bug_a", "bug_b"],
                "hard_negatives": ["false_alarm_1"],
                "budget_usd": 2.5,
            }
        ]
    }
    manifest_file = tmp_path / "tasks.json"
    manifest_file.write_text(json.dumps(manifest_data))

    tasks = load_manifest(manifest_file)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.task_id == "task-01"
    assert t.repo_url == "https://github.com/example/lib"
    assert t.package == "lib"
    assert t.ref == "v1.0"
    assert t.known_defects == ("bug_a", "bug_b")
    assert t.hard_negatives == ("false_alarm_1",)
    assert t.budget_usd == 2.5


def test_run_evaluation_cli_self_test(tmp_path):
    out_json = tmp_path / "sub" / "eval.json"
    out_md = tmp_path / "sub" / "eval.md"

    code = main([
        "--self-test",
        "--output-json", str(out_json),
        "--output-md", str(out_md),
    ])
    assert code == 0
    assert out_json.exists()
    assert out_md.exists()

    data = json.loads(out_json.read_text())
    assert data["manifest_name"] == "toycodec-offline-selftest"
    assert data["core"]["report_precision"] == 1.0
    assert data["baseline"]["report_precision"] == 0.5
