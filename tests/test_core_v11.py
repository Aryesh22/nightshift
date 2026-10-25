"""Offline Core v1.1 contract, investigator, credit-ledger and integration regressions."""

import asyncio
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import respx

from nightshift.config import Settings
from nightshift.contracts import Contract, Evidence, Harness
from nightshift.contracts.model import sha256_text
from nightshift.contracts.runner import run_contract
from nightshift.llm import Budget, BudgetExceeded, NemotronClient, ResponseCache
from nightshift.llm.client import LLMResult
from nightshift.pipeline.contracts_stage import (
    ADAPTER_REVIEW_SYSTEM, CONTRACT_SYSTEM, HARNESS_SYSTEM, ApprovedHarness,
    build_documentation, literal_value, parse_contracts, retrieve_documentation,
)
from nightshift.pipeline.investigator import INVESTIGATE_SYSTEM, RefutationTools, investigate_candidate
from nightshift.pipeline.read import source_revision
from nightshift.pipeline.run import RunConfig, run_nightshift
from nightshift.report import Report
from nightshift.sandbox.local import UnsafeLocalSandbox
from nightshift.tavily import AirgapViolation, CreditLedger, CreditLimitExceeded, TavilyClient, content_hash

PROMISE = "For supported strings, decode(encode(x)) returns x without losing characters."
BODY_SENTINEL = "IMPLEMENTATION_BODY_MUST_NEVER_REACH_ORACLE"
LIBRARY = f'''"""Module documentation: stateless string transformations."""
def encode(x: str) -> str:
    """Encode a supported string; decode(encode(x)) returns x."""
    marker = {BODY_SENTINEL!r}
    return x.replace(chr(92), '')

def decode(x: str) -> str:
    """Decode a string produced by encode."""
    return x
'''
ADAPTER = "import reviewlib\ndef forward(x):\n    return reviewlib.encode(x)\ndef backward(x):\n    return reviewlib.decode(x)\n"
STRATEGY = "def inputs():\n    return st.sampled_from(['ok', chr(92)])\n"


@pytest.fixture
def core_repo(tmp_path):
    repo = tmp_path / "source"
    (repo / "reviewlib").mkdir(parents=True)
    (repo / "reviewlib/__init__.py").write_text(LIBRARY)
    (repo / "README.md").write_text("# reviewlib\n" + PROMISE + "\n")
    for command in (["git", "init", "-q", "-b", "main"], ["git", "add", "."],
                    ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "fixture"]):
        subprocess.run(command, cwd=repo, check=True)
    return repo


def contract_payload(source="README.md"):
    return {"contracts": [{"contract_id": "reviewlib.roundtrip", "family": "roundtrip",
        "apis": ["reviewlib.encode", "reviewlib.decode"], "claim": PROMISE,
        "evidence": [{"source": source, "excerpt": PROMISE}], "precondition": "isinstance(x, str)",
        "equivalence": "type_and_value", "status": "explicit"}]}


