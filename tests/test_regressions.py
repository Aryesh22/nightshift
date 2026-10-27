"""Regression tests for the review of PR #1: harness fidelity, patch policy, budget
accounting, and the baseline pipeline's failure handling.

Only trusted, locally authored fixtures execute. HTTP requests use MockTransport.
"""
import importlib
import json
import os
import sys
import types
from pathlib import Path

import httpx
import pytest

from nightshift.cli import load_sandbox
from nightshift.config import ModelSpec, Settings
from nightshift.contracts import Contract, Evidence, Harness
from nightshift.contracts.library import BASE64_HARNESS, BASE64_ROUNDTRIP
from nightshift.contracts.runner import run_contract
from nightshift.llm import Budget, BudgetExceeded, NemotronClient, ResponseCache
from nightshift.llm.client import LLMResult
from nightshift.pipeline import prompts
from nightshift.pipeline.cascade import call_with_cascade
from nightshift.pipeline.confirm import confirm
from nightshift.pipeline.propose import parse_test
from nightshift.pipeline.read import SourceIndex, clone
from nightshift.pipeline.report import build_report
from nightshift.pipeline.router import Router, bucket
from nightshift.pipeline.run import RunConfig, run_nightshift
from nightshift.pipeline.types import Execution, PropertyTest, Target, TriageVerdict
from nightshift.report import Report
from nightshift.sandbox import EnvHandle
from nightshift.sandbox.local import UnsafeLocalSandbox

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (Evidence.manual('trusted fixture specification', 'The relation preserves the original input.'),)
TARGET = Target('t1', 'checkedlib.value', '() -> int', 'value returns 1', 'invariant', 'Returns 1.')
PROPERTY = PropertyTest('p1', 't1', 'assert value() == 1')
EXECUTION = Execution('p1', 'fail', 'assertion', 'AssertionError: 0 != 1')
VERDICT = TriageVerdict('p1', 'real_bug', 0.9, 'Offline scripted verdict')


