"""Docker on an explicitly configured Nebius VM; no local or native-API fallback.

This transport requires a remote Docker engine provisioned by the operator. It does
not claim to implement the unverified Nebius/Contree managed sandbox API.
"""

from __future__ import annotations

import os

from nightshift.sandbox.base import SandboxError
from nightshift.sandbox.docker import DockerSandbox


class NebiusDockerSandbox(DockerSandbox):
    def __init__(self, *, host: str | None = None, **kwargs):
        super().__init__(host=host or os.getenv("NIGHTSHIFT_NEBIUS_DOCKER_HOST"), **kwargs)

    async def prepare(self, repo_url, ref, setup_cmds):
        if not self.host or not self.host.startswith("ssh://"):
            raise SandboxError("set NIGHTSHIFT_NEBIUS_DOCKER_HOST=ssh://user@your-nebius-vm; local fallback is disabled")
        return await super().prepare(repo_url, ref, setup_cmds)
