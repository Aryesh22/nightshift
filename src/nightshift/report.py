"""The report.json contract: the single file the dashboard reads (runs/<run_id>/report.json).

Schema v1 (research plan, Oct 20). Add fields freely; renaming or removing one breaks the
dashboard, so tell Ruchir first and regenerate samples/report.json in the same PR.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = 1

FindingStatus = Literal[
    "raw_anomaly", "reproducible", "ai_reviewed", "human_validated", "maintainer_confirmed",
    "unresolved", "rejected",
]
VALIDATED = ("human_validated", "maintainer_confirmed")


@dataclass
class RouteStep:
    stage: str  # contract | strategy | investigate | known_behaviour | review | patch
    model: str  # lightning | super | ultra
    thinking: int | None
    cost_usd: float
    cached: bool = False
    escalation_reason: str | None = None


@dataclass
class EvidenceRef:
    source: str  # URL or path
    excerpt: str
    retrieved: str = ""  # "live <time>" | "cache <time>" | "manual"


@dataclass
class ContractRef:
    contract_id: str
    version: int
    hash: str
    family: str  # roundtrip | equivalent | composition | state
    claim: str
    status: str  # explicit | inferred | ambiguous
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass
class Check:
    """One experiment that tried to disprove the finding."""
    question: str  # e.g. "Is the input inside the documented domain?"
    tool: str  # run_control_input | inspect_doc_and_source | check_boundary_neighborhood | ...
    result: str
    effect: str  # supports | refutes | neutral


@dataclass
class KnownBehaviour:
    outcome: str  # exact_existing_issue | documented_intended | related_issue | no_match_found | lookup_unavailable
    links: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Finding:
    id: str
    title: str
    status: FindingStatus
    contract: ContractRef
    repro: str  # reduced repro script, not claimed minimal
    actual: str
    expected: str
    traceback: str = ""
    control: str = ""  # nearby valid input that behaves correctly
    replays_passed: int = 0  # fresh-process replays that reproduced the failure
    replays_attempted: int = 0
    checks: list[Check] = field(default_factory=list)
    known_behaviour: KnownBehaviour | None = None
    uncertainty: str = ""
    rejection_reason: str | None = None
    root_cause: str | None = None  # only from a review stage, with citations
    patch_diff: str | None = None
    patch_validation: str | None = None  # what the patch was tested against
    cost_usd: float = 0.0
    route_trace: list[RouteStep] = field(default_factory=list)


@dataclass
class Library:
    name: str
    version: str
    repo: str | None = None


@dataclass
class Stats:
    contracts: int = 0
    campaigns: int = 0
    infra_failures: int = 0  # timeouts, setup errors, vacuous tests: never counted as bugs
    cost_usd: float = 0.0
    tavily_credits: float = 0.0
    human_review_minutes: float = 0.0


@dataclass
class Report:
    run_id: str
    library: Library
    stats: Stats = field(default_factory=Stats)
    cost_by_model: dict[str, float] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.status] = counts.get(f.status, 0) + 1
        return counts

    @property
    def cost_per_validated_finding(self) -> float | None:
        """Undefined (None) with zero validated findings; never a misleading finite number."""
        n = sum(f.status in VALIDATED for f in self.findings)
        return round(self.stats.cost_usd / n, 4) if n else None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema_version"] = SCHEMA_VERSION
        d["status_counts"] = self.status_counts()
        d["cost_per_validated_finding"] = self.cost_per_validated_finding
        return d

    def write(self, runs_dir: Path | str = "runs") -> Path:
        path = Path(runs_dir) / self.run_id / "report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    @classmethod
    def from_dict(cls, d: dict) -> Report:
        return cls(
            run_id=d["run_id"],
            library=Library(**d["library"]),
            stats=Stats(**d.get("stats", {})),
            cost_by_model=d.get("cost_by_model", {}),
            findings=[_finding(f) for f in d.get("findings", [])],
        )

    @classmethod
    def load(cls, path: Path | str) -> Report:
        return cls.from_dict(json.loads(Path(path).read_text()))


def _finding(f: dict) -> Finding:
    c = f["contract"]
    kb = f.get("known_behaviour")
    return Finding(**{
        **f,
        "contract": ContractRef(**{**c, "evidence": [EvidenceRef(**e) for e in c.get("evidence", [])]}),
        "checks": [Check(**x) for x in f.get("checks", [])],
        "known_behaviour": KnownBehaviour(**kb) if kb else None,
        "route_trace": [RouteStep(**s) for s in f.get("route_trace", [])],
    })
