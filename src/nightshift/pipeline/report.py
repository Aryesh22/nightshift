"""Compatibility imports; campaign reports now use the shared v1 schema."""

from nightshift.report import build_campaign_report as build_report
from nightshift.report import write_campaign_report as write_report

__all__ = ["build_report", "write_report"]
