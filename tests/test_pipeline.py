"""End-to-end run against a tiny git repo, a scripted model, and a trusted process runner for real confirmation."""

import difflib
import json
import shlex
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
import respx

from nightshift.config import Settings
from nightshift.llm import NemotronClient, ResponseCache
from nightshift.pipeline import prompts
from nightshift.pipeline.run import RunConfig, run_nightshift
from nightshift.sandbox import RunResult
from nightshift.sandbox.local import UnsafeLocalSandbox
from nightshift.report import Report

LIB = r'''
def encode(s: str) -> str:
    """Escape commas so that decode(encode(s)) == s for any str."""
    return s.replace("\\", "").replace(",", "\\,")


def decode(s: str) -> str:
    return s.replace("\\,", ",")


def slugify(s: str) -> str:
    """Idempotent: slugify(slugify(s)) == slugify(s)."""
    return s.strip().lower().replace(" ", "-")
'''
FIXED_LIB = LIB.replace(r's.replace("\\", "").replace', 's.replace')
PATCH_DIFF = "".join(difflib.unified_diff(
    LIB.splitlines(keepends=True), FIXED_LIB.splitlines(keepends=True),
    fromfile="a/minilib/__init__.py", tofile="b/minilib/__init__.py",
))

FAILING_TEST = "from hypothesis import given, settings, strategies as st\nfrom minilib import encode, decode\n\n@given(st.text())\n@settings(max_examples=300, deadline=None)\ndef test_property(s):  # expect-fail\n    assert decode(encode(s)) == s\n"
PASSING_TEST = "from hypothesis import given, settings, strategies as st\nfrom minilib import slugify\n\n@given(st.text())\n@settings(max_examples=300, deadline=None)\ndef test_property(s):\n    assert slugify(slugify(s)) == slugify(s)\n"
BROKEN_TEST = PASSING_TEST.replace("from minilib import slugify", "from minilib import slugfy  # expect-invalid")


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "minilib-repo"
    (path / "minilib").mkdir(parents=True)
    (path / "minilib" / "__init__.py").write_text(LIB)
    (path / "README.md").write_text("# minilib\nencode/decode round-trip any string.\n")
    for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "."],
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"]):
        subprocess.run(cmd, cwd=path, check=True)
    return f"file://{path}"


class FakeSandbox(UnsafeLocalSandbox):
    """Script proposal outcomes; execute confirmation, discovery replay and patches.

    Only this trusted fixture runs on the host. Production uses DockerSandbox.
    """

    async def prepare(self, repo_url, ref, setup_cmds):
        return await super().prepare(repo_url, ref, [])

    async def run(self, env, cmd, timeout_s=120.0):
        if "-m pytest " in cmd and "test_discovery.py" not in cmd:
            code = (Path(env.meta["workdir"]) / cmd.split()[-1]).read_text()
            if "expect-invalid" in code:
                return RunResult(2, "ERROR collecting test\nImportError: cannot import name 'slugfy'", "", 0.1)
            if "expect-fail" in code:
                return RunResult(1, "Falsifying example: test_property(s='backslash')\nAssertionError: roundtrip lost input", "", 0.2)
            return RunResult(0, "1 passed", "", 0.2)
        if cmd.startswith("python "):
            cmd = shlex.quote(sys.executable) + cmd[len("python"):]
        return await super().run(env, cmd, timeout_s)


def scripted_model(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    system, user = body["messages"][0]["content"], body["messages"][1]["content"]
    retried = len(body["messages"]) > 2
    if system == prompts.READ_SYSTEM:
        answer = {"targets": [
            {"qualname": "minilib.encode", "signature": "(s: str) -> str", "kind": "roundtrip",
             "claim": "decode(encode(s)) == s", "evidence": "decode(encode(s)) == s for any str"},
            {"qualname": "minilib.slugify", "signature": "(s: str) -> str", "kind": "idempotence",
             "claim": "slugify is idempotent", "evidence": "Idempotent"},
        ]}
    elif system == prompts.PROPOSE_SYSTEM:
        if "minilib.encode" in user:
            code = FAILING_TEST
        else:
            code = PASSING_TEST if retried else BROKEN_TEST  # first attempt is broken -> escalation
        answer = {"test_code": code}
    elif system == prompts.TRIAGE_SYSTEM:
        answer = {"verdict": "real_bug", "confidence": 0.9, "reason": "Backslashes are not escaped."}
    elif system == prompts.CONFIRM_SYSTEM:
        answer = {"title": "encode/decode round-trip loses backslash before comma", "severity": "medium",
                  "repro": "from minilib import encode, decode\nassert decode(encode('\\\\,')) == '\\\\,'\n",
                  "root_cause": "encode drops existing backslashes.",
                  "patch_diff": PATCH_DIFF}
    else:
        raise AssertionError("unknown prompt")
    usage = {"prompt_tokens": 2000, "completion_tokens": 300}
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}], "usage": usage})


