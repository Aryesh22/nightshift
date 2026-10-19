"""Write runs/<run_id>/report.json in the shape the dashboard reads (see TEAM.md)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from nightshift.pipeline.types import Bug


def build_report(
    run_id: str,
    library: dict,
    stats: dict,
    budget_summary: dict,
    bugs: list[Bug],
    router_summary: list[dict],
    stopped_reason: str | None = None,
) -> dict:
    verified = sum(b.repro_verified for b in bugs)
    spent = budget_summary["spent_usd"]
    return {
        "run_id": run_id,
        "library": library,
        "stats": {
            **stats,
            "verified": verified,
            "cost_usd": round(spent, 4),
            "cost_per_verified_bug": round(spent / verified, 4) if verified else None,
        },
        "cost_by_model": budget_summary["by_tier"],
        "cost_by_stage": budget_summary["by_stage"],
        "routing": router_summary,
        "stopped_reason": stopped_reason,
        "bugs": [asdict(b) for b in bugs],
    }


def write_report(run_dir: Path, report: dict) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "report.json"
    path.write_text(json.dumps(report, indent=2))
    return path
