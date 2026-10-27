"""The report.json contract: the single file the dashboard reads (runs/<run_id>/report.json).

Schema v1 (research plan, Oct 20). Add fields freely; renaming or removing one breaks the
dashboard, so tell Ruchir first and regenerate samples/report.json in the same PR.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
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
    content_hash: str = ""


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
    mode: str | None = None
    retrieval_receipts: list[dict] = field(default_factory=list)
    retrieval_failures: list[dict] = field(default_factory=list)
    contracts: list[dict] = field(default_factory=list)
    _extra: dict = field(default_factory=dict)
    _include_fields: set[str] = field(default_factory=set)

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
        d.pop("_extra", None)
        d.pop("_include_fields", None)
        d["schema_version"] = SCHEMA_VERSION
        d["status_counts"] = self.status_counts()
        d["cost_per_validated_finding"] = self.cost_per_validated_finding
        if self.mode is not None and ("mode" in self._include_fields or self.mode != "core"):
            d["mode"] = self.mode
        elif "mode" not in self._include_fields:
            d.pop("mode", None)
        if not self.retrieval_receipts and "retrieval_receipts" not in self._include_fields:
            d.pop("retrieval_receipts", None)
        if not self.retrieval_failures and "retrieval_failures" not in self._include_fields:
            d.pop("retrieval_failures", None)
        if not self.contracts and "contracts" not in self._include_fields:
            d.pop("contracts", None)
        d.update(self._extra)
        return d

    def write(self, runs_dir: Path | str = "runs") -> Path:
        path = Path(runs_dir) / self.run_id / "report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    @classmethod
    def from_dict(cls, d: dict) -> Report:
        if d.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("report must use schema v1")
        known = {
            "run_id", "library", "stats", "cost_by_model", "findings",
            "mode", "retrieval_receipts", "retrieval_failures", "contracts",
            "schema_version", "status_counts", "cost_per_validated_finding",
        }
        extra = {k: v for k, v in d.items() if k not in known}
        include = {k for k in ("mode", "retrieval_receipts", "retrieval_failures", "contracts") if k in d}
        return cls(
            run_id=d["run_id"],
            library=Library(**d["library"]),
            stats=Stats(**{k: v for k, v in d.get("stats", {}).items()
                           if k in {f.name for f in fields(Stats)}}),
            cost_by_model=d.get("cost_by_model", {}),
            findings=[_finding(f) for f in d.get("findings", [])],
            mode=d.get("mode"),
            retrieval_receipts=d.get("retrieval_receipts", []),
            retrieval_failures=d.get("retrieval_failures", []),
            contracts=d.get("contracts", []),
            _extra=extra,
            _include_fields=include,
        )

    @classmethod
    def load(cls, path: Path | str) -> Report:
        return cls.from_dict(json.loads(Path(path).read_text()))


def build_campaign_report(run_id, library, stats, budget_summary, bugs, router_summary,
                          stopped_reason=None, *, targets=(), verdicts=(), failures=()):
    """Canonical v1 producer, with deprecated v0 views for existing callers.

    Repro verification is never human validation. Source-informed legacy claims
    remain explicitly inferred; these records do not pretend to be docs-only contracts.
    """
    from nightshift.contracts.model import sha256_text

    by_id = {t.id: t for t in targets}
    by_name = {t.qualname: t for t in targets}
    findings = []
    accepted = {b.target for b in bugs}
    for bug in bugs:
        target = by_name.get(bug.target)
        claim = target.claim if target else bug.property
        contract = ContractRef(
            contract_id=f"legacy.{target.id if target else bug.target}", version=1,
            hash=sha256_text(claim), family=bug.property, claim=claim, status="inferred",
            evidence=[EvidenceRef("repository documentation/source", target.evidence, "manual", sha256_text(target.evidence))]
                     if target and target.evidence else [],
        )
        validation = getattr(bug, "verification", {})
        receipts = validation.get("replays", [])
        findings.append(Finding(
            id=bug.id, title=bug.title, status="ai_reviewed" if bug.repro_verified else "unresolved",
            contract=contract, repro=bug.repro, actual=bug.traceback, expected=claim,
            traceback=bug.traceback, root_cause=bug.root_cause, patch_diff=bug.patch_diff or None,
            patch_validation=validation.get("patch_scope", "patch not validated"),
            replays_passed=sum(r.get("matched", False) for r in receipts), replays_attempted=len(receipts),
            uncertainty="Legacy source-informed claim; no human validation or docs-only contract approval.",
            route_trace=[RouteStep(s.stage, s.model, s.thinking, s.cost_usd) for s in bug.route_trace],
        ))
    judged = {v.property_id: v for v in verdicts}
    for prop, execution in failures:
        target = by_id.get(prop.target_id)
        if target and target.qualname in accepted:
            continue
        verdict = judged.get(prop.id)
        rejected = verdict is not None and verdict.verdict == "bad_test"
        reason = verdict.reason if verdict else stopped_reason or "investigation incomplete"
        findings.append(Finding(
            id=f"candidate.{prop.id}", title=f"Unconfirmed anomaly: {target.qualname if target else prop.target_id}",
            status="rejected" if rejected else "unresolved",
            contract=ContractRef(f"legacy.{prop.target_id}", 1, sha256_text(target.claim if target else ""),
                                 target.kind if target else "invariant", target.claim if target else "", "inferred"),
            repro=prop.code, actual=execution.output, expected=target.claim if target else "",
            uncertainty=reason, rejection_reason=reason if rejected else None,
        ))
    report = Report(
        run_id, Library(library["name"], library.get("version", library.get("ref", "unknown")), library.get("repo")),
        Stats(contracts=stats.get("targets", 0), campaigns=stats.get("properties_proposed", 0),
              infra_failures=stats.get("infra_failures", 0), cost_usd=budget_summary["spent_usd"]),
        cost_by_model=budget_summary["by_tier"], findings=findings,
    ).to_dict()
    verified = sum(b.repro_verified for b in bugs)
    spent = budget_summary["spent_usd"]
    report["stats"].update(stats, verified=verified,
                           cost_per_verified_bug=round(spent / verified, 4) if verified else None)
    report.update(bugs=[asdict(b) for b in bugs], routing=router_summary,
                  cost_by_stage=budget_summary["by_stage"], stopped_reason=stopped_reason,
                  accounting=budget_summary,
                  compatibility_note="bugs/verified are deprecated repro-only views; use findings/status_counts")
    return report


def write_campaign_report(run_dir: Path, report: dict) -> Path:
    payload = json.dumps(report, indent=2) + "\n"
    Report.from_dict(json.loads(payload))
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "report.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(payload)
    temporary.replace(path)
    return path


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
