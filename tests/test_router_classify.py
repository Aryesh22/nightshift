from nightshift.pipeline.classify import classify
from nightshift.pipeline.router import LADDER, Router, bucket, cyclomatic_complexity
from nightshift.sandbox import RunResult

COMPLEX = "def f(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(12)) + "    return -1\n"


def test_rules_route_by_failure_kind():
    router = Router()
    assert LADDER[router.start("triage", bucket("crash"))].tier == "lightning"
    assert LADDER[router.start("triage", bucket("assertion"))].tier == "super"
    assert LADDER[router.start("confirm", bucket("assertion"))].tier == "ultra"


def test_complex_code_starts_one_rung_higher():
    assert cyclomatic_complexity(COMPLEX) >= 10
    router = Router()
    assert router.start("triage", bucket("crash", COMPLEX)) == router.start("triage", bucket("crash")) + 1


def test_escalation_stops_at_the_stage_ceiling():
    router = Router()
    assert router.next_rung("propose", 0) == 1
    assert router.next_rung("propose", 1) is None


def test_learns_to_start_cheaper_when_cheap_route_is_reliable():
    router = Router(min_obs=5)
    key = bucket("assertion")
    assert router.start("triage", key) == 2
    for _ in range(10):
        router.record("triage", key, 0, success=True, cost_usd=0.0001)
    assert router.start("triage", key) == 0


def test_learns_to_start_higher_when_rule_route_keeps_failing():
    router = Router(min_obs=5)
    key = bucket("crash")
    for _ in range(10):
        router.record("triage", key, 0, success=False, cost_usd=0.0001)
    assert router.start("triage", key) == 1


def run(code, out="", err="", timed_out=False):
    return RunResult(code, out, err, 1.0, timed_out)


def test_classify_outcomes():
    assert classify("p", run(0, "1 passed")).status == "pass"
    assert classify("p", run(1, timed_out=True)).status == "timeout"

    fail = classify("p", run(1, "Falsifying example: test_property(\n    s='\\x00',\n)\nE   AssertionError: assert 'a' == 'b'"))
    assert (fail.status, fail.failure_kind) == ("fail", "assertion")
    assert "s='\\x00'" in fail.falsifying_example

    crash = classify("p", run(1, "Falsifying example: test_property(x=0)\nE   ZeroDivisionError: division by zero"))
    assert (crash.status, crash.failure_kind) == ("fail", "crash")

    assert classify("p", run(2, "ERROR collecting test.py\nModuleNotFoundError: No module named 'x'")).status == "invalid"
    assert classify("p", run(1, "hypothesis.errors.FailedHealthCheck: filter too much")).status == "invalid"
