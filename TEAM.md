# 👥 Nightshift Team Plan

**Deadline:** Oct 30, 2026 @ 10:00am PDT. **Our target: submit Oct 29.**
**Budget:** $0 out of pocket (free credits only). **Rule:** if a task stalls for more than 1 day, say so in the group chat and Aryesh takes it over.

## Roles
Swap roles if someone's skills fit another one better. Just update this file.

| Person | Role | Owns |
|---|---|---|
| **Aryesh** ([@Aryesh22](https://github.com/Aryesh22)) | 🧠 AI pipeline lead | Model client, prompts, Read → Propose → Triage → Confirm, cascade router, benchmark |
| **Jatin** ([@jatin-encrypted](https://github.com/jatin-encrypted)) | ⚙️ Execution & integrations | Sandbox (Docker + Nebius), test runner, Tavily, Serverless Jobs, target library shortlist |
| **Ruchir** ([@Ruchir038](https://github.com/Ruchir038)) | 🎨 Product & story | Next.js dashboard, replay mode, deploy, README, video, Devpost write-up |

## Contracts between us (agree on these on Day 1 so everyone can work in parallel)
- **Aryesh ↔ Jatin:** the `SandboxExecutor` interface (`prepare`, `fork`, `run` → `RunResult`). Aryesh's pipeline only calls this interface.
- **Aryesh/Jatin → Ruchir:** `runs/<run_id>/report.json`, the single file the dashboard reads. Ruchir builds against a **fake sample `report.json`** from Day 1 and doesn't wait for the real pipeline.

```jsonc
// report.json (shape v0, extend as needed)
{
  "run_id": "2026-10-23-attrs",
  "library": {"name": "attrs", "version": "x.y.z", "repo": "https://github.com/..."},
  "stats": {"properties_proposed": 200, "failures": 40, "triaged_real": 9, "verified": 6,
            "cost_usd": 0.82, "cost_per_verified_bug": 0.14},
  "cost_by_model": {"lightning": 0.21, "super": 0.33, "ultra": 0.28},
  "bugs": [{
    "id": "b1", "title": "...", "severity": "medium", "property": "roundtrip",
    "repro": "python code", "traceback": "...", "root_cause": "...",
    "patch_diff": "...", "patch_verified": true, "duplicate_of": null,
    "route_trace": [{"stage": "triage", "model": "super", "thinking": 512, "cost_usd": 0.004}]
  }]
}
```

## Timeline and tasks
Tick the boxes as you go.

### Phase 1: Foundations (Oct 19–20)
- [x] **Aryesh:** repo layout, `uv` project, Nemotron client (cache + cost meter + hard $ cap), `SandboxExecutor` + `report.json` contracts, fake `samples/report.json`
- [ ] **Aryesh:** check model IDs with `scripts/check_models.py` (needs `NEBIUS_API_KEY`)
- [ ] **Jatin:** request Sandbox beta access *today*, `SandboxExecutor` + `DockerSandbox`, claim credits, get Tavily key
- [ ] **Ruchir:** Next.js app skeleton, fake `report.json`, layout of the morning report page

### Phase 2: Pipeline + dashboard (Oct 21–23)
- [ ] **Aryesh:** Read + Propose (Hypothesis properties) → Triage (Super) → Confirm (Ultra repro + patch)
- [ ] **Jatin:** checkpoint-and-fork parallel runner, timeouts, Tavily docs crawl + GitHub issue dedupe, `NebiusContreeSandbox` once access arrives
- [ ] **Ruchir:** bug cards, repro viewer, patch diff view, cost page, pipeline animation

### Phase 3: Real hunting (Oct 23–26)
- [ ] **Jatin:** shortlist 20 libraries (used, pure Python, thin tests, clear properties), overnight runs (Serverless Jobs if possible)
- [ ] **Aryesh:** cascade router (rules first, escalate on failure, log cost), tune false positives
- [ ] **ALL:** a human reproduces every bug → file genuine ones **by Oct 25–26** (polite, note AI assistance)
- [ ] **Ruchir:** replay mode, capped "try live" button, deploy to Vercel/Render (free)

### Phase 4: Proof + submission (Oct 26–29)
- [ ] **Aryesh:** benchmark on 3–5 libraries: Nightshift vs. "Ultra for everything" vs. "Lightning for everything" → bugs-per-$ chart, honest precision
- [ ] **Jatin:** product feedback write-up (Token Factory, Sandboxes, Nemotron), setup instructions in the README
- [ ] **Ruchir:** 3-min video (script + recording), Devpost write-up, architecture diagram
- [ ] **ALL (Oct 29):** final checklist: repo **public**, license visible, demo live until Dec 15, video public, submit

## Daily rhythm
- **10-minute sync each day:** what I did, what I'm doing next, what's blocking me
- Work on branches → PR → one teammate reviews → merge to `main`
- Never commit API keys. Use `.env`, which is gitignored.
