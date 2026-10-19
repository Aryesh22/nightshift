"""Confirm the Nemotron model IDs exist and each tier answers a one-line prompt.

Usage: uv run python scripts/check_models.py [--ping]
Without --ping it only lists models (free). --ping spends a fraction of a cent per tier.
"""

from __future__ import annotations

import asyncio
import sys

from nightshift.config import MODELS
from nightshift.llm import NemotronClient
from nightshift.llm.cache import ResponseCache


async def main(ping: bool) -> int:
    ok = True
    async with NemotronClient(cache=ResponseCache(":memory:")) as client:
        for base_url in sorted({s.base_url for s in MODELS.values()}):
            ids = {m["id"] for m in await client.list_models(base_url)}
            nemotron = sorted(i for i in ids if "nemotron" in i.lower())
            print(f"\n{base_url}\n  nemotron models: {nemotron or 'none'}")
            for spec in MODELS.values():
                if spec.base_url == base_url:
                    found = spec.model_id in ids
                    ok &= found
                    print(f"  [{'ok' if found else 'MISSING'}] {spec.tier}: {spec.model_id}")

        if ping:
            for tier in MODELS:
                for thinking in (0, 256):
                    try:
                        r = await client.chat(
                            tier,
                            [{"role": "user", "content": "Reply with the single word: pong"}],
                            stage="check",
                            max_tokens=32,
                            thinking=thinking,
                        )
                        print(
                            f"  {tier} thinking={thinking}: {r.text.strip()!r} "
                            f"reasoning={'yes' if r.reasoning else 'no'} "
                            f"tokens={r.input_tokens}/{r.output_tokens} ${r.cost_usd:.6f}"
                        )
                    except Exception as e:  # report every tier, don't stop at the first failure
                        ok = False
                        print(f"  {tier} thinking={thinking}: FAILED {e}")
            print(f"\nspend: {client.budget.summary()}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--ping" in sys.argv)))
