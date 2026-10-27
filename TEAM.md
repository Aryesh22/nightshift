# 👥 Nightshift Team Plan (v3, Oct 27)

**Deadline:** Oct 30, 2026 @ 10:00am PDT (10:30pm IST). **Our target: submit Oct 29 evening IST.**
**Budget:** $0 out of pocket (free credits only). **Rule:** if a task stalls for more than half a day now, say so in the group chat and Aryesh takes it over.

## What changed in v3 (read this first)
- **PR #1 (Jatin) is merged.** `main` now has the Core contract-first pipeline, `DockerSandbox`, the Nebius-VM variant, the Tavily client with credit ledger, the Super investigator and 3-replay runner. Aryesh's review fixes are on `aryesh/core-from-pr1` (budget overrun handling, Tavily edge cases, Docker timeout, defaults, README) and go in next.
- **PR #2 (Jatin, paired evaluation harness) is under review, not merged.** The metric code is reusable, but the "self-test" produces a Core-vs-Baseline table from hand-written numbers. Nothing from it may appear in the write-up, video or README until it has run on real PBT-Bench tasks with PBT-Bench's own evaluator. See "Claims we must NOT make".
- **Nothing has talked to a real model or a real Docker engine yet.** Every passing test uses a scripted model and the unsafe local runner. That is the single biggest risk with 3 days left, so the first two tasks below are about that.
- **Only tick a box for your own task, after you ran it.** v2's board had boxes ticked for work the ticker could not have seen. A ❓ below means "owner, confirm in today's sync".

The plan itself is unchanged: **find bugs that break what the docs promise, try hard to prove each bug is fake, and show the evidence.** Contract first, few smart generators, API pairs, detective triage that may say `unresolved`, an evidence bundle per bug, Ultra only on survivors, one honest benchmark, no learned router.

## Roles

