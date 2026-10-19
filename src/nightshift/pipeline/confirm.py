"""Stage 5: turn a triaged failure into a verified bug report.

Verification happens in fresh sandbox forks, never on the host:
1. the repro must FAIL on the original code (the bug is real and reproducible);
2. after `git apply` of the patch, the repro must PASS (the patch fixes it).
A bug with an unverified repro is never reported; an unverified patch is reported as such.
"""

from __future__ import annotations

from nightshift.llm import NemotronClient
from nightshift.pipeline import prompts
from nightshift.pipeline.cascade import call_with_cascade
from nightshift.pipeline.router import Router, bucket
from nightshift.pipeline.types import Bug, Execution, PropertyTest, Target, TriageVerdict
from nightshift.sandbox import EnvHandle, SandboxExecutor

REPRO_PATH = "nightshift_repro.py"
PATCH_PATH = "nightshift_fix.patch"
REPRO_TIMEOUT_S = 60.0
SEVERITIES = {"low", "medium", "high"}


def parse_report(payload: dict) -> dict:
    for key in ("title", "repro", "root_cause", "patch_diff"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"missing {key!r}")
    compile(payload["repro"], REPRO_PATH, "exec")
    if "assert" not in payload["repro"]:
        raise ValueError("repro must end with an assert that fails while the bug exists")
    payload["severity"] = payload.get("severity") if payload.get("severity") in SEVERITIES else "medium"
    return payload


async def confirm(
    client: NemotronClient,
    router: Router,
    sandbox: SandboxExecutor,
    base_env: EnvHandle,
    target: Target,
    source_path: str,
    file_source: str,
    prop: PropertyTest,
    execution: Execution,
    verdict: TriageVerdict,
    bug_id: str,
) -> Bug | None:
    checks: dict[str, bool] = {}
    reproducible: dict = {}  # latest report whose repro was verified, even if its patch was not

    async def verify(report: dict) -> tuple[bool, str]:
        checks.clear()
        original = await sandbox.fork(base_env)
        try:
            await sandbox.put_file(original, REPRO_PATH, report["repro"])
            before = await sandbox.run(original, f"python {REPRO_PATH}", REPRO_TIMEOUT_S)
        finally:
            await sandbox.close(original)
        checks["repro"] = before.exit_code != 0 and not before.timed_out
        if not checks["repro"]:
            return False, "The repro PASSED on the original code, so it does not demonstrate the bug."
        reproducible.clear()
        reproducible.update(report)

        patched = await sandbox.fork(base_env)
        try:
            await sandbox.put_file(patched, REPRO_PATH, report["repro"])
            await sandbox.put_file(patched, PATCH_PATH, report["patch_diff"].rstrip("\n") + "\n")
            applied = await sandbox.run(patched, f"git apply --whitespace=nowarn {PATCH_PATH}", 30.0)
            after = await sandbox.run(patched, f"python {REPRO_PATH}", REPRO_TIMEOUT_S) if applied.exit_code == 0 else None
        finally:
            await sandbox.close(patched)
        checks["patch"] = after is not None and after.exit_code == 0
        if applied.exit_code != 0:
            return False, f"`git apply` rejected the patch:\n{applied.output[-1500:]}"
        if not checks["patch"]:
            return False, f"With the patch applied the repro still fails:\n{after.output[-1500:]}"
        return True, ""

    messages = [
        {"role": "system", "content": prompts.CONFIRM_SYSTEM},
        {
            "role": "user",
            "content": prompts.CONFIRM_USER.format(
                qualname=target.qualname,
                signature=target.signature,
                claim=target.claim,
                evidence=target.evidence,
                reason=verdict.reason,
                source_path=source_path or "(unknown)",
                source=file_source or target.source or "(source unavailable)",
                test_code=prop.code,
                output=execution.output[-4000:],
                retry_feedback="",
            ),
        },
    ]
    report, trace = await call_with_cascade(
        client, router, "confirm", bucket(execution.failure_kind, target.source), messages,
        parse=parse_report, verify=verify, max_tokens=4096,
    )
    patch_verified = report is not None
    # A reproducible bug whose patch never verified is still worth reporting.
    report = report or reproducible or None
    if report is None:
        return None
    return Bug(
        id=bug_id,
        title=report["title"],
        severity=report["severity"],
        property=target.kind,
        target=target.qualname,
        repro=report["repro"],
        traceback=execution.output[-3000:],
        root_cause=report["root_cause"],
        patch_diff=report["patch_diff"],
        patch_verified=patch_verified,
        repro_verified=True,
        route_trace=verdict.trace + trace,
    )
