"""The report.json contract: the single file the dashboard reads (runs/<run_id>/report.json).

Shape v0 from TEAM.md. Add fields freely; renaming or removing one breaks the dashboard,
so tell Ruchir first and update samples/report.json in the same PR.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA_VERSION = 0


@dataclass
class RouteStep:
    stage: str  # read | propose | triage | confirm | dedupe
    model: str  # lightning | super | ultra
    thinking: int | None
    cost_usd: float
    cached: bool = False


@dataclass
class Bug:
    id: str
    title: str
    severity: str  # low | medium | high
    property: str  # roundtrip | invariant | metamorphic | oracle | crash
    repro: str
    traceback: str
    root_cause: str
    patch_diff: str
    patch_verified: bool
    duplicate_of: str | None = None  # URL of an existing GitHub issue
    route_trace: list[RouteStep] = field(default_factory=list)


@dataclass
class Library:
    name: str
    version: str
    repo: str | None = None


@dataclass
class Stats:
    properties_proposed: int = 0
    failures: int = 0
    triaged_real: int = 0
    verified: int = 0
    cost_usd: float = 0.0

    @property
    def cost_per_verified_bug(self) -> float | None:
        return round(self.cost_usd / self.verified, 4) if self.verified else None


@dataclass
class Report:
    run_id: str
    library: Library
    stats: Stats = field(default_factory=Stats)
    cost_by_model: dict[str, float] = field(default_factory=dict)
    bugs: list[Bug] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema_version"] = SCHEMA_VERSION
        d["stats"]["cost_per_verified_bug"] = self.stats.cost_per_verified_bug
        return d

    def write(self, runs_dir: Path | str = "runs") -> Path:
        path = Path(runs_dir) / self.run_id / "report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    @classmethod
    def from_dict(cls, d: dict) -> Report:
        stats = {k: v for k, v in d.get("stats", {}).items() if k != "cost_per_verified_bug"}
        return cls(
            run_id=d["run_id"],
            library=Library(**d["library"]),
            stats=Stats(**stats),
            cost_by_model=d.get("cost_by_model", {}),
            bugs=[
                Bug(**{**b, "route_trace": [RouteStep(**s) for s in b.get("route_trace", [])]})
                for b in d.get("bugs", [])
            ],
        )

    @classmethod
    def load(cls, path: Path | str) -> Report:
        return cls.from_dict(json.loads(Path(path).read_text()))