| Person | Role | Owns |
|---|---|---|
| **Aryesh** ([@Aryesh22](https://github.com/Aryesh22)) | 🧠 Pipeline backend | Contract format, adapters, test wrapper, prompts, Lightning generation, Super investigator, Ultra review, escalation rules, running the real campaigns, `main` and reviews |
| **Jatin** ([@jatin-encrypted](https://github.com/jatin-encrypted)) | ⚙️ Runtime & evidence | Sandbox (Docker → Nebius VM), fresh-process replay, investigator tools, Tavily docs + known-issue search with receipts, real-package campaigns, product feedback write-up |
| **Ruchir** ([@Ruchir038](https://github.com/Ruchir038)) | 🎨 Access, evaluation & product | **Nebius/Tavily keys and model checks**, human-validation CLI, benchmark manifest + scoring script, Next.js dashboard, deploy, video, Devpost write-up |

## Contracts between us (unchanged, two additions)
- **Aryesh ↔ Jatin:** `src/nightshift/sandbox/base.py` (`prepare`, `fork`, `put_file`, `run` → `RunResult`, `close`). `DockerSandbox` must pass the same behaviour as `UnsafeLocalSandbox` does in the tests.
- **Aryesh/Jatin → Ruchir:** `runs/<run_id>/report.json`, schema v1 in `src/nightshift/report.py`. Build the dashboard against **`samples/report.json`**; regenerate it with `uv run python samples/make_sample_report.py`. **Schema changes go in their own PR, with Ruchir tagged, and the sample regenerated in the same PR.** Core reports also carry `contracts`, `campaigns`, `accounting`, `tavily_ledger`, `retrieval_receipts`, `rejected.json`, `unresolved.json` next to the report.
- **Ruchir → Aryesh/Jatin (new):** `benchmark/tasks.json`, a task manifest in the format `src/nightshift/eval.py` reads on PR #2: `task_id, repo_url, ref, package, doc_paths, setup_cmds, known_defects, hard_negatives, budget_usd`.
- **Finding statuses:** `raw_anomaly` → `reproducible` → `ai_reviewed` → `human_validated` → `maintainer_confirmed`, plus `unresolved` and `rejected` (with a reason). Only a human sets `human_validated`; the code never does.

## Status board (honest, as of Oct 27 morning)

### Done and on `main`
- [x] **Aryesh:** repo, `uv`, Nemotron client (cache, cost meter, hard $ cap), sandbox + report contracts
- [x] **Aryesh:** contract format, controller-owned test wrapper, adapter audit, first contract/adapter pair (`base64` round trip)
- [x] **Aryesh:** `pipeline/` on contracts + `report.json` v1 (landed via PR #1, reviewed by Aryesh)
- [x] **Jatin:** `DockerSandbox` (no secrets inside, CPU/memory/pids/time/output limits, offline forks) and the Nebius-VM variant, **written and unit-tested only**
- [x] **Jatin:** Tavily Search + Extract with URL, excerpt, hash, request id, credits, live/cache receipts; per-run credit ledger; air gap
- [x] **Jatin:** 3-replay fresh-process runner and the four investigator tools (`run_control_input`, `inspect_doc_and_source`, `check_boundary_neighborhood`, `search_known_issues_tavily`)
- [x] **Jatin + Aryesh:** Lightning writes contracts from docs only and harnesses from contract + source; Super approves adapters without bodies and investigates with a refutation loop that may answer `unresolved`; baseline arm kept for the comparison

### Not done, or unverified
- [ ] **Ruchir (moved from Aryesh):** Nebius API key, then `uv run python scripts/check_models.py`. Confirm the three model IDs and which reasoning controls work. **Nothing else matters until this works.**
- [ ] ❓ **Jatin:** Sandbox beta access requested? Tavily key obtained?
- [ ] **Jatin:** run `DockerSandbox` for real once (`base64` contract: prepare → fork → put_file → run → close) and paste the output in the PR thread
- [ ] ❓ **Ruchir:** Next.js skeleton against `samples/report.json`? Finding card with the 5 questions?
- [ ] ❓ **Ruchir:** 2 PBT-Bench tasks preflighted through PBT-Bench's own evaluator; selection rules for the 10 tasks written down
- [ ] **Ruchir:** the 10 tasks picked (4 L1, 4 L2, 2 L3), answers hidden from the agent, `benchmark/tasks.json` committed

## The last three days

### Oct 27 (today): make it real
- [ ] **Aryesh:** merge `aryesh/core-from-pr1`. Review PR #2 (see above).
- [ ] **Ruchir:** Nebius key + model check (item 1 below) **first thing**, then the dashboard.
- [ ] **Aryesh:** first **real** Core campaign on one small, pure-Python package (candidates: `python-slugify`, `toml`, `tabulate`) with `--budget 0.50 --airgapped --sandbox docker` as soon as Jatin's Docker run is confirmed. Fix whatever breaks in contract extraction, harness generation and the investigator loop. This is where the prompts meet reality for the first time.
- [ ] **Jatin:** real Docker run (above). Then prepare 2 real packages (clone + install inside the sandbox works, `setup_cmds` recorded) and run one Core campaign on each with `--online-lookup` so we get real Tavily receipts.
- [ ] **Jatin:** on PR #2, split the reusable part (`EvalTask`, `load_manifest`, `compute_metrics`, the Markdown table) from the hand-written self-test, give each arm its own `Budget(task.budget_usd)`, and drop `--sandbox local` for real packages.
- [ ] **Ruchir:** everything under "Ruchir's work" below, in that order.

### Oct 28: evidence
- [ ] **Aryesh:** run the **paired comparison** on the 10 tasks from Ruchir's manifest (20 campaigns, cap $10) and commit the `runs/` output. Record every cost, failure and denominator. If credits are short, run 5 tasks and say so.
- [ ] **Ruchir:** score those runs with PBT-Bench's evaluator and put the table in `benchmark/RESULTS.md`, with denominators.
- [ ] **ALL:** a human reproduces every `ai_reviewed` survivor from the real campaigns. Set `human_validated` by hand in the run's `report.json` only after you ran the repro yourself. File genuine ones upstream (polite, mention AI assistance, link the evidence bundle).
- [ ] **Jatin:** known-issue search on every survivor; product feedback write-up (Token Factory, Sandboxes, Nemotron, Tavily) as `docs/product-feedback.md`.
- [ ] **Aryesh:** capped Ultra review on 1–2 validated survivors (skip if none). Optional patch only with validation.
- [ ] **Ruchir:** deploy the dashboard with replay mode loading our real runs; demo button capped at $0.25.

### Oct 29: ship
- [ ] **Ruchir:** 3-min video, Devpost write-up, architecture diagram (uses only numbers from the real runs and the benchmark table)
- [ ] **Jatin:** README setup instructions verified on a clean machine (Docker path end to end)
- [ ] **Aryesh:** final pass on `main`, tag `v0.1`
- [ ] **ALL:** final checklist: repo **public**, license visible, demo live until Dec 15, video public, submit

## Ruchir's work (Oct 27–29, in priority order)
All items are yours alone; none waits on Aryesh or Jatin. Items 1, 3 and 4 are backend work in Python; 2, 5 and 6 are the product. If something is unclear, post the question in the group chat and move to the next item. Suggested time next to each.

1. **Access and model check (today, first, ~1–2 h).**
   - Get the Nebius Token Factory API key (the hackathon credits page) and a Tavily key. Put them in your local `.env` as `NEBIUS_API_KEY` and `TAVILY_API_KEY`. Never commit them.
   - Run `uv run python scripts/check_models.py`. It lists the models the key can see, calls each of Lightning / Super / Ultra once (well under $0.01), and prints token usage and whether the thinking switch worked.
   - Write what you saw into `docs/access.md`: exact model IDs, which endpoint served Ultra, whether `chat_template_kwargs.enable_thinking` or a `reasoning_budget` field was honoured, prices from the pricing page. If any ID differs from `src/nightshift/config.py`, change `config.py` in the same PR.
   - Post in the group chat the moment the three models answer. Everything Aryesh does today waits on this.
2. **Dashboard against `samples/report.json`** (today + tomorrow, Next.js, Vercel free tier):
   - **Run overview:** library name + version/commit, `status_counts`, total cost, `cost_per_validated_finding` ("n/a" when null; never divide by zero in the UI), Tavily credits used.
   - **Finding card** answering the 5 questions below: `contract.claim` + `contract.evidence[]` (source link, excerpt, retrieved live/cache/manual) → Q1; `repro`, `actual`, `expected` → Q2; `checks[]` (`question`, `tool`, `result`, `effect`) + `control` + `replays_passed/attempted` → Q3; `status`, `uncertainty`, `rejection_reason`, `known_behaviour` → Q4; `cost_usd`, `route_trace[]` → Q5.
   - **Rejected and unresolved view** (same cards, filtered) and a **cost table** (`cost_by_model`, per-finding cost).
   - **Replay mode:** load any `report.json` by file upload or `?report=<url>`. This is how the demo stays live after credits run out.
3. **Human-validation CLI (Oct 28 morning, ~2 h, Python).** `scripts/validate_finding.py <run_dir> <finding_id>`: prints the finding's claim, evidence and repro; runs `findings/<id>/repro.py` in a fresh process and shows the output; asks `validated / rejected / skip`; on an answer, rewrites `report.json` with the new `status` (`human_validated` or `rejected` with your typed reason), `validated_by` and an ISO timestamp, via `Report.load` / `Report.write` in `src/nightshift/report.py`. Add one test. This is the only code path allowed to set `human_validated`.
4. **Benchmark manifest and scoring (today evening + Oct 28, Python).**
   - `benchmark/SELECTION.md`: the rules (4 L1, 4 L2, 2 L3; pure Python; installs offline inside Docker; docs in the repo) and why.
   - Run 2 tasks through PBT-Bench's **own** evaluator (no Nightshift, no API key) and paste its output format into `SELECTION.md`.
   - `benchmark/tasks.json` in the manifest format above. `known_defects` and `hard_negatives` stay out of anything the agent reads.
   - `scripts/score_benchmark.py <runs_dir> <tasks.json>`: for each task, point PBT-Bench's evaluator at the `findings/<id>/repro.py` files of the run, collect its verdicts, and write `benchmark/RESULTS.md` with the table (precision, recall, cost, with denominators) for baseline and core. No keyword matching, no hand-typed numbers.
5. **Deploy** (Oct 28): Vercel, replay mode on by default, "try live" button capped at $0.25 and off when credits are gone.
6. **Video + Devpost + diagram** (Oct 29): one real finding card walked end to end, the table from `benchmark/RESULTS.md`, the cost. Script it on Oct 28 evening. The only input you need from others is the `runs/` folder, which Aryesh commits on Oct 28.
7. **Submission checklist owner:** you own the Oct 29 checklist and ping everyone until each box is ticked.

What **not** to spend time on: a learned router view, patch diffs (optional and last), animations, a landing page.

## Aryesh's work (Oct 27–29)
Backend only. Merge `aryesh/core-from-pr1`; review PR #2; once Ruchir's model check and Jatin's Docker run are green, run the first real Core campaign and fix contract extraction, harness generation and the investigator loop against a real model; run the 20-campaign comparison on Oct 28 and commit `runs/`; capped Ultra review on validated survivors; tag `v0.1` on Oct 29.

## Every finding card answers 5 questions
1. What documented behaviour seems broken? (with the doc link + excerpt)
2. What is the smallest repro we actually got?
3. Which checks tried to disprove it, and what happened?
4. What is its status, and what are we still unsure about?
5. What did it cost, including the rejected candidates?

## Credit budget (only if $50 actually arrives)
| Purpose | Cap |
|---|---:|
| Access checks + tiny pilot | $5 |
| Generation + investigator development | $12 |
| Real-package hunting | $8 |
| PBT-Bench comparison | $10 |
| Final demo + Ultra review + optional patch | $5 |
| Reserve for judges trying the demo | $10 |

Tavily (1,000 free credits/month): 250 docs · 200 known-issue search · 200 dev/demo · 350 reserve. The CLI caps each run at 100 by default. **Never enable paid overage.**

## Claims we must NOT make
- "First system to…" or "proves the bug/patch is correct"
- "New bug" just because a search found no matching issue
- "Maintainer confirmed" or "human validated" when only the code checked it
- Copying a paper's numbers as our results. We only claim what we measured, with the counts.
- **Any number from a self-test, fixture or sample report.** If it did not come from `runs/<run_id>/` of a real campaign, it is not a result.

## Daily rhythm
- **10-minute sync each day** (fixed time, pick one today): what I did, what I'm doing next, what's blocking me
- Work on branches → PR **with a body** (what, why, how tested) → one teammate reviews → merge to `main`. One topic per PR; PRs from a branch, not from a fork's `main`.
- Only the owner ticks their box, after running it.
- Never commit API keys. Use `.env`, which is gitignored.
