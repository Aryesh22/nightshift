"""Run one contract campaign in a sandbox and classify the result."""

from __future__ import annotations

import shlex

from nightshift.contracts.model import Contract
from nightshift.contracts.outcome import CampaignOutcome, classify
from nightshift.contracts.render import Harness, render_test
from nightshift.sandbox import EnvHandle, SandboxExecutor

TEST_PATH = "nightshift_tests/test_contract.py"


def contract_pytest_cmd(path: str = TEST_PATH, python: str = "python") -> str:
    # -s so the NIGHTSHIFT_STATS line reaches stdout
    return f"{shlex.quote(python)} -m pytest -q -s -p no:cacheprovider {path}"


async def run_contract(
    sandbox: SandboxExecutor,
    base_env: EnvHandle,
    contract: Contract,
    harness: Harness,
    *,
    max_examples: int = 200,
    timeout_s: float = 120.0,
    python: str = "python",
) -> CampaignOutcome:
    """Render (which audits), run in a fresh fork, classify. Raises HarnessRejected before running."""
    code = render_test(contract, harness, max_examples=max_examples)
    env = await sandbox.fork(base_env)
    try:
        await sandbox.put_file(env, TEST_PATH, code)
        return classify(await sandbox.run(env, contract_pytest_cmd(python=python), timeout_s))
    finally:
        await sandbox.close(env)

