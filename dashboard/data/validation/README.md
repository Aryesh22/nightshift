# Human Validation Overlay Protocol

This directory contains human validation records for Nightshift findings. 

Per the research and team plan, an anomaly stays an **AI-reviewed candidate** until an engineer independently reproduces it in a clean environment.

## Validation Protocol (Step-by-Step)
For every surviving candidate:
1. **Fresh Environment**: Create a fresh venv and install the library at the exact **pinned ref/commit** recorded in `report.json`.
2. **Execute Repro & Control**:
   - Run the reduced repro code. Confirm the failure reproduces exactly as reported.
   - Run the passing control input. Confirm it succeeds without error.
3. **Verify Contract Invariant**: Open the pinned documentation URL. Read the excerpt in context and confirm the docs explicitly promise that behavior.
4. **Duplicate Issue Check**: Search upstream issues and changelogs.
5. **Record Finding**: Create `<run_id>.json` in this directory.

## File Format: `<run_id>.json`
```json
{
  "run_id": "RUN-2026-10-28-mypkg",
  "validations": [
    {
      "finding_id": "f1",
      "status": "human_validated",
      "validator": "Ruchir",
      "date": "2026-10-28T14:30:00Z",
      "environment": "Python 3.12, Windows 11, clean venv",
      "result": "validated",
      "notes": "Reproduced failure with trailing whitespace. Docs at api.html#decode promise exact inverse.",
      "upstream_issue_url": "https://github.com/example/fakelib/issues/104"
    }
  ]
}
```

The dashboard automatically detects and overlays these files at build and runtime, updating the finding badge to **"Human validated"** with the reviewer's signature.

