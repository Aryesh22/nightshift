"""Async client for Nemotron models on Nebius Token Factory (OpenAI-compatible API).

Every call goes through the response cache and the hard budget. The `thinking`
argument is the router's knob: 0 disables reasoning, N > 0 enables it and allows up
to N reasoning tokens on top of the answer tokens.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass

import httpx

from nightshift.config import MODELS, ModelSpec, Settings
from nightshift.llm.budget import Budget, cost_usd
from nightshift.llm.cache import ResponseCache, cache_key

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
THINK_BLOCK = re.compile(r"<think>(.*?)</think>", re.DOTALL)
JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

# Token Factory's exact knob for a reasoning budget is unconfirmed; scripts/check_models.py
# probes it. Until then the budget is enforced through max_tokens.
SEND_REASONING_BUDGET = os.getenv("NIGHTSHIFT_SEND_REASONING_BUDGET", "0") == "1"


@dataclass(frozen=True)
class LLMResult:
    tier: str
    model_id: str
    thinking: int
    text: str
    reasoning: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool
    finish_reason: str | None

    def json(self) -> dict:
        """Parse the answer as a JSON object, tolerating a markdown fence around it."""
        text = self.text.strip()
        if fenced := JSON_FENCE.search(text):
            text = fenced.group(1).strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"no JSON object in model output: {self.text[:200]!r}")
        return json.loads(text[start : end + 1])


def split_reasoning(message: dict) -> tuple[str, str]:
    """Return (answer, reasoning), handling both a separate field and inline <think> tags."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    if not reasoning:
        blocks = THINK_BLOCK.findall(content)
        if blocks:
            reasoning = "\n".join(b.strip() for b in blocks)
            content = THINK_BLOCK.sub("", content)
        elif "</think>" in content:  # opening tag consumed by the chat template
            reasoning, content = content.split("</think>", 1)
    return content.strip(), reasoning.strip()


def estimate_tokens(messages: list[dict]) -> int:
    # Deliberately pessimistic (~3 chars/token) so reservations overestimate.
    return sum(len(str(m.get("content", ""))) for m in messages) // 3 + 16 * len(messages)


class NemotronClient:
    def __init__(
        self,
        settings: Settings | None = None,
        budget: Budget | None = None,
        cache: ResponseCache | None = None,
        models: dict[str, ModelSpec] | None = None,
        http: httpx.AsyncClient | None = None,
        max_retries: int = 4,
    ):
        self.settings = settings or Settings.from_env()
        self.budget = budget or Budget(self.settings.budget_usd)
        self.cache = cache or ResponseCache(self.settings.cache_path)
        self.models = models or MODELS
        self.http = http or httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0))
        self.max_retries = max_retries
        self._limits = {tier: asyncio.Semaphore(s.max_concurrency) for tier, s in self.models.items()}

    async def chat(
        self,
        tier: str,
        messages: list[dict],
        *,
        stage: str,
        thinking: int = 0,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        json_mode: bool = False,
        variant: int = 0,
    ) -> LLMResult:
        """`variant` lets callers draw distinct samples that are still cached on re-runs."""
        spec = self.models[tier]
        body: dict = {
            "model": spec.model_id,
            "messages": messages,
            "max_tokens": max_tokens + thinking,
            "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": thinking > 0},
        }
        if thinking > 0 and SEND_REASONING_BUDGET:
            body["reasoning_budget"] = thinking
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        key = cache_key({"base_url": spec.base_url, "body": body, "variant": variant})
        if (hit := self.cache.get(key)) is not None:
            return self._result(spec, thinking, hit, cached=True)

        worst_case = cost_usd(spec, estimate_tokens(messages), body["max_tokens"])
        reservation = self.budget.reserve(worst_case)
        try:
            async with self._limits[tier]:
                data = await self._post(spec, body)
        except BaseException:
            self.budget.release(reservation)
            raise
        result = self._result(spec, thinking, data, cached=False)
        self.budget.settle(reservation, result.cost_usd, tier=tier, stage=stage)
        self.cache.put(key, data)
        return result

    async def _post(self, spec: ModelSpec, body: dict) -> dict:
        url = spec.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self.http.post(url, json=body, headers=headers)
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
            else:
                if resp.status_code not in RETRYABLE_STATUS or attempt == self.max_retries:
                    resp.raise_for_status()
                    return resp.json()
            await asyncio.sleep(min(2**attempt, 30))
        raise AssertionError("unreachable")

    def _result(self, spec: ModelSpec, thinking: int, data: dict, cached: bool) -> LLMResult:
        choice = data["choices"][0]
        text, reasoning = split_reasoning(choice["message"])
        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        return LLMResult(
            tier=spec.tier,
            model_id=spec.model_id,
            thinking=thinking,
            text=text,
            reasoning=reasoning,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0 if cached else cost_usd(spec, input_tokens, output_tokens),
            cached=cached,
            finish_reason=choice.get("finish_reason"),
        )

    async def aclose(self) -> None:
        await self.http.aclose()
        self.cache.close()
