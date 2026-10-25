# 🌙 Nightshift

**An overnight AI bug hunter for open-source Python libraries.**
Run a supported library campaign and review candidate findings with reduced reproductions,
optional patch checks, and cost accounting. Human validation remains a separate step.

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) · Track: **Coding & Agentic Engineering**

## Intended workflow (integration in progress)
1. **Read:** Nemotron 3.5 Lightning reads the whole library and its docs (Tavily pulls docs and changelogs)
2. **Propose:** parallel Lightning calls write Hypothesis property-based tests
3. **Execute:** tests run in isolated sandboxes (Nebius Token Factory Sandboxes, falling back to Docker), branched from one checkpoint
4. **Triage:** Nemotron 3 Super decides whether the *test* is wrong or the *code* is wrong
5. **Confirm:** Nemotron 3 Ultra writes a minimal reproduction and a patch, then verifies the patch
6. **Dedupe:** Tavily checks for existing GitHub issues
7. **Report:** morning dashboard showing bugs, repros, patches, and cost per verified bug

A cost-aware cascade routes each step to the cheapest (model, thinking budget) that works, and escalates only on verifier failure.

## Stack
- NVIDIA Nemotron (Lightning / Super / Ultra) on Nebius Token Factory
- Nebius Token Factory Sandboxes and Serverless Jobs
- Tavily
- Python, Hypothesis, Next.js

## Setup
Needs [uv](https://docs.astral.sh/uv/) and Python 3.12.
```bash
uv sync                                       # install deps into .venv
cp .env.example .env                          # then paste NEBIUS_API_KEY and TAVILY_API_KEY
uv run python scripts/check_models.py         # confirm the Nemotron model IDs
uv run pytest                                 # run the tests (no API key needed)
```

## Repo layout
| Path | What | Owner |
|---|---|---|
| `src/nightshift/llm/` | Nemotron client: response cache, cost meter, hard $ cap | Aryesh |
| `src/nightshift/contracts/` | Contract records, frozen test wrapper, harness audit, outcome classes | Aryesh |
| `src/nightshift/pipeline/` | Read → propose → triage → confirm (moving to contract-first) | Aryesh |
| `src/nightshift/sandbox/` | `SandboxExecutor` interface + dev-only local runner (**not isolated**) | Jatin |
| `src/nightshift/report.py` | `report.json` contract (schema v1) | shared |
| `samples/report.json` | **Fake** report for building the dashboard | Ruchir |

## Status
🚧 Under active development.

## Campaign modes

The CLI defaults to `--mode core`. The repaired original pipeline remains available as
`--mode baseline`. Legacy Python calls that omit `mode` retain Baseline behavior;
select `RunConfig(..., mode="core")` or pass `mode="core"` to `run_nightshift` for Core.

```bash
uv run nightshift run https://github.com/ORG/REPO --package PACKAGE --mode core --airgapped --budget 1
uv run nightshift run https://github.com/ORG/REPO --package PACKAGE --mode baseline --airgapped --budget 1
```

Core derives frozen `roundtrip`/`equivalent` contracts from pinned README text, public
signatures and docstrings. Function bodies, decorators and executable default expressions
are excluded from that context. `--doc-path docs/versioned-guide.md` selects
approved text paths. A separate Lightning context receives the frozen contract and source
to generate adapters and constructive strategies; Super approves the mapping without the
target bodies. Controller-owned `run_contract` checks execution fidelity and allows one
bounded harness repair without changing the claim.

Core uses fixed model roles: Lightning for contracts/strategies, Super for adapter review
and active refutation. Each candidate receives three fresh-process replays. The investigator
has six total tool calls, three runtime experiments and two known-issue searches. It can
inspect allowlisted source, run literal-safe controls, test a bounded neighborhood and
request known-issue research. Acceptance requires matching replays, a passing control and
documentation inspection. Rejected and unresolved candidates remain visible.

External retrieval is opt-in with `--online-lookup` and `TAVILY_API_KEY`. Tavily Search and
Extract use explicit depths, `include_usage=True`, content hashes, request IDs and live/cache
receipts. Documentation extraction accepts commit-pinned GitHub URLs with matching local
evidence; unversioned search snippets cannot become contract evidence. Known-issue leads
remain uncertain until their applicability is checked. `--tavily-credits` sets a separate
ledger cap up to 1,000 credits. Reuse an injected Tavily client/ledger to share a cap across
multiple campaigns. Unknown charges remain estimated/pending.

`--airgapped` overrides online lookup and blocks retrieval caches too. Use it with frozen,
agent-approved documentation for controlled benchmark discovery. Mode selection alone
does not freeze the matched task, prompt, model, budget and cache configuration required
for the Research Section 16.2 comparison; Baseline preserves its existing routing policy.

Ultra is off by default. `--ultra-review --ultra-budget 0.02` enables a separately capped
survivor review. Unavailability or failed patch validation cannot erase a valid finding.
It does not grant human/maintainer validation or claim complete patch correctness.

Both modes emit shared schema v1. Core also writes contracts, adapter approvals, full
wrapper hashes, actual body/assertion counts (including shrink/replay), an execution
manifest, investigation/replay receipts, rejected/unresolved logs, model accounting and
Tavily ledgers under `runs/<run_id>/`. Each Core run receives a distinct response-cache
namespace unless an explicit `RunConfig.cache_namespace` is supplied.

`nightshift run` writes schema v1 reports. Findings remain AI-reviewed candidates until a
human validates them; the legacy `bugs`/`verified` fields are compatibility views of repro
checks. Patches are optional candidates checked against the unchanged discovery test and
repro, protected file hashes, and a library-only diff policy. Hidden tests and a complete
upstream test suite are not yet part of patch validation.

The `docker` backend requires a running Docker engine. Its first preparation builds a
Python 3.12 image with Git, pytest and Hypothesis. Clone/install preparation has network
access; workers use independent filesystem checkpoints with network disabled, no host
mounts or application credentials, and CPU/memory/process/time/output limits.
`--sandbox nebius` uses Docker on a provisioned Nebius VM: set
`NIGHTSHIFT_NEBIUS_DOCKER_HOST=ssh://user@your-nebius-vm`. It has no local fallback and does
not implement the native Nebius/Contree managed sandbox API.

The model client reserves a conservative UTF-8 byte bound for supported text requests.
Each retry receives its own reservation. Missing usage, ambiguous transport failures and
malformed responses remain pending in the report's accounting ledger. Provider rates and
tokenizer/template assumptions still require verification; over-bound usage blocks
further calls for reconciliation.

## Team
- [@Aryesh22](https://github.com/Aryesh22)
- [@jatin-encrypted](https://github.com/jatin-encrypted)
- [@Ruchir038](https://github.com/Ruchir038)

## License
MIT
