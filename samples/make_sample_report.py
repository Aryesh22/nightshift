"""Regenerate samples/report.json, the FAKE report the dashboard builds against.

Usage: uv run python samples/make_sample_report.py
"""

from pathlib import Path

from nightshift.report import Bug, Library, Report, RouteStep, Stats

ROUNDTRIP_PATCH = """--- a/src/fakelib/codec.py
+++ b/src/fakelib/codec.py
@@ -41,7 +41,7 @@ def decode(data: str) -> dict:
-    key, _, value = line.partition("=")
+    key, _, value = line.partition("=")  # keep '=' inside values
-    return {k: v.strip() for k, v in pairs}
+    return {k: v for k, v in pairs}
"""

report = Report(
    run_id="FAKE-2026-10-19-fakelib",
    library=Library(name="fakelib", version="1.4.2", repo="https://github.com/example/fakelib"),
    stats=Stats(properties_proposed=214, failures=37, triaged_real=8, verified=5, cost_usd=0.87),
    cost_by_model={"lightning": 0.19, "super": 0.36, "ultra": 0.32},
    bugs=[
        Bug(
            id="b1",
            title="decode(encode(x)) drops trailing whitespace in values",
            severity="medium",
            property="roundtrip",
            repro='from fakelib import encode, decode\nx = {"a": "b "}\nassert decode(encode(x)) == x',
            traceback="AssertionError: assert {'a': 'b'} == {'a': 'b '}",
            root_cause="decode() calls .strip() on every value, but encode() never escapes whitespace.",
            patch_diff=ROUNDTRIP_PATCH,
            patch_verified=True,
            route_trace=[
                RouteStep("propose", "lightning", 0, 0.0011),
                RouteStep("triage", "super", 512, 0.0042),
                RouteStep("confirm", "ultra", 2048, 0.0310),
                RouteStep("dedupe", "lightning", 0, 0.0004),
            ],
        ),
        Bug(
            id="b2",
            title="parse_range crashes with IndexError on an empty string",
            severity="low",
            property="crash",
            repro='from fakelib import parse_range\nparse_range("")',
            traceback='Traceback (most recent call last):\n  File "fakelib/ranges.py", line 12, in parse_range\n    start = parts[0][0]\nIndexError: string index out of range',
            root_cause="No guard for empty input before indexing the first character.",
            patch_diff="--- a/src/fakelib/ranges.py\n+++ b/src/fakelib/ranges.py\n@@ -10,2 +10,4 @@\n+    if not text:\n+        raise ValueError(\"empty range\")\n",
            patch_verified=True,
            route_trace=[RouteStep("propose", "lightning", 0, 0.0009), RouteStep("triage", "lightning", 0, 0.0006)],
        ),
        Bug(
            id="b3",
            title="merge() is not associative for overlapping keys",
            severity="medium",
            property="invariant",
            repro="from fakelib import merge\na, b, c = {'k': [1]}, {'k': [2]}, {'k': [3]}\nassert merge(merge(a, b), c) == merge(a, merge(b, c))",
            traceback="AssertionError: [1, 2, 3] != [1, [2, 3]]",
            root_cause="Nested lists are appended instead of extended when the right side is already merged.",
            patch_diff="",
            patch_verified=False,
            duplicate_of="https://github.com/example/fakelib/issues/123",
            route_trace=[
                RouteStep("propose", "lightning", 0, 0.0012),
                RouteStep("triage", "super", 1024, 0.0071),
                RouteStep("dedupe", "lightning", 0, 0.0003),
            ],
        ),
    ],
)

if __name__ == "__main__":
    import json

    out = Path(__file__).with_name("report.json")
    out.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    print(f"wrote {out}")
