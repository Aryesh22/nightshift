"""Run one contract campaign in a sandbox and classify the result."""

from __future__ import annotations

import shlex
from dataclasses import replace

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
        result = await sandbox.run(env, contract_pytest_cmd(python=python), timeout_s)
        outcome = classify(result)
        if outcome.stats and outcome.stats.get("contract_hash") != contract.hash:
            return CampaignOutcome("infra_error", "worker receipt belongs to another contract", outcome.stats,
                                   execution=result)
        return replace(outcome, execution=result)
    finally:
        await sandbox.close(env)


async def run_literal_cases(sandbox, base_env, contract, harness, literals: list[str], *,
                            python: str = "python", timeout_s: float = 60):
    """One controller-owned experiment, restricted to small literal value fixtures.

    Only the input strategy changes. The same approved adapter and frozen predicate,
    comparator and precondition execute through run_contract in a fresh environment.
    """
    from nightshift.pipeline.contracts_stage import literal_value
    if not 1 <= len(literals) <= 5:
        raise ValueError("an experiment accepts 1–5 approved literal cases")
    values = [literal_value(s) for s in literals]
    strategy = "import copy\ndef inputs():\n    return st.sampled_from(" + repr(values) + ").map(copy.deepcopy)\n"
    return await run_contract(sandbox, base_env, contract, Harness(harness.adapter_source, strategy),
                              max_examples=len(values), python=python, timeout_s=timeout_s)

