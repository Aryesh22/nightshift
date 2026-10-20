import sys
from pathlib import Path

import pytest

from nightshift.contracts import Contract, Evidence, Harness, HarnessRejected, classify, render_test
from nightshift.contracts.library import BASE64_HARNESS, BASE64_ROUNDTRIP
from nightshift.sandbox.base import LibraryTarget
from nightshift.sandbox.local import UnsafeLocalSandbox

FIXTURES = str(Path(__file__).parent / "fixtures")
EVIDENCE = (Evidence.manual("toycodec docs", "decode(encode(d)) returns d"),)

TOY_ROUNDTRIP = Contract(
    contract_id="toycodec.roundtrip", package="toycodec", package_revision="dev", family="roundtrip",
    apis=("toycodec.encode", "toycodec.decode"), claim="decode(encode(d)) == d", evidence=EVIDENCE,
    precondition="all('=' not in k and '\\n' not in k + v for k, v in x.items())",
)
TOY_HARNESS = Harness(
    adapter_source="import toycodec\n\ndef forward(x):\n    return toycodec.encode(x)\n\n"
    "def backward(y):\n    return toycodec.decode(y)\n",
    strategy_source="def inputs():\n    return st.dictionaries(st.text('ab=', min_size=1, max_size=3), "
    "st.text('ab \\n', max_size=4), max_size=3)\n",
)


async def run(contract, harness, **kw):
    box_exec = UnsafeLocalSandbox(python=sys.executable, pythonpath=[FIXTURES])
    base = await box_exec.prepare(LibraryTarget(contract.apis[0].split(".")[0]))
    box = await box_exec.fork(base)
    try:
        return classify(await box_exec.run(box, render_test(contract, harness, **kw), timeout_s=120))
    finally:
        await box_exec.close(box)


async def test_base64_contract_passes_and_is_not_vacuous():
    out = await run(BASE64_ROUNDTRIP, BASE64_HARNESS, max_examples=50)
    assert out.kind == "passed", out.reason
    assert out.stats["assertion_reached"] >= 50
    assert all(n > 0 for n in out.stats["api_calls"].values())
    assert out.stats["contract_hash"] == BASE64_ROUNDTRIP.hash


async def test_planted_roundtrip_bug_is_found_and_shrunk():
    out = await run(TOY_ROUNDTRIP, TOY_HARNESS)
    assert out.kind == "violation" and out.is_candidate
    assert out.stats["last_failure"]["input"] in ("{'a': ' '}", "{'b': ' '}")


async def test_equivalent_interfaces_disagreement_is_found():
    contract = Contract(
        contract_id="toycodec.slug.equiv", package="toycodec", package_revision="dev", family="equivalent",
        apis=("toycodec.slugify", "toycodec.slugify_fast"), claim="slugify_fast agrees with slugify",
        evidence=EVIDENCE, precondition="True",
    )
    harness = Harness(
        "import toycodec\n\ndef call_a(x):\n    return toycodec.slugify(x)\n\n"
        "def call_b(x):\n    return toycodec.slugify_fast(x)\n",
        "def inputs():\n    return st.text('aB \\t', max_size=5)\n",
    )
    out = await run(contract, harness)
    assert out.kind == "violation"


async def test_adapter_that_skips_the_api_is_vacuous():
    lazy = Harness("def forward(x):\n    return x\n\ndef backward(y):\n    return y\n", BASE64_HARNESS.strategy_source)
    out = await run(BASE64_ROUNDTRIP, lazy, max_examples=20)
    assert out.kind == "vacuous" and "never called" in out.reason


async def test_precondition_that_rejects_everything_is_vacuous():
    contract = BASE64_ROUNDTRIP.revise("test: impossible precondition", precondition="False")
    out = await run(contract, BASE64_HARNESS, max_examples=20)
    assert out.kind == "vacuous"


async def test_broken_strategy_is_setup_error_not_bug():
    broken = Harness(BASE64_HARNESS.adapter_source, "def inputs():\n    return st.binary(max_size=-1)\n")
    out = await run(BASE64_ROUNDTRIP, broken)
    assert out.kind in ("setup_error", "infra_error") and not out.is_candidate


@pytest.mark.parametrize("adapter, problem", [
    ("def forward(x):\n    try:\n        return f(x)\n    except Exception:\n        return x\n"
     "def backward(y):\n    return y\n", "broad `except`"),
    ("def forward(x):\n    assert x\n    return x\ndef backward(y):\n    return y\n", "`assert`"),
    ("import sys\ndef forward(x):\n    sys.exit(0)\ndef backward(y):\n    return y\n", "sys.exit"),
    ("def forward(x):\n    return x\n", "missing top-level function `backward`"),
])
def test_audit_rejects_harness_tricks(adapter, problem):
    with pytest.raises(HarnessRejected) as e:
        render_test(BASE64_ROUNDTRIP, Harness(adapter, BASE64_HARNESS.strategy_source))
    assert any(problem in p for p in e.value.problems)


def test_strategy_may_not_filter_with_assume():
    bad = Harness(BASE64_HARNESS.adapter_source, "def inputs():\n    return st.binary().filter(lambda b: assume(b))\n")
    with pytest.raises(HarnessRejected):
        render_test(BASE64_ROUNDTRIP, bad)


def test_revision_is_traceable_and_ambiguous_contracts_are_refused():
    v2 = BASE64_ROUNDTRIP.revise("docs say ASCII str input is also accepted", precondition="True")
    assert v2.version == 2 and v2.supersedes == BASE64_ROUNDTRIP.hash and v2.hash != BASE64_ROUNDTRIP.hash
    with pytest.raises(ValueError):
        BASE64_ROUNDTRIP.revise("  ")
    with pytest.raises(HarnessRejected):
        render_test(BASE64_ROUNDTRIP.revise("unclear", status="ambiguous"), BASE64_HARNESS)
