"""Async Nemotron client for Token Factory (OpenAI-compatible chat completions).

Every call goes through the response cache and the hard budget cap, and is
limited per tier to that model's `max_concurrency`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from nightshift.config import MODELS, ModelSpec, Settings
from nightshift.llm.budget import Budget, cost_usd
from nightshift.llm.cache import ResponseCache, cache_key

RETRY_STATUSES = {429, 500, 502, 503, 504}
# Deliberately pessimistic so the budget reservation is never below the real cost.
CHARS_PER_TOKEN_LOWER_BOUND = 2


@dataclass(frozen=True)
class LLMResponse:
    text: str
    reasoning: str | None
    tier: str
    model_id: str
    stage: str
    thinking: int | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool

    def trace(self) -> dict:
        """One `route_trace` entry for report.json."""
        return {
            "stage": self.stage,
            "model": self.tier,
            "thinking": self.thinking,
            "cost_usd": round(self.cost_usd, 6),
            "cached": self.cached,
        }


def thinking_params(thinking: int | None) -> dict:
    """Request fields that control Nemotron reasoning.

    None leaves the model default. 0 turns reasoning off. A positive number turns it
    on with that token budget. Confirm field names with scripts/check_models.py.
    """
    if thinking is None:
        return {}
    if thinking == 0:
        return {"chat_template_kwargs": {"enable_thinking": False}}
    return {"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": thinking}


def estimate_input_tokens(messages: list[dict]) -> int:
    chars = sum(len(str(m.get("content", ""))) for m in messages)
    return chars // CHARS_PER_TOKEN_LOWER_BOUND + 16 * len(messages)


class NemotronClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        budget: Budget | None = None,
        cache: ResponseCache | None = None,
        models: dict[str, ModelSpec] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 4,
        timeout_s: float = 300.0,
    ):
        self.settings = settings or Settings.from_env()
        if not self.settings.api_key:
            raise ValueError("NEBIUS_API_KEY is not set (put it in .env)")
        self.budget = budget or Budget(limit_usd=self.settings.budget_usd)
        self.cache = cache if cache is not None else ResponseCache(self.settings.cache_path)
        self.models = models or MODELS
        self.max_retries = max_retries
        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            timeout=timeout_s,
            transport=transport,
        )
        self._limits = {t: asyncio.Semaphore(s.max_concurrency) for t, s in self.models.items()}

    async def __aenter__(self) -> NemotronClient:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self.cache.close()

    async def chat(
        self,
        tier: str,
        messages: list[dict],
        *,
        stage: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        thinking: int | None = None,
        use_cache: bool = True,
        **extra,
    ) -> LLMResponse:
        spec = self.models[tier]
        payload = {
            "model": spec.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **thinking_params(thinking),
            **extra,
        }
        key = cache_key({"base_url": spec.base_url, **payload})

        if use_cache and (body := self.cache.get(key)) is not None:
            return self._parse(body, spec, stage, thinking, cost=0.0, cached=True)

        worst_case = cost_usd(spec, estimate_input_tokens(messages), max_tokens + (thinking or 0))
        reservation = self.budget.reserve(worst_case)
        try:
            async with self._limits[tier]:
                body = await self._post(spec, payload)
        except BaseException:
            self.budget.release(reservation)
            raise

        usage = body.get("usage") or {}
        cost = cost_usd(spec, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        if not usage:
            cost = worst_case  # no usage reported: charge the worst case rather than nothing
        self.budget.settle(reservation, cost, tier, stage)
        if use_cache:
            self.cache.put(key, body)
        return self._parse(body, spec, stage, thinking, cost=cost, cached=False)

    async def list_models(self, base_url: str) -> list[dict]:
        resp = await self._http.get(base_url.rstrip("/") + "/models")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def _post(self, spec: ModelSpec, payload: dict) -> dict:
        url = spec.base_url.rstrip("/") + "/chat/completions"
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._http.post(url, json=payload)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
            else:
                if resp.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                    resp.raise_for_status()
                    return resp.json()
                if retry_after := resp.headers.get("retry-after"):
                    await asyncio.sleep(min(float(retry_after), 60.0))
                    continue
            await asyncio.sleep(min(2**attempt, 30))
        raise AssertionError("unreachable")

    @staticmethod
    def _parse(
        body: dict, spec: ModelSpec, stage: str, thinking: int | None, *, cost: float, cached: bool
    ) -> LLMResponse:
        message = body["choices"][0]["message"]
        usage = body.get("usage") or {}
        return LLMResponse(
            text=message.get("content") or "",
            reasoning=message.get("reasoning_content") or message.get("reasoning"),
            tier=spec.tier,
            model_id=spec.model_id,
            stage=stage,
            thinking=thinking,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cost_usd=cost,
            cached=cached,
        )
