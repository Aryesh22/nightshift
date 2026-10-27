# 🌙 Nightshift

**Autonomous, Contract-Driven Bug-Hunting Pipeline for Open-Source Python Libraries.**  
*Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) — Track: Coding & Agentic Engineering.*

---

## 🚀 Overview & Research v1.1 Architecture

Current automated bug-hunting tools and LLM code generators suffer from the **curse of synthetic testing**: hallucinated specifications, vacuous generator hacks (`assume(False)` or constant inputs), code-contaminated properties that merely reflect existing bugs, and noisy false alarms.

**Nightshift Research v1.1** eliminates false positives through formal contract isolation, constructive Hypothesis property generation, active refutation investigation, and multi-process replay determinism:

```
           ┌──────────────────────────────────────────────┐
           │        Pinned Documentation & Type Stubs     │
           └──────────────────────┬───────────────────────┘
                                  │
                       [ Upgrade A: Docs-Only Isolation ]
                                  ▼
           ┌──────────────────────────────────────────────┐
           │  Frozen Contracts (Round-Trip / Equivalence) │
           │   - Extracted by Nemotron-3.5-Lightning      │
           │   - SHA-256 Content-Hashed Evidence          │
           └──────────────────────┬───────────────────────┘
                                  │
                      [ Upgrade C: Audited Harnesses ]
                                  ▼
           ┌──────────────────────────────────────────────┐
           │ Constructive Hypothesis Strategies & Runners │
           │   - AST Audit (No sys.exit, assert, assume)  │
           │   - Non-Vacuity Counters (API Calls, Bodies) │
           └──────────────────────┬───────────────────────┘
                                  │ (Anomaly Discovered)
                                  ▼
           ┌──────────────────────────────────────────────┐
           │ [ Upgrade G: 3x Fresh-Process Replay Check ] │
           └──────────────────────┬───────────────────────┘
                                  │ (Survived Replays)
                                  ▼
           ┌──────────────────────────────────────────────┐
           │   [ Upgrade E: Active Refutation Agent ]     │
           │   - Nemotron-3-Super-120B (4 Bounded Tools)  │
           │     1. run_control_input (environment check) │
           │     2. inspect_doc_and_source (spec check)   │
           │     3. check_boundary_neighborhood (domain)  │
           │     4. search_known_issues_tavily (upstream) │
           └──────────────────────┬───────────────────────┘
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
             [ Validated Finding ]    [ Rejected Candidate ]
             (Full Provenance,        (Recorded in Report;
              Replay Receipts)         Zero False Alarms)
```

### The Four Core Upgrades (Research v1.1)

1. **Upgrade A: Docs-Only Contract Isolation**
   - The contract-synthesis LLM prompt receives **only** pinned documentation (`README`, Sphinx docs), public module signatures, and docstrings.
   - Function bodies, decorators, and internal implementations are strictly excluded. This ensures the contract reflects the library's **promised semantic specification**, rather than echoing current implementation bugs.
2. **Upgrade C: Constructive Hypothesis Strategies & Non-Vacuity Counters**
   - Property tests are synthesized using audited Hypothesis strategies with strict AST vetting (`HarnessRejected` triggered on broad `except Exception`, raw `assert`, `sys.exit`, or filter chaining).
   - Controller-injected instrumentation tracks non-vacuity counters: `entered`, `precondition_ok`, `assertion_reached`, and per-API call frequencies. Vacuous strategies that filter out inputs or bypass the target API are rejected as setup errors, not bugs.
3. **Upgrade E: Active Refutation Investigator**
   - When a test fails, Nightshift does not naively report a bug. It initiates an active refutation investigation powered by `nemotron-3-super-120b-a12b` equipped with 4 bounded tools:
     - `run_control_input`: Runs a documented standard input in a fresh subprocess to confirm the sandbox environment is healthy.
     - `inspect_doc_and_source`: Inspects allowlisted source files and documentation to check whether the input violates undocumented preconditions.
     - `check_boundary_neighborhood`: Tests neighboring values around the failing input to verify if the anomaly is a localized boundary edge case.
     - `search_known_issues_tavily`: Searches GitHub issues via Tavily to determine if the behavior is a known upstream design choice.
   - If the refuter finds documentation refuting the contract or identifies that the input is outside domain scope, the candidate is marked as `rejected` with an explicit reason—preventing false positives.
