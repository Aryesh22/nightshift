import json
from pathlib import Path

from nightshift.report import Report

SAMPLE = Path(__file__).parents[1] / "samples" / "report.json"


def test_sample_report_matches_contract():
    d = json.loads(SAMPLE.read_text())
    report = Report.from_dict(d)
    assert report.to_dict() == d


def test_write_puts_report_under_run_id(tmp_path):
    report = Report.load(SAMPLE)
    path = report.write(tmp_path)
    assert path == tmp_path / report.run_id / "report.json"
    assert Report.load(path).to_dict() == report.to_dict()


def test_cost_per_verified_bug_handles_zero():
    report = Report.load(SAMPLE)
    report.stats.verified = 0
    assert report.to_dict()["stats"]["cost_per_verified_bug"] is None
