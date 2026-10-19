"""The SandboxExecutor contract between the AI pipeline (Aryesh) and execution (Jatin).

The pipeline only ever talks to this interface. Implementations: DockerSandbox
(local), NebiusContreeSandbox (Token Factory Sandboxes), FakeSandbox (tests).

Lifecycle:
    base = await executor.prepare(target)   # install the library once, take a checkpoint
    box = await executor.fork(base)         # cheap copy of the checkpoint, one per test batch
    result = await executor.run(box, test_code, timeout_s=60)
    await executor.close(box)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LibraryTarget:
    name: str  # PyPI name, e.g. "attrs"
    version: str | None = None  # None means latest
    repo: str | None = None  # git URL, used to read source and dedupe issues
    extra_packages: tuple[str, ...] = ("hypothesis", "pytest")


@dataclass(frozen=True)
class SandboxHandle:
    id: str  # opaque to the pipeline; implementations put whatever they need here
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    # pytest node id -> "passed" | "failed" | "error", when the runner can tell
    outcomes: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class SandboxExecutor(ABC):
    @abstractmethod
    async def prepare(self, target: LibraryTarget) -> SandboxHandle:
        """Install the target and its test deps, then checkpoint. Called once per run."""

    @abstractmethod
    async def fork(self, base: SandboxHandle) -> SandboxHandle:
        """Return an isolated sandbox that starts from the `prepare` checkpoint."""

    @abstractmethod
    async def run(self, box: SandboxHandle, test_code: str, *, timeout_s: float = 60.0) -> RunResult:
        """Write `test_code` to a test file in `box`, run pytest on it, return the result.

        Must never raise for test failures, crashes or timeouts; report them in RunResult.
        """

    @abstractmethod
    async def close(self, box: SandboxHandle) -> None:
        """Free the sandbox. Safe to call twice."""
