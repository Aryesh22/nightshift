"""Turn raw pytest + Hypothesis output into an Execution status and failure kind."""

from __future__ import annotations

import re

from nightshift.pipeline.types import Execution
from nightshift.sandbox import RunResult

# pytest exit codes: 1 tests failed, 2 interrupted (often collection errors), 3 internal error,
# 4 usage error, 5 no tests collected.
INVALID_EXIT_CODES = {2, 3, 4, 5}

# The test itself is broken or vacuous, not the library.
INVALID_MARKERS = (
    "ERROR collecting",
    "SyntaxError",
    "ImportError",
    "ModuleNotFoundError",
    "NameError",
    "FailedHealthCheck",
    "Unsatisfiable",
    "InvalidArgument",
    "fixture '",
)

CRASH_EXCEPTIONS = (
    "TypeError",
    "ValueError",
    "KeyError",
    "IndexError",
    "AttributeError",
    "ZeroDivisionError",
    "RecursionError",
    "OverflowError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "RuntimeError",
)

FALSIFYING = re.compile(r"Falsifying example:.*?(?=\n\S|\n\n|\Z)", re.DOTALL)
MAX_OUTPUT_CHARS = 6000


def classify(property_id: str, result: RunResult) -> Execution:
    output = result.output
    trimmed = output[-MAX_OUTPUT_CHARS:]
    if result.timed_out:
        return Execution(property_id, "timeout", "timeout", trimmed)
    if result.exit_code == 0:
        return Execution(property_id, "pass", output=trimmed[-500:])

    falsifying = FALSIFYING.search(output)
    example = falsifying.group(0).strip() if falsifying else ""
    if result.exit_code in INVALID_EXIT_CODES or (not example and any(m in output for m in INVALID_MARKERS)):
        return Execution(property_id, "invalid", output=trimmed)

    kind = "assertion" if "AssertionError" in output or "assert " in output else "crash"
    if kind == "assertion" and any(f"{e}:" in output for e in CRASH_EXCEPTIONS):
        kind = "crash"
    return Execution(property_id, "fail", kind, trimmed, example)
