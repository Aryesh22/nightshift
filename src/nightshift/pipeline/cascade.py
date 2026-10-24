"""Run one LLM step through the router: start cheap, escalate until the output verifies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from nightshift.llm import NemotronClient
from nightshift.pipeline.router import LADDER, Router
from nightshift.pipeline.types import RouteStep

T = TypeVar("T")

# verify(parsed) -> (ok, feedback for the next attempt)
Verifier = Callable[[T], Awaitable[tuple[bool, str]]]


async def call_with_cascade(
    client: NemotronClient,
    router: Router,
    stage: str,
    bucket_key: str,
    messages: list[dict],
    parse: Callable[[dict], T],
    *,
    verify: Verifier | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    variant: int = 0,
) -> tuple[T | None, list[RouteStep]]:
    """Return (last verified output, or None if every rung failed; route trace).

    `parse` receives the model's JSON and raises ValueError/KeyError/TypeError when the
    output is unusable. `verify` runs a real check (usually in the sandbox). Either kind of
    failure is recorded against the rung, and the next rung sees the feedback.
    BudgetExceeded propagates so the run can stop cleanly.
    """
    trace: list[RouteStep] = []
    feedback = ""
    rung: int | None = router.start(stage, bucket_key)
    while rung is not None:
        route = LADDER[rung]
        attempt = messages
        if feedback:
            attempt = [*messages, {"role": "user", "content": f"Your previous attempt failed:\n{feedback}\nFix it."}]
        result = await client.chat(
            route.tier,
            attempt,
            stage=stage,
            thinking=route.thinking,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
            variant=variant,
        )
        try:
            parsed = parse(result.json())
        except (ValueError, KeyError, TypeError, SyntaxError) as exc:
            parsed, ok, feedback = None, False, f"Output was not usable: {exc}"
        else:
            ok, feedback = await verify(parsed) if verify else (True, "")
        router.record(stage, bucket_key, rung, ok, result.cost_usd)
        trace.append(RouteStep(stage, route.tier, route.thinking, result.cost_usd, ok))
        if ok:
            return parsed, trace
        rung = router.next_rung(stage, rung)
    return None, trace
