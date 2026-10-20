"""Controller-owned property bodies, one per relation family.

These hold the assertion, the comparator and the precondition check. Model-written code
(adapter, strategy) is executed in separate namespaces and only supplies inputs and
observed results; it never sees or edits these bodies.
"""

from __future__ import annotations

from nightshift.contracts.model import sha256_text

# Functions each family needs from the adapter.
ADAPTER_FUNCTIONS = {
    "roundtrip": ("forward", "backward"),
    "equivalent": ("call_a", "call_b"),
}

_ROUNDTRIP = '''
def _check(x):
    try:
        out = _adapter.backward(_adapter.forward(x))
    except Exception as e:
        _fail("exception", x, error=f"{type(e).__name__}: {e}")
        raise
    _STATS["assertion_reached"] += 1
    if not _equiv(out, x):
        _fail("violation", x, actual=repr(out), expected=repr(x))
        raise AssertionError(f"contract {CONTRACT_ID} violated: backward(forward(x)) != x")
'''

_EQUIVALENT = '''
def _outcome(fn, x):
    try:
        return ("value", fn(x))
    except Exception as e:
        return ("raised", type(e))

def _check(x):
    a, b = _outcome(_adapter.call_a, x), _outcome(_adapter.call_b, x)
    _STATS["assertion_reached"] += 1
    same = a[0] == b[0] and (a[1] is b[1] if a[0] == "raised" else _equiv(a[1], b[1]))
    if not same:
        _fail("violation", x, actual=repr(a), expected=repr(b))
        raise AssertionError(f"contract {CONTRACT_ID} violated: call_a(x) and call_b(x) disagree")
'''

BODIES = {"roundtrip": _ROUNDTRIP, "equivalent": _EQUIVALENT}


def template_hash(family: str) -> str:
    return sha256_text(BODIES[family])
