"""Async client for Nemotron models on Nebius Token Factory or OpenRouter (OpenAI-compatible API).

Every call goes through the response cache and the hard budget. The `thinking`
argument is the router's knob: 0 disables reasoning, N > 0 enables it and allows up
to N reasoning tokens on top of the answer tokens.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, replace

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
    cost_status: str = "confirmed"

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


def thinking_fields(provider: str, thinking: int) -> dict:
    """Provider-specific request fields that turn reasoning off (0) or on with a budget."""
    if provider == "openrouter":
        return {"reasoning": {"max_tokens": thinking} if thinking > 0 else {"enabled": False}}
    fields: dict = {"chat_template_kwargs": {"enable_thinking": thinking > 0}}
    if thinking > 0 and SEND_REASONING_BUDGET:
        fields["reasoning_budget"] = thinking
    return fields


def estimate_tokens(messages: list[dict]) -> int:
    """Conservative bound for supported text requests to byte-level tokenizers.

    One token per UTF-8 byte, plus framing/special-token headroom. Multimodal payloads
    have no defensible text bound and are refused. Provider rates and tokenizer/chat
    template assumptions still require verification; over-bound usage blocks the client.
    """
    if any(not isinstance(m.get("content", ""), str) for m in messages):
        raise ValueError("only text messages have a supported reservation bound")
    return len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + 1024 * len(messages) + 256


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
        namespace: str = "",
        retry_limit: int | None = None,
    ) -> LLMResult:
        """`variant` lets callers draw distinct samples that are still cached on re-runs."""
        spec = self.models[tier]
        retries = self.max_retries if retry_limit is None else retry_limit
        if type(retries) is not int or not 0 <= retries <= self.max_retries:
            raise ValueError("retry_limit may only reduce the client's retry ceiling")
        body: dict = {
            "model": spec.model_id,
            "messages": messages,
            "max_tokens": max_tokens + thinking,
            "temperature": temperature,
            **thinking_fields(spec.provider, thinking),
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        key = cache_key({"base_url": spec.base_url, "body": body, "variant": variant, "namespace": namespace})
        if (hit := self.cache.get(key)) is not None:
            return self._result(spec, thinking, hit, cached=True)

        if thinking < 0 or max_tokens <= 0:
            raise ValueError("token limits must be positive (thinking may be zero)")
        input_bound = estimate_tokens(messages)
        if input_bound + body["max_tokens"] > spec.context_tokens:
            raise ValueError("request's conservative token bound exceeds the model context")
        worst_case = cost_usd(spec, input_bound, body["max_tokens"])
        for retry in range(retries + 1):
            async with self._limits[tier]:
                reservation = self.budget.reserve(worst_case)
                attempt = self.budget.submitted(reservation, tier, stage)
                attempt.update(model_id=spec.model_id, base_url=spec.base_url,
                               max_tokens=body["max_tokens"], input_bound=input_bound,
                               requested_controls=thinking_fields(spec.provider, thinking))
                try:
                    data = await self._post(spec, body)
                    # Parsing is part of the accounting guard: a malformed 200 response
                    # can still be billable and must become an explicit pending charge.
                    result = self._result(spec, thinking, data, cached=False)
                    usage = data.get("usage") or {}
                    known = all(k in usage for k in ("prompt_tokens", "completion_tokens"))
                    if not known:
                        self.budget.mark_pending(attempt, "successful response omitted complete usage")
                        result = replace(result, cost_usd=reservation, cost_status="pending")
                    else:
                        attempt.update(input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                                       reported_usd=result.cost_usd)
                        if result.input_tokens > input_bound or result.output_tokens > body["max_tokens"]:
                            attempt["over_bound"] = True  # settle() records the overrun
                        self.budget.settle(reservation, result.cost_usd, tier=tier, stage=stage)
                        attempt.update(status="settled", cost_usd=result.cost_usd)
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
                    self.budget.release(reservation)
                    attempt["status"] = "not_submitted"
                    if retry == retries:
                        raise
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status == 408 or status >= 500:
                        self.budget.mark_pending(attempt, f"ambiguous HTTP {status}")
                    else:
                        self.budget.release(reservation)
                        attempt["status"] = "rejected"
                    if status not in RETRYABLE_STATUS or retry == retries:
                        raise
                except httpx.TransportError as exc:
                    self.budget.mark_pending(attempt, f"ambiguous transport: {type(exc).__name__}")
                    if retry == retries:
                        raise
                except BaseException as exc:
                    if attempt["status"] == "submitted":
                        self.budget.mark_pending(attempt, f"unreconciled response: {type(exc).__name__}")
                    raise
                else:
                    self.cache.put(key, data)
                    return result
            await asyncio.sleep(min(2**retry, 30))
        raise AssertionError("unreachable")

    async def _post(self, spec: ModelSpec, body: dict) -> dict:
        url = spec.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        resp = await self.http.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def _result(self, spec: ModelSpec, thinking: int, data: dict, cached: bool) -> LLMResult:
        choice = data["choices"][0]
        text, reasoning = split_reasoning(choice["message"])
        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
            raise ValueError("provider token usage must contain nonnegative integers")
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
