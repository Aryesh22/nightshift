"""Regenerate samples/report.json, the FAKE report the dashboard builds against (schema v1).

Usage: python samples/make_sample_report.py
Covers every status the dashboard must render, including rejected and unresolved,
with rich v1.1 Core contracts, Tavily retrieval receipts, and active refutation traces.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from nightshift.contracts.model import sha256_text
from nightshift.report import (
    Check, ContractRef, EvidenceRef, Finding, KnownBehaviour, Library, Report, RouteStep, Stats,
)
from nightshift.tavily import RetrievalReceipt

DOCS = "https://fakelib.readthedocs.io/en/1.4.2/api.html"
REPO = "https://github.com/example/fakelib"

roundtrip = ContractRef(
    contract_id="fakelib.codec.roundtrip",
    version=1,
    hash=sha256_text("fakelib.codec.roundtrip:v1"),
    family="roundtrip",
    claim="For any dict of str to str without '=' or newlines in keys, decode(encode(d)) == d.",
    status="explicit",
    evidence=[
        EvidenceRef(
            source=DOCS + "#fakelib.decode",
            excerpt="decode() is the exact inverse of encode().",
            retrieved="live 2026-10-23T02:14:00Z",
            content_hash=sha256_text("decode() is the exact inverse of encode()."),
        ),
    ],
)

equivalent = ContractRef(
    contract_id="fakelib.slug.equivalent",
    version=1,
    hash=sha256_text("fakelib.slug.equivalent:v1"),
    family="equivalent",
    claim="slugify_fast(s) returns the same result as slugify(s) for every str.",
    status="explicit",
    evidence=[
        EvidenceRef(
            source=DOCS + "#fakelib.slugify_fast",
            excerpt="A faster drop-in replacement for slugify().",
            retrieved="live 2026-10-23T02:15:00Z",
            content_hash=sha256_text("A faster drop-in replacement for slugify()."),
        ),
    ],
)

merge = ContractRef(
    contract_id="fakelib.merge.associative",
    version=2,
    hash=sha256_text("fakelib.merge.associative:v2"),
    family="composition",
    claim="merge(merge(a, b), c) == merge(a, merge(b, c)) for dicts of lists.",
    status="inferred",
    evidence=[
        EvidenceRef(
            source=DOCS + "#fakelib.merge",
            excerpt="Merging is order-independent for list values.",
            retrieved="cache 2026-10-23T02:15:00Z",
            content_hash=sha256_text("Merging is order-independent for list values."),
        ),
    ],
)

ranges = ContractRef(
    contract_id="fakelib.ranges.domain",
    version=1,
    hash=sha256_text("fakelib.ranges.domain:v1"),
    family="roundtrip",
    claim="parse_range(format_range(r)) == r for valid ranges.",
    status="explicit",
    evidence=[
        EvidenceRef(
            source=DOCS + "#fakelib.parse_range",
            excerpt="parse_range(r) expects a non-empty range string.",
            retrieved="live 2026-10-23T02:16:00Z",
            content_hash=sha256_text("parse_range(r) expects a non-empty range string."),
        ),
    ],
)

receipt_extract = RetrievalReceipt(
    url=DOCS + "#fakelib.decode",
    retrieved_at="2026-10-23T02:14:00Z",
    content_hash=sha256_text("Fakelib API Reference v1.4.2: decode(encode(d)) == d. decode() is the exact inverse of encode()."),
    excerpt="decode() is the exact inverse of encode().",
    request_id="tvly-req-extract-48201",
    status="live",
    endpoint="extract",
    text="Fakelib API Reference v1.4.2: decode(encode(d)) == d. decode() is the exact inverse of encode().",
    response_hash=sha256_text("raw_extract_response_48201"),
    credits=1.0,
    credit_status="reported",
    source_version="1.4.2",
    version_match=True,
)

receipt_search = RetrievalReceipt(
    url="https://github.com/example/fakelib/issues/88",
    retrieved_at="2026-10-23T02:15:30Z",
    content_hash=sha256_text("Issue #88: slugify with tab characters produces unexpected output."),
    excerpt="Issue #88: slugify with tab characters produces unexpected output.",
    request_id="tvly-req-search-91304",
    status="live",
    endpoint="search",
    text="Discussion on Issue #88 regarding slugify whitespace normalization with tabs vs spaces.",
    response_hash=sha256_text("raw_search_response_91304"),
    query="https://github.com/example/fakelib/ slugify whitespace tab",
    credits=1.0,
    credit_status="reported",
    source_version=None,
    version_match=False,
)

receipt_search_codec = RetrievalReceipt(
    url="https://github.com/example/fakelib/issues?q=strip+whitespace",
    retrieved_at="2026-10-23T02:14:45Z",
    content_hash=sha256_text("No issues matching 'strip whitespace' found in fakelib repository."),
    excerpt="No matching issues or PRs found.",
    request_id="tvly-req-search-91305",
    status="live",
    endpoint="search",
    text="No matching issues or PRs found.",
    response_hash=sha256_text("raw_search_response_91305"),
    query="https://github.com/example/fakelib/ fakelib.decode strip whitespace",
    credits=1.0,
    credit_status="reported",
    source_version=None,
    version_match=False,
)

receipt_extract_ranges = RetrievalReceipt(
    url=DOCS + "#fakelib.parse_range",
    retrieved_at="2026-10-23T02:16:00Z",
    content_hash=sha256_text("Fakelib API Reference: parse_range(r) expects a non-empty range string. Empty strings raise ValueError."),
    excerpt="parse_range(r) expects a non-empty range string.",
    request_id="tvly-req-extract-48202",
    status="live",
    endpoint="extract",
    text="Fakelib API Reference: parse_range(r) expects a non-empty range string. Empty strings raise ValueError.",
    response_hash=sha256_text("raw_extract_response_48202"),
    credits=1.0,
    credit_status="reported",
    source_version="1.4.2",
    version_match=True,
)

retrieval_receipts = [
    receipt_extract.to_dict(),
    receipt_search.to_dict(),
    receipt_search_codec.to_dict(),
    receipt_extract_ranges.to_dict(),
]

sample_contracts = [
    {
        "contract_id": roundtrip.contract_id, "version": roundtrip.version, "hash": roundtrip.hash,
        "family": roundtrip.family, "claim": roundtrip.claim, "status": roundtrip.status,
        "evidence": [asdict(e) for e in roundtrip.evidence],
    },
    {
        "contract_id": equivalent.contract_id, "version": equivalent.version, "hash": equivalent.hash,
        "family": equivalent.family, "claim": equivalent.claim, "status": equivalent.status,
        "evidence": [asdict(e) for e in equivalent.evidence],
    },
    {
        "contract_id": merge.contract_id, "version": merge.version, "hash": merge.hash,
        "family": merge.family, "claim": merge.claim, "status": merge.status,
        "evidence": [asdict(e) for e in merge.evidence],
    },
    {
        "contract_id": ranges.contract_id, "version": ranges.version, "hash": ranges.hash,
        "family": ranges.family, "claim": ranges.claim, "status": ranges.status,
        "evidence": [asdict(e) for e in ranges.evidence],
    },
]

findings = [
    Finding(
        id="f1",
        title="decode(encode(d)) drops trailing whitespace in values",
        status="human_validated",
        contract=roundtrip,
        repro="from fakelib import decode, encode\nd = {'a': ' '}\nprint(decode(encode(d)))  # {'a': ''}",
        actual="{'a': ''}",
        expected="{'a': ' '}",
        traceback="AssertionError: contract fakelib.codec.roundtrip violated: backward(forward(x)) != x",
        control="{'a': 'b'} round-trips correctly",
        replays_passed=3,
        replays_attempted=3,
        checks=[
            Check(
                question="Does a documented normal input work in this environment?",
                tool="run_control_input",
                result=json.dumps({
                    "execution": {"exit_code": 0, "output": "", "status": "pass"},
                    "kind": "passed",
                    "low_reach": False,
                    "reach_rate": 1.0,
                    "reason": "passed",
                    "stats": {"assertion_reached": 1, "entered": 1, "precondition_ok": 1},
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Does the pinned documentation and source support the claimed semantics?",
                tool="inspect_doc_and_source",
                result=json.dumps({
                    "contract_evidence": [asdict(e) for e in roundtrip.evidence],
                    "docstring": "Values may be any str; ' ' is allowed. Docs mention no whitespace stripping.",
                    "package_revision": "1.4.2",
                    "path": "fakelib/codec.py",
                    "source": "def decode(text: str) -> dict:\n    pairs = (line.partition('=') for line in text.splitlines() if line)\n    return {k: v.strip() for k, _, v in pairs}\n",
                    "source_hash": sha256_text("fakelib.codec"),
                    "symbol": "fakelib.decode",
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Is the discrepancy localized around the reduced boundary?",
                tool="check_boundary_neighborhood",
                result=json.dumps({
                    "inputs": ["{'a': 'b'}", "{'a': ''}"],
                    "original_input_preserved": "{'a': ' '}",
                    "outcome": {
                        "execution": {"exit_code": 0, "output": "", "status": "pass"},
                        "kind": "passed",
                        "low_reach": False,
                        "reach_rate": 1.0,
                        "reason": "passed",
                        "stats": {"assertion_reached": 2, "entered": 2, "precondition_ok": 2},
                    },
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Has this whitespace-dropping issue already been reported upstream?",
                tool="search_known_issues_tavily",
                result=json.dumps({
                    "extracted": [],
                    "failures": [],
                    "outcome": "no_match_found",
                    "query": "https://github.com/example/fakelib/ fakelib.decode fakelib.encode strip whitespace",
                    "search": [],
                }, sort_keys=True),
                effect="neutral",
            ),
        ],
        known_behaviour=KnownBehaviour(
            outcome="no_match_found",
            links=[],
            note="Searched issues and changelog for 'strip', 'whitespace'. Not proof it is new.",
        ),
        uncertainty="Maintainers may consider stripping intentional; the docs do not say so.",
        root_cause="decode() calls .strip() on each value (codec.py:44) but encode() never escapes whitespace.",
        patch_diff="--- a/fakelib/codec.py\n+++ b/fakelib/codec.py\n@@ -44 +44 @@\n-    return {k: v.strip() for k, _, v in pairs}\n+    return {k: v for k, _, v in pairs}\n",
        patch_validation="Discovery test, 212 project tests, 500 fresh hidden inputs: all pass.",
        cost_usd=0.061,
        route_trace=[
            RouteStep("contract", "lightning", 0, 0.0011),
            RouteStep("strategy", "lightning", 0, 0.0014),
            RouteStep("investigate", "super", 1024, 0.0118, escalation_reason="candidate survived replay"),
            RouteStep("review", "ultra", 2048, 0.0467, escalation_reason="validated survivor; root-cause review"),
        ],
    ),
    Finding(
        id="f2",
        title="slugify_fast disagrees with slugify on repeated spaces",
        status="ai_reviewed",
        contract=equivalent,
        repro="from fakelib import slugify, slugify_fast\nprint(slugify('a  b'), slugify_fast('a  b'))",
        actual="'a--b'",
        expected="'a-b'",
        control="'a b' agrees: 'a-b'",
        replays_passed=3,
        replays_attempted=3,
        checks=[
            Check(
                question="Does slugify_fast agree with slugify on single spaces?",
                tool="run_control_input",
                result=json.dumps({
                    "execution": {"exit_code": 0, "output": "", "status": "pass"},
                    "kind": "passed",
                    "low_reach": False,
                    "reach_rate": 1.0,
                    "reason": "passed",
                    "stats": {"assertion_reached": 1, "entered": 1, "precondition_ok": 1},
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Is slugify_fast documented as equivalent?",
                tool="inspect_doc_and_source",
                result=json.dumps({
                    "contract_evidence": [asdict(e) for e in equivalent.evidence],
                    "docstring": "A faster drop-in replacement for slugify().",
                    "package_revision": "1.4.2",
                    "path": "fakelib/slug.py",
                    "source": "def slugify_fast(s: str) -> str:\n    return s.lower().replace(' ', '-')\n",
                    "source_hash": sha256_text("fakelib.slug"),
                    "symbol": "fakelib.slugify_fast",
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Is the discrepancy specific to multiple adjacent spaces?",
                tool="check_boundary_neighborhood",
                result=json.dumps({
                    "inputs": ["'a b'", "'ab'"],
                    "original_input_preserved": "'a  b'",
                    "outcome": {
                        "execution": {"exit_code": 0, "output": "", "status": "pass"},
                        "kind": "passed",
                        "low_reach": False,
                        "reach_rate": 1.0,
                        "reason": "passed",
                        "stats": {"assertion_reached": 2, "entered": 2, "precondition_ok": 2},
                    },
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Are there existing issues about slugify_fast space handling?",
                tool="search_known_issues_tavily",
                result=json.dumps({
                    "extracted": [receipt_search.to_dict()],
                    "failures": [],
                    "outcome": "related_issue",
                    "query": "https://github.com/example/fakelib/ slugify whitespace tab",
                    "search": [receipt_search.to_dict()],
                }, sort_keys=True),
                effect="supports",
            ),
        ],
        known_behaviour=KnownBehaviour(
            outcome="related_issue",
            links=["https://github.com/example/fakelib/issues/88"],
            note="Issue #88 mentions tabs, not repeated spaces.",
        ),
        uncertainty="Awaiting human review.",
        cost_usd=0.014,
        route_trace=[
            RouteStep("strategy", "lightning", 0, 0.0012),
            RouteStep("investigate", "super", 512, 0.0128),
        ],
    ),
    Finding(
        id="f3",
        title="merge() not associative for nested lists",
        status="unresolved",
        contract=merge,
        repro="from fakelib import merge\na, b, c = {'k': [1]}, {'k': [2]}, {'k': [3]}\nprint(merge(merge(a, b), c), merge(a, merge(b, c)))",
        actual="{'k': [1, 2, 3]}",
        expected="{'k': [1, [2, 3]]}",
        replays_passed=3,
        replays_attempted=3,
        checks=[
            Check(
                question="Does merge work for basic non-nested dicts?",
                tool="run_control_input",
                result=json.dumps({
                    "execution": {"exit_code": 0, "output": "", "status": "pass"},
                    "kind": "passed",
                    "low_reach": False,
                    "reach_rate": 1.0,
                    "reason": "passed",
                    "stats": {"assertion_reached": 1, "entered": 1, "precondition_ok": 1},
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Do the docs promise associativity for nested lists?",
                tool="inspect_doc_and_source",
                result=json.dumps({
                    "contract_evidence": [asdict(e) for e in merge.evidence],
                    "docstring": "Merging is order-independent for list values. May refer only to commutativity of keys.",
                    "package_revision": "1.4.2",
                    "path": "fakelib/merge.py",
                    "source": "def merge(a: dict, b: dict) -> dict:\n    ...\n",
                    "source_hash": sha256_text("fakelib.merge"),
                    "symbol": "fakelib.merge",
                }, sort_keys=True),
                effect="neutral",
            ),
            Check(
                question="Does associativity hold for flat list elements?",
                tool="check_boundary_neighborhood",
                result=json.dumps({
                    "inputs": ["{'k': [1, 2]}", "{'k': [2, 3]}"],
                    "original_input_preserved": "{'k': [1]}",
                    "outcome": {
                        "execution": {"exit_code": 0, "output": "", "status": "pass"},
                        "kind": "passed",
                        "low_reach": False,
                        "reach_rate": 1.0,
                        "reason": "passed",
                        "stats": {"assertion_reached": 2, "entered": 2, "precondition_ok": 2},
                    },
                }, sort_keys=True),
                effect="neutral",
            ),
            Check(
                question="Has nested list associativity been clarified upstream?",
                tool="search_known_issues_tavily",
                result=json.dumps({
                    "extracted": [],
                    "failures": [],
                    "outcome": "lookup_unavailable",
                    "query": "https://github.com/example/fakelib/ fakelib.merge nested list associativity",
                    "search": [],
                }, sort_keys=True),
                effect="neutral",
            ),
        ],
        uncertainty="The contract was inferred; the docs are ambiguous about grouping.",
        cost_usd=0.009,
        route_trace=[RouteStep("investigate", "super", 1024, 0.009)],
    ),
    Finding(
        id="f4",
        title="parse_range('') raises IndexError",
        status="rejected",
        contract=ranges,
        repro="from fakelib import parse_range\nparse_range('')",
        actual="IndexError",
        expected="ValueError",
        rejection_reason="Input outside the contract: docs say the argument must be a non-empty range string.",
        checks=[
            Check(
                question="Does a documented normal input format work in this environment?",
                tool="run_control_input",
                result=json.dumps({
                    "execution": {"exit_code": 0, "output": "", "status": "pass"},
                    "kind": "passed",
                    "low_reach": False,
                    "reach_rate": 1.0,
                    "reason": "passed",
                    "stats": {"assertion_reached": 1, "entered": 1, "precondition_ok": 1},
                }, sort_keys=True),
                effect="supports",
            ),
            Check(
                question="Does the documentation declare empty string as a valid range?",
                tool="inspect_doc_and_source",
                result=json.dumps({
                    "contract_evidence": [asdict(e) for e in ranges.evidence],
                    "docstring": "parse_range(r): r must be a non-empty range string formatted as 'start-end'.",
                    "package_revision": "1.4.2",
                    "path": "fakelib/ranges.py",
                    "source": "def parse_range(r: str) -> tuple[int, int]:\n    if not r:\n        raise ValueError('range string cannot be empty')\n",
                    "source_hash": sha256_text("fakelib.ranges"),
                    "symbol": "fakelib.parse_range",
                }, sort_keys=True),
                effect="refutes",
            ),
            Check(
                question="Does the failure persist for non-empty boundary inputs?",
                tool="check_boundary_neighborhood",
                result=json.dumps({
                    "inputs": ["'0-1'", "'1-1'"],
                    "original_input_preserved": "''",
                    "outcome": {
                        "execution": {"exit_code": 0, "output": "", "status": "pass"},
                        "kind": "passed",
                        "low_reach": False,
                        "reach_rate": 1.0,
                        "reason": "passed",
                        "stats": {"assertion_reached": 2, "entered": 2, "precondition_ok": 2},
                    },
                }, sort_keys=True),
                effect="neutral",
            ),
            Check(
                question="Are there existing issues discussing empty range string handling?",
                tool="search_known_issues_tavily",
                result=json.dumps({
                    "extracted": [{
                        "content_hash": sha256_text("Issue 12 empty string"),
                        "excerpt": "Empty input string raises ValueError by design",
                        "url": "https://github.com/example/fakelib/issues/12",
                    }],
                    "failures": [],
                    "outcome": "related_issue",
                    "query": "https://github.com/example/fakelib/ fakelib.parse_range empty string ValueError",
                    "search": [{"url": "https://github.com/example/fakelib/issues/12"}],
                }, sort_keys=True),
                effect="refutes",
            ),
        ],
        cost_usd=0.003,
        route_trace=[RouteStep("investigate", "super", 256, 0.003)],
    ),
]

report = Report(
    run_id="FAKE-2026-10-23-fakelib",
    library=Library(name="fakelib", version="1.4.2", repo=REPO),
    stats=Stats(
        contracts=12,
        campaigns=31,
        infra_failures=4,
        cost_usd=0.87,
        tavily_credits=23,
        human_review_minutes=18,
    ),
    cost_by_model={"lightning": 0.21, "super": 0.44, "ultra": 0.22},
    findings=findings,
    mode="core",
    retrieval_receipts=retrieval_receipts,
    contracts=sample_contracts,
    _extra={
        "tavily_ledger": {
            "limit": 1000.0,
            "used": 23.0,
            "blocked": False,
            "reported": 23.0,
            "estimated": 0.0,
            "pending": 0.0,
        },
    },
)

if __name__ == "__main__":
    out = Path(__file__).with_name("report.json")
    out.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    print(f"wrote {out}")