class ScriptedCore:
    def __init__(self, *, decision="accept", broken_first=False, always_broken=False, no_tools=False,
                 ultra_unavailable=False):
        self.calls, self.contexts = [], []
        self.decision, self.broken_first, self.always_broken = decision, broken_first, always_broken
        self.no_tools, self.ultra_unavailable = no_tools, ultra_unavailable
        self.strategy_calls = 0

    def __call__(self, request):
        body = json.loads(request.content)
        self.calls.append(body)
        self.contexts.append(body["messages"])
        system = body["messages"][0]["content"]
        if system == CONTRACT_SYSTEM:
            context = json.loads(body["messages"][1]["content"].split("\nPropose", 1)[0])
            remote = [d["source"] for d in context["documents"] if d["source"].startswith("https://")]
            payload = contract_payload(remote[0] if remote else "README.md")
        elif system == HARNESS_SYSTEM:
            self.strategy_calls += 1
            bad = self.always_broken or self.broken_first and self.strategy_calls == 1
            payload = {"adapter_source": ADAPTER.replace("reviewlib.encode(x)", "missing_helper(x)") if bad else ADAPTER,
                       "strategy_source": STRATEGY, "control_input": repr("ok")}
        elif system == ADAPTER_REVIEW_SYSTEM:
            payload = {"approved": True, "reason": "Direct declared calls preserve their inputs/results; immutable claim."}
        elif system == INVESTIGATE_SYSTEM:
            initial = json.loads(body["messages"][1]["content"])
            turns = sum(m["role"] == "assistant" for m in body["messages"])
            actions = [
                {"tool": "run_control_input", "arguments": {"adapter_id": initial["adapter_id"], "input_literal": repr("ok")},
                 "question": "Does a documented normal input work in this environment?"},
                {"tool": "inspect_doc_and_source", "arguments": {"symbol": "reviewlib.encode"},
                 "question": "Does the pinned documentation support the claimed semantics?"},
                {"tool": "check_boundary_neighborhood", "arguments": {"candidate_id": initial["candidate_id"], "profile": "length"},
                 "question": "Is the discrepancy localized around the reduced boundary?"},
                {"tool": "search_known_issues_tavily", "arguments": {"candidate_id": initial["candidate_id"], "terms": "backslash information loss"},
                 "question": "Is the behavior documented in an existing issue or release note?"},
            ]
            if turns < len(actions) and not self.no_tools:
                payload = actions[turns]
            else:
                payload = {"verdict": self.decision, "reason": "Decision cites the recorded control, pinned docs and replays.",
                           "check_ids": [0] if self.no_tools else [0, 1, 2, 3, 4]}
        else:
            if self.ultra_unavailable:
                raise httpx.ConnectError("offline optional Ultra", request=request)
            payload = {"root_cause": "encode drops backslashes", "patch_diff": ""}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}, "finish_reason": "stop"}],
                                       "usage": {"prompt_tokens": 10, "completion_tokens": 10}})


def model_client(tmp_path):
    return NemotronClient(Settings("offline", 1, tmp_path / "cache", tmp_path / "runs"),
                           cache=ResponseCache(":memory:"), max_retries=0)


def core_config(repo, tmp_path, **options):
    return RunConfig(f"file://{repo}", "reviewlib", mode="core", runs_dir=tmp_path / "runs",
                      setup_cmds=(), variants_per_target=1, max_examples=5, python=sys.executable, **options)


async def test_docs_only_digest_never_contains_function_bodies(core_repo):
    revision = await source_revision(core_repo)
    bundle, index = build_documentation(core_repo, "reviewlib", revision)
    digest = bundle.digest()
    assert PROMISE in digest and "def encode" in digest
    assert "Module documentation: stateless string transformations." in digest
    assert BODY_SENTINEL not in digest and "x.replace" not in digest
    assert BODY_SENTINEL in index.lookup("reviewlib.encode")[1]
    assert bundle.pair_hints[0]["family_hint"] == "roundtrip"
    assert all(d.revision == revision for d in bundle.documents.values())


async def test_signature_defaults_and_decorators_cannot_leak_implementation(core_repo):
    path = core_repo / "reviewlib/__init__.py"
    path.write_text(path.read_text() + '\n@decorator("DECORATOR_SECRET")\ndef special(x=(lambda: "DEFAULT_BODY_SECRET")()):\n    return "BODY_SECRET"\n')
    bundle, _ = build_documentation(core_repo, "reviewlib", "pinned-fixture")
    digest = bundle.digest()
    assert "DECORATOR_SECRET" not in digest and "DEFAULT_BODY_SECRET" not in digest
    assert 'return "BODY_SECRET"' not in digest
    assert "default expression omitted" in digest


