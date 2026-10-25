"""Development-only executor: runs commands in a temp directory on this machine.

NOT ISOLATED: no network or filesystem sandboxing. Use it only for trusted targets
(the stdlib, our own fixtures). Untrusted packages must go through DockerSandbox or
the Nebius sandbox.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from nightshift.sandbox.base import EnvHandle, RunResult, SandboxError, SandboxExecutor

SECRET_ENV_PREFIXES = ("NEBIUS_", "TAVILY_", "OPENAI_", "OPENROUTER_", "ANTHROPIC_", "NIGHTSHIFT_")


def clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(SECRET_ENV_PREFIXES)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


class UnsafeLocalSandbox(SandboxExecutor):
    async def prepare(self, repo_url: str, ref: str, setup_cmds: list[str]) -> EnvHandle:
        """`repo_url` may be a local directory (copied) or a git URL (cloned at `ref`)."""
        workdir = Path(tempfile.mkdtemp(prefix="nightshift-"))
        env = EnvHandle(id=f"local-{uuid.uuid4().hex[:8]}", meta={"workdir": str(workdir)})
        if repo_url and Path(repo_url).is_dir():
            shutil.copytree(repo_url, workdir, dirs_exist_ok=True)
        elif repo_url:
            setup_cmds = [f"git clone -q --no-checkout -- {shlex.quote(repo_url)} .",
                          f"git checkout -q --detach {shlex.quote(ref)}"] + list(setup_cmds)
        for cmd in setup_cmds:
            result = await self.run(env, cmd, timeout_s=600)
            if result.exit_code != 0:
                await self.close(env)
                raise SandboxError(f"setup failed: {cmd}\n{result.output[-2000:]}")
        return env

    async def fork(self, env: EnvHandle) -> EnvHandle:
        workdir = tempfile.mkdtemp(prefix="nightshift-")
        shutil.copytree(env.meta["workdir"], workdir, dirs_exist_ok=True)
        return EnvHandle(id=f"{env.id}-{uuid.uuid4().hex[:8]}", meta={"workdir": workdir})

    async def put_file(self, env: EnvHandle, path: str, content: str) -> None:
        target = Path(env.meta["workdir"]) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    async def run(self, env: EnvHandle, cmd: str, timeout_s: float = 120.0) -> RunResult:
        start = time.monotonic()
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=env.meta["workdir"], env=clean_env(),
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

    async def close(self, env: EnvHandle) -> None:
        shutil.rmtree(env.meta.get("workdir", ""), ignore_errors=True)
