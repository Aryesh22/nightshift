"""Contract records: what the documentation says an API must do, frozen before testing.

A contract is derived from docs, signatures and examples, never from the implementation
body or observed outputs. Once a campaign uses it, it can only change by `revise()`,
which creates a new version that records why and points at the old one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from typing import Literal

Family = Literal["roundtrip", "equivalent"]
Status = Literal["explicit", "inferred", "ambiguous"]
Equivalence = Literal["exact", "type_and_value"]


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Evidence:
    source: str  # versioned doc URL or path
    excerpt: str  # short exact supporting text
    content_hash: str  # hash of the retrieved material the excerpt came from
    retrieved: str = ""  # "live <iso time>", "cache <iso time>", or "manual"

    @classmethod
    def manual(cls, source: str, excerpt: str) -> Evidence:
        return cls(source=source, excerpt=excerpt, content_hash=sha256_text(excerpt), retrieved="manual")


@dataclass(frozen=True)
class Contract:
    contract_id: str
    package: str
    package_revision: str  # version string or commit the evidence applies to
    family: Family
    # Dotted public APIs the harness must actually call, e.g. ("base64.b64encode", ...)
    apis: tuple[str, ...]
    claim: str
    evidence: tuple[Evidence, ...]
    # Python expression over `x`; inputs where it is False are outside the contract.
    precondition: str = "True"
    equivalence: Equivalence = "exact"
    status: Status = "explicit"
    exclusions: tuple[str, ...] = ()  # documented unsupported or unspecified cases
    version: int = 1
    supersedes: str | None = None  # hash of the previous version
    revision_reason: str | None = None
    notes: dict = field(default_factory=dict, compare=False, hash=False)

    def semantic_fields(self) -> dict:
        d = asdict(self)
        d.pop("notes")
        return d

    @property
    def hash(self) -> str:
        return sha256_text(json.dumps(self.semantic_fields(), sort_keys=True, separators=(",", ":")))

    def revise(self, reason: str, **changes) -> Contract:
        if not reason.strip():
            raise ValueError("a contract revision needs a reason")
        forbidden = {"contract_id", "version", "supersedes", "revision_reason"} & changes.keys()
        if forbidden:
            raise ValueError(f"cannot set {sorted(forbidden)} directly")
        return replace(
            self, **changes, version=self.version + 1, supersedes=self.hash, revision_reason=reason
        )

    def to_dict(self) -> dict:
        return {**self.semantic_fields(), "hash": self.hash}