def test_docs_and_source_index_do_not_follow_symlinks_outside_the_checkout(core_repo, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text('def hidden():\n    """PRIVATE_OUTSIDE_DOCSTRING"""\n    return "PRIVATE_OUTSIDE_BODY"\n')
    (core_repo / "reviewlib/escape.py").symlink_to(outside)
    bundle, index = build_documentation(core_repo, "reviewlib", "pinned")
    assert "PRIVATE_OUTSIDE" not in bundle.digest()
    assert not any("escape" in name for name in index.functions)


@pytest.mark.parametrize("mutation", ["quote", "revision", "family", "api", "precondition"])
async def test_contract_records_are_runtime_validated(core_repo, mutation):
    bundle, _ = build_documentation(core_repo, "reviewlib", "a" * 40)
    payload = contract_payload()
    record = payload["contracts"][0]
    if mutation == "quote":
        record["evidence"][0]["excerpt"] = "a hallucinated promise"
    elif mutation == "revision":
        record["package_revision"] = "wrong-version"
    elif mutation == "family":
        record["family"] = "arbitrary Python"
    elif mutation == "api":
        record["apis"][0] = "os.system"
    else:
        record["precondition"] = "__import__('os').system('bad')"
    with pytest.raises(ValueError):
        parse_contracts(payload, bundle, "reviewlib", 2)


@respx.mock
@pytest.mark.parametrize("decision", ["accept", "reject", "unresolved"])
async def test_core_end_to_end_real_contract_tools_and_v1(core_repo, tmp_path, monkeypatch, decision):
    script = ScriptedCore(decision=decision)
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    monkeypatch.setattr("nightshift.pipeline.router.Router.start", lambda *a: (_ for _ in ()).throw(AssertionError("Core consulted bandit")))
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path, airgapped=True), client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["stopped_reason"] is None, payload["errors"]
    parsed = Report.from_dict(json.loads(json.dumps(payload)))
    assert payload["mode"] == "core" and parsed.library.version == await source_revision(core_repo)
    [finding] = parsed.findings
    assert finding.status == {"accept": "ai_reviewed", "reject": "rejected", "unresolved": "unresolved"}[decision]
    assert finding.replays_passed == finding.replays_attempted == 3
    assert finding.control == repr("ok")
    assert {c.tool for c in finding.checks} >= {"run_control_input", "inspect_doc_and_source", "check_boundary_neighborhood", "search_known_issues_tavily"}
    assert finding.known_behaviour.outcome == "lookup_unavailable"
    assert parsed.cost_per_validated_finding is None
    assert payload["stats"]["body_entries"] > 0 and payload["stats"]["assertions_reached"] > 0
    assert all(c["contract_hash"] == payload["contracts"][0]["hash"] for c in payload["campaigns"])
    assert payload["harness_approvals"][0]["contract_hash"] == finding.contract.hash
    for messages in script.contexts:
        joined = json.dumps(messages)
        if messages[0]["content"] in {CONTRACT_SYSTEM, ADAPTER_REVIEW_SYSTEM}:
            assert BODY_SENTINEL not in joined
        if messages[0]["content"] == HARNESS_SYSTEM:
            assert BODY_SENTINEL in joined
    tiers = {t["stage"]: t["model"] for t in payload["model_trace"]}
    assert tiers["contract"] == tiers["strategy"] == "lightning"
    assert tiers["adapter_review"] == tiers["investigate"] == "super"
    assert "ultra" not in tiers.values()
    run_dir = tmp_path / "runs" / payload["run_id"]
    assert (run_dir / "findings/f1/repro.py").exists()
    assert (run_dir / "investigations/f1.json").exists()
    assert len(json.loads((run_dir / "rejected.json").read_text())) == (decision == "reject")
    assert len(json.loads((run_dir / "unresolved.json").read_text())) == (decision == "unresolved")


@respx.mock
async def test_core_one_bounded_harness_repair_keeps_contract_frozen(core_repo, tmp_path):
    script = ScriptedCore(broken_first=True)
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path), client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["stopped_reason"] is None, payload["errors"]
    assert script.strategy_calls == 2
    assert [r["kind"] for r in payload["campaigns"]] == ["setup_error", "violation"]
    assert len({r["contract_hash"] for r in payload["campaigns"]}) == 1
    assert payload["findings"][0]["status"] == "ai_reviewed"


@respx.mock
async def test_core_harness_repair_cannot_loop_forever(core_repo, tmp_path):
    script = ScriptedCore(always_broken=True)
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path), client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert script.strategy_calls == 2 and len(payload["campaigns"]) == 2
    assert payload["findings"] == []
    assert payload["stats"]["infra_failures"] == 2


@respx.mock
async def test_investigator_cannot_accept_without_control_and_inspection(core_repo, tmp_path):
    script = ScriptedCore(no_tools=True)
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path), client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["findings"][0]["status"] == "unresolved"
    assert "passing control" in payload["findings"][0]["uncertainty"]


async def make_tools(repo):
    revision = await source_revision(repo)
    bundle, index = build_documentation(repo, "reviewlib", revision)
    contract = parse_contracts(contract_payload(), bundle, "reviewlib", 1)[0]
    approved = ApprovedHarness(Harness(ADAPTER, STRATEGY), repr("ok"), {"contract_hash": contract.hash})
    sandbox = UnsafeLocalSandbox()
    base = await sandbox.prepare(f"file://{repo}", revision, [])
    return RefutationTools(sandbox, base, contract, approved, index, "f1", repr(chr(92)), python=sys.executable)


