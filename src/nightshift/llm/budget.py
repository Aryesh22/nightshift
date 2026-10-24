"""Hard spending cap with per-stage and per-tier cost accounting.

Each call reserves its worst-case cost before it is sent and settles to the real
cost afterwards, so concurrent calls can never push spend past the cap.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from nightshift.config import ModelSpec


class BudgetExceeded(RuntimeError):
    pass


def cost_usd(spec: ModelSpec, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * spec.input_price + output_tokens * spec.output_price) / 1_000_000


@dataclass
class Budget:
    limit_usd: float
    spent_usd: float = 0.0
    reserved_usd: float = 0.0
    by_tier: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    by_stage: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    calls: int = 0
    attempts: list[dict] = field(default_factory=list)
    pending: list[dict] = field(default_factory=list)
    blocked_reason: str | None = None

    def __post_init__(self):
        if not math.isfinite(self.limit_usd) or self.limit_usd < 0:
            raise ValueError("budget limit must be finite and nonnegative")

    @property
    def remaining_usd(self) -> float:
        return self.limit_usd - self.spent_usd - self.reserved_usd

    def reserve(self, amount_usd: float) -> float:
        if not math.isfinite(amount_usd) or amount_usd < 0:
            raise ValueError("reservation must be finite and nonnegative")
        if self.blocked_reason:
            raise BudgetExceeded(self.blocked_reason)
        if amount_usd > self.remaining_usd:
            raise BudgetExceeded(
                f"call needs up to ${amount_usd:.4f} but only ${self.remaining_usd:.4f} "
                f"of ${self.limit_usd:.2f} remains"
            )
        self.reserved_usd += amount_usd
        return amount_usd

    def release(self, reservation_usd: float) -> None:
        self.reserved_usd = max(0.0, self.reserved_usd - reservation_usd)

    def submitted(self, reservation_usd: float, tier: str, stage: str) -> dict:
        attempt = {"id": len(self.attempts) + 1, "tier": tier, "stage": stage,
                   "reservation_usd": reservation_usd, "status": "submitted"}
        self.attempts.append(attempt)
        self.calls += 1
        return attempt

    def mark_pending(self, attempt: dict, reason: str, reported_usd: float | None = None) -> None:
        """Keep the reservation encumbered until provider reconciliation, including retries."""
        attempt.update(status="pending", reason=reason)
        if reported_usd is not None:
            attempt["reported_usd"] = reported_usd
        self.pending.append(attempt)

    def settle(self, reservation_usd: float, actual_usd: float, tier: str, stage: str) -> None:
        if not math.isfinite(actual_usd) or actual_usd < 0:
            raise ValueError("usage cost must be finite and nonnegative")
        if actual_usd > reservation_usd + 1e-12:
            self.blocked_reason = "provider usage exceeded the reserved bound; reconcile before continuing"
            raise BudgetExceeded(self.blocked_reason)
        self.release(reservation_usd)
        self.spent_usd += actual_usd
        self.by_tier[tier] += actual_usd
        self.by_stage[stage] += actual_usd

    def summary(self) -> dict:
        return {
            "limit_usd": self.limit_usd,
            "spent_usd": round(self.spent_usd, 6),
            "reserved_usd": round(self.reserved_usd, 6),
            "pending_usd": round(sum(a["reservation_usd"] for a in self.pending), 6),
            "pending": list(self.pending),
            "attempts": list(self.attempts),
            "blocked_reason": self.blocked_reason,
            "calls": self.calls,
            "by_tier": {k: round(v, 6) for k, v in self.by_tier.items()},
            "by_stage": {k: round(v, 6) for k, v in self.by_stage.items()},
        }
