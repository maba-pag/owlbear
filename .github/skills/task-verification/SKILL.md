---
name: task-verification
description: "Exit gate verification workflow: verify AC with evidence → score confidence → archive or reject → commit. Use when closing completed tasks."
---

# Task Verification Workflow

Step-by-step process for the exit gate (done → archived).

## Step 1 — Gather done tasks

```powershell
kanban\kanban-md.exe list --compact --status done
```

For each task, read full AC and claim it:

```powershell
kanban\kanban-md.exe show {id}
kanban\kanban-md.exe edit {id} --claim <agent>
```

## Step 2 — Verify each task

For every AC item on every task, collect concrete evidence:

- **File exists:** `read_file` — verify the file, don't assume
- **Code matches AC:** grep or read for specific classes, functions, signatures
- **Tests pass:** Run the full suite plain (see the `pytest-and-linting` skill,
  read it with `read_file` if not already loaded,
  for piping rules and the Python fallback):

  ```powershell
  uv run pytest tests/ -m "not api" -q --tb=short
  ```

  **NOTE:** Unlike the reviewer (who scopes tests to task-specific files), the auditor
  intentionally runs the FULL test suite. As 3rd-line defense, the auditor checks for
  cross-task regressions that scoped runs would miss. This is by design.
- **Lint clean:** Run `uv run ruff check src/ tests/` once
- **AC deviations:** Note differences between AC and implementation
  - Minor deviations (better naming, improved path): acceptable if intent is met
  - Major deviations (missing functionality, incomplete features): not acceptable

## Step 3 — Score and decide

| Score | Meaning | Action |
|-------|---------|--------|
| `1.0` | Every AC verified, no deviations | Archive |
| `.95` | All AC met, minor naming/path deviations | Archive |
| `.90` | Most AC met, trivial cosmetic deviation | Reject to review |
| `.85` | Functional, minor non-trivial deviation | Reject to review |
| `< .85` | Incomplete or unverifiable | Reject to backlog |

- **≥ .95:** `kanban\kanban-md.exe archive {id}` then `kanban\kanban-md.exe edit {id} --release`
- **< .95 fixable:** `kanban\kanban-md.exe edit {id} --status review --block "reason" --release`
- **< .95 fundamental:** `kanban\kanban-md.exe edit {id} --status backlog --block "reason" --release`

## Step 4 — Audit report

| ID | Title | Evidence summary | Confidence | Action |
|----|-------|-----------------|------------|--------|

Totals: X archived, Y rejected, Z flagged.

## Step 5 — Commit in packages

1. `git status --short` + `git log --oneline -5`
2. Group files by cohesion:
   - Feature: source + tests + config → `feat:`
   - Infra/tooling/deps → `chore:`
   - Kanban board changes → `chore:`
   - Docs → `docs:`
   - Agent definitions + prompts → `docs:`
3. Stage each package's files, commit with conventional message, next package
4. Do **not** push — the user pushes manually

## Step 6 — Final summary

Write the final summary to **Channel B** (append to the last task's body or
`docs/scratch/{id}-auditor.md`). Include: commits made (with hashes), tasks archived,
tasks rejected, remaining items.

Your return to the caller is **Channel A only** — the signal line(s). No commit tables,
no summaries in the return text.