async def test_invalid_investigator_requests_consume_call_cap_without_execution(core_repo, tmp_path):
    tools = await make_tools(core_repo)
    marker = tmp_path / "must-not-exist"
    try:
        for _ in range(6):
            response = await tools.execute("run_control_input", {"adapter_id": tools.contract.hash,
                "input_literal": f"__import__('pathlib').Path({str(marker)!r}).touch()"}, "Can this unsafe expression execute?")
            assert "error" in response["result"]
        assert tools.result.calls == 6 and tools.result.runtime_experiments == 0
        assert not marker.exists()
        with pytest.raises(ValueError, match="cap"):
            await tools.execute("inspect_doc_and_source", {"symbol": "os.system"}, "One more call?")
    finally:
        await tools.sandbox.close(tools.base_env)


async def test_runtime_experiments_have_a_separate_three_call_cap(core_repo):
    tools = await make_tools(core_repo)
    try:
        for value in ("ok", "a", "b"):
            await tools.execute("run_control_input", {"adapter_id": tools.contract.hash, "input_literal": repr(value)}, "Does a valid control work?")
        response = await tools.execute("run_control_input", {"adapter_id": tools.contract.hash, "input_literal": repr("c")}, "Can a fourth runtime experiment run?")
        assert tools.result.runtime_experiments == 3 and tools.result.calls == 4
        assert "runtime experiment cap" in response["result"]
        bad_symbol = await tools.execute("inspect_doc_and_source", {"symbol": "os.system"}, "Can unrelated source be inspected?")
        assert "not allowlisted" in bad_symbol["result"]
    finally:
        await tools.sandbox.close(tools.base_env)


@respx.mock
async def test_optional_ultra_unavailability_preserves_a_reviewed_survivor(core_repo, tmp_path):
    script = ScriptedCore(ultra_unavailable=True)
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path, ultra_review=True, ultra_budget_usd=.1),
                                       client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["stopped_reason"] is None
    assert payload["findings"][0]["status"] == "ai_reviewed"
    assert "unavailable" in payload["findings"][0]["patch_validation"]


@respx.mock
async def test_tavily_receipts_cache_and_separate_credit_cap():
    search = respx.post("https://api.tavily.com/search").mock(return_value=httpx.Response(200, json={
        "request_id": "search-1", "usage": {"credits": 1},
        "results": [{"url": "https://example.org/v1/docs", "content": "official documentation"}]}))
    extract = respx.post("https://api.tavily.com/extract").mock(return_value=httpx.Response(200, json={
        "request_id": "extract-1", "usage": {"credits": 1},
        "results": [{"url": "https://example.org/v1/docs", "raw_content": PROMISE}], "failed_results": []}))
    client = TavilyClient("offline", ledger=CreditLedger(2))
    try:
        live = await client.search("version 1 documentation")
        cached = await client.search("version 1 documentation")
        result = await client.extract(["https://example.org/v1/docs"])
        assert live.receipts[0].status == "live" and cached.receipts[0].status == "cache"
        assert cached.receipts[0].retrieved_at == live.receipts[0].retrieved_at
        receipt = result.receipts[0]
        assert receipt.request_id == "extract-1" and receipt.content_hash == content_hash(PROMISE)
        assert receipt.excerpt == PROMISE and receipt.text == PROMISE
        assert client.ledger.used == 2 and search.call_count == extract.call_count == 1
        assert json.loads(search.calls[0].request.content)["include_usage"] is True
        assert json.loads(extract.calls[0].request.content)["include_usage"] is True
        with pytest.raises(CreditLimitExceeded):
            await client.search("a different request")
        assert search.call_count == 1
    finally:
        await client.aclose()


@respx.mock
async def test_airgap_blocks_both_live_and_cached_evidence():
    route = respx.post("https://api.tavily.com/search").mock(return_value=httpx.Response(200, json={
        "results": [{"url": "https://example.org/issues/1", "content": "hidden benchmark fix"}], "usage": {"credits": 1}}))
    client = TavilyClient("offline")
    try:
        await client.search("known issue")
        client.airgapped = True
        with pytest.raises(AirgapViolation):
            await client.search("known issue")
        with pytest.raises(AirgapViolation):
            await client.extract(["https://example.org/issues/1"])
        assert route.call_count == 1 and client.ledger.used == 1
    finally:
        await client.aclose()


