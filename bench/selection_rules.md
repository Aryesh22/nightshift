# PBT-Bench Task Selection Rules

**Document Timestamp:** 2026-10-27T22:30:00Z  
**Target:** 10 Tasks (20 total campaigns: 10 Baseline vs 10 Nightshift Core)  
**Budget Cap:** $10.00 total ($0.45 per run cap, $1.00 reserve)

---

## 1. Composition
The benchmark sample of 10 tasks is stratified across difficulty tiers:
- **4 × Level 1 (L1)**: Single-function unit invariants (e.g., codec roundtrip, idempotency).
- **4 × Level 2 (L2)**: Multi-step compositional properties & drop-in equivalent API pairs.
- **2 × Level 3 (L3)**: Complex stateful workflows and data structure invariants.

## 2. Selection Determinism
- Selection is determined by a deterministic pseudorandom seed (`SEED = 42`) over the verified PBT-Bench repository manifest, or lexicographic task order.
- **Rule:** Task selection was frozen **before** running either Nightshift Core or Baseline on the dataset. Task candidates were never chosen or swapped based on observed pipeline detection performance.

## 3. Strict Defect Isolation
- Upstream answers, ground-truth patches, and evaluator test notes are strictly excluded from the agent's filesystem and context.
- Before execution, the runner verifies that no files matching `*test_patch*`, `*defect_note*`, or ground truth answers are visible to the agent's environment.

## 4. Exclusion Protocol
Exclusions are permitted **only** for verifiable infrastructure incompatibilities:
1. Tasks requiring unsupported non-Python native toolchains (e.g., custom C/Rust compiler extensions unavailable in standard Python 3.12 wheel builds).
2. Tasks requiring external proprietary network endpoints in an airgapped test environment.
Any excluded task is logged with its exact error traceback and the next deterministic candidate in the same tier is selected.

## 5. Matched Task Pairing
Every task evaluated in Nightshift Core is evaluated under identical repository commits, Python versions, and runtime timeouts in Baseline.
Execution order is **interleaved** (Task 1: Baseline then Core, Task 2: Core then Baseline) to mitigate temporal infrastructure variance.

