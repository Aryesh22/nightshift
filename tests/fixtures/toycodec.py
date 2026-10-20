"""A tiny library with planted bugs, used to prove the harness catches them."""


def encode(d: dict) -> str:
    return "\n".join(f"{k}={v}" for k, v in d.items())


def decode(text: str) -> dict:
    pairs = (line.partition("=") for line in text.splitlines() if line)
    return {k: v.strip() for k, _, v in pairs}  # BUG: strips whitespace from values


def slugify(s: str) -> str:
    return "-".join(s.lower().split())


def slugify_fast(s: str) -> str:
    return s.lower().replace(" ", "-")  # BUG: disagrees with slugify on repeated/other whitespace
