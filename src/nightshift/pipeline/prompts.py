"""Prompt templates for every pipeline stage.

The property catalog and failure classification follow Trail of Bits' property-based
testing guidance: assert the strongest grounded property, push constraints into
strategies, and separate wrong properties from real bugs before reporting anything.
"""

from __future__ import annotations

PROPERTY_CATALOG = """\
| kind           | formula                         | applies to                                 |
|----------------|---------------------------------|--------------------------------------------|
| roundtrip      | decode(encode(x)) == x          | serializers, parsers, conversion pairs     |
| inverse        | f(g(x)) == x                    | compress/decompress, escape/unescape       |
| idempotence    | f(f(x)) == f(x)                 | normalizers, formatters, canonicalizers    |
| invariant      | property holds before and after | transformations, data structures           |
| oracle         | new(x) == reference(x)          | reimplementations of stdlib behaviour      |
| easy_to_verify | is_sorted(sort(x))              | algorithms with cheap checkers             |
| commutativity  | f(a, b) == f(b, a)              | merges, set-like operations                |
| error_contract | raises DocumentedError or ok    | decoders/validators on arbitrary input     |
| language       | a == b implies hash(a)==hash(b) | __eq__/__hash__, ordering, iterator protocol |"""

READ_SYSTEM = f"""\
You are a senior engineer hunting for real bugs in a Python library with property-based tests.
From the source and documentation, pick functions whose behaviour is constrained by a rule
you can state and check. Prefer pure functions with an algebraic shape:

{PROPERTY_CATALOG}

Rules:
- Every claim must be grounded in the docs, docstrings, type hints, a referenced spec, or a
  Python language contract. Quote the grounding text in "evidence".
- Prefer places where the docs promise more than the code obviously delivers: edge cases,
  unicode, empty inputs, numeric boundaries, round-trips.
- Skip anything needing network, filesystem state, randomness, or the current time.
- "qualname" must be importable as written, e.g. "pkg.module.func" or "pkg.module.Class.method".

Reply with JSON only:
{{"targets": [{{"qualname": "...", "signature": "...", "kind": "<kind from the table>",
  "claim": "one sentence rule", "evidence": "quoted grounding text"}}]}}"""

READ_USER = """\
Library: {library}
Return up to {max_targets} targets, strongest and most bug-prone first.

{digest}"""

PROPOSE_SYSTEM = """\
You write one Hypothesis property-based test for a Python function. Rules:
- Assert the claim given, at its strongest grounded form. Never restate the implementation
  (no tautologies like `assert add(a, b) == a + b`).
- Put constraints in strategies (min_value, alphabet, st.builds, st.composite), not in
  assume(). Generate only inputs the documentation says are valid.
- Pin known edge cases with @example: empty, single element, zero, negative, unicode, max values.
- Use @settings(max_examples=300, deadline=None).
- For error contracts, catch only the documented exception; let anything else fail.
- Import the target exactly as `qualname` says. Only use the standard library, hypothesis,
  and the library under test. Name the test function `test_property`.

Reply with JSON only: {"test_code": "<complete python file>"}"""

PROPOSE_USER = """\
Target: {qualname}{signature}
Property kind: {kind}
Claim: {claim}
Evidence: {evidence}

Source:
```python
{source}
```
{variant_hint}"""

VARIANT_HINTS = (
    "",
    "Write a different test than the obvious one: target boundary inputs and unusual but valid values.",
    "Write a different test: focus on unicode, empty, and extreme numeric inputs that are still valid.",
)

TRIAGE_SYSTEM = """\
A property-based test failed. Decide what it means:
- "real_bug": the input is in the documented domain and a documented guarantee or a Python
  language contract is violated.
- "bad_test": the property is wrong, the strategy generates inputs the docs exclude, or the
  test has a mistake.
- "unclear": behaviour at this edge was never specified (needs a maintainer decision).

Authority, strongest first: external spec > type hints > docstrings > existing tests > name.
Precondition violations and explicitly undefined behaviour are never bugs. Be skeptical: false
bug reports waste maintainers' time.

Reply with JSON only:
{"verdict": "real_bug|bad_test|unclear", "confidence": 0.0-1.0, "reason": "two sentences max"}"""

TRIAGE_USER = """\
Target: {qualname}{signature}
Claim: {claim}
Evidence: {evidence}

Source:
```python
{source}
```

Test:
```python
{test_code}
```

Failure output:
```
{output}
```"""

CONFIRM_SYSTEM = """\
You are confirming a suspected bug in a Python library and preparing a report a maintainer
would welcome. Produce:
1. "repro": a minimal standalone Python script (no hypothesis, no pytest) that uses the
   shrunk input and ends with an assert that FAILS while the bug exists and PASSES once it is
   fixed. It must not catch the failure.
2. "root_cause": the precise cause, pointing at the responsible code.
3. "patch_diff": a minimal unified diff against the repository (paths relative to the repo
   root, as `git apply` expects) that fixes the root cause without changing documented behaviour.
4. "title" (under 80 characters) and "severity" (low|medium|high).

Reply with JSON only:
{"title": "...", "severity": "...", "repro": "...", "root_cause": "...", "patch_diff": "..."}"""

CONFIRM_USER = """\
Target: {qualname}{signature}
Claim: {claim}
Evidence: {evidence}
Triage reasoning: {reason}

Source file `{source_path}`:
```python
{source}
```

Failing test:
```python
{test_code}
```

Failure output:
```
{output}
```
{retry_feedback}"""
