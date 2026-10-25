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
    _input = _input_repr(x)
    try:
        _x_expected = _snapshot(x)
        encoded = _invoke(_adapter.forward, x, _APIS[0])
        out = _invoke(_adapter.backward, encoded, _APIS[1])
        out = _snapshot(out)
    except _FidelityError as e:
        _fail("vacuous", _input, error=str(e))
        raise
    except (_UnsupportedDomain, _AdapterError) as e:
        _fail("setup_error", _input, error=str(e))
        raise
    except Exception as e:
        kind = "exception" if _FAILURE_API else "setup_error"
        _fail(kind, _input, error=f"{type(e).__name__}: {e}", target_api=_FAILURE_API)
        raise
    _STATS["assertion_reached"] += 1
    if not _equiv(out, _x_expected):
        _fail("violation", _input, actual=repr(out), expected=repr(_x_expected))
        raise AssertionError(f"contract {CONTRACT_ID} violated: backward(forward(x)) != x")
'''

_EQUIVALENT = '''
def _outcome(fn, x, api):
    try:
        return ("value", _snapshot(_invoke(fn, x, api)))
    except (_UnsupportedDomain, _AdapterError, _FidelityError):
        raise
    except Exception as e:
        return ("raised", type(e))

def _check(x):
    _input = _input_repr(x)
    try:
        _x_a, _x_b = _snapshot(x), _snapshot(x)
        a = _outcome(_adapter.call_a, _x_a, _APIS[0])
        b = _outcome(_adapter.call_b, _x_b, _APIS[1])
    except _FidelityError as e:
        _fail("vacuous", _input, error=str(e))
        raise
    except (_UnsupportedDomain, _AdapterError) as e:
        _fail("setup_error", _input, error=str(e))
        raise
    _STATS["assertion_reached"] += 1
    same = a[0] == b[0] and (a[1] is b[1] if a[0] == "raised" else _equiv(a[1], b[1]))
    if not same:
        _fail("violation", _input, actual=repr(a), expected=repr(b))
        raise AssertionError(f"contract {CONTRACT_ID} violated: call_a(x) and call_b(x) disagree")
'''

BODIES = {"roundtrip": _ROUNDTRIP, "equivalent": _EQUIVALENT}


def template_hash(family: str) -> str:
    return sha256_text(BODIES[family])
