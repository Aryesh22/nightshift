"""Docker executor: filesystem checkpoints and independent, offline worker containers.

Preparation alone has network access for clone/install. No host directories, Docker
socket, application environment or credentials are mounted into a workload container.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import time
import uuid
from dataclasses import replace
from pathlib import PurePosixPath

from nightshift.sandbox.base import EnvHandle, RunResult, SandboxError, SandboxExecutor

_DOCKERFILE = b'''FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \\
    && rm -rf /var/lib/apt/lists/* \\
    && useradd --create-home --uid 10001 nightshift \\
    && python -m venv /opt/venv \\
    && /opt/venv/bin/pip install --no-cache-dir pytest==9.1.1 hypothesis==6.170.5 \\
    && mkdir /work && chown -R 10001:10001 /work /opt/venv
ENV PATH="/opt/venv/bin:$PATH" HOME="/home/nightshift" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
WORKDIR /work
CMD ["sleep", "infinity"]
'''


class _OutputLimit(Exception):
    pass


class DockerSandbox(SandboxExecutor):
    def __init__(self, *, image: str | None = None, host: str | None = None,
                 memory: str = "512m", cpus: float = 1, pids: int = 128,
                 output_limit: int = 1_048_576):
        self.image = image or os.getenv("NIGHTSHIFT_SANDBOX_IMAGE", "nightshift-runtime:py312-v1")
        self.host = host
        self.memory, self.cpus, self.pids = memory, cpus, pids
        self.output_limit = output_limit
        self._envs: dict[str, dict] = {}
        self._image_id: str | None = None
        self._image_lock = asyncio.Lock()

    async def _command(self, *args: str, input_bytes: bytes | None = None,
                       timeout_s: float = 30, container: str | None = None) -> RunResult:
        command = ["docker", *(["--host", self.host] if self.host else []), *args]
        started = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *command, stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise SandboxError("Docker CLI is unavailable") from exc
        buffers = [bytearray(), bytearray()]
        total = 0

        async def read(stream, index):
            nonlocal total
            while chunk := await stream.read(65536):
                remaining = self.output_limit - total
                buffers[index].extend(chunk[:max(remaining, 0)])
                total += len(chunk)
                if total > self.output_limit:
                    raise _OutputLimit()

        async def write():
            if input_bytes is not None:
                try:
                    proc.stdin.write(input_bytes)
                    await proc.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    proc.stdin.close()

        tasks = [asyncio.create_task(read(proc.stdout, 0)), asyncio.create_task(read(proc.stderr, 1)),
                 asyncio.create_task(write()), asyncio.create_task(proc.wait())]
        timed_out = False
        limited = False
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout_s)
        except (TimeoutError, _OutputLimit, asyncio.CancelledError) as exc:
            timed_out, limited = isinstance(exc, TimeoutError), isinstance(exc, _OutputLimit)
            if proc.returncode is None:
                proc.kill()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.wait_for(proc.wait(), 5)
            if container:
                # Killing only the CLI would leave worker descendants alive.
                stopped = await asyncio.shield(self._command("rm", "--force", container, timeout_s=15))
                if stopped.exit_code != 0:
                    raise SandboxError("failed to terminate the worker container")
            if isinstance(exc, asyncio.CancelledError):
                raise
        stderr = buffers[1].decode(errors="replace")
        if limited:
            stderr += "\nworker exceeded its output limit"
        return RunResult(proc.returncode if proc.returncode is not None else -1,
                         buffers[0].decode(errors="replace"), stderr,
                         time.monotonic() - started, timed_out)

    async def _checked(self, *args: str, **kwargs) -> RunResult:
        result = await self._command(*args, **kwargs)
        if result.exit_code != 0 or result.timed_out:
            raise SandboxError(f"Docker {args[0]} failed: {result.output[-1500:]}")
        return result

    async def _ensure_image(self):
        async with self._image_lock:
            if self._image_id:
                return
            await self._checked("info", "--format", "{{.ServerVersion}}")
            result = await self._command("image", "inspect", "--format", "{{.Id}}", self.image)
            if result.exit_code != 0:
                if self.image != "nightshift-runtime:py312-v1":
                    raise SandboxError("configured sandbox image must already exist on the Docker engine")
                await self._checked("build", "--tag", self.image, "-", input_bytes=_DOCKERFILE, timeout_s=600)
                result = await self._checked("image", "inspect", "--format", "{{.Id}}", self.image)
            self._image_id = result.stdout.strip()

    async def _create(self, image: str, *, network: str = "none") -> str:
        name = "nightshift-" + uuid.uuid4().hex
        try:
            await self._checked(
                "create", "--name", name, "--network", network, "--init", "--cpus", str(self.cpus),
                "--memory", self.memory, "--memory-swap", self.memory, "--pids-limit", str(self.pids),
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "10001:10001",
                "--ulimit", "fsize=67108864:67108864", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
                "--log-opt", "max-size=1m", "--log-opt", "max-file=1", "--workdir", "/work",
                image, "sleep", "infinity",
            )
            await self._checked("start", name)
        except BaseException:
            await asyncio.shield(self._command("rm", "--force", name))
            raise
        return name

    def _state(self, env: EnvHandle) -> dict:
        try:
            return self._envs[env.id]
        except KeyError as exc:
            raise SandboxError("environment is closed or belongs to another executor") from exc

    async def prepare(self, repo_url: str, ref: str, setup_cmds: list[str]) -> EnvHandle:
        await self._ensure_image()
        name = await self._create(self._image_id, network="bridge")
        checkpoint = None
        try:
            commands = []
            if repo_url:
                if not ref or ref.startswith("-"):
                    raise SandboxError("an explicit non-option source revision is required")
                commands = [f"git clone --no-checkout -- {shlex.quote(repo_url)} .",
                            f"git fetch --depth 1 origin {shlex.quote(ref)}",
                            f"git checkout --detach FETCH_HEAD"]
            for cmd in [*commands, *setup_cmds]:
                result = await self._command("exec", name, "sh", "-c", cmd, timeout_s=600, container=name)
                if result.exit_code != 0 or result.timed_out:
                    raise SandboxError(f"sandbox preparation failed: {result.output[-1500:]}")
            checkpoint = (await self._checked("commit", name)).stdout.strip()
            offline = await self._create(checkpoint)
            self._envs[offline] = {"image": checkpoint, "owned_image": checkpoint}
            return EnvHandle(offline, {"image": checkpoint, "backend": "docker"})
        except BaseException:
            if checkpoint:
                await asyncio.shield(self._command("image", "rm", checkpoint))
            raise
        finally:
            await asyncio.shield(self._command("rm", "--force", name))

    async def fork(self, env: EnvHandle) -> EnvHandle:
        self._state(env)
        checkpoint = (await self._checked("commit", env.id)).stdout.strip()
        try:
            name = await self._create(checkpoint)
        except BaseException:
            await asyncio.shield(self._command("image", "rm", checkpoint))
            raise
        self._envs[name] = {"image": checkpoint, "owned_image": checkpoint}
        return EnvHandle(name, {"image": checkpoint, "backend": "docker"})

    async def put_file(self, env: EnvHandle, path: str, content: str) -> None:
        self._state(env)
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            raise SandboxError("file must be inside the sandbox work directory")
        script = ("import sys; from pathlib import Path; p=Path('/work')/sys.argv[1]; "
                  "assert p.resolve().is_relative_to('/work'), 'path escapes work directory'; "
                  "p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(sys.stdin.buffer.read())")
        await self._checked("exec", "-i", env.id, "python", "-c", script, path,
                            input_bytes=content.encode(), container=env.id)

    async def run(self, env: EnvHandle, cmd: str, timeout_s: float = 120.0) -> RunResult:
        self._state(env)
        # `timeout` inside the container ends the command (and its children, via --init)
        # without taking the environment with it, so a slow test on the base environment
        # does not strand the rest of the campaign. The outer deadline is the last resort
        # and does remove the container.
        guarded = f"timeout -k 2 {timeout_s:g} sh -c {shlex.quote(cmd)}"
        result = await self._command("exec", env.id, "sh", "-c", guarded,
                                     timeout_s=timeout_s + 15, container=env.id)
        if result.exit_code in (124, 137) and not result.timed_out:
            return replace(result, timed_out=True)
        return result

    async def close(self, env: EnvHandle) -> None:
        state = self._envs.pop(env.id, None)
        if state:
            removed = await self._command("rm", "--force", env.id)
            if removed.exit_code != 0 and "No such container" not in removed.output:
                self._envs[env.id] = state
                raise SandboxError("container cleanup failed: " + removed.output[-1000:])
            await self._checked("image", "rm", state["owned_image"])
