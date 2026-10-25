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


async def call_fixed_role(client, tier: str, stage: str, messages: list[dict], parse,
                          *, verify=None, attempts: int = 1, max_tokens: int = 2048,
                          thinking: int = 0, variant: int = 0, namespace: str = ""):
    """Bounded repair on one fixed model. Core never consults or trains the router."""
    from nightshift.report import RouteStep as CoreRouteStep

    if attempts not in {1, 2}:
        raise ValueError("a fixed-role stage allows at most one repair")
    trace, feedback = [], ""
    for attempt in range(attempts):
        context = [*messages]
        if feedback:
            context.append({"role": "user", "content": "Repair the harness/output only; preserve the frozen claim.\n" + feedback})
        result = await client.chat(tier, context, stage=stage, thinking=thinking, max_tokens=max_tokens,
                                   temperature=0.2, json_mode=True, variant=variant + attempt,
                                   namespace=namespace)
        try:
            parsed = parse(result.json())
            ok, feedback = await verify(parsed) if verify else (True, "")
        except (ValueError, TypeError, KeyError, SyntaxError) as exc:
            parsed, ok, feedback = None, False, str(exc)
        trace.append(CoreRouteStep(stage, tier, thinking, result.cost_usd, cached=result.cached,
                                   escalation_reason=feedback if not ok else ("bounded repair" if attempt else None)))
        if ok:
            return parsed, trace
    return None, trace