@respx.mock
async def test_missing_usage_and_ambiguous_failures_retain_credit_exposure():
    route = respx.post("https://api.tavily.com/search").mock(return_value=httpx.Response(200, json={"results": []}))
    client = TavilyClient("offline", ledger=CreditLedger(2))
    try:
        await client.search("no usage in response")
        assert client.ledger.summary()["estimated"] == 1
        route.mock(side_effect=httpx.ReadTimeout("submitted, response unknown"))
        with pytest.raises(httpx.ReadTimeout):
            await client.search("ambiguous response")
        assert client.ledger.summary()["pending"] == 1
        with pytest.raises(CreditLimitExceeded):
            await client.search("must not be submitted")
        assert route.call_count == 2
    finally:
        await client.aclose()


@respx.mock
async def test_failed_or_empty_extractions_are_retained_not_promoted_to_evidence():
    respx.post("https://api.tavily.com/extract").mock(return_value=httpx.Response(200, json={
        "results": [{"url": "https://example.org/empty", "raw_content": ""},
                    {"url": "https://unrequested.example.org/secret", "raw_content": "must not become evidence"}], "usage": {"credits": 0},
        "failed_results": [{"url": "https://example.org/failure", "error": "extraction failed"}]}))
    client = TavilyClient("offline")
    try:
        result = await client.extract(["https://example.org/empty", "https://example.org/failure"])
        assert not result.receipts and len(result.failures) == 3 and client.ledger.used == 0
    finally:
        await client.aclose()


@respx.mock
async def test_concurrent_credit_reservations_cannot_both_spend_the_last_credit():
    async def answer(request):
        await asyncio.sleep(.01)
        return httpx.Response(200, json={"results": [], "usage": {"credits": 1}})
    route = respx.post("https://api.tavily.com/search").mock(side_effect=answer)
    client = TavilyClient("offline", ledger=CreditLedger(1))
    try:
        results = await asyncio.gather(client.search("first"), client.search("second"), return_exceptions=True)
        assert sum(isinstance(r, CreditLimitExceeded) for r in results) == 1
        assert route.call_count == 1 and client.ledger.used == 1
    finally:
        await client.aclose()


@respx.mock
async def test_live_receipts_bind_versioned_docs_and_known_issue_tools(core_repo, tmp_path, monkeypatch):
    revision = await source_revision(core_repo)
    origin = "https://github.com/example/reviewlib"
    url = f"{origin}/blob/{revision}/README.md"
    script = ScriptedCore()
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    def search(request):
        body = json.loads(request.content)
        issue = "official documentation" not in body["query"]
        return httpx.Response(200, json={"request_id": "issue-search" if issue else "docs-search",
            "usage": {"credits": 1}, "results": [{"url": origin + "/issues/7" if issue else url,
                                                     "content": "backslash issue" if issue else "versioned docs"}]})
    def extract(request):
        urls = json.loads(request.content)["urls"]
        return httpx.Response(200, json={"request_id": "extract-" + str(len(urls)), "usage": {"credits": 1},
            "results": [{"url": u, "raw_content": PROMISE if u == url else "Related backslash issue; applicability requires review."} for u in urls]})
    respx.post("https://api.tavily.com/search").mock(side_effect=search)
    respx.post("https://api.tavily.com/extract").mock(side_effect=extract)
    async def local_clone(*args):
        return core_repo
    monkeypatch.setattr("nightshift.pipeline.core.clone", local_clone)
    class LocalSource(UnsafeLocalSandbox):
        async def prepare(self, repo_url, ref, setup_cmds):
            return await super().prepare(f"file://{core_repo}", ref, [])
    config = replace(core_config(core_repo, tmp_path, online_lookup=True), repo_url=origin)
    client, tavily = model_client(tmp_path), TavilyClient("offline")
    try:
        payload = await run_nightshift(config, client, LocalSource(), tavily=tavily)
    finally:
        await client.aclose()
        await tavily.aclose()
    assert payload["stopped_reason"] is None, payload["errors"]
    [finding] = payload["findings"]
    assert finding["contract"]["evidence"][0]["source"] == url
    assert finding["contract"]["evidence"][0]["retrieved"].startswith("live")
    assert finding["known_behaviour"]["outcome"] == "related_issue"
    assert payload["stats"]["tavily_credits"] == 3  # docs extract + issue search + issue extract
    assert any(r["version_match"] and r["source_version"] == revision for r in payload["retrieval_receipts"])


