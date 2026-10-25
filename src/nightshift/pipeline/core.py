"""Contract-first Core campaign, deliberately separate from the Baseline controller."""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from nightshift.contracts import Harness
from nightshift.contracts.model import sha256_text
from nightshift.contracts.render import render_test
from nightshift.contracts.runner import run_contract
from nightshift.llm import BudgetExceeded
from nightshift.pipeline.contracts_stage import (
    build_documentation, extract_contracts, generate_harness, literal_value, retrieve_documentation,
)
from nightshift.pipeline.investigator import (
    RefutationTools, failure_fingerprint, investigate_candidate, outcome_dict,
)
from nightshift.pipeline.read import clone, source_revision
from nightshift.report import ContractRef, EvidenceRef, Finding, Library, Report, Stats, write_campaign_report
from nightshift.tavily import CreditLedger, TavilyClient


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


async def run_core(config, client, sandbox, *, tavily=None):
    library = config.library or config.package
    run_id = f"{datetime.now(timezone.utc):%Y-%m-%d-%H%M%S}-{uuid4().hex[:8]}-core-{library}"
    directory = config.runs_dir / run_id
    directory.mkdir(parents=True)
    namespace = config.cache_namespace or run_id
    report = Report(run_id, Library(library, "unresolved", config.repo_url))
    contracts, campaigns, traces, errors, approvals, pinned_receipts = [], [], [], [], [], []
    investigations = {}
    fingerprints = {}
    stopped, env, own_tavily = None, None, False
    ultra_spend, ultra_survivors = 0.0, 0
    if tavily is None and config.online_lookup and not config.airgapped:
        tavily = TavilyClient(os.getenv("TAVILY_API_KEY", ""), ledger=CreditLedger(config.tavily_credits),
                              namespace=namespace)
        own_tavily = True

    def checkpoint():
        for finding in report.findings:
            tools = investigations.get(finding.id)
            if tools is not None:
                investigation = tools.result
                finding.status = investigation.status
                finding.checks = list(investigation.checks)
                finding.control = investigation.control
                finding.replays_attempted = len(investigation.replays)
                finding.replays_passed = sum(r["matched"] for r in investigation.replays)
                finding.known_behaviour = investigation.known_behaviour
                finding.uncertainty = ("AI review only; human validation pending. " +
                    ("Known-issue lookup unavailable; no novelty conclusion." if investigation.known_behaviour.outcome == "lookup_unavailable"
                     else investigation.known_behaviour.note)) if investigation.status == "ai_reviewed" else investigation.reason
                finding.rejection_reason = investigation.reason if investigation.status == "rejected" else None
                _write(directory / "investigations" / f"{finding.id}.json", asdict(investigation))
            finding.cost_usd = sum(t.cost_usd for t in finding.route_trace)
        report.stats.cost_usd = client.budget.spent_usd
        report.cost_by_model = dict(client.budget.by_tier)
        report.stats.tavily_credits = tavily.ledger.used if tavily else 0
        payload = report.to_dict()
        receipts = { (r.url, r.endpoint, r.request_id, r.status): r for r in (tavily.receipts if tavily else []) }
        receipts.update({(r.url, r.endpoint, r.request_id, r.status): r for r in pinned_receipts})
        payload.update(mode="core", stopped_reason=stopped, cache_namespace=namespace, airgapped=config.airgapped,
                       accounting=client.budget.summary(), tavily_ledger=tavily.ledger.summary() if tavily else CreditLedger(config.tavily_credits).summary(),
                       retrieval_receipts=[r.to_dict() for r in receipts.values()],
                       retrieval_failures=tavily.failures if tavily else [],
                       campaigns=campaigns, contracts=[c.to_dict() for c in contracts],
                       harness_approvals=approvals, model_trace=[asdict(t) for t in traces], errors=errors)
        payload["ultra_allowance"] = {"limit_usd": config.ultra_budget_usd, "exposure_usd": ultra_spend,
                                      "reviewed_survivors": ultra_survivors, "survivor_limit": config.ultra_max_survivors}
        payload["stats"].update(body_entries=sum((c.get("stats") or {}).get("entered", 0) for c in campaigns),
                                 assertions_reached=sum((c.get("stats") or {}).get("assertion_reached", 0) for c in campaigns),
                                 attempted_campaigns=len(campaigns))
        write_campaign_report(directory, payload)
        _write(directory / "rejected.json", [asdict(f) for f in report.findings if f.status == "rejected"])
        _write(directory / "unresolved.json", [asdict(f) for f in report.findings if f.status == "unresolved"])
        _write(directory / "executions.json", campaigns)
        return payload

    checkpoint()
    try:
        repo = await clone(config.repo_url, config.ref, config.runs_dir / "_src" / f"{library}-{config.ref}")
        revision = await source_revision(repo)
        report.library.version = revision
        bundle, index = build_documentation(repo, config.package, revision, doc_paths=config.doc_paths)
        if config.online_lookup and not config.airgapped and tavily is not None:
            try:
                pinned_receipts.extend(await retrieve_documentation(bundle, config.repo_url, tavily))
            except Exception as exc:
                errors.append({"stage": "documentation_retrieval", "error": type(exc).__name__, "message": str(exc)})
        (directory / "docs_digest.json").write_text(bundle.digest())
        contracts_result, extraction_trace = await extract_contracts(client, bundle, config.package,
                                                                      config.max_targets, namespace=namespace)
        traces.extend(extraction_trace)
        if contracts_result is None:
            stopped = "contract extraction did not yield validated documentation-backed records"
            return checkpoint()
        contracts.extend(contracts_result)
        report.stats.contracts = len(contracts)
        _write(directory / "contracts.json", [c.to_dict() for c in contracts])
        checkpoint()
        env = await sandbox.prepare(config.repo_url, revision, list(config.setup_cmds))
        installed = await sandbox.run(env, "git rev-parse HEAD", 30)
        if installed.exit_code != 0 or installed.stdout.strip() != revision:
            raise ValueError("execution checkout does not match the pinned source revision")
        metadata_script = (
            "import importlib.metadata as m, importlib.util as u, json, sys; from pathlib import Path; "
            f"spec=u.find_spec({config.package!r}); "
            "origin=spec.origin if spec else None; "
            "matches=bool(spec and ((origin and Path(origin).resolve().is_relative_to(Path.cwd())) or "
            "(spec.submodule_search_locations and all(Path(p).resolve().is_relative_to(Path.cwd()) for p in spec.submodule_search_locations)))); "
            "print(json.dumps({'python':sys.version,'target_import_origin':origin,'source_matches_checkout':matches,"
            "'dependencies':sorted((d.metadata.get('Name','unknown'),d.version) for d in m.distributions())}))")
        metadata = await sandbox.run(env, shlex.quote(config.python) + " -c " + shlex.quote(metadata_script), 30)
        if metadata.exit_code != 0:
            raise ValueError("execution environment manifest could not be collected")
        manifest = json.loads(metadata.stdout.strip().splitlines()[-1])
        if not manifest.get("source_matches_checkout"):
            raise ValueError("installed target import does not resolve to the pinned checkout")
        _write(directory / "environment.json", {"repository": config.repo_url, "commit": revision,
                                                 "setup_commands": list(config.setup_cmds), **manifest})
        for contract in contracts:
            if contract.status == "ambiguous":
                errors.append({"contract_id": contract.contract_id, "stage": "contract", "error": "ambiguous contract refused"})
                checkpoint()
                continue
            for variant in range(config.variants_per_target):
                feedback = ""
                for attempt in range(2):
                    frozen = contract.hash
                    row = {"contract_id": contract.contract_id, "contract_hash": frozen,
                           "variant": variant, "attempt": attempt, "kind": "generating", "stats": None}
                    campaigns.append(row)
                    checkpoint()
                    approved, strategy_trace, feedback = await generate_harness(client, contract, index,
                        namespace=namespace, variant=variant * 2 + attempt, feedback=feedback)
                    traces.extend(strategy_trace)
                    if approved is None:
                        row.update(kind="harness_rejected", reason=feedback)
                        report.stats.infra_failures += 1
                        checkpoint()
                        continue
                    approvals.append(approved.approval)
                    artifact = directory / "harnesses" / f"{contract.contract_id}-v{variant}-a{attempt}.json"
                    _write(artifact, {"adapter_source": approved.harness.adapter_source,
                                      "strategy_source": approved.harness.strategy_source,
                                      "control_input": approved.control_input, "approval": approved.approval})
                    code = render_test(contract, approved.harness, max_examples=config.max_examples)
                    row.update(approval=approved.approval, wrapper_hash=sha256_text(code), kind="executing")
                    checkpoint()
                    outcome = await run_contract(sandbox, env, contract, approved.harness,
                                                   max_examples=config.max_examples, python=config.python,
                                                   timeout_s=config.campaign_timeout_s)
                    if contract.hash != frozen:
                        raise RuntimeError("campaign modified a frozen contract")
                    report.stats.campaigns += 1
                    row.update(outcome_dict(outcome))
                    checkpoint()
                    if outcome.is_candidate:
                        signature = failure_fingerprint(outcome)
                        if signature in fingerprints:
                            row["duplicate_of"] = fingerprints[signature]
                            checkpoint()
                            break
                        failure = outcome.stats["last_failure"]
                        identifier = f"f{len(report.findings) + 1}"
                        fingerprints[signature] = identifier
                        finding = Finding(identifier, contract.claim, "raw_anomaly",
                            ContractRef(contract.contract_id, contract.version, contract.hash, contract.family,
                                        contract.claim, contract.status,
                                        [EvidenceRef(e.source, e.excerpt, e.retrieved, getattr(e, "content_hash", "")) for e in contract.evidence]),
                            repro=code, actual=failure.get("actual", failure.get("error", outcome.reason)),
                            expected=failure.get("expected", contract.claim))
                        finding.route_trace.extend([*extraction_trace, *strategy_trace])
                        report.findings.append(finding)
                        checkpoint()
                        try:
                            value = literal_value(failure["input"])
                            fixed = Harness(approved.harness.adapter_source,
                                            "import copy\ndef inputs():\n    return st.just(" + repr(value) + ").map(copy.deepcopy)\n")
                            finding.repro = render_test(contract, fixed, max_examples=1) + "\nif __name__ == '__main__':\n    test_contract()\n"
                        except ValueError:
                            pass  # Investigator retains this as unresolved; no unsafe eval fallback.
                        finding_dir = directory / "findings" / identifier
                        finding_dir.mkdir(parents=True)
                        (finding_dir / "repro.py").write_text(finding.repro)
                        (finding_dir / "discovery.py").write_text(code)
                        tools = RefutationTools(sandbox, env, contract, approved, index, identifier, failure["input"],
                                                python=config.python, tavily=tavily, online_lookup=config.online_lookup,
                                                airgapped=config.airgapped, repo_url=config.repo_url)
                        investigations[identifier] = tools
                        tools.on_update = checkpoint
                        investigation = await investigate_candidate(client, tools, outcome, namespace=namespace)
                        traces.extend(investigation.trace)
                        finding.route_trace.extend(investigation.trace)
                        checkpoint()
                        if (investigation.status == "ai_reviewed" and config.ultra_review
                            and ultra_survivors < config.ultra_max_survivors):
                            from nightshift.pipeline.confirm import review_core_survivor
                            ultra_survivors += 1
                            trace_count = len(finding.route_trace)
                            ultra_spend += await review_core_survivor(client, sandbox, env, finding, contract, approved, index,
                                config, namespace=namespace, allowance_usd=max(0, config.ultra_budget_usd - ultra_spend))
                            tools.result.checks = list(finding.checks)
                            traces.extend(finding.route_trace[trace_count:])
                        checkpoint()
                        break
                    repairable = (outcome.kind in {"vacuous", "setup_error", "infra_error"} or outcome.low_reach)
                    if outcome.kind != "passed":
                        report.stats.infra_failures += 1
                    feedback = json.dumps({"kind": outcome.kind, "reason": outcome.reason,
                        "reach_rate": outcome.reach_rate, "low_reach": outcome.low_reach,
                        "counters": {k: (outcome.stats or {}).get(k) for k in
                                     ("entered", "precondition_ok", "assertion_reached", "api_calls", "untracked_apis")}})
                    checkpoint()
                    if not repairable:
                        break
    except BudgetExceeded as exc:
        stopped = f"budget: {exc}"
        for tools in investigations.values():
            if tools.result.status == "unresolved":
                tools.result.reason = stopped
        errors.append({"stage": "core", "error": type(exc).__name__, "message": str(exc)})
    except Exception as exc:
        stopped = f"infrastructure: {type(exc).__name__}: {exc}"
        errors.append({"stage": "core", "error": type(exc).__name__, "message": str(exc)})
    finally:
        if env is not None:
            try:
                await sandbox.close(env)
            except Exception as exc:
                errors.append({"stage": "cleanup", "error": type(exc).__name__, "message": str(exc)})
        if own_tavily:
            await tavily.aclose()
        checkpoint()
    return checkpoint()
