"""Model registry and runtime settings.

Prices are USD per 1M tokens. Verify them with `uv run python scripts/check_models.py`
and the Token Factory pricing page before trusting cost reports.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
US_CENTRAL_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1/"


@dataclass(frozen=True)
class ModelSpec:
    tier: str
    model_id: str
    base_url: str
    input_price: float  # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    context_tokens: int
    max_concurrency: int


MODELS: dict[str, ModelSpec] = {
    # Price unpublished in the cookbook; Super's price used as a deliberately high placeholder.
    "lightning": ModelSpec(
        tier="lightning",
        model_id=os.getenv("NIGHTSHIFT_LIGHTNING_MODEL", "nvidia/Nemotron-3_5-Lightning"),
        base_url=os.getenv("NIGHTSHIFT_LIGHTNING_BASE_URL", DEFAULT_BASE_URL),
        input_price=0.30,
        output_price=0.90,
        context_tokens=1_000_000,
        max_concurrency=16,
    ),
    "super": ModelSpec(
        tier="super",
        model_id=os.getenv("NIGHTSHIFT_SUPER_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
        base_url=os.getenv("NIGHTSHIFT_SUPER_BASE_URL", DEFAULT_BASE_URL),
        input_price=0.30,
        output_price=0.90,
        context_tokens=256_000,
        max_concurrency=8,
    ),
    # Ultra is served from the us-central1 endpoint only.
    "ultra": ModelSpec(
        tier="ultra",
        model_id=os.getenv("NIGHTSHIFT_ULTRA_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b"),
        base_url=os.getenv("NIGHTSHIFT_ULTRA_BASE_URL", US_CENTRAL_BASE_URL),
        input_price=1.00,
        output_price=3.00,
        context_tokens=1_000_000,
        max_concurrency=2,
    ),
}


@dataclass(frozen=True)
class Settings:
    api_key: str
    budget_usd: float
    cache_path: Path
    runs_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            api_key=os.getenv("NEBIUS_API_KEY", ""),
            budget_usd=float(os.getenv("NIGHTSHIFT_BUDGET_USD", "2.00")),
            cache_path=Path(os.getenv("NIGHTSHIFT_CACHE", ".nightshift/llm_cache.sqlite3")),
            runs_dir=Path(os.getenv("NIGHTSHIFT_RUNS_DIR", "runs")),
        )
