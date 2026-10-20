"""Regenerate samples/report.json, the FAKE report the dashboard builds against (schema v1).

Usage: uv run python samples/make_sample_report.py
Covers every status the dashboard must render, including rejected and unresolved.
"""

import json
from pathlib import Path

from nightshift.report import (
    Check, ContractRef, EvidenceRef, Finding, KnownBehaviour, Library, Report, RouteStep, Stats,
)

DOCS = "https://fakelib.readthedocs.io/en/1.4.2/api.html"

roundtrip = ContractRef(
    contract_id="fakelib.codec.roundtrip", version=1, hash="sha256:" + "a" * 64, family="roundtrip",
    claim="For any dict of str to str without '=' or newlines in keys, decode(encode(d)) == d.",
    status="explicit",
    evidence=[EvidenceRef(DOCS + "#fakelib.decode", "decode() is the exact inverse of encode().", "live 2026-10-23T02:14Z")],
)
equivalent = ContractRef(
    contract_id="fakelib.slug.equivalent", version=1, hash="sha256:" + "b" * 64, family="equivalent",
    claim="slugify_fast(s) returns the same result as slugify(s) for every str.",
    status="explicit",
    evidence=[EvidenceRef(DOCS + "#fakelib.slugify_fast", "A faster drop-in replacement for slugify().", "live 2026-10-23T02:15Z")],
)
merge = ContractRef(
    contract_id="fakelib.merge.associative", version=2, hash="sha256:" + "c" * 64, family="composition",
    claim="merge(merge(a, b), c) == merge(a, merge(b, c)) for dicts of lists.",
    status="inferred",
    evidence=[EvidenceRef(DOCS + "#fakelib.merge", "Merging is order-independent for list values.", "cache 2026-10-23T02:15Z")],
)

report = Report(
    run_id="FAKE-2026-10-23-fakelib",
    library=Library(name="fakelib", version="1.4.2", repo="https://github.com/example/fakelib"),
    stats=Stats(contracts=12, campaigns=31, infra_failures=4, cost_usd=0.87, tavily_credits=23, human_review_minutes=18),
    cost_by_model={"lightning": 0.21, "super": 0.44, "ultra": 0.22},
    findings=[
        Finding(
            id="f1", title="decode(encode(d)) drops trailing whitespace in values", status="human_validated",
            contract=roundtrip,
            repro="from fakelib import decode, encode\nd = {'a': ' '}\nprint(decode(encode(d)))  # {'a': ''}",
            actual="{'a': ''}", expected="{'a': ' '}",
            traceback="AssertionError: contract fakelib.codec.roundtrip violated: backward(forward(x)) != x",
            control="{'a': 'b'} round-trips correctly", replays_passed=3, replays_attempted=3,
            checks=[
                Check("Is the input inside the documented domain?", "inspect_doc_and_source",
                      "Values may be any str; ' ' is allowed.", "supports"),
                Check("Is this documented normalization?", "inspect_doc_and_source",
                      "Docs mention no whitespace stripping.", "supports"),
                Check("Does a nearby valid input still fail?", "check_boundary_neighborhood",
                      "Fails for any value with leading/trailing whitespace; passes otherwise.", "supports"),
            ],
            known_behaviour=KnownBehaviour("no_match_found", [], "Searched issues and changelog for 'strip', 'whitespace'. Not proof it is new."),
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
            id="f2", title="slugify_fast disagrees with slugify on repeated spaces", status="ai_reviewed",
            contract=equivalent,
            repro="from fakelib import slugify, slugify_fast\nprint(slugify('a  b'), slugify_fast('a  b'))",
            actual="'a--b'", expected="'a-b'", control="'a b' agrees: 'a-b'",
            replays_passed=3, replays_attempted=3,
            checks=[Check("Is slugify_fast documented as equivalent?", "inspect_doc_and_source",
                          "Docs call it a 'drop-in replacement'.", "supports")],
            known_behaviour=KnownBehaviour("related_issue", ["https://github.com/example/fakelib/issues/88"], "Issue #88 mentions tabs, not repeated spaces."),
            uncertainty="Awaiting human review.",
            cost_usd=0.014,
            route_trace=[RouteStep("strategy", "lightning", 0, 0.0012), RouteStep("investigate", "super", 512, 0.0128)],
        ),
        Finding(
            id="f3", title="merge() not associative for nested lists", status="unresolved",
            contract=merge,
            repro="from fakelib import merge\na, b, c = {'k': [1]}, {'k': [2]}, {'k': [3]}\nprint(merge(merge(a, b), c), merge(a, merge(b, c)))",
            actual="{'k': [1, 2, 3]}", expected="{'k': [1, [2, 3]]}",
            replays_passed=3, replays_attempted=3,
            checks=[Check("Do the docs promise associativity?", "inspect_doc_and_source",
                          "Docs say 'order-independent', which may mean commutative only.", "neutral")],
            uncertainty="The contract was inferred; the docs are ambiguous about grouping.",
            cost_usd=0.009,
            route_trace=[RouteStep("investigate", "super", 1024, 0.009)],
        ),
        Finding(
            id="f4", title="parse_range('') raises IndexError", status="rejected",
            contract=ContractRef("fakelib.ranges.domain", 1, "sha256:" + "d" * 64, "roundtrip",
                                 "parse_range(format_range(r)) == r for valid ranges.", "explicit"),
            repro="from fakelib import parse_range\nparse_range('')", actual="IndexError", expected="ValueError",
            rejection_reason="Input outside the contract: docs say the argument must be a non-empty range string.",
            checks=[Check("Is '' a valid input?", "inspect_doc_and_source", "Docs require a non-empty string.", "refutes")],
            cost_usd=0.003,
            route_trace=[RouteStep("investigate", "super", 256, 0.003)],
        ),
    ],
)

if __name__ == "__main__":
    out = Path(__file__).with_name("report.json")
    out.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    print(f"wrote {out}")
