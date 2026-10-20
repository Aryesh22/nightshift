# 👥 Nightshift Team Plan (v2, Oct 20)

**Deadline:** Oct 30, 2026 @ 10:00am PDT (10:30pm IST). **Our target: submit Oct 29.**
**Budget:** $0 out of pocket (free credits only). **Rule:** if a task stalls for more than 1 day, say so in the group chat and Aryesh takes it over.

## What changed in v2 (read this first)
We changed the plan after the research review in `NIGHTSHIFT_RESEARCH.md`. In one line:
**Find bugs that break what the docs promise, try hard to prove each bug is fake, and show the evidence.**

1. **Contract first.** Before testing, write down what the *docs* promise (a "contract"), without looking at the code. Then test the code against it, so the AI can't copy a bug into its own test.
2. **Few smart generators, not hundreds of tests.** The model writes a Hypothesis strategy, and Hypothesis runs thousands of inputs.
3. **Test pairs of APIs.** Examples: `encode`/`decode`, a convenience call vs. the general call, chunked vs. whole.
4. **Triage is a detective.** Super tries to *disprove* each bug (bad input? version? flaky? broken test?) and may answer **unresolved**.
5. **Evidence bundle per bug:** a reduced repro, a passing control, 3 fresh-process replays, the doc source, and the detective's checks.
6. **Ultra only on the best survivors.** Patches are optional and come last.
7. **One honest benchmark:** 10 PBT-Bench tasks × (simple baseline vs. Nightshift) = 20 runs, under $10.
8. **No learned router before the deadline.** Use simple escalation rules and log why each step escalated.

## Roles

| Person | Role | Owns |
|---|---|---|
| **Aryesh** ([@Aryesh22](https://github.com/Aryesh22)) | 🧠 Contracts & AI pipeline | Contract format, adapters, test wrapper, prompts, Lightning generation, Super investigator, Ultra review, escalation rules |
| **Jatin** ([@jatin-encrypted](https://github.com/jatin-encrypted)) | ⚙️ Runtime & evidence | Sandbox (Docker → Nebius), fresh-process replay, shrinking, investigator tools, Tavily docs + known-issue search with receipts, real-package campaigns |
| **Ruchir** ([@Ruchir038](https://github.com/Ruchir038)) | 🎨 Product & evaluation | Next.js dashboard, evidence views, PBT-Bench evaluation (Aryesh helps set it up), deploy, video, Devpost write-up |

## Contracts between us
- **Aryesh ↔ Jatin:** `src/nightshift/sandbox/base.py` (`prepare(repo_url, ref, setup_cmds)`, `fork`, `put_file`, `run(cmd)` → `RunResult`, `close`).
  `src/nightshift/sandbox/local.py` is a working (un-isolated) reference implementation; `DockerSandbox` should pass the same tests.
  Contract campaigns run `python -m pytest -q -s ...`, whose stdout carries a `NIGHTSHIFT_STATS {...}` line.
- **Aryesh/Jatin → Ruchir:** `runs/<run_id>/report.json`, defined in `src/nightshift/report.py`.
  Build the dashboard against **`samples/report.json`** (fake data, schema v1). Regenerate it with `uv run python samples/make_sample_report.py`.
- **Finding statuses**, used everywhere: `raw_anomaly` → `reproducible` → `ai_reviewed` → `human_validated` → `maintainer_confirmed`, plus `unresolved` and `rejected` (with a reason). The dashboard shows rejected findings too.

## Timeline and tasks
Tick the boxes as you go.

### Phase 1: Foundations (Oct 19–21)
- [x] **Aryesh:** repo, `uv`, Nemotron client (cache, cost meter, hard $ cap), sandbox + report contracts
- [x] **Aryesh:** contract format, controller-owned test wrapper, adapter audit, first contract/adapter pair (`base64` round trip)
- [ ] **Aryesh:** move `pipeline/` onto contracts + `report.json` v1 (it still writes v0 and uses the old learned router)
- [ ] **Aryesh:** get the Nebius API key, then run `scripts/check_models.py --ping`. Confirm model IDs and which reasoning controls actually work.
- [ ] **Jatin:** request Sandbox beta access **today**. Build `DockerSandbox` (no secrets inside, CPU/memory/time limits). Get a Tavily key.
- [ ] **Ruchir:** Next.js skeleton using `samples/report.json`, plus the finding card layout (the 5 questions below)
- [ ] **Ruchir + Aryesh:** preflight **2 PBT-Bench tasks** through its evaluator, then write down the rules for choosing the 10 tasks *before* running Nightshift

### Phase 2: Working slice (Oct 22–23)
- [ ] **Aryesh:** Lightning writes contracts from docs only and strategies from the contract + source. Add API-pair hints (names, signatures, existing tests). Build the Super investigator with a refutation checklist that may answer `unresolved`.
- [ ] **Jatin:** Tavily Search + Extract for versioned docs (store URL, excerpt, hash, credits). Add the 3-replay fresh-process runner, the shrinking pass, and the investigator tools (`run_control_input`, `inspect_doc_and_source`, `check_boundary_neighborhood`, `search_known_issues_tavily`).
- [ ] **Ruchir:** finding cards, a "Documentation evidence" view, a "Checks we ran" view, a rejected-findings view, and a cost view
- [ ] **Ruchir:** pick the 10 PBT-Bench tasks (4 L1, 4 L2, 2 L3). Hide answers, fixes and defect notes from the agent.

### Phase 3: Real hunting + benchmark (Oct 24–25)
- [ ] **Aryesh:** fix the generation/triage failures we observe. Build the **baseline** variant (one prompt + passive judge) for the comparison.
- [ ] **Jatin:** campaigns on **1–3 prepared real packages**. Known-issue search on survivors.
- [ ] **Ruchir + Aryesh:** run the **20-campaign comparison** (cap $10). Record every cost, failure and denominator.
- [ ] **ALL:** a human reproduces every survivor. File genuine ones **by Oct 25–26** (be polite, mention AI assistance).
- [ ] **Ruchir:** deploy the dashboard (Vercel/Render free) with replay mode and a capped "try live" button

### Phase 4: Proof + submission (Oct 26–29)
- [ ] **Aryesh:** capped Ultra root-cause review on 1–2 validated survivors (skip it if there are none). Optional patch, only with hidden-test validation.
- [ ] **Jatin:** product feedback write-up (Token Factory, Sandboxes, Nemotron, Tavily). Setup instructions in the README.
- [ ] **Ruchir:** 3-min video, Devpost write-up, architecture diagram
- [ ] **ALL (Oct 29):** final checklist: repo **public**, license visible, demo live until Dec 15, video public, submit

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

Tavily (1,000 free credits/month): 250 docs · 200 known-issue search · 200 dev/demo · 350 reserve. **Never enable paid overage.**

## Claims we must NOT make
- "First system to…" or "proves the bug/patch is correct"
- "New bug" just because a search found no matching issue
- "Maintainer confirmed" when only we checked it
- Copying a paper's numbers as our results. We only claim what we measured, with the counts.

## Daily rhythm
- **10-minute sync each day:** what I did, what I'm doing next, what's blocking me
- Work on branches → PR → one teammate reviews → merge to `main`
- Never commit API keys. Use `.env`, which is gitignored.
