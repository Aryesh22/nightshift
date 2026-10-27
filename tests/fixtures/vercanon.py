"""Version canonicalization equivalence pair with pre-release separator bug."""

from __future__ import annotations

import re

_CANON_RE = re.compile(
    r"^v?(?P<release>[0-9]+(?:\.[0-9]+)*)(?:[-._]?(?P<pre>(?:a|b|c|rc|alpha|beta|preview))[.-]?(?P<prenum>[0-9]+)?)?$",
    re.IGNORECASE,
)


def canonical_version(v: str) -> str:
    """Canonical PEP 440 style normalizer (reference specification)."""
    m = _CANON_RE.match(v.strip())
    if not m:
        return v.strip().lower()
    release = m.group("release")
    pre = m.group("pre")
    if not pre:
        return release
    pre_tag = pre.lower()
    if pre_tag == "alpha":
        pre_tag = "a"
    elif pre_tag == "beta":
        pre_tag = "b"
    elif pre_tag in ("c", "preview"):
        pre_tag = "rc"
    prenum = m.group("prenum") or "0"
    return f"{release}{pre_tag}{prenum}"


def normalize_version(v: str) -> str:
    """Faster drop-in alternative for version normalization.

    BUG: Leaves hyphen before pre-release tag (e.g. '1.2.0-rc1' instead of '1.2.0rc1').
    """
    cleaned = v.strip().lower().lstrip("v")
    # BUG: Disagrees with canonical_version on pre-release separator
    if "-rc" in cleaned:
        cleaned = re.sub(r"-rc\.?(\d+)", r"-rc\1", cleaned)
    elif "-alpha" in cleaned or "-a" in cleaned:
        cleaned = re.sub(r"-(?:alpha|a)\.?(\d+)", r"-a\1", cleaned)
    elif "-beta" in cleaned or "-b" in cleaned:
        cleaned = re.sub(r"-(?:beta|b)\.?(\d+)", r"-b\1", cleaned)
    else:
        # Standard release numbers agree
        cleaned = re.sub(r"[^0-9.]", "", cleaned)
    return cleaned
