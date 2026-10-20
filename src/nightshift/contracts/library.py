"""Hand-written contract/harness pairs: the development baseline for generated ones."""

from __future__ import annotations

from nightshift.contracts.model import Contract, Evidence
from nightshift.contracts.render import Harness

PY_DOCS = "https://docs.python.org/3.12/library/base64.html"

BASE64_ROUNDTRIP = Contract(
    contract_id="stdlib.base64.b64.roundtrip",
    package="python-stdlib",
    package_revision="3.12",
    family="roundtrip",
    apis=("base64.b64encode", "base64.b64decode"),
    claim="For any bytes value s, b64decode(b64encode(s)) returns bytes equal to s.",
    evidence=(
        Evidence.manual(PY_DOCS + "#base64.b64encode",
                        "Encode the bytes-like object s using Base64 and return the encoded bytes."),
        Evidence.manual(PY_DOCS + "#base64.b64decode",
                        "Decode the Base64 encoded bytes-like object or ASCII string s and return the decoded bytes."),
    ),
    precondition="isinstance(x, bytes)",
    equivalence="type_and_value",
    # The round trip is implied by the two definitions, not stated as one sentence.
    status="inferred",
    exclusions=("altchars and validate options are not covered by this contract",),
)

BASE64_HARNESS = Harness(
    adapter_source=(
        "from base64 import b64decode, b64encode\n\n"
        "def forward(x):\n    return b64encode(x)\n\n"
        "def backward(y):\n    return b64decode(y)\n"
    ),
    strategy_source="def inputs():\n    return st.binary(max_size=256)\n",
)
