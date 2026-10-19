"""Cost-aware cascade over (model tier, thinking budget).

Routes form a ladder ordered by cost. Each (stage, bucket) starts at a hand-written rule,
escalates one rung when the verifier rejects the result, and over time learns from
observed success rates:
- if a cheaper rung has proven reliable enough, start there (saves money);
- if the rule's rung keeps failing, start one rung higher (saves wasted calls).
Success estimates use a Beta(1, 1) prior, so few observations never drive decisions.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    tier: str
    thinking: int

    def __str__(self) -> str:
        return f"{self.tier}/think={self.thinking}"


LADDER: tuple[Route, ...] = (
    Route("lightning", 0),
    Route("lightning", 1024),
    Route("super", 512),
    Route("super", 2048),
    Route("ultra", 2048),
    Route("ultra", 8192),
)

# Starting rung per (stage, failure kind). "*" matches any kind.
START_RULES: dict[tuple[str, str], int] = {
    ("read", "*"): 1,
    ("propose", "*"): 0,
    ("triage", "crash"): 0,
    ("triage", "assertion"): 2,
    ("triage", "timeout"): 2,
    ("triage", "*"): 2,
    ("confirm", "*"): 4,
}

# Highest rung each stage may escalate to.
MAX_RUNG: dict[str, int] = {"read": 2, "propose": 1, "triage": 4, "confirm": 5}

HIGH_COMPLEXITY = 10


def cyclomatic_complexity(source: str) -> int:
    """McCabe-style count of decision points; 1 if the source does not parse."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 1
    branches = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.IfExp, ast.comprehension, ast.Match)
    count = 1
    for node in ast.walk(tree):
        if isinstance(node, branches):
            count += 1
        elif isinstance(node, ast.BoolOp):
            count += len(node.values) - 1
        elif isinstance(node, ast.ExceptHandler):
            count += 1
    return count


def bucket(failure_kind: str = "*", source: str = "") -> str:
    band = "high" if source and cyclomatic_complexity(source) >= HIGH_COMPLEXITY else "low"
    return f"{failure_kind or '*'}:{band}"


@dataclass
class _Stats:
    trials: int = 0
    successes: int = 0
    cost_usd: float = 0.0

    @property
    def mean(self) -> float:
        return (self.successes + 1) / (self.trials + 2)


class Router:
    def __init__(self, target_success: float = 0.7, floor_success: float = 0.25, min_obs: int = 5):
        self.target_success = target_success
        self.floor_success = floor_success
        self.min_obs = min_obs
        self._stats: dict[tuple[str, str, int], _Stats] = defaultdict(_Stats)

    def rule_rung(self, stage: str, bucket_key: str) -> int:
        kind, band = bucket_key.split(":")
        rung = START_RULES.get((stage, kind), START_RULES.get((stage, "*"), 0))
        if band == "high":
            rung += 1
        return min(rung, MAX_RUNG[stage])

    def start(self, stage: str, bucket_key: str) -> int:
        rung = self.rule_rung(stage, bucket_key)
        for cheaper in range(rung):
            s = self._stats[(stage, bucket_key, cheaper)]
            if s.trials >= self.min_obs and s.mean >= self.target_success:
                return cheaper
        s = self._stats[(stage, bucket_key, rung)]
        if s.trials >= self.min_obs and s.mean < self.floor_success:
            rung = min(rung + 1, MAX_RUNG[stage])
        return rung

    def next_rung(self, stage: str, rung: int) -> int | None:
        return rung + 1 if rung < MAX_RUNG[stage] else None

    def record(self, stage: str, bucket_key: str, rung: int, success: bool, cost_usd: float) -> None:
        s = self._stats[(stage, bucket_key, rung)]
        s.trials += 1
        s.successes += int(success)
        s.cost_usd += cost_usd

    def summary(self) -> list[dict]:
        return [
            {
                "stage": stage,
                "bucket": bucket_key,
                "route": str(LADDER[rung]),
                "trials": s.trials,
                "success_rate": round(s.successes / s.trials, 3) if s.trials else None,
                "cost_usd": round(s.cost_usd, 6),
            }
            for (stage, bucket_key, rung), s in sorted(self._stats.items())
        ]
