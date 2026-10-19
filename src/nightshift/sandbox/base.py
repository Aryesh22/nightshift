"""The contract between the pipeline (Aryesh) and sandbox implementations (Jatin).

The pipeline only ever talks to `SandboxExecutor`. Implementations: DockerSandbox for local
development, NebiusContreeSandbox for Token Factory Sandboxes. Generated code must only
ever run through an executor, never directly on the host.

Expectations for every implementation:
- `prepare` clones `repo_url` at `ref` into the sandbox working directory (a git checkout,
  so the pipeline can `git apply` patches), runs `setup_cmds` there, and checkpoints the
  result. It must raise SandboxError if any setup command fails.
- `fork` returns an independent copy of a prepared environment; changes in a fork never
  leak into its parent or siblings.
- `run` executes a shell command in the working directory with no network access and
  never raises for a non-zero exit code; it reports it in RunResult.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class SandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnvHandle:
    id: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False

    @property
    def output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


class SandboxExecutor(ABC):
    @abstractmethod
    async def prepare(self, repo_url: str, ref: str, setup_cmds: list[str]) -> EnvHandle: ...

    @abstractmethod
    async def fork(self, env: EnvHandle) -> EnvHandle: ...

    @abstractmethod
    async def put_file(self, env: EnvHandle, path: str, content: str) -> None:
        """Write a text file at `path`, relative to the working directory."""

    @abstractmethod
    async def run(self, env: EnvHandle, cmd: str, timeout_s: float = 120.0) -> RunResult: ...

    @abstractmethod
    async def close(self, env: EnvHandle) -> None: ...