@pytest.fixture(autouse=True)
def use_temporary_environment_python(monkeypatch):
    # The legacy confirmation path hard-codes `python`; point it at the review venv.
    monkeypatch.setenv('PATH', str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'])


class ScriptedClient:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = 0
        self.budget = Budget(1)

    async def chat(self, tier, messages, **kwargs):
        payload = self.payloads[min(self.calls, len(self.payloads) - 1)]
        self.calls += 1
        return LLMResult(tier, 'offline', kwargs.get('thinking', 0), json.dumps(payload), '', 0, 0, 0, False, 'stop')


async def campaign(tmp_path, contract, harness, module_source=''):
    fixture = tmp_path / 'fixture'
    fixture.mkdir()
    (fixture / 'trusted_probe.py').write_text(module_source)
    sandbox = UnsafeLocalSandbox()
    base = await sandbox.prepare(str(fixture), '', [])
    try:
        return await run_contract(sandbox, base, contract, harness, max_examples=20, python=sys.executable)
    finally:
        await sandbox.close(base)


def relation(family, apis):
    return Contract('review.' + family, 'trusted_probe', 'fixture-v1', family, apis,
                    'Preserve the documented input relation', EVIDENCE)


async def test_roundtrip_uses_original_expected_value(tmp_path):
    contract = relation('roundtrip', ('trusted_probe.encode', 'trusted_probe.decode'))
    harness = Harness('import trusted_probe\ndef forward(x):\n    return trusted_probe.encode(x)\n'
                      'def backward(y):\n    return trusted_probe.decode(y)\n',
                      'def inputs():\n    return st.builds(list, st.just((1, 2)))\n')
    out = await campaign(tmp_path, contract, harness,
                         'def encode(x):\n    x[:] = [0]\n    return tuple(x)\n'
                         'def decode(y):\n    return list(y)\n')
    assert out.kind == 'violation', (out.kind, out.stats)


async def test_equivalent_calls_start_from_independent_equal_inputs(tmp_path):
    contract = relation('equivalent', ('trusted_probe.pop_a', 'trusted_probe.pop_b'))
    harness = Harness('import trusted_probe\ndef call_a(x):\n    return trusted_probe.pop_a(x)\n'
                      'def call_b(x):\n    return trusted_probe.pop_b(x)\n',
                      'def inputs():\n    return st.builds(list, st.just((1, 2)))\n')
    out = await campaign(tmp_path, contract, harness,
                         'def pop_a(x):\n    return x.pop()\n'
                         'def pop_b(x):\n    return x.pop()\n')
    assert out.kind == 'passed', (out.kind, out.stats)


async def test_adapter_name_error_is_not_a_bug_candidate(tmp_path):
    harness = Harness('def forward(x):\n    return missing_helper(x)\n'
                      'def backward(y):\n    return y\n', BASE64_HARNESS.strategy_source)
    out = await campaign(tmp_path, BASE64_ROUNDTRIP, harness)
    assert not out.is_candidate, (out.kind, out.stats)
    # Do not "fix" this by discarding a genuine first-stage target exception.
    target_fixture = tmp_path / 'early-target'
    target_fixture.mkdir()
    contract = relation('roundtrip', ('trusted_probe.encode', 'trusted_probe.decode'))
    direct = Harness('import trusted_probe\ndef forward(x):\n    return trusted_probe.encode(x)\n'
                     'def backward(y):\n    return trusted_probe.decode(y)\n',
                     'def inputs():\n    return st.just(1)\n')
    early = await campaign(target_fixture, contract, direct,
                           'def encode(x):\n    raise ValueError("valid input, target failure")\n'
                           'def decode(y):\n    return y\n')
    assert early.kind == 'exception' and early.is_candidate
    assert early.stats['api_calls']['trusted_probe.decode'] == 0


async def test_untracked_apis_cannot_authorize_a_pass(tmp_path):
    contract = relation('roundtrip', ('builtins.str.lower', 'builtins.str.casefold'))
    harness = Harness('def forward(x):\n    return x\ndef backward(y):\n    return y\n',
                      "def inputs():\n    return st.text(alphabet='ab', max_size=10)\n")
    out = await campaign(tmp_path, contract, harness)
    assert out.kind != 'passed', (out.kind, out.stats)


async def test_discarding_both_api_results_is_not_faithful(tmp_path):
    harness = Harness('import base64\ndef forward(x):\n    base64.b64encode(x)\n    return x\n'
                      "def backward(y):\n    base64.b64decode(b'')\n    return y\n",
                      BASE64_HARNESS.strategy_source)
    out = await campaign(tmp_path, BASE64_ROUNDTRIP, harness)
    assert out.kind != 'passed', (out.kind, out.stats)


def report_payload(repro, patch):
    return dict(title='Offline candidate', severity='medium', repro=repro,
                root_cause='Offline fixture', patch_diff=patch)


async def confirmation(tmp_path, payload):
    fixture = tmp_path / 'confirmation_fixture'
    fixture.mkdir()
    (fixture / 'checkedlib.py').write_text('def value():\n    return 0\n')
    sandbox = UnsafeLocalSandbox()
    base = await sandbox.prepare(str(fixture), '', [])
    try:
        return await confirm(ScriptedClient([payload]), Router(), sandbox, base, TARGET,
                             'checkedlib.py', 'def value(): return 0', PROPERTY, EXECUTION,
                             VERDICT, 'b1')
    finally:
        await sandbox.close(base)


async def test_import_error_does_not_verify_the_semantic_repro(tmp_path):
    payload = report_payload('import definitely_missing_nightshift_audit_dependency\nassert True\n',
                             'not a valid diff')
    bug = await confirmation(tmp_path, payload)
    assert bug is None or not bug.repro_verified, bug


async def test_patch_cannot_replace_its_own_test(tmp_path):
    payload = report_payload('from checkedlib import value\nassert value() == 1\n',
                             '--- a/nightshift_repro.py\n+++ b/nightshift_repro.py\n'
                             '@@ -1,2 +1 @@\n-from checkedlib import value\n'
                             '-assert value() == 1\n+assert True\n')
    bug = await confirmation(tmp_path, payload)
    assert bug is None or not bug.patch_verified, bug


def http_client(tmp_path, handler, limit=1):
    spec = ModelSpec('lightning', 'offline', 'https://offline.invalid/v1', 1, 1, 10000, 1)
    settings = Settings('offline-fake-key', limit, tmp_path / 'unused-cache', tmp_path)
    return NemotronClient(settings, cache=ResponseCache(':memory:'), models={'lightning': spec},
                          http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), max_retries=0)


