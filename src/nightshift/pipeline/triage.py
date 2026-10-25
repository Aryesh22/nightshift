"""Stage 4: decide whether a failing property means the code or the test is wrong.

"unclear" counts as a verifier failure, so an unsure cheap model escalates to a stronger one.
If even the top rung is unsure, the verdict stays "unclear" and nothing is reported.
"""

from __future__ import annotations

from nightshift.llm import NemotronClient
from nightshift.pipeline import prompts
from nightshift.pipeline.cascade import call_with_cascade
from nightshift.pipeline.router import Router, bucket
from nightshift.pipeline.types import Execution, PropertyTest, Target, TriageVerdict

VERDICTS = {"real_bug", "bad_test", "unclear"}
MIN_CONFIDENCE = 0.6


def parse_verdict(payload: dict) -> tuple[str, float, str]:
    verdict = payload["verdict"]
    confidence = float(payload.get("confidence", 0.0))
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}")
    if verdict == "unclear" or confidence < MIN_CONFIDENCE:
        raise ValueError(f"not decisive ({verdict}, confidence {confidence:.2f})")
    return verdict, confidence, str(payload.get("reason", ""))


async def triage(
    client: NemotronClient,
    router: Router,
    target: Target,
    prop: PropertyTest,
    execution: Execution,
) -> TriageVerdict:
    messages = [
        {"role": "system", "content": prompts.TRIAGE_SYSTEM},
        {
            "role": "user",
            "content": prompts.TRIAGE_USER.format(
                qualname=target.qualname,
                signature=target.signature,
                claim=target.claim,
                evidence=target.evidence,
                source=target.source or "(source unavailable)",
                test_code=prop.code,
                output=execution.output[-4000:],
            ),
        },
    ]
    parsed, trace = await call_with_cascade(
        client, router, "triage", bucket(execution.failure_kind, target.source), messages,
        parse=parse_verdict, max_tokens=1024,
    )
    if parsed is None:
        return TriageVerdict(prop.id, "unclear", 0.0, "no rung reached a confident verdict", trace)
    verdict, confidence, reason = parsed
    return TriageVerdict(prop.id, verdict, confidence, reason, trace)
