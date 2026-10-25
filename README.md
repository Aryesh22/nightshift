# 🌙 Nightshift

**An overnight AI bug hunter for open-source Python libraries.**
Point it at a library before bed. In the morning you get candidate bugs that break what the docs promise, each with a reduced repro, the checks that tried to disprove it, and the dollar cost of finding it.

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) · Track: **Coding & Agentic Engineering**

## How it works
1. **Contract:** Nemotron 3.5 Lightning reads only the docs, signatures and docstrings and writes down what the library *promises* (round trips, equivalent calls), with an exact quote as evidence
2. **Harness:** a second Lightning context writes the adapter and a Hypothesis strategy from the frozen contract and the source; Nemotron 3 Super approves the adapter without seeing function bodies
3. **Execute:** the controller-owned test wrapper runs in an isolated sandbox (Docker locally, Docker on a Nebius VM remotely), forked from one checkpoint; it counts whether inputs really reached the assertion and the APIs
4. **Investigate:** Super tries to *disprove* each failure with a fixed tool set and 3 fresh-process replays, and may answer `unresolved`
5. **Dedupe:** Tavily searches the repo's own issues and release notes for known behaviour, as a lead to check
6. **Report:** `report.json` with every candidate, rejected ones included, the checks that ran, and the cost

Patches are optional and come last (a capped Nemotron 3 Ultra review of the best survivors).

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
| `src/nightshift/pipeline/` | `core.py` contract-first campaign; `run.py` baseline arm; investigator, verification | Aryesh |
| `src/nightshift/sandbox/` | `SandboxExecutor` interface, `DockerSandbox`, Nebius-VM variant, dev-only local runner (**not isolated**) | Jatin |
| `src/nightshift/tavily.py` | Tavily Search/Extract with receipts, credit ledger and air gap | Jatin |
| `src/nightshift/report.py` | `report.json` contract (schema v1) | shared |
| `samples/report.json` | **Fake** report for building the dashboard | Ruchir |

## Status
🚧 Under active development.

## Running a campaign
```bash
uv run nightshift run https://github.com/ORG/REPO --package PACKAGE --budget 1 --sandbox docker
```
Two modes share one `report.json` schema (v1):
- `--mode core` (default): the contract-first pipeline from TEAM.md v2. Lightning writes contracts from docs only, then adapters + Hypothesis strategies from the frozen contract and source. Super approves the adapter without seeing function bodies, then plays detective on each failure with a fixed tool set (control input, doc/source inspection, boundary neighbourhood, known-issue search) and may answer `unresolved`. Every candidate gets 3 fresh-process replays.
- `--mode baseline`: the original one-prompt + passive-judge pipeline, kept only as the comparison arm of the PBT-Bench benchmark.

Useful flags: `--doc-path docs/guide.md` (repeatable; which files count as documentation), `--max-examples 200`, `--ultra-review --ultra-budget 0.02` (optional, separately capped root-cause review of survivors; never needed for a finding), `--airgapped` (no external retrieval, not even from cache; use for benchmark runs).

Each run writes `runs/<run_id>/`: `report.json`, `contracts.json`, `harnesses/`, `findings/<id>/{repro.py,discovery.py}`, `investigations/`, `rejected.json`, `unresolved.json`, `executions.json`, `environment.json`. Findings stay `ai_reviewed` until a human validates them; nothing in the code marks a finding `human_validated` or `maintainer_confirmed`.

## Sandboxes
Generated code only ever runs through a `SandboxExecutor` (`src/nightshift/sandbox/base.py`).
- `--sandbox docker` (default) needs a running Docker engine. The first run builds `nightshift-runtime:py312-v1` (Python 3.12, git, pytest, Hypothesis). `prepare` clones and installs with network access, commits a checkpoint image, and every `fork` runs from that image with `--network none`, no host mounts, no credentials, dropped capabilities, and CPU/memory/pids/file-size/output limits.
- `--sandbox nebius` is the same executor talking to a Docker engine on a Nebius VM: set `NIGHTSHIFT_NEBIUS_DOCKER_HOST=ssh://user@vm`. It is not the Token Factory managed-sandbox API.
- `UnsafeLocalSandbox` is for tests and the stdlib only. It is not isolated.

## Tavily
Retrieval is opt-in: `--online-lookup` plus `TAVILY_API_KEY`. Each run has its own credit ledger (`--tavily-credits`, default 100 of the 1,000 free credits/month; overage is never enabled). Documentation is extracted from GitHub at the pinned commit and only becomes contract evidence when its text matches the local file. Known-issue search is limited to the repo's own issues/releases and produces a lead to check, never a "new bug" or "known bug" verdict. Every request leaves a receipt (URL, content hash, request id, credits, live/cache).

## Team
- [@Aryesh22](https://github.com/Aryesh22)
- [@jatin-encrypted](https://github.com/jatin-encrypted)
- [@Ruchir038](https://github.com/Ruchir038)

## License
MIT