4. **Upgrade G: 3x Fresh-Process Replay Determinism**
   - To eliminate transient race conditions, state leaks, and non-deterministic environment artifacts, every failing input must reproduce identically across **3 freshly spawned subprocesses** with clean memory and sandbox isolation.

---

## 📊 Paired Evaluation Summary (5-Task Offline Benchmark)

Nightshift was rigorously benchmarked across 5 self-contained tasks in `tests/fixtures/` comparing the legacy naive baseline (`mode="baseline"`) against Nightshift Core (`mode="core"`) under matched execution budgets:
- `toycodec`: Codec round-trip with trailing whitespace stripping bug.
- `envcodec`: Key-value `.env` parser with quote/newline escaping bug.
- `vercanon`: Semantic version normalizer with pre-release hyphen mismatch bug.
- `iniparser`: Section/key parser with multi-line indentation bug.
- `urlcanon`: **Hard-negative control task** (clean, bug-free codec) used to evaluate false positive resistance.

### Benchmark Results (`samples/EVALUATION.md`)

| Metric | Baseline | Nightshift Core | Delta / Improvement |
|---|---|---|---|
| **Report precision** | 37.50% | **100.00%** | **+62.50%** |
| **Known-defect recall** | 60.00% | **100.00%** | **+40.00%** |
| **False-positive rate** | 100.00% | **0.00%** | **-100.00%** |
| **Valid-input rate** | 36.79% | **89.19%** | **+52.40%** |
| **Cost per validated finding** | $0.2000 | **$0.0800** | **$-0.1200** |
| **Tavily credits** | 0.0 | **0.0** | 0.0 (airgapped) |
| **Total spend (USD)** | $0.6000 | **$0.4000** | **$-0.2000** |
| **Total findings reviewed** | 8 | 10 | +2 |
| **Validated findings** | 3 | **5** | +2 |
| **Rejected / unresolved** | 0 | **5** | +5 |

> **Key Takeaway:** Baseline flags invalid out-of-spec inputs as bugs, yielding a 100% false positive rate on hard negatives and only 37.5% report precision. **Nightshift Core achieves 100% precision, 100% defect recall, and 0% false positive rate**, saving 60% of cost per validated finding while maintaining complete offline air-gapped reproducibility.

---

## ⚡ Quickstart & Reproducible Commands

Nightshift runs completely offline with **$0.00 API spend** for testing and benchmark verification, and scales to live Nebius/NVIDIA/Tavily clouds when API keys are configured.

### 1. Environment Setup

```bash
# Clone and install dependencies with uv
cd /path/to/nightshift
uv sync

# Configure API keys (optional for offline evaluation)
cp .env.example .env
# Set NEBIUS_API_KEY and TAVILY_API_KEY in .env
```

### 2. Run the 5-Task Offline Benchmark ($0.00 API Spend)

Execute the full paired evaluation across local subprocesses, generating both JSON and Markdown benchmark summaries:

```bash
.venv/bin/python scripts/run_evaluation.py --self-test \
  --output-json samples/eval_summary.json \
  --output-md samples/EVALUATION.md
```

### 3. Generate Multi-Run Sample Reports for the Dashboard

Generate the primary showcase report (`samples/report.json`), the multi-run campaign manifest (`samples/runs/index.json`), and 3 realistic library runs (`python-dotenv`, `tomlkit`, `packaging`):

```bash
.venv/bin/python samples/make_sample_report.py
```

### 4. Run the Full Test Suite

Run all unit, integration, and contract tests (90+ tests, 100% offline):