def completion(usage=None):
    result = {'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}]}
    if usage is not None:
        result['usage'] = usage
    return result


async def test_reservation_bounds_actual_settlement(tmp_path):
    client = http_client(tmp_path, lambda r: httpx.Response(200, json=completion(
        {'prompt_tokens': 600, 'completion_tokens': 1})), limit=0.0004)
    try:
        try:
            await client.chat('lightning', [{'role': 'user', 'content': '\u2603' * 600}],
                              stage='audit', max_tokens=1)
        except BudgetExceeded:
            # Refusing an unsafe request before submission satisfies the hard cap.
            assert not client.budget.attempts
        assert client.budget.spent_usd <= client.budget.limit_usd, client.budget.summary()
    finally:
        await client.aclose()


async def test_missing_usage_retains_estimated_or_pending_cost(tmp_path):
    client = http_client(tmp_path, lambda r: httpx.Response(200, json=completion()))
    try:
        await client.chat('lightning', [{'role': 'user', 'content': 'hello'}], stage='audit', max_tokens=10)
        assert client.budget.spent_usd + client.budget.reserved_usd > 0, client.budget.summary()
    finally:
        await client.aclose()
    malformed = http_client(tmp_path, lambda r: httpx.Response(200, json={'choices': []}))
    try:
        with pytest.raises(IndexError):
            await malformed.chat('lightning', [{'role': 'user', 'content': 'hello'}], stage='audit', max_tokens=10)
        assert malformed.budget.reserved_usd > 0
        assert malformed.budget.pending[0]['status'] == 'pending'
    finally:
        await malformed.aclose()


async def test_read_timeout_retains_potential_charge(tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout('submitted, response unknown', request=request)
    client = http_client(tmp_path, timeout)
    try:
        with pytest.raises(httpx.ReadTimeout):
            await client.chat('lightning', [{'role': 'user', 'content': 'hello'}], stage='audit', max_tokens=10)
        assert client.budget.reserved_usd > 0, client.budget.summary()
    finally:
        await client.aclose()
    attempts = 0
    def retry_then_succeed(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout('first response unknown', request=request)
        return httpx.Response(200, json=completion({'prompt_tokens': 1, 'completion_tokens': 1}))
    retrying = http_client(tmp_path, retry_then_succeed)
    retrying.max_retries = 1
    try:
        await retrying.chat('lightning', [{'role': 'user', 'content': 'hello'}], stage='audit', max_tokens=10)
        assert len(retrying.budget.attempts) == 2
        assert [a['status'] for a in retrying.budget.attempts] == ['pending', 'settled']
        assert retrying.budget.reserved_usd > 0 and retrying.budget.spent_usd > 0
    finally:
        await retrying.aclose()


async def test_syntax_error_reaches_bounded_repair():
    invalid = 'from hypothesis import given, strategies as st\n@given(st.integers())\ndef test_property(x)\n    pass\n'
    valid = invalid.replace('def test_property(x)\n', 'def test_property(x):\n')
    client = ScriptedClient([{'test_code': invalid}, {'test_code': valid}])
    result, trace = await call_with_cascade(client, Router(), 'propose', bucket(), [], parse_test)
    assert result == valid and client.calls == 2


class NoExecutionSandbox:
    async def prepare(self, *args):
        return EnvHandle('base')

    async def close(self, env):
        pass


async def test_finished_work_survives_sibling_budget_exhaustion(tmp_path, monkeypatch):
    run_module = importlib.import_module('nightshift.pipeline.run')
    target2 = Target('t2', 'checkedlib.other', '()', 'other', 'invariant')

    async def fake_clone(*args):
        return tmp_path

    async def fake_extract(*args):
        return [TARGET, target2], SourceIndex({}), []

    async def fake_propose(client, router, sandbox, base, target, variant):
        if target.id == 't2':
            raise BudgetExceeded('offline sibling exhausted budget')
        return PROPERTY, EXECUTION, []

    monkeypatch.setattr(run_module, 'clone', fake_clone)
    async def fake_revision(*args):
        return 'a' * 40
    monkeypatch.setattr(run_module, 'source_revision', fake_revision)
    monkeypatch.setattr(run_module, 'extract_targets', fake_extract)
    monkeypatch.setattr(run_module, 'propose_and_run', fake_propose)
    report = await run_nightshift(RunConfig('file:///unused', 'checkedlib', mode='baseline', runs_dir=tmp_path,
                                          variants_per_target=1), ScriptedClient([]), NoExecutionSandbox())
    assert report['stats']['properties_proposed'] == 1 and report['stats']['failures'] == 1, report
    assert list(tmp_path.glob('*/executions.jsonl'))


async def test_unverified_source_directory_cannot_be_a_cache_hit(tmp_path):
    dest = tmp_path / 'cache'
    dest.mkdir()
    (dest / 'unrelated-marker').write_text('not a checkout')
    try:
        result = await clone('file:///definitely_missing_nightshift_repo', 'main', dest)
    except (ValueError, RuntimeError):
        return
    assert (result / '.git').is_dir(), result


def test_fixture_really_exhibits_its_claimed_bug(monkeypatch):
    spec = importlib.util.spec_from_file_location('review_pipeline_fixture', ROOT / 'tests/test_pipeline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checked = types.ModuleType('minilib')
    exec(module.LIB, checked.__dict__)
    monkeypatch.setitem(sys.modules, 'minilib', checked)
    request = httpx.Request('POST', 'https://offline.invalid', json={
        'messages': [{'role': 'system', 'content': prompts.CONFIRM_SYSTEM},
                     {'role': 'user', 'content': ''}]})
    response = module.scripted_model(request).json()
    repro = json.loads(response['choices'][0]['message']['content'])['repro']
    with pytest.raises(AssertionError):
        exec(repro, {})


@pytest.mark.parametrize('backend', ['docker', 'nebius'])
def test_cli_backend_is_loadable(backend):
    assert load_sandbox(backend) is not None


def test_actual_report_producer_is_compatible_with_v1_consumer():
    payload = build_report('offline-run', {'name': 'checkedlib', 'repo': 'file:///local', 'ref': 'main'},
                           {'targets': 1, 'properties_proposed': 1, 'failures': 0, 'triaged_real': 0},
                           Budget(1).summary(), [], [])
    assert Report.from_dict(json.loads(json.dumps(payload))).run_id == 'offline-run'


async def test_control_genuine_base64_relation_passes(tmp_path):
    out = await campaign(tmp_path, BASE64_ROUNDTRIP, BASE64_HARNESS)
    assert out.kind == 'passed'
    assert out.stats['assertion_reached'] >= 20
    assert all(n > 0 for n in out.stats['api_calls'].values())


async def test_control_identity_adapter_without_calls_is_vacuous(tmp_path):
    harness = Harness('def forward(x):\n    return x\ndef backward(y):\n    return y\n',
                      BASE64_HARNESS.strategy_source)
    out = await campaign(tmp_path, BASE64_ROUNDTRIP, harness)
    assert out.kind == 'vacuous' and not out.is_candidate


def test_budget_overrun_is_charged_and_recorded_not_a_permanent_block():
    budget = Budget(1.0)
    reservation = budget.reserve(0.01)
    budget.settle(reservation, 0.02, tier='lightning', stage='audit')  # estimate was wrong, cap is not
    assert budget.spent_usd == pytest.approx(0.02) and budget.reserved_usd == 0
    assert budget.overruns == [{'tier': 'lightning', 'stage': 'audit', 'reserved_usd': 0.01, 'actual_usd': 0.02}]
    assert budget.reserve(0.5) == 0.5  # the next call is still allowed
    budget.release(0.5)
    tight = Budget(0.015)
    with pytest.raises(BudgetExceeded):
        tight.settle(tight.reserve(0.01), 0.02, tier='lightning', stage='audit')
    assert tight.spent_usd == pytest.approx(0.02), 'the real charge is still recorded'


async def test_tavily_skips_a_non_https_result_instead_of_discarding_the_response():
    from nightshift.tavily import TavilyClient

    def handler(request):
        return httpx.Response(200, json={'usage': {'credits': 1}, 'results': [
            {'url': 'http://example.org/plain', 'content': 'insecure'},
            {'url': 'https://example.org/docs', 'content': 'documented behaviour'}]})
    client = TavilyClient('offline', http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        result = await client.search('documented behaviour')
    finally:
        await client.aclose()
    assert [r.url for r in result.receipts] == ['https://example.org/docs']
    assert result.failures[0]['url'] == 'http://example.org/plain'
    assert client.ledger.used == 1


async def test_docker_run_wraps_the_command_in_timeout_and_keeps_the_environment(monkeypatch):
    from nightshift.sandbox.base import RunResult
    from nightshift.sandbox.docker import DockerSandbox

    sandbox = DockerSandbox()
    sandbox._envs['c1'] = {'image': 'img', 'owned_image': 'img'}
    seen = {}

    async def fake_command(*args, timeout_s=30, container=None, **kwargs):
        seen.update(args=args, timeout_s=timeout_s, container=container)
        return RunResult(124, '', '', 1.0)  # GNU timeout's exit status on expiry
    monkeypatch.setattr(sandbox, '_command', fake_command)
    result = await sandbox.run(EnvHandle('c1'), 'sleep 999', timeout_s=5)
    assert result.timed_out and result.exit_code == 124
    assert seen['args'][:4] == ('exec', 'c1', 'sh', '-c') and seen['args'][4].startswith('timeout -k 2 5 sh -c ')
    assert seen['timeout_s'] == 20 and seen['container'] == 'c1'
    assert 'c1' in sandbox._envs


def test_core_finding_cost_excludes_the_shared_contract_extraction_call():
    """Two findings must not each be charged the one contract-extraction call."""
    import inspect
    from nightshift.pipeline import core
    source = inspect.getsource(core.run_core)
    assert 'finding.route_trace.extend(strategy_trace)' in source
    assert 'extend([*extraction_trace' not in source
    assert 'payload["shared_cost_usd"]' in source
