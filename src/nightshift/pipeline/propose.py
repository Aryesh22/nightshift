"""Stage 2+3: write a property test for a target and run it in the sandbox.

A test only counts as a valid proposal once it actually runs. Collection errors, vacuous
strategies, and import mistakes are fed back so the next rung can fix them.
"""

from __future__ import annotations

from nightshift.llm import NemotronClient
from nightshift.pipeline import prompts
from nightshift.pipeline.cascade import call_with_cascade
from nightshift.pipeline.classify import classify
from nightshift.pipeline.router import Router, bucket
from nightshift.pipeline.types import Execution, PropertyTest, RouteStep, Target
from nightshift.sandbox import EnvHandle, SandboxExecutor

TEST_TIMEOUT_S = 180.0


def parse_test(payload: dict) -> str:
    code = payload["test_code"]
    if not isinstance(code, str) or "def test_property" not in code or "@given" not in code:
        raise ValueError("test must define test_property decorated with @given")
    compile(code, "test_property.py", "exec")  # SyntaxError is a ValueError subclass
    return code


def pytest_cmd(path: str) -> str:
    return f"python -m pytest -x -q -p no:cacheprovider --hypothesis-seed=0 {path}"


async def propose_and_run(
    client: NemotronClient,
    router: Router,
    sandbox: SandboxExecutor,
    base_env: EnvHandle,
    target: Target,
    variant: int,
) -> tuple[PropertyTest | None, Execution | None, list[RouteStep]]:
    prop_id = f"{target.id}v{variant}"
    path = f"nightshift_tests/test_{prop_id}.py"
    env = await sandbox.fork(base_env)
    executions: list[Execution] = []

    async def verify(code: str) -> tuple[bool, str]:
        await sandbox.put_file(env, path, code)
        execution = classify(prop_id, await sandbox.run(env, pytest_cmd(path), TEST_TIMEOUT_S))
        executions.append(execution)
        if execution.status == "invalid":
            return False, f"The test did not run correctly:\n{execution.output[-2000:]}"
        return True, ""

    messages = [
        {"role": "system", "content": prompts.PROPOSE_SYSTEM},
        {
            "role": "user",
            "content": prompts.PROPOSE_USER.format(
                qualname=target.qualname,
                signature=target.signature,
                kind=target.kind,
                claim=target.claim,
                evidence=target.evidence,
                source=target.source or "(source unavailable)",
                variant_hint=prompts.VARIANT_HINTS[variant % len(prompts.VARIANT_HINTS)],
            ),
        },
    ]
    try:
        code, trace = await call_with_cascade(
            client, router, "propose", bucket(source=target.source), messages,
            parse=parse_test, verify=verify, temperature=0.7, variant=variant,
        )
    finally:
        await sandbox.close(env)
    if code is None:
        return None, executions[-1] if executions else None, trace
    return PropertyTest(prop_id, target.id, code, variant), executions[-1], trace