```bash
.venv/bin/pytest -q
```

### 5. Launch a Live Autonomous Campaign (Online Mode)

When `NEBIUS_API_KEY` and `TAVILY_API_KEY` are provided:

```bash
# Run Core campaign inside isolated Docker sandbox with Tavily documentation lookup
uv run nightshift run https://github.com/theskumar/python-dotenv \
  --package dotenv \
  --mode core \
  --sandbox docker \
  --budget 1.0 \
  --online-lookup
```

---

## 📂 Repository Structure & Target Manifests

```
nightshift/
├── manifests/
│   ├── upstream_targets.json    # 5 shortlisted pure-Python target repositories
│   └── paired_benchmark.json    # Executable task manifest for run_evaluation.py
├── samples/
│   ├── EVALUATION.md            # Generated paired evaluation Markdown comparison
│   ├── eval_summary.json        # Evaluated system metrics (precision, recall, cost)
│   ├── report.json              # Main showcase sample report (schema v1.1)
│   └── runs/                    # Multi-run campaign reports for dashboard picker
│       ├── index.json           # Manifest listing available campaign runs
│       ├── python-dotenv-core.json
│       ├── tomlkit-core.json
│       └── packaging-core.json
├── scripts/
│   ├── run_evaluation.py        # CLI evaluation runner (--self-test or --manifest)
│   └── check_models.py          # Nebius Token Factory model verification script
├── src/nightshift/
│   ├── contracts/               # Model, audit, renderer, runner & library presets
│   ├── pipeline/                # Core v1.1 orchestration, investigator & verification
│   ├── sandbox/                 # Docker, Nebius SSH, and UnsafeLocalSandbox engines
│   ├── eval.py                  # Paired evaluation framework & metrics calculator
│   ├── report.py                # Schema v1 Report, Finding, Check & Evidence dataclasses
│   ├── tavily.py                # Tavily search/extract client with credit ledger
│   └── llm.py                   # 3-tier Nemotron client with strict budget reservation
└── tests/
    ├── fixtures/                # 5 self-contained test codecs (toycodec, envcodec, etc.)
    ├── test_contracts.py        # Contract runner tests for stdlib and installed packages
    ├── test_core_v11.py         # End-to-end v1.1 core pipeline integration tests
    ├── test_evaluation.py       # Benchmark evaluation and metric assertions
    └── test_report.py           # Report schema round-trip serialization tests
```

### Shortlisted Upstream Targets (`manifests/upstream_targets.json`)

1. **`python-dotenv`** (`dotenv.main`, `dotenv.parser`): Round-trip and equivalence contracts on variable expansion, quote escaping, and multi-line parsing.
2. **`packaging`** (`packaging.version`, `packaging.specifiers`): PEP 440 canonical version round-trip and specifier set compatibility relations.
3. **`tomlkit`** (`tomlkit.api`, `tomlkit.parser`): Style-preserving round-trip contracts verifying comments and whitespace are preserved.
4. **`iniconfig`** (`iniconfig`): Section/key INI parsing round-trip invariants.
5. **`jmespath`** (`jmespath.parser`, `jmespath.visitor`): AST parser and evaluation equivalence contracts.

---

## 💡 Sponsor Product Feedback & Engineering Insights

During the development and testing of Nightshift, we made extensive use of **Nebius Token Factory**, **NVIDIA Nemotron**, and **Tavily API**. Here is our detailed technical feedback and operational observations:

### 1. Nebius Token Factory & NVIDIA Nemotron 3-Tier Routing

