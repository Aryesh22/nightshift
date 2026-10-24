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
