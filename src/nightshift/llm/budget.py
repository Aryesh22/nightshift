"""Hard spending cap with per-stage and per-tier cost accounting.

Each call reserves its worst-case cost before it is sent and settles to the real
cost afterwards, so concurrent calls can never push spend past the cap.
"""

from __future__ import annotations

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

    @property
    def remaining_usd(self) -> float:
        return self.limit_usd - self.spent_usd - self.reserved_usd

    def reserve(self, amount_usd: float) -> float:
        if amount_usd > self.remaining_usd:
            raise BudgetExceeded(
                f"call needs up to ${amount_usd:.4f} but only ${self.remaining_usd:.4f} "
                f"of ${self.limit_usd:.2f} remains"
            )
        self.reserved_usd += amount_usd
        return amount_usd

    def release(self, reservation_usd: float) -> None:
        self.reserved_usd -= reservation_usd

    def settle(self, reservation_usd: float, actual_usd: float, tier: str, stage: str) -> None:
        self.release(reservation_usd)
        self.spent_usd += actual_usd
        self.by_tier[tier] += actual_usd
        self.by_stage[stage] += actual_usd
        self.calls += 1

    def summary(self) -> dict:
        return {
            "limit_usd": self.limit_usd,
            "spent_usd": round(self.spent_usd, 6),
            "calls": self.calls,
            "by_tier": {k: round(v, 6) for k, v in self.by_tier.items()},
            "by_stage": {k: round(v, 6) for k, v in self.by_stage.items()},
        }
