import httpx
import pytest
import respx

from nightshift.config import ModelSpec, Settings
from nightshift.llm import Budget, BudgetExceeded, NemotronClient, ResponseCache

BASE = "https://llm.test/v1/"
SPEC = ModelSpec("lightning", "nvidia/test-model", BASE, 1.0, 2.0, 100_000, 2)


def completion(text="hi", prompt_tokens=1000, completion_tokens=500):
    return {
        "choices": [{"message": {"content": text, "reasoning_content": "because"}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


@pytest.fixture
def client():
    settings = Settings(api_key="k", budget_usd=1.0, cache_path=":memory:")
    c = NemotronClient(settings, cache=ResponseCache(":memory:"), models={"lightning": SPEC})
    yield c


MSGS = [{"role": "user", "content": "hello"}]


@respx.mock
async def test_chat_charges_real_cost_and_caches(client):
    route = respx.post(BASE + "chat/completions").respond(json=completion())
    r = await client.chat("lightning", MSGS, stage="propose")
    assert r.text == "hi" and r.reasoning == "because" and not r.cached
    assert r.cost_usd == pytest.approx((1000 * 1.0 + 500 * 2.0) / 1e6)
    assert client.budget.by_stage["propose"] == pytest.approx(r.cost_usd)
    assert client.budget.reserved_usd == pytest.approx(0)

    again = await client.chat("lightning", MSGS, stage="propose")
    assert again.cached and again.cost_usd == 0 and route.call_count == 1


@respx.mock
async def test_budget_cap_blocks_call_before_sending(client):
    route = respx.post(BASE + "chat/completions").respond(json=completion())
    client.budget = Budget(limit_usd=0.0001)
    with pytest.raises(BudgetExceeded):
        await client.chat("lightning", MSGS, stage="propose", max_tokens=4096)
    assert route.call_count == 0


@respx.mock
async def test_failed_call_releases_reservation(client):
    respx.post(BASE + "chat/completions").respond(400, json={"error": "bad"})
    with pytest.raises(httpx.HTTPStatusError):
        await client.chat("lightning", MSGS, stage="propose")
    assert client.budget.reserved_usd == pytest.approx(0) and client.budget.spent_usd == 0


@respx.mock
async def test_retries_on_429(client):
    route = respx.post(BASE + "chat/completions").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(200, json=completion("ok")),
        ]
    )
    r = await client.chat("lightning", MSGS, stage="triage")
    assert r.text == "ok" and route.call_count == 2


@respx.mock
async def test_thinking_budget_sent_and_traced(client):
    route = respx.post(BASE + "chat/completions").respond(json=completion())
    r = await client.chat("lightning", MSGS, stage="triage", thinking=512)
    sent = route.calls.last.request
    import json

    body = json.loads(sent.content)
    assert body["chat_template_kwargs"] == {"enable_thinking": True}
    assert body["reasoning_budget"] == 512
    assert r.trace() == {
        "stage": "triage", "model": "lightning", "thinking": 512,
        "cost_usd": round(r.cost_usd, 6), "cached": False,
    }


def test_missing_api_key_fails_fast():
    with pytest.raises(ValueError):
        NemotronClient(Settings(api_key="", budget_usd=1.0, cache_path=":memory:"))
