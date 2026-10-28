# PBT-Bench Evaluation Preflight Notes

**Author:** Ruchir  
**Collaborator:** Aryesh  
**Preflight Tasks Evaluated:** `pbt-bench-l1-01`, `pbt-bench-l1-02`

---

## 1. Task Invocation & Pointing
Tasks are supplied as a cloned repository directory containing a target Python package, its public documentation (in `docs/` or docstrings), and a pytest test runner.

Command shape:
```bash
uv run nightshift run <path-to-task-repo> \
  --package <package-name> \
  --mode <core|baseline> \
  --airgapped \
  --budget 0.45 \
  --timeout 300
```

## 2. Defect Labels & Ground Truth Hiding
- In PBT-Bench, ground-truth bug descriptions and upstream patches reside in `.pbt_eval/ground_truth/`.
- **Verification check:** Before running Nightshift, the runner confirms that `.pbt_eval/` is excluded from the sandbox volume mount or stripped from the agent's repository view.
- Grepping agent prompt logs confirmed **0 occurrences** of ground truth tokens.

## 3. Evaluator Scoring Mechanism
The evaluator runs the candidate repro script against:
1. The **unpatched buggy codebase** (must fail with reproducible assertion/exception).
2. The **developer patched codebase** (must pass without error).
If both conditions hold, `evaluator_detected = true`.
If the repro fails on both (e.g. invalid test setup) or passes on both (no bug triggered), `evaluator_detected = false`.

## 4. Observed Preflight Resource Usage
- **Core Mode:**
  - `pbt-bench-l1-01`: 94s wall time, $0.34 cost, 1 candidate surviving refutation (detected).
  - `pbt-bench-l1-02`: 105s wall time, $0.36 cost, 3 candidates rejected, 1 survivor (detected).
- **Baseline Mode:**
  - `pbt-bench-l1-01`: 112s wall time, $0.38 cost, 3 anomalies reported, 1 verified (detected).
  - `pbt-bench-l1-02`: 135s wall time, $0.41 cost, 4 anomalies reported, 0 verified (not detected).

## 5. Failure Handlers
- If Docker/container sandbox timeout occurs, it is recorded explicitly as `status = failed` with `failure_reason = "Sandbox timeout"`.
- Denominators are strictly preserved (10 tasks total).

