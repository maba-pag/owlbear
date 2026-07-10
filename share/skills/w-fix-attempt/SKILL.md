---
name: w-fix-attempt
description: "Workflow: Fix-attempt — fresh-context single-shot repair of a failing builder task"
user-invocable: false
---

# Fix-Attempt

Fresh-context, single-shot repair invoked by the builder when same-context retries have failed. The fix-attempt subagent is a short-lived utility — it does not claim, advance, or comment on the kanban board. The caller (builder) owns task lifecycle.

## Input Contract

The caller provides these fields when invoking via `runSubagent`:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Kanban task identifier (e.g. `318`) — used only for evidence labelling |
| `failing_command` | string | Focused command that failed |
| `test_file` | string | Optional relative path to a failing test file |
| `source_files` | string[] | Source files implicated by the error |
| `retry_hint` | string | Verbal feedback from the prior attempt — diagnoses where to look first |
| `error_summary` | string | Truncated pytest/ruff output from the failing run |

## Output Contract

Return one Channel A line:

| Verdict | Format |
|---------|--------|
| Fixed | `FIXED #{task_id} \| {command} passed, lint clean \| files_changed: {list}` |
| Failed | `FAILED #{task_id} \| {reason} \| files_changed: {list} \| evidence: {summary}` |

Both verdicts must include `files_changed` and an `evidence` summary (test count, ruff status, and a one-line description of the fix or the diagnosis).

## Step 1 — Parse Inputs

Extract `task_id`, `failing_command`, optional `test_file`, `source_files`, `retry_hint`, and `error_summary` from the invocation. Read `retry_hint` carefully — it encodes the prior attempt's diagnosis.

## Step 2 — Read Failing Proof

If `test_file` is provided, read it and identify the exact assertions corresponding to `error_summary`. Do not modify tests unless the builder explicitly listed them in `source_files`.

## Step 3 — Read Source Files

Read each file listed in `source_files`. Focus on interfaces and code paths exercised by the failing tests.

## Step 4 — Apply Fix

Write the minimum change that satisfies the failing assertions. Follow surrounding code style. Keep the diff surgical — no unrelated edits.

## Step 5 — Verify

```sh
{failing_command}
uv run ruff check {changed_files}
```

## Step 6 — Single Retry (max 1)

If tests still fail after Step 5, perform **one** retry: re-read the error, adjust the fix, re-run. This is the only internal retry permitted — fix-attempt IS the fresh perspective; a second retry would re-accumulate the builder's failure mode.

If tests pass after retry: report `FIXED`. If still failing: report `FAILED` with a clear diagnosis.

## Known Pitfalls

- **Proof mutation:** If the failing proof is genuinely wrong and was not listed in `source_files`, report `FAILED` with a note for the builder to reject to shape — never edit proof files just to make them pass.
- **Scope creep:** Edit only files in `source_files`. Drive-by fixes hide the real failure.
- **Second retry:** A third variation is the same trap the builder hit. Stop and report.
