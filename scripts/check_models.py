"""Day-1 probe: confirm model IDs, endpoints, token usage, and how thinking is controlled.

Usage: uv run python scripts/check_models.py
Spends well under $0.01. Results go to stdout; update src/nightshift/config.py if anything differs.
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

from nightshift.config import API_KEY_ENV, MODELS, PROVIDER, Settings
from nightshift.llm.client import split_reasoning

PROMPT = [{"role": "user", "content": "What is 17 * 23? Answer with just the number."}]


async def list_models(http: httpx.AsyncClient, base_url: str, key: str) -> set[str]:
    resp = await http.get(base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"})
    resp.raise_for_status()
    return {m["id"] for m in resp.json().get("data", [])}


async def probe(http: httpx.AsyncClient, base_url: str, key: str, model: str, extra: dict) -> str:
    body = {"model": model, "messages": PROMPT, "max_tokens": 600, "temperature": 0, **extra}
    resp = await http.post(base_url.rstrip("/") + "/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"})
    if resp.status_code != 200:
        return f"HTTP {resp.status_code}: {resp.text[:160]}"
    data = resp.json()
    text, reasoning = split_reasoning(data["choices"][0]["message"])
    usage = data.get("usage", {})
    return (
        f"answer={text[:30]!r} reasoning_chars={len(reasoning)} "
        f"in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}"
    )


async def main() -> None:
    settings = Settings.from_env()
    if not settings.api_key:
        sys.exit(f"{API_KEY_ENV[PROVIDER]} is not set (provider: {PROVIDER}).")
    if PROVIDER == "openrouter":
        variants = {
            "thinking off": {"reasoning": {"enabled": False}},
            "thinking on": {"reasoning": {"enabled": True}},
            "reasoning max_tokens=128": {"reasoning": {"max_tokens": 128}},
        }
    else:
        variants = {
            "thinking off": {"chat_template_kwargs": {"enable_thinking": False}},
            "thinking on": {"chat_template_kwargs": {"enable_thinking": True}},
            "reasoning_budget=128": {"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 128},
        }
    async with httpx.AsyncClient(timeout=120) as http:
        for base_url in sorted({s.base_url for s in MODELS.values()}):
            try:
                ids = await list_models(http, base_url, settings.api_key)
            except httpx.HTTPError as exc:
                print(f"{base_url}: could not list models ({exc})")
                continue
            nvidia = sorted(i for i in ids if "nemotron" in i.lower() or i.lower().startswith("nvidia/"))
            print(f"\n{base_url}\n  NVIDIA models: {', '.join(nvidia) or '(none)'}")
        for spec in MODELS.values():
            print(f"\n[{spec.tier}] {spec.model_id} @ {spec.base_url}")
            for label, extra in variants.items():
                print(f"  {label:22} {await probe(http, spec.base_url, settings.api_key, spec.model_id, extra)}")
    if PROVIDER == "nebius" and os.getenv("NIGHTSHIFT_SEND_REASONING_BUDGET") != "1":
        print("\nIf 'reasoning_budget=128' produced shorter reasoning, set NIGHTSHIFT_SEND_REASONING_BUDGET=1.")


if __name__ == "__main__":
    asyncio.run(main())
