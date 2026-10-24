"""Preserve the discovery relation through three fresh-process semantic replays.

Patches are optional candidates with an explicitly recorded validation scope. Failed
patch checks cannot erase an independently reproduced candidate.
"""

from __future__ import annotations

import ast

from nightshift.llm import NemotronClient
from nightshift.pipeline import prompts
from nightshift.pipeline.cascade import call_with_cascade
from nightshift.pipeline.router import Router, bucket
from nightshift.pipeline.types import Bug, Execution, PropertyTest, Target, TriageVerdict
from nightshift.pipeline.verification import (
    DISCOVERY_PATH, VERIFIER_PATH, FORBIDDEN_ERRORS, hash_guard, patch_paths,
    replay_program, replay_receipt,
)
from nightshift.sandbox import EnvHandle, SandboxError, SandboxExecutor

REPRO_PATH = "nightshift_repro.py"
PATCH_PATH = "nightshift_fix.patch"
REPRO_TIMEOUT_S = 60.0
SEVERITIES = {"low", "medium", "high"}


def parse_report(payload: dict) -> dict:
    for key in ("title", "repro"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"missing {key!r}")
    compile(payload["repro"], REPRO_PATH, "exec")
    if not any(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(payload["repro"]))):
        raise ValueError("repro must contain a semantic assertion")
    for key in ("root_cause", "patch_diff"):
        payload[key] = payload.get(key) or ""
        if not isinstance(payload[key], str):
            raise ValueError(f"invalid {key!r}")
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
    evidence: dict = {}

    async def verify(report: dict) -> tuple[bool, str]:
        checks.clear()
        evidence.clear()
        try:
            verifier = replay_program(report["repro"], prop.code, target.qualname,
                                      execution.failure_kind, execution.output)
        except (ValueError, SyntaxError) as exc:
            return False, str(exc)
        evidence["replays"] = []
        for _ in range(3):
            original = await sandbox.fork(base_env)
            try:
                await sandbox.put_file(original, REPRO_PATH, report["repro"])
                await sandbox.put_file(original, VERIFIER_PATH, verifier)
                before = await sandbox.run(original, f"python {VERIFIER_PATH}", REPRO_TIMEOUT_S)
            finally:
                await sandbox.close(original)
            receipt = replay_receipt(before, report["repro"], target.qualname)
            if before.exit_code != 1 or not receipt or not receipt.get("matched"):
                return False, "Repro did not replay the frozen target assertion/failure: " + before.output[-1500:]
            receipt.update(stdout=before.stdout, stderr=before.stderr, duration_s=before.duration_s,
                           exit_code=before.exit_code)
            evidence["replays"].append(receipt)
        checks["repro"] = True
        reproducible.clear()
        reproducible.update(report)
        checks["patch"] = False
        evidence["patch_scope"] = "No patch validated; the reproducible candidate stands independently."
        if not report["patch_diff"]:
            return True, ""
        try:
            paths = patch_paths(report["patch_diff"], source_path)
        except ValueError as exc:
            evidence["patch_scope"] = f"Patch rejected by diff policy: {exc}"
            return True, ""
        patched = None
        try:
            patched = await sandbox.fork(base_env)
            await sandbox.put_file(patched, REPRO_PATH, report["repro"])
            await sandbox.put_file(patched, VERIFIER_PATH, verifier)
            await sandbox.put_file(patched, DISCOVERY_PATH, prop.code)
            await sandbox.put_file(patched, PATCH_PATH, report["patch_diff"].rstrip("\n") + "\n")
            test_cmd = f"python -m pytest -q -p no:cacheprovider --hypothesis-seed=0 {DISCOVERY_PATH}"
            discovery_before = await sandbox.run(patched, test_cmd, REPRO_TIMEOUT_S)
            if (discovery_before.exit_code != 1 or discovery_before.timed_out or
                any(error + ":" in discovery_before.output for error in FORBIDDEN_ERRORS)):
                evidence["patch_scope"] = "Patch unvalidated: unchanged discovery test did not demonstrate the original failure."
                return True, ""
            inspected = await sandbox.run(patched, f"git apply --numstat {PATCH_PATH}", 30.0)
            actual_paths = {line.split("\t", 2)[-1] for line in inspected.stdout.splitlines() if "\t" in line}
            if inspected.exit_code != 0 or actual_paths != paths:
                evidence["patch_scope"] = "Patch rejected: Git's parsed paths do not match the approved diff."
                return True, ""
            dry_run = await sandbox.run(patched, f"git apply --check {PATCH_PATH}", 30.0)
            if dry_run.exit_code != 0:
                evidence["patch_scope"] = "Patch failed git apply --check: " + dry_run.output[-1000:]
                return True, ""
            applied = await sandbox.run(patched, f"git apply --whitespace=nowarn {PATCH_PATH}", 30.0)
            guarded = await sandbox.run(patched, hash_guard(report["repro"], prop.code), 30.0)
            changed = await sandbox.run(patched, "git diff --name-only --no-renames HEAD", 30.0)
            if (applied.exit_code != 0 or guarded.exit_code != 0 or changed.exit_code != 0 or
                set(changed.stdout.splitlines()) != paths):
                evidence["patch_scope"] = "Patch rejected: application, protected hashes or resulting diff failed policy."
                return True, ""
            after = await sandbox.run(patched, f"python {VERIFIER_PATH}", REPRO_TIMEOUT_S)
            receipt = replay_receipt(after, report["repro"], target.qualname)
            discovery_after = await sandbox.run(patched, test_cmd, REPRO_TIMEOUT_S)
            guarded_after = await sandbox.run(patched, hash_guard(report["repro"], prop.code), 30.0)
            checks["patch"] = (after.exit_code == 0 and receipt is not None and receipt.get("passed", False)
                               and discovery_after.exit_code == 0 and not discovery_after.timed_out
                               and guarded_after.exit_code == 0)
            evidence.update(discovery_before=discovery_before.output, discovery_after=discovery_after.output,
                            patch_replay=receipt, protected_hashes_unchanged=guarded_after.exit_code == 0)
            evidence["patch_scope"] = (
                "Candidate patch passed the unchanged discovery property and repro, target reach, protected SHA-256 "
                "and library-only diff checks. No independent hidden or complete project-suite validation."
                if checks["patch"] else "Patch failed unchanged discovery/repro validation."
            )
        except SandboxError as exc:
            checks["patch"] = False
            evidence["patch_scope"] = f"Patch unvalidated due to sandbox error: {exc}"
        finally:
            if patched is not None:
                try:
                    await sandbox.close(patched)
                except SandboxError as exc:
                    checks["patch"] = False
                    evidence["cleanup_error"] = str(exc)
                    evidence["patch_scope"] = "Patch unvalidated: sandbox cleanup failed."
        # Optional patch failure cannot invalidate the independently reproduced finding.
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
    patch_verified = checks.get("patch", False)
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
        verification=evidence,
    )
