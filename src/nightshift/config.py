"""Model registry and runtime settings.

Prices are USD per 1M tokens. Verify them with `uv run python scripts/check_models.py`
and the Token Factory pricing page before trusting cost reports.

NIGHTSHIFT_PROVIDER picks where the same Nemotron models are served:
- "nebius" (default): Nebius Token Factory, the hackathon's required platform.
- "openrouter": OpenRouter's free Nemotron variants, for development only while we
  wait for Token Factory access. Free variants are heavily rate limited.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("NIGHTSHIFT_PROVIDER", "nebius").lower()
if PROVIDER not in ("nebius", "openrouter"):
    raise ValueError(f"NIGHTSHIFT_PROVIDER must be nebius or openrouter, not {PROVIDER!r}")

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
US_CENTRAL_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1/"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/"
API_KEY_ENV = {"nebius": "NEBIUS_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


@dataclass(frozen=True)
class ModelSpec:
    tier: str
    model_id: str
    base_url: str
    input_price: float  # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    context_tokens: int
    max_concurrency: int
    provider: str = "nebius"


NEBIUS_MODELS: dict[str, ModelSpec] = {
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


# Free variants listed by https://openrouter.ai/api/v1/models on 2026-10-20. $0 price, so the
# budget never trips; the real limit is OpenRouter's free-tier request quota.
OPENROUTER_MODELS: dict[str, ModelSpec] = {
    tier: ModelSpec(
        tier=tier,
        model_id=os.getenv(f"NIGHTSHIFT_{tier.upper()}_MODEL", model_id),
        base_url=OPENROUTER_BASE_URL,
        input_price=0.0,
        output_price=0.0,
        context_tokens=context,
        max_concurrency=2,
        provider="openrouter",
    )
    for tier, model_id, context in (
        ("lightning", "nvidia/nemotron-3.5-lightning:free", 1_000_000),
        ("super", "nvidia/nemotron-3-super-120b-a12b:free", 262_144),
        ("ultra", "nvidia/nemotron-3-ultra-550b-a55b:free", 1_000_000),
    )
}

MODELS: dict[str, ModelSpec] = OPENROUTER_MODELS if PROVIDER == "openrouter" else NEBIUS_MODELS


@dataclass(frozen=True)
class Settings:
    api_key: str
    budget_usd: float
    cache_path: Path
    runs_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            api_key=os.getenv(API_KEY_ENV[PROVIDER], ""),
            budget_usd=float(os.getenv("NIGHTSHIFT_BUDGET_USD", "2.00")),
            cache_path=Path(os.getenv("NIGHTSHIFT_CACHE", ".nightshift/llm_cache.sqlite3")),
            runs_dir=Path(os.getenv("NIGHTSHIFT_RUNS_DIR", "runs")),
        )
