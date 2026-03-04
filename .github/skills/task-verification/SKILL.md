---
name: task-verification
description: "Exit gate verification workflow: verify AC with evidence → score confidence → archive or reject → commit + push. Use when closing completed tasks."
---

# Task Verification Workflow

Step-by-step process for the exit gate (done → archived).

## Step 1 — Gather done tasks

```powershell
kanban\kanban-md.exe list --compact --status done
```

For each task, read full AC: `kanban\kanban-md.exe show {id}`

## Step 2 — Verify each task

For every AC item on every task, collect concrete evidence:

- **File exists:** `read_file` — verify the file, don't assume
- **Code matches AC:** grep or read for specific classes, functions, signatures
- **Tests pass:** Run `uv run pytest tests/ -m "not api" --tb=short -q` once for full suite
- **Lint clean:** Run `uv run ruff check src/ tests/` once
- **AC deviations:** Note differences between AC and implementation
  - Minor deviations (better naming, improved path): acceptable if intent is met
  - Major deviations (missing functionality, incomplete features): not acceptable

## Step 3 — Score and decide

| Score | Meaning | Action |
|-------|---------|--------|
| `1.0` | Every AC verified, no deviations | Archive |
| `.90` | All AC met, minor naming/path deviations | Archive |
| `.80` | Most AC met, one non-trivial deviation | Archive |
| `.70` | Functional but multiple deviations | Reject to review |
| `< .70` | Incomplete or unverifiable | Reject to backlog |

- **≥ .80:** `kanban\kanban-md.exe archive {id}`
- **< .80 fixable:** `kanban\kanban-md.exe move {id} review --block "reason"`
- **< .80 fundamental:** `kanban\kanban-md.exe move {id} backlog --block "reason"`

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
4. `git push` — ask user first if there are rejected tasks

## Step 6 — Final summary

Commits made (with hashes), tasks archived, tasks rejected, remaining items.
