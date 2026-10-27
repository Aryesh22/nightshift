"""Environment variable codec with realistic quoting/escaping bugs for testing."""

from __future__ import annotations


def dump_env(mapping: dict[str, str]) -> str:
    """Serialize a mapping of environment variables to .env format.

    BUG: Does not escape quotes or internal newlines inside quoted values.
    """
    lines = []
    for k, v in sorted(mapping.items()):
        if any(c in v for c in ' \t\n"='):
            # Naive quoting without escaping internal double quotes
            lines.append(f'{k}="{v}"')
        else:
            lines.append(f"{k}={v}")
    return "\n".join(lines)


def parse_env(text: str) -> dict[str, str]:
    """Parse a .env formatted string into a dictionary.

    BUG: Naively strips outer quotes without unescaping, causing round-trip failure
    when values contain internal double quotes.
    """
    mapping = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if len(v) >= 2 and v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        mapping[k] = v
    return mapping


def is_valid_identifier(k: str) -> bool:
    """Precondition check for environment keys."""
    return bool(k and k.isidentifier())