@respx.mock
async def test_full_run_finds_verifies_and_reports_the_planted_bug(repo, tmp_path):
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=scripted_model)
    settings = Settings(api_key="t", budget_usd=1.0, cache_path=tmp_path / "c", runs_dir=tmp_path / "runs")
    client = NemotronClient(settings, cache=ResponseCache(":memory:"))
    config = RunConfig(repo_url=repo, package="minilib", mode="baseline", runs_dir=tmp_path / "runs", variants_per_target=1)

    report = await run_nightshift(config, client, FakeSandbox())

    assert report["stopped_reason"] is None
    assert report["stats"]["targets"] == 2
    assert report["stats"]["properties_proposed"] == 2
    assert report["stats"]["failures"] == 1
    assert report["stats"]["verified"] == 1
    assert report["stats"]["cost_per_verified_bug"] > 0

    [bug] = report["bugs"]
    assert bug["target"] == "minilib.encode"
    assert bug["repro_verified"] and bug["patch_verified"]
    assert [s["stage"] for s in bug["route_trace"]] == ["triage", "confirm"]
    assert bug["route_trace"][-1]["model"] == "ultra"

    # The broken slugify test escalated from Lightning/no-thinking to Lightning/thinking.
    propose_routes = {r["route"]: r for r in report["routing"] if r["stage"] == "propose"}
    assert propose_routes["lightning/think=0"]["success_rate"] < 1
    assert "lightning/think=1024" in propose_routes

    written = json.loads(next((tmp_path / "runs").glob("*-minilib/report.json")).read_text())
    assert written["bugs"][0]["id"] == "b1"
    parsed = Report.from_dict(written)
    assert parsed.findings[0].status == "ai_reviewed"
    assert parsed.findings[0].replays_passed == 3
    assert parsed.cost_per_validated_finding is None
    assert set(report["cost_by_model"]) <= {"lightning", "super", "ultra"}


@respx.mock
async def test_bug_is_dropped_when_repro_passes_on_original_code(repo, tmp_path):
    def bogus_repro(request):
        response = scripted_model(request)
        body = json.loads(request.content)
        if body["messages"][0]["content"] == prompts.CONFIRM_SYSTEM:
            data = json.loads(response.content)
            answer = json.loads(data["choices"][0]["message"]["content"])
            answer["repro"] = "# expect-bogus\nassert True\n"
            data["choices"][0]["message"]["content"] = json.dumps(answer)
            return httpx.Response(200, json=data)
        return response

    respx.post(url__regex=r".*/chat/completions").mock(side_effect=bogus_repro)
    settings = Settings(api_key="t", budget_usd=1.0, cache_path=tmp_path / "c", runs_dir=tmp_path / "runs")
    client = NemotronClient(settings, cache=ResponseCache(":memory:"))
    config = RunConfig(repo_url=repo, package="minilib", mode="baseline", runs_dir=tmp_path / "runs", variants_per_target=1)

    report = await run_nightshift(config, client, FakeSandbox())

    assert report["stats"]["triaged_real"] == 1
    assert report["bugs"] == []
    assert report["stats"]["cost_per_verified_bug"] is None
    confirm_routes = [r for r in report["routing"] if r["stage"] == "confirm"]
    assert sum(r["trials"] for r in confirm_routes) == 2  # escalated ultra 2048 -> 8192, both rejected


@respx.mock
async def test_run_stops_cleanly_and_still_writes_report_when_budget_runs_out(repo, tmp_path):
    respx.post(url__regex=r".*/chat/completions").mock(side_effect=scripted_model)
    settings = Settings(api_key="t", budget_usd=0.004, cache_path=tmp_path / "c", runs_dir=tmp_path / "runs")
    client = NemotronClient(settings, cache=ResponseCache(":memory:"))
    config = RunConfig(repo_url=repo, package="minilib", mode="baseline", runs_dir=tmp_path / "runs", variants_per_target=1)

    report = await run_nightshift(config, client, FakeSandbox())

    assert report["stopped_reason"].startswith("budget")
    assert client.budget.spent_usd <= 0.004
    assert next((tmp_path / "runs").glob("*-minilib/report.json")).exists()