We structured our agentic pipeline into a strict 3-tier routing architecture based on cost and reasoning capability:
- **`nvidia/nemotron-3-5-lightning` ($0.20/1M tokens):** Dedicated to high-throughput, low-latency tasks: docs-only contract extraction and Hypothesis strategy synthesis. Lightning excels at generating structured Python code and AST constructs, achieving >89% valid input rates under audited prompt schemas.
- **`nvidia/nemotron-3-super-120b-a12b` ($0.80/1M tokens):** Dedicated to the 4-tool Active Refutation Investigator. Super exhibited outstanding critical-thinking capabilities, actively finding documentation exceptions and questioning whether observed failures were genuine bugs or caller misuses.
- **`nvidia/nemotron-3-ultra-550b-a55b` ($2.50/1M tokens):** Optional capped escalation for root-cause synthesis and minimal unified patch generation on validated survivors.

#### Engineering Observations & Suggestions:
- **Pre-Request Reservation vs. Usage Settlement:** Because parallel hypothesis campaigns can trigger multiple simultaneous LLM calls, naive concurrency can easily overshoot budget caps. We implemented a conservative pre-request byte/token reservation ledger that deducts maximum potential spend *before* issuing the HTTP request, reconciling with exact server-reported `usage` tokens upon response. Providing a header-based pre-flight reservation or native client-side budget cap in the Nebius SDK would simplify financial safety for autonomous agents.
- **Read-Timeout Charge Uncertainty:** During peak cluster loads, HTTP read-timeouts occasionally occur. It is currently ambiguous whether tokens consumed prior to a client-side timeout are billed. We treat unconfirmed requests as "pending/estimated" in our budget ledger. Standardizing idempotency keys (`Idempotency-Key` headers) across the Token Factory inference endpoints would allow safe retries without double-billing risks.

### 2. Execution Sandboxes (Docker & Nebius SSH VM)

To execute untrusted Python code and Hypothesis property generators safely, Nightshift supports both local Docker containers and provisioned Nebius cloud VMs over SSH (`NIGHTSHIFT_NEBIUS_DOCKER_HOST`):
- **Process-Tree Termination:** Hypothesis test runs can spawn child processes or multithreaded workers that linger if the parent Python process times out. We enforced process group isolation (`os.setsid`) and sent termination signals to the entire process group (`kill -9 -- -$PGID`), preventing runaway CPU consumption.
- **Secret Stripping & Network Isolation:** Workers run with `--network none` and an explicitly scrubbed environment: all `NEBIUS_*`, `OPENROUTER_*`, and `TAVILY_*` tokens are stripped before entering the sandbox, ensuring that arbitrary generated code cannot exfiltrate credentials.
- **Fresh-Process Determinism:** We observed that testing within a long-lived Python interpreter causes global state contamination (e.g., `sys.modules` pollution, modified class attributes). Upgrade G's requirement of 3x fresh subprocess execution completely eliminated false positives caused by module caching.

### 3. Tavily Search & Extract API

Nightshift uses Tavily's `/extract` and `/search` APIs for documentation retrieval and upstream deduplication:
- **Exact Provenance via `/extract`:** Tavily's `/extract` endpoint allows Nightshift to retrieve raw markdown from pinned documentation URLs. We generate SHA-256 content hashes of the retrieved content, embedding them into frozen `Contract` and `EvidenceRef` objects. This provides an immutable cryptographic audit trail linking every test invariant to the exact documentation excerpt that justified it.
- **Usage & Ledger Accounting:** By querying with `include_usage=True`, Nightshift accurately tracks credit consumption per request. We implemented a hard client-side credit ledger (`limit: 1000.0 credits`) that blocks outgoing calls if the credit ceiling is reached, logging estimated vs. reported credit discrepancies.
- **Air-Gapped Mode for Controlled Benchmarking:** For reproducible scientific evaluation, Nightshift provides an `--airgapped` mode that blocks network retrieval and prevents local cache leakage, ensuring that benchmark runs (such as the 5-task offline suite) remain 100% reproducible and contamination-free.

---

## 👥 Team

- **Aryesh Thakur** ([@Aryesh22](https://github.com/Aryesh22))
- **Jatin Kukreja** ([@jatin-encrypted](https://github.com/jatin-encrypted))
- **Ruchir** ([@Ruchir038](https://github.com/Ruchir038))

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
