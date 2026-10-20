import json
from pathlib import Path

from nightshift.report import SCHEMA_VERSION, Report

SAMPLE = Path(__file__).parents[1] / "samples" / "report.json"


def test_sample_report_matches_contract():
    d = json.loads(SAMPLE.read_text())
    assert d["schema_version"] == SCHEMA_VERSION
    assert Report.from_dict(d).to_dict() == d


def test_sample_covers_statuses_the_dashboard_must_render():
    statuses = {f.status for f in Report.load(SAMPLE).findings}
    assert {"human_validated", "ai_reviewed", "unresolved", "rejected"} <= statuses


def test_write_puts_report_under_run_id(tmp_path):
    report = Report.load(SAMPLE)
    path = report.write(tmp_path)
    assert path == tmp_path / report.run_id / "report.json"
    assert Report.load(path).to_dict() == report.to_dict()


def test_cost_per_validated_finding_is_undefined_without_validated_findings():
    report = Report.load(SAMPLE)
    assert report.cost_per_validated_finding == report.stats.cost_usd  # exactly one validated
    report.findings = [f for f in report.findings if f.status != "human_validated"]
    assert report.to_dict()["cost_per_validated_finding"] is None
