"""Classify one campaign run. Infrastructure problems, vacuous tests and real contract
failures are different outcomes and must never be counted together as bugs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nightshift.contracts.render import parse_stats
from nightshift.sandbox.base import RunResult

Kind = Literal["passed", "violation", "exception", "vacuous", "setup_error", "timeout", "infra_error"]

# Initial warning level from the research plan; calibrate on development tasks.
LOW_REACH_RATE = 0.2
MIN_SAMPLE_FOR_REACH = 20


@dataclass(frozen=True)
class CampaignOutcome:
    kind: Kind
    reason: str
    stats: dict | None
    reach_rate: float | None = None
    low_reach: bool = False

    @property
    def is_candidate(self) -> bool:
        """A contract failure worth shrinking, replaying and investigating."""
        return self.kind in ("violation", "exception")


def classify(result: RunResult) -> CampaignOutcome:
    if result.timed_out:
        return CampaignOutcome("timeout", "worker hit its time limit", parse_stats(result.stdout))
    stats = parse_stats(result.stdout)
    if stats is None:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        return CampaignOutcome("infra_error", "no stats line: " + " | ".join(tail), None)
    if stats["entered"] == 0:
        return CampaignOutcome("setup_error", "no generated input entered the property", stats)

    reach = stats["assertion_reached"] / stats["entered"]
    low = stats["entered"] >= MIN_SAMPLE_FOR_REACH and reach < LOW_REACH_RATE
    uncalled = [api for api, n in stats["api_calls"].items() if n == 0]

    failure = stats.get("last_failure")
    if failure and result.exit_code != 0:
        # A real failure on the first input is meaningful even with a tiny sample.
        reason = failure.get("error") or f"actual={failure.get('actual')} expected={failure.get('expected')}"
        return CampaignOutcome(failure["kind"], f"input={failure['input']}: {reason}", stats, reach, low)
    if stats["assertion_reached"] == 0:
        return CampaignOutcome("vacuous", "no input reached the assertion", stats, reach, low)
    if result.exit_code != 0:
        return CampaignOutcome("setup_error", "test errored outside the property body", stats, reach, low)
    if uncalled:
        return CampaignOutcome("vacuous", f"adapter never called {uncalled}", stats, reach, low)
    return CampaignOutcome("passed", f"{stats['assertion_reached']} checks passed", stats, reach, low)
