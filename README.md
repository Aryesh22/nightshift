# 🌙 Nightshift

**An overnight AI bug hunter for open-source Python libraries.**
Point it at a library before bed. In the morning you get verified bugs, each with a minimal reproduction, a tested patch, and the dollar cost of finding it.

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) · Track: **Coding & Agentic Engineering**

## How it works
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

## Team
- [@Aryesh22](https://github.com/Aryesh22)
- [@jatin-encrypted](https://github.com/jatin-encrypted)
- [@Ruchir038](https://github.com/Ruchir038)

## License
MIT