@respx.mock
async def test_core_airgap_overrides_online_flag_before_any_retrieval(core_repo, tmp_path):
    script = ScriptedCore()
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    external = respx.post(url__regex=r"https://api.tavily.com/.*").mock(side_effect=AssertionError("benchmark leaked externally"))
    client, tavily = model_client(tmp_path), TavilyClient("offline")
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path, airgapped=True, online_lookup=True),
                                       client, UnsafeLocalSandbox(), tavily=tavily)
    finally:
        await client.aclose()
        await tavily.aclose()
    assert external.call_count == 0 and payload["stats"]["tavily_credits"] == 0
    assert payload["findings"][0]["status"] == "ai_reviewed"


def test_unsafe_literals_and_private_retrieval_urls_are_rejected():
    with pytest.raises(ValueError):
        literal_value("__import__('os').system('command')")
    from nightshift.tavily import public_url
    for value in ("http://example.org", "https://127.0.0.1/secret", "https://user:password@example.org/"):
        with pytest.raises(ValueError):
            public_url(value)


def test_cli_and_run_config_default_to_core(tmp_path, monkeypatch):
    from nightshift import cli
    seen = []
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def aclose(self):
            pass
    async def campaign(config, *args, **kwargs):
        seen.append(config)
        return {"stats": {}, "stopped_reason": None}
    monkeypatch.setattr(cli.Settings, 'from_env', lambda: Settings('offline', 1, tmp_path / 'cache', tmp_path))
    monkeypatch.setattr(cli, 'NemotronClient', Client)
    monkeypatch.setattr(cli, 'load_sandbox', lambda name: object())
    monkeypatch.setattr(cli, 'run_nightshift', campaign)
    cli.main(['run', 'file:///unused', '--package', 'reviewlib', '--airgapped'])
    cli.main(['run', 'file:///unused', '--package', 'reviewlib', '--mode', 'baseline'])
    assert [c.mode for c in seen] == ['core', 'baseline']
    assert seen[0].airgapped and RunConfig('file:///unused', 'reviewlib').mode == 'core'


@respx.mock
async def test_core_budget_stop_preserves_a_completed_finding(core_repo, tmp_path, monkeypatch):
    script = ScriptedCore()
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    original = client.chat
    async def stop_next_strategy(*args, **kwargs):
        if kwargs.get("stage") == "strategy" and script.strategy_calls:
            raise BudgetExceeded("offline stop before second profile")
        return await original(*args, **kwargs)
    monkeypatch.setattr(client, "chat", stop_next_strategy)
    config = replace(core_config(core_repo, tmp_path), variants_per_target=2)
    try:
        payload = await run_nightshift(config, client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["stopped_reason"].startswith("budget:")
    assert payload["findings"][0]["status"] == "ai_reviewed"
    saved = Report.load(tmp_path / "runs" / payload["run_id"] / "report.json")
    assert saved.findings[0].replays_passed == 3
    assert payload["campaigns"][-1]["kind"] == "generating"


@respx.mock
async def test_core_deduplicates_matching_frozen_failure_receipts(core_repo, tmp_path):
    script = ScriptedCore()
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(replace(core_config(core_repo, tmp_path), variants_per_target=2),
                                       client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["stopped_reason"] is None
    assert len(payload["findings"]) == 1 and len(payload["campaigns"]) == 2
    assert payload["campaigns"][1]["duplicate_of"] == payload["findings"][0]["id"]


@respx.mock
async def test_optional_ultra_cap_refuses_before_submission(core_repo, tmp_path):
    script = ScriptedCore()
    route = respx.post(url__regex=r".*/chat/completions").mock(side_effect=script)
    client = model_client(tmp_path)
    try:
        payload = await run_nightshift(core_config(core_repo, tmp_path, ultra_review=True, ultra_budget_usd=0),
                                       client, UnsafeLocalSandbox())
    finally:
        await client.aclose()
    assert payload["findings"][0]["status"] == "ai_reviewed"
    assert payload["ultra_allowance"]["exposure_usd"] == 0
    assert any("exceeds remaining Ultra" in c["result"] for c in payload["findings"][0]["checks"])
    assert not any("Ultra" in json.loads(c.request.content)["model"] for c in route.calls)
