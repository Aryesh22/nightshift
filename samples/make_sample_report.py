"""Regenerate samples/report.json and multi-run samples in samples/runs/.

Usage: python samples/make_sample_report.py
Covers every status the dashboard must render, including rejected and unresolved,
with rich v1.1 Core contracts, Tavily retrieval receipts, and active refutation traces.
Generates:
  - samples/report.json (main showcase sample)
  - samples/runs/python-dotenv-core.json
  - samples/runs/tomlkit-core.json
  - samples/runs/packaging-core.json
  - samples/runs/index.json (run manifest for dashboard campaign picker)
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


def make_fakelib_report() -> Report:
    docs = "https://fakelib.readthedocs.io/en/1.4.2/api.html"
    repo = "https://github.com/example/fakelib"

    roundtrip = ContractRef(
        contract_id="fakelib.codec.roundtrip",
        version=1,
        hash=sha256_text("fakelib.codec.roundtrip:v1"),
        family="roundtrip",
        claim="For any dict of str to str without '=' or newlines in keys, decode(encode(d)) == d.",
        status="explicit",
        evidence=[
            EvidenceRef(
                source=docs + "#fakelib.decode",
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
                source=docs + "#fakelib.slugify_fast",
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
                source=docs + "#fakelib.merge",
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
                source=docs + "#fakelib.parse_range",
                excerpt="parse_range(r) expects a non-empty range string.",
                retrieved="live 2026-10-23T02:16:00Z",
                content_hash=sha256_text("parse_range(r) expects a non-empty range string."),
            ),
        ],
    )

    receipt_extract = RetrievalReceipt(
        url=docs + "#fakelib.decode",
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
        url=docs + "#fakelib.parse_range",
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
                Check("Does a documented normal input work in this environment?", "run_control_input",
                      json.dumps({"execution": {"exit_code": 0, "output": "", "status": "pass"}, "kind": "passed", "reach_rate": 1.0}), "supports"),
                Check("Does the pinned documentation support claimed semantics?", "inspect_doc_and_source",
                      json.dumps({"docstring": "Values may be any str; ' ' is allowed.", "path": "fakelib/codec.py"}), "supports"),
                Check("Is the discrepancy localized around the reduced boundary?", "check_boundary_neighborhood",
                      json.dumps({"inputs": ["{'a': 'b'}", "{'a': ''}"], "outcome": {"kind": "passed"}}), "supports"),
                Check("Has this whitespace-dropping issue already been reported upstream?", "search_known_issues_tavily",
                      json.dumps({"outcome": "no_match_found", "query": "fakelib decode strip whitespace"}), "neutral"),
            ],
            known_behaviour=KnownBehaviour(outcome="no_match_found", links=[], note="Searched issues for whitespace stripping."),
            uncertainty="Maintainers may consider stripping intentional; docs do not say so.",
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
                Check("Does slugify_fast agree with slugify on single spaces?", "run_control_input", json.dumps({"kind": "passed"}), "supports"),
                Check("Is slugify_fast documented as equivalent?", "inspect_doc_and_source", json.dumps({"doc": "drop-in replacement"}), "supports"),
                Check("Is the discrepancy specific to adjacent spaces?", "check_boundary_neighborhood", json.dumps({"inputs": ["'a b'"]}), "supports"),
                Check("Are there existing issues about space handling?", "search_known_issues_tavily", json.dumps({"outcome": "related_issue"}), "supports"),
            ],
            known_behaviour=KnownBehaviour("related_issue", ["https://github.com/example/fakelib/issues/88"], "Issue #88 mentions tabs, not repeated spaces."),
            uncertainty="Awaiting human review.",
            cost_usd=0.014,
            route_trace=[RouteStep("strategy", "lightning", 0, 0.0012), RouteStep("investigate", "super", 512, 0.0128)],
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
                Check("Does merge work for basic non-nested dicts?", "run_control_input", json.dumps({"kind": "passed"}), "supports"),
                Check("Do the docs promise associativity for nested lists?", "inspect_doc_and_source", json.dumps({"doc": "order-independent"}), "neutral"),
                Check("Does associativity hold for flat list elements?", "check_boundary_neighborhood", json.dumps({"kind": "passed"}), "neutral"),
                Check("Has nested list associativity been clarified upstream?", "search_known_issues_tavily", json.dumps({"outcome": "lookup_unavailable"}), "neutral"),
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
                Check("Does a documented normal input format work?", "run_control_input", json.dumps({"kind": "passed"}), "supports"),
                Check("Does documentation declare empty string as valid?", "inspect_doc_and_source", json.dumps({"doc": "must be non-empty"}), "refutes"),
                Check("Does failure persist for non-empty boundary inputs?", "check_boundary_neighborhood", json.dumps({"kind": "passed"}), "neutral"),
                Check("Are there existing issues discussing empty range string?", "search_known_issues_tavily", json.dumps({"outcome": "related_issue"}), "refutes"),
            ],
            cost_usd=0.003,
            route_trace=[RouteStep("investigate", "super", 256, 0.003)],
        ),
    ]

    return Report(
        run_id="FAKE-2026-10-23-fakelib",
        library=Library(name="fakelib", version="1.4.2", repo=repo),
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
        _include_fields={"mode", "retrieval_receipts", "contracts"},
    )



def make_dotenv_report() -> Report:
    repo = "https://github.com/theskumar/python-dotenv"
    contract_parse = ContractRef(
        contract_id="dotenv.parse.roundtrip",
        version=1,
        hash=sha256_text("dotenv.parse.roundtrip:v1"),
        family="roundtrip",
        claim="dotenv_values(stream) round-trips serialize_env(mapping) for valid mappings.",
        status="explicit",
        evidence=[
            EvidenceRef("https://github.com/theskumar/python-dotenv/blob/v1.0.1/README.md",
                        "Key-value pairs can be parsed from and written to env files.",
                        "live 2026-10-26T12:00:00Z", sha256_text("dotenv README")),
        ],
    )
    contract_find = ContractRef(
        contract_id="dotenv.find.domain",
        version=1,
        hash=sha256_text("dotenv.find.domain:v1"),
        family="roundtrip",
        claim="find_dotenv(filename) locates .env file in parent directories.",
        status="explicit",
        evidence=[EvidenceRef("README.md", "find_dotenv searches parent directories.", "manual", sha256_text("find"))],
    )

    f1 = Finding(
        id="dotenv_f1",
        title="dotenv_values drops internal quotes in double-quoted values",
        status="human_validated",
        contract=contract_parse,
        repro='import io\nfrom dotenv import dotenv_values\nstream = io.StringIO(\'KEY="val"quote"\')\nprint(dotenv_values(stream_=stream))',
        actual="{'KEY': 'val'}",
        expected="{'KEY': 'val\"quote'}",
        control="{'KEY': 'plain_value'} parses correctly",
        replays_passed=3,
        replays_attempted=3,
        checks=[
            Check("Does plain value parse correctly?", "run_control_input", json.dumps({"kind": "passed"}), "supports"),
            Check("Does documentation allow internal quotes?", "inspect_doc_and_source", json.dumps({"doc": "supports escaped quotes"}), "supports"),
            Check("Check single quote boundary neighborhood", "check_boundary_neighborhood", json.dumps({"inputs": ["'val\\'quote'"]}), "supports"),
            Check("Search known issues on quote escaping", "search_known_issues_tavily", json.dumps({"outcome": "no_match_found"}), "neutral"),
        ],
        known_behaviour=KnownBehaviour("no_match_found", [], "No matching issue on internal unescaped quote truncation."),
        root_cause="Regex parser matches up to next unescaped quote without lookahead.",
        cost_usd=0.042,
        route_trace=[RouteStep("contract", "lightning", 0, 0.002), RouteStep("investigate", "super", 512, 0.020), RouteStep("review", "ultra", 1024, 0.020)],
    )
    f2 = Finding(
        id="dotenv_f2",
        title="find_dotenv('') raises ValueError on empty filename",
        status="rejected",
        contract=contract_find,
        repro="from dotenv import find_dotenv\nfind_dotenv('')",
        actual="ValueError",
        expected="''",
        rejection_reason="Empty filename is outside documented contract domain for file discovery.",
        checks=[
            Check("Is empty filename valid?", "inspect_doc_and_source", json.dumps({"doc": "filename must be non-empty"}), "refutes"),
        ],
        cost_usd=0.008,
        route_trace=[RouteStep("investigate", "super", 256, 0.008)],
    )

    receipt = RetrievalReceipt(
        url="https://github.com/theskumar/python-dotenv/blob/v1.0.1/README.md",
        retrieved_at="2026-10-26T12:00:00Z",
        content_hash=sha256_text("python-dotenv README documentation content"),
        excerpt="Key-value pairs can be parsed from and written to env files.",
        request_id="tvly-dotenv-001",
        status="live",
        endpoint="extract",
        text="python-dotenv reads key-value pairs from .env and sets them as environment variables.",
        response_hash=sha256_text("dotenv_resp_001"),
        credits=1.0,
        credit_status="reported",
        source_version="1.0.1",
        version_match=True,
    )

    return Report(
        run_id="2026-10-26-081200-core-python-dotenv",
        library=Library(name="python-dotenv", version="1.0.1", repo=repo),
        stats=Stats(contracts=4, campaigns=8, infra_failures=0, cost_usd=0.42, tavily_credits=4.0, human_review_minutes=8.0),
        cost_by_model={"lightning": 0.12, "super": 0.20, "ultra": 0.10},
        findings=[f1, f2],
        mode="core",
        retrieval_receipts=[receipt.to_dict()],
        contracts=[asdict(contract_parse), asdict(contract_find)],
        _extra={"tavily_ledger": {"limit": 1000.0, "used": 4.0, "blocked": False, "reported": 4.0, "estimated": 0.0, "pending": 0.0}},
        _include_fields={"mode", "retrieval_receipts", "contracts"},
    )



def make_tomlkit_report() -> Report:
    repo = "https://github.com/sdispater/tomlkit"
    contract_rt = ContractRef(
        contract_id="tomlkit.dumps.roundtrip",
        version=1,
        hash=sha256_text("tomlkit.dumps.roundtrip:v1"),
        family="roundtrip",
        claim="parse(dumps(doc)) == doc while preserving comments and whitespace.",
        status="explicit",
        evidence=[EvidenceRef("https://tomlkit.readthedocs.io/en/latest/", "Style-preserving TOML library.", "live 2026-10-26T12:10:00Z", sha256_text("tomlkit docs"))],
    )
    contract_key = ContractRef(
        contract_id="tomlkit.key.domain",
        version=1,
        hash=sha256_text("tomlkit.key.domain:v1"),
        family="roundtrip",
        claim="parse('a.b = 1') parses dotted keys.",
        status="explicit",
        evidence=[EvidenceRef("docs", "Dotted keys are supported in TOML v1.0.0", "manual", sha256_text("tomlkit dotted"))],
    )

    f1 = Finding(
        id="tomlkit_f1",
        title="Inline table comment loss during serialization roundtrip",
        status="human_validated",
        contract=contract_rt,
        repro="import tomlkit\ns = 'table = { a = 1 # comment\\n }'\nprint(tomlkit.dumps(tomlkit.parse(s)))",
        actual="'table = { a = 1 }'",
        expected="table = { a = 1 # comment\\n }",
        control="'table = { a = 1 }' roundtrips cleanly",
        replays_passed=3,
        replays_attempted=3,
        checks=[
            Check("Does plain inline table roundtrip?", "run_control_input", json.dumps({"kind": "passed"}), "supports"),
            Check("Do docs promise comment preservation for inline tables?", "inspect_doc_and_source", json.dumps({"doc": "preserves all comments and indentation"}), "supports"),
            Check("Check multiline comment neighborhood", "check_boundary_neighborhood", json.dumps({"inputs": ["table = { a = 1 }"]}), "supports"),
            Check("Search known issues on inline comments", "search_known_issues_tavily", json.dumps({"outcome": "no_match_found"}), "neutral"),
        ],
        known_behaviour=KnownBehaviour("no_match_found", [], "No matching closed issue found."),
        root_cause="InlineTable parser discards tokens of type Comment inside braces.",
        cost_usd=0.058,
        route_trace=[RouteStep("contract", "lightning", 0, 0.003), RouteStep("investigate", "super", 512, 0.025), RouteStep("review", "ultra", 1024, 0.030)],
    )
    f2 = Finding(
        id="tomlkit_f2",
        title="Bare key with space raises ParseError",
        status="rejected",
        contract=contract_key,
        repro="import tomlkit\ntomlkit.parse('key with space = 1')",
        actual="ParseError: Invalid key",
        expected="Parsed dict",
        rejection_reason="Bare keys cannot contain spaces under TOML v1.0.0 specification.",
        checks=[
            Check("Does TOML spec permit spaces in bare keys?", "inspect_doc_and_source", json.dumps({"doc": "bare keys may contain only A-Za-z0-9_-"}), "refutes"),
        ],
        cost_usd=0.009,
        route_trace=[RouteStep("investigate", "super", 256, 0.009)],
    )

    receipt = RetrievalReceipt(
        url="https://tomlkit.readthedocs.io/en/latest/",
        retrieved_at="2026-10-26T12:10:00Z",
        content_hash=sha256_text("tomlkit documentation content"),
        excerpt="Style-preserving TOML library for Python.",
        request_id="tvly-tomlkit-002",
        status="live",
        endpoint="extract",
        text="tomlkit is a 1.0.0-compliant TOML library with full style-preservation support.",
        response_hash=sha256_text("tomlkit_resp_002"),
        credits=1.0,
        credit_status="reported",
        source_version="0.12.4",
        version_match=True,
    )

    return Report(
        run_id="2026-10-26-092500-core-tomlkit",
        library=Library(name="tomlkit", version="0.12.4", repo=repo),
        stats=Stats(contracts=5, campaigns=11, infra_failures=1, cost_usd=0.58, tavily_credits=5.0, human_review_minutes=12.0),
        cost_by_model={"lightning": 0.16, "super": 0.26, "ultra": 0.16},
        findings=[f1, f2],
        mode="core",
        retrieval_receipts=[receipt.to_dict()],
        contracts=[asdict(contract_rt), asdict(contract_key)],
        _extra={"tavily_ledger": {"limit": 1000.0, "used": 5.0, "blocked": False, "reported": 5.0, "estimated": 0.0, "pending": 0.0}},
        _include_fields={"mode", "retrieval_receipts", "contracts"},
    )



def make_packaging_report() -> Report:
    repo = "https://github.com/pypa/packaging"
    contract_ver = ContractRef(
        contract_id="packaging.version.roundtrip",
        version=1,
        hash=sha256_text("packaging.version.roundtrip:v1"),
        family="roundtrip",
        claim="Version(str(v)) == v for any valid Version instance.",
        status="explicit",
        evidence=[EvidenceRef("https://packaging.pypa.io/en/stable/version/", "PEP 440 version implementation.", "live 2026-10-26T12:20:00Z", sha256_text("packaging docs"))],
    )
    contract_spec = ContractRef(
        contract_id="packaging.specifiers.domain",
        version=1,
        hash=sha256_text("packaging.specifiers.domain:v1"),
        family="roundtrip",
        claim="SpecifierSet('~=1.0.*') raises InvalidSpecifier",
        status="explicit",
        evidence=[EvidenceRef("docs", "Wildcard with compatible release is invalid", "manual", sha256_text("packaging spec"))],
    )

    f1 = Finding(
        id="pkg_f1",
        title="Local version segment with multiple hyphens normalizes inconsistently",
        status="human_validated",
        contract=contract_ver,
        repro="from packaging.version import Version\nv = Version('1.0.0+local-build-1')\nassert Version(str(v)) == v",
        actual="Version('1.0.0+local.build.1')",
        expected="Version('1.0.0+local-build-1')",
        control="Version('1.0.0') roundtrips cleanly",
        replays_passed=3,
        replays_attempted=3,
        checks=[
            Check("Does standard release roundtrip?", "run_control_input", json.dumps({"kind": "passed"}), "supports"),
            Check("Does PEP 440 allow hyphens in local version?", "inspect_doc_and_source", json.dumps({"doc": "local versions permit alphanumeric and dots"}), "supports"),
            Check("Check dot-separated neighborhood", "check_boundary_neighborhood", json.dumps({"inputs": ["'1.0.0+local.1'"]}), "supports"),
            Check("Search known issues on local version hyphens", "search_known_issues_tavily", json.dumps({"outcome": "no_match_found"}), "neutral"),
        ],
        known_behaviour=KnownBehaviour("no_match_found", [], "No matching open issues."),
        root_cause="Local segment canonicalization replaces hyphen with period unconditionally.",
        cost_usd=0.036,
        route_trace=[RouteStep("contract", "lightning", 0, 0.002), RouteStep("investigate", "super", 512, 0.018), RouteStep("review", "ultra", 1024, 0.016)],
    )
    f2 = Finding(
        id="pkg_f2",
        title="InvalidSpecifier raised for '~=1.0.*'",
        status="rejected",
        contract=contract_spec,
        repro="from packaging.specifiers import SpecifierSet\nSpecifierSet('~=1.0.*')",
        actual="InvalidSpecifier",
        expected="SpecifierSet instance",
        rejection_reason="PEP 440 explicitly prohibits wildcard with compatible release (~=) operator.",
        checks=[
            Check("Is ~= with wildcard valid in PEP 440?", "inspect_doc_and_source", json.dumps({"doc": "The prefix matching operator != does not allow wildcards"}), "refutes"),
        ],
        cost_usd=0.007,
        route_trace=[RouteStep("investigate", "super", 256, 0.007)],
    )

    receipt = RetrievalReceipt(
        url="https://packaging.pypa.io/en/stable/version/",
        retrieved_at="2026-10-26T12:20:00Z",
        content_hash=sha256_text("packaging documentation content"),
        excerpt="Core utilities for Python packages (PEP 440).",
        request_id="tvly-pkg-003",
        status="live",
        endpoint="extract",
        text="packaging.version implements PEP 440 version handling.",
        response_hash=sha256_text("pkg_resp_003"),
        credits=1.0,
        credit_status="reported",
        source_version="24.0",
        version_match=True,
    )

    return Report(
        run_id="2026-10-26-104000-core-packaging",
        library=Library(name="packaging", version="24.0", repo=repo),
        stats=Stats(contracts=3, campaigns=6, infra_failures=0, cost_usd=0.36, tavily_credits=3.0, human_review_minutes=6.0),
        cost_by_model={"lightning": 0.10, "super": 0.16, "ultra": 0.10},
        findings=[f1, f2],
        mode="core",
        retrieval_receipts=[receipt.to_dict()],
        contracts=[asdict(contract_ver), asdict(contract_spec)],
        _extra={"tavily_ledger": {"limit": 1000.0, "used": 3.0, "blocked": False, "reported": 3.0, "estimated": 0.0, "pending": 0.0}},
        _include_fields={"mode", "retrieval_receipts", "contracts"},
    )



if __name__ == "__main__":
    samples_dir = Path(__file__).resolve().parent
    runs_dir = samples_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Main showcase report (fakelib)
    fakelib_report = make_fakelib_report()
    out_main = samples_dir / "report.json"
    out_main.write_text(json.dumps(fakelib_report.to_dict(), indent=2) + "\n")
    print(f"wrote {out_main}")

    # 2. Multi-run reports under samples/runs/
    named_reports = [
        ("python-dotenv-core.json", make_dotenv_report()),
        ("tomlkit-core.json", make_tomlkit_report()),
        ("packaging-core.json", make_packaging_report()),
    ]

    index_entries = []
    for filename, rep in named_reports:
        out_file = runs_dir / filename
        out_file.write_text(json.dumps(rep.to_dict(), indent=2) + "\n")
        print(f"wrote {out_file}")
        index_entries.append({
            "run_id": rep.run_id,
            "library": rep.library.name,
            "version": rep.library.version,
            "repo": rep.library.repo,
            "mode": rep.mode or "core",
            "findings_count": len(rep.findings),
            "status_counts": rep.status_counts(),
            "cost_usd": rep.stats.cost_usd,
            "cost_per_validated_finding": rep.cost_per_validated_finding,
            "filename": filename,
            "path": f"samples/runs/{filename}",
        })

    index_path = runs_dir / "index.json"
    index_path.write_text(json.dumps({"runs": index_entries}, indent=2) + "\n")
    print(f"wrote {index_path}")

