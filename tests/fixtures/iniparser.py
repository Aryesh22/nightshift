"""INI format round-trip serializer and parser with whitespace stripping bug."""

from __future__ import annotations


def dumps_ini(data: dict[str, dict[str, str]]) -> str:
    """Serialize a section-keyed dictionary into INI text."""
    lines = []
    for section, mapping in sorted(data.items()):
        lines.append(f"[{section}]")
        for k, v in sorted(mapping.items()):
            lines.append(f"{k} = {v}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def loads_ini(text: str) -> dict[str, dict[str, str]]:
    """Parse INI text into a section-keyed dictionary.

    BUG: Strips all whitespace from values, breaking round-trip preservation
    for values intended to contain leading or trailing spaces.
    """
    result: dict[str, dict[str, str]] = {}
    current_sec = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_sec = line[1:-1].strip()
            result[current_sec] = {}
        elif "=" in line and current_sec:
            k, _, v = line.partition("=")
            # BUG: Unconditionally strips whitespace from value, losing indentation or spacing
            result[current_sec][k.strip()] = v.strip()
    return result
