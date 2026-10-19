import httpx
import pytest
import respx

from nightshift.config import MODELS, Settings
from nightshift.llm import Budget, BudgetExceeded, NemotronClient, ResponseCache, cost_usd
from nightshift.llm.client import split_reasoning

LIGHTNING_URL = MODELS["lightning"].base_url.rstrip("/") + "/chat/completions"
ULTRA_URL = MODELS["ultra"].base_url.rstrip("/") + "/chat/completions"


def completion(content, prompt_tokens=1000, completion_tokens=500, **message):
    return {
        "choices": [{"message": {"role": "assistant", "content": content, **message}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


@pytest.fixture
def client(tmp_path):
    settings = Settings(api_key="test", budget_usd=1.0, cache_path=tmp_path / "c.sqlite3", runs_dir=tmp_path)
    c = NemotronClient(settings, cache=ResponseCache(":memory:"))
    yield c


@respx.mock
async def test_charges_real_usage_and_caches_repeat_calls(client):
    route = respx.post(LIGHTNING_URL).mock(return_value=httpx.Response(200, json=completion("42")))
    msgs = [{"role": "user", "content": "q"}]

    first = await client.chat("lightning", msgs, stage="propose")
    second = await client.chat("lightning", msgs, stage="propose")

    assert first.text == "42" and not first.cached
    assert first.cost_usd == pytest.approx(cost_usd(MODELS["lightning"], 1000, 500))
    assert second.cached and second.cost_usd == 0.0
    assert route.call_count == 1
    assert client.budget.spent_usd == pytest.approx(first.cost_usd)
    assert client.budget.by_stage["propose"] == pytest.approx(first.cost_usd)


@respx.mock
async def test_variant_draws_a_distinct_sample(client):
    route = respx.post(LIGHTNING_URL).mock(return_value=httpx.Response(200, json=completion("x")))
    msgs = [{"role": "user", "content": "q"}]
    await client.chat("lightning", msgs, stage="propose", variant=0)
    await client.chat("lightning", msgs, stage="propose", variant=1)
    assert route.call_count == 2


@respx.mock
async def test_ultra_uses_its_own_endpoint_and_thinking_flag(client):
    route = respx.post(ULTRA_URL).mock(return_value=httpx.Response(200, json=completion("ok")))
    await client.chat("ultra", [{"role": "user", "content": "q"}], stage="confirm", thinking=2048, max_tokens=100)
    body = route.calls[0].request.read()
    assert b'"enable_thinking":true' in body.replace(b" ", b"")
    assert b'"max_tokens":2148' in body.replace(b" ", b"")


async def test_refuses_calls_that_could_exceed_the_cap(tmp_path):
    settings = Settings(api_key="t", budget_usd=0.001, cache_path=tmp_path / "c", runs_dir=tmp_path)
    client = NemotronClient(settings, cache=ResponseCache(":memory:"))
    with pytest.raises(BudgetExceeded):
        await client.chat("ultra", [{"role": "user", "content": "q"}], stage="confirm", max_tokens=4096)
    assert client.budget.spent_usd == 0 and client.budget.reserved_usd == 0


@respx.mock
async def test_retries_rate_limits_and_releases_reservation_on_failure(client, monkeypatch):
    monkeypatch.setattr("nightshift.llm.client.asyncio.sleep", _no_sleep)
    respx.post(LIGHTNING_URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json=completion("done"))]
    )
    assert (await client.chat("lightning", [{"role": "user", "content": "a"}], stage="s")).text == "done"

    respx.post(LIGHTNING_URL).mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(httpx.HTTPStatusError):
        await client.chat("lightning", [{"role": "user", "content": "b"}], stage="s")
    assert client.budget.reserved_usd == pytest.approx(0.0)


def test_concurrent_reservations_cannot_overshoot():
    budget = Budget(1.0)
    budget.reserve(0.6)
    with pytest.raises(BudgetExceeded):
        budget.reserve(0.6)


@pytest.mark.parametrize(
    "message, expected",
    [
        ({"content": "<think>hmm</think>391"}, ("391", "hmm")),
        ({"content": "hmm</think>\n391"}, ("391", "hmm")),
        ({"content": "391", "reasoning_content": "hmm"}, ("391", "hmm")),
        ({"content": "391"}, ("391", "")),
    ],
)
def test_split_reasoning(message, expected):
    assert split_reasoning(message) == expected


async def _no_sleep(_):
    return None
