from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Target:
    """A function plus a claim about it that a property test can check."""

    id: str
    qualname: str  # importable dotted path, e.g. "pkg.module.func"
    signature: str
    claim: str
    kind: str  # roundtrip | inverse | idempotence | invariant | oracle | easy_to_verify | commutativity | ...
    evidence: str = ""  # doc or docstring text the claim comes from
    source: str = ""  # source of the function, used for complexity and prompts


@dataclass
class PropertyTest:
    id: str
    target_id: str
    code: str
    variant: int = 0


@dataclass
class Execution:
    property_id: str
    status: str  # pass | fail | invalid | timeout
    failure_kind: str = ""  # crash | assertion | timeout
    output: str = ""
    falsifying_example: str = ""


@dataclass
class RouteStep:
    stage: str
    model: str
    thinking: int
    cost_usd: float
    ok: bool


@dataclass
class TriageVerdict:
    property_id: str
    verdict: str  # real_bug | bad_test | unclear
    confidence: float
    reason: str
    trace: list[RouteStep] = field(default_factory=list)


@dataclass
class Bug:
    id: str
    title: str
    severity: str
    property: str
    target: str
    repro: str
    traceback: str
    root_cause: str
    patch_diff: str
    patch_verified: bool
    repro_verified: bool
    duplicate_of: str | None = None
    route_trace: list[RouteStep] = field(default_factory=list)
