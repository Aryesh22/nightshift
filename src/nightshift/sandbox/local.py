"""Development-only executor: runs tests in a subprocess of this machine's Python.

NOT ISOLATED. Use it only for trusted targets (the stdlib, our own fixtures). Untrusted
packages must go through DockerSandbox or the Nebius sandbox.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

from nightshift.sandbox.base import LibraryTarget, RunResult, SandboxExecutor, SandboxHandle

PYTEST_ARGS = ("-m", "pytest", "-q", "-s", "-p", "no:cacheprovider")
SECRET_ENV_PREFIXES = ("NEBIUS_", "TAVILY_", "OPENAI_", "ANTHROPIC_", "NIGHTSHIFT_")


def clean_env(extra_pythonpath: list[str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(SECRET_ENV_PREFIXES)}
    if extra_pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(extra_pythonpath + [env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return env


class UnsafeLocalSandbox(SandboxExecutor):
    def __init__(self, python: str = sys.executable, pythonpath: list[str] | None = None):
        self.python = python
        self.pythonpath = pythonpath or []

    async def prepare(self, target: LibraryTarget) -> SandboxHandle:
        proc = await asyncio.create_subprocess_exec(
            self.python, "-c", f"import {target.name}",
            env=clean_env(self.pythonpath), stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"{target.name} is not importable locally: {err.decode().strip()}")
        return SandboxHandle(id=f"local-{target.name}", meta={"target": target.name})

    async def fork(self, base: SandboxHandle) -> SandboxHandle:
        workdir = tempfile.mkdtemp(prefix="nightshift-")
        return SandboxHandle(id=f"{base.id}-{uuid.uuid4().hex[:8]}", meta={**base.meta, "workdir": workdir})

    async def run(self, box: SandboxHandle, test_code: str, *, timeout_s: float = 60.0) -> RunResult:
        workdir = Path(box.meta["workdir"])
        test_file = workdir / "test_nightshift.py"
        test_file.write_text(test_code)
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            self.python, *PYTEST_ARGS, str(test_file),
            cwd=workdir, env=clean_env(self.pythonpath),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout_s)
            timed_out = False
        except TimeoutError:
            proc.kill()
            out, err = await proc.communicate()
            timed_out = True
        return RunResult(
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=out.decode(errors="replace"),
            stderr=err.decode(errors="replace"),
            duration_s=time.monotonic() - start,
            timed_out=timed_out,
        )

    async def close(self, box: SandboxHandle) -> None:
        shutil.rmtree(box.meta.get("workdir", ""), ignore_errors=True)
