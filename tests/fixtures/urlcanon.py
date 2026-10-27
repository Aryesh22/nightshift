"""Bug-free URL component codec used as a clean control task for false-alarm rejection."""

from __future__ import annotations

import urllib.parse


def encode_component(s: str) -> str:
    """Safely percent-encode a URI component for transport. Bug-free."""
    if not isinstance(s, str):
        raise TypeError("component must be a str")
    return urllib.parse.quote(s, safe="")


def decode_component(encoded: str) -> str:
    """Decode a percent-encoded URI component. Bug-free.

    Raises ValueError on malformed percent sequences (e.g. '%', '%1', '%ZZ').
    """
    if not isinstance(encoded, str):
        raise TypeError("encoded component must be a str")
    # Verify valid percent-encoding: every '%' must be followed by two hex digits
    i = 0
    n = len(encoded)
    while i < n:
        if encoded[i] == "%":
            if i + 2 >= n:
                raise ValueError("incomplete percent-encoding sequence at end of string")
            hex_part = encoded[i + 1 : i + 3]
            try:
                int(hex_part, 16)
            except ValueError:
                raise ValueError(f"invalid hex digits in percent-encoding: '%{hex_part}'")
            i += 3
        else:
            i += 1
    return urllib.parse.unquote(encoded, errors="strict")
