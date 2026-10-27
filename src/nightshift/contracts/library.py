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


def make_json_contract() -> tuple[Contract, Harness]:
    """Helper constructor for stdlib json loads/dumps roundtrip."""
    contract = Contract(
        contract_id="stdlib.json.dumps_loads.roundtrip",
        package="python-stdlib",
        package_revision="3.12",
        family="roundtrip",
        apis=("json.dumps", "json.loads"),
        claim="For any dict of ASCII keys and integer values, loads(dumps(d)) == d.",
        evidence=(
            Evidence.manual(
                "https://docs.python.org/3/library/json.html#json.loads",
                "json.loads deserializes s to a Python object.",
            ),
            Evidence.manual(
                "https://docs.python.org/3/library/json.html#json.dumps",
                "json.dumps serializes obj to a JSON formatted str.",
            ),
        ),
        precondition="isinstance(x, dict)",
        equivalence="type_and_value",
        status="explicit",
    )
    harness = Harness(
        adapter_source=(
            "import json\n\n"
            "def forward(x):\n    return json.dumps(x)\n\n"
            "def backward(y):\n    return json.loads(y)\n"
        ),
        strategy_source=(
            "def inputs():\n"
            "    return st.dictionaries(st.text('abcdef', min_size=1, max_size=5), st.integers(-500, 500), max_size=4)\n"
        ),
    )
    return contract, harness


def make_urllib_quote_contract() -> tuple[Contract, Harness]:
    """Helper constructor for stdlib urllib.parse quote/unquote roundtrip."""
    contract = Contract(
        contract_id="stdlib.urllib.quote_unquote.roundtrip",
        package="python-stdlib",
        package_revision="3.12",
        family="roundtrip",
        apis=("urllib.parse.quote", "urllib.parse.unquote"),
        claim="For any printable ASCII string, unquote(quote(s)) returns original string.",
        evidence=(
            Evidence.manual(
                "https://docs.python.org/3/library/urllib.parse.html#urllib.parse.unquote",
                "Replace %xx escapes with their single-character equivalent.",
            ),
        ),
        precondition="isinstance(x, str)",
        equivalence="type_and_value",
        status="explicit",
    )
    harness = Harness(
        adapter_source=(
            "from urllib.parse import quote, unquote\n\n"
            "def forward(x):\n    return quote(x)\n\n"
            "def backward(y):\n    return unquote(y)\n"
        ),
        strategy_source=(
            "def inputs():\n"
            "    return st.text('abcdef0123456789_ -~', max_size=25)\n"
        ),
    )
    return contract, harness


def make_idna_contract() -> tuple[Contract, Harness]:
    """Helper constructor for installed idna encode/decode roundtrip."""
    contract = Contract(
        contract_id="installed.idna.encode_decode.roundtrip",
        package="idna",
        package_revision="3.x",
        family="roundtrip",
        apis=("idna.encode", "idna.decode"),
        claim="For any valid DNS label string, decode(encode(label)) returns label.",
        evidence=(
            Evidence.manual(
                "https://github.com/kjd/idna#usage",
                "idna.encode() and idna.decode() implement RFC 5891 IDNA processing.",
            ),
        ),
        precondition="isinstance(x, str)",
        equivalence="type_and_value",
        status="explicit",
    )
    harness = Harness(
        adapter_source=(
            "import idna\n\n"
            "def forward(x):\n    return idna.encode(x)\n\n"
            "def backward(y):\n    return idna.decode(y)\n"
        ),
        strategy_source=(
            "def inputs():\n"
            "    return st.from_regex(r'[a-z0-9]{1,8}(\\.[a-z0-9]{1,8}){1,2}', fullmatch=True)\n"
        ),
    )
    return contract, harness


JSON_ROUNDTRIP, JSON_HARNESS = make_json_contract()
URLLIB_ROUNDTRIP, URLLIB_HARNESS = make_urllib_quote_contract()
IDNA_ROUNDTRIP, IDNA_HARNESS = make_idna_contract()

