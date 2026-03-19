---
name: task-verification
description: "Exit gate verification workflow: verify AC with evidence → score confidence → archive or reject → commit. Use when closing completed tasks."
---

# Task Verification Workflow

Step-by-step process for the exit gate (done → archived).

## kanban-md Commands

| Action | Command |
|--------|---------|
| List done tasks | `kanban\kanban-md.exe list --compact --status done` |
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| Append audit | `kanban\kanban-md.exe edit {id} -a "## Audit\n{content}" -t --claim <agent>` |
| Archive (pass) | `kanban\kanban-md.exe archive {id}` then `kanban\kanban-md.exe edit {id} --release` |
| Reject (fixable) | `kanban\kanban-md.exe edit {id} --status review --block "reason" --release` |
| Reject (fundamental) | `kanban\kanban-md.exe edit {id} --status backlog --block "reason" --release` |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.

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

## Step 5 — Verify commits and commit leftovers

Upstream agents (test-writer, builder, writer) should have committed their deliverables already (see `agent-common.instructions.md` → **Commit discipline**). Your job is to verify and clean up.

### 5a — Verify upstream commits

For each archived task's deliverable files:

```powershell
git log --oneline -5 -- <deliverable-files>
```

Confirm the files appear in recent commits. If deliverables are uncommitted, note this as a quality gap in the audit report.

### 5b — Stage and commit leftovers

**VS Code auto-staging trap:** VS Code SCM can auto-stage files from other tasks. Always run `git diff --cached` + `git status --short` before committing. If you see unexpected files, `git reset HEAD` first, then selectively `git add`.

1. `git status --short` — identify uncommitted files
2. Group by cohesion and commit:
   - Kanban board changes → `chore: update board state (#id, auditor)`
   - Any orphaned deliverables → appropriate type with a note about upstream gap
3. Follow the commit message format in `agent-common.instructions.md` → **Commit discipline**
4. Do **not** push — the user pushes manually

## Step 6 — Final summary

Write the final summary to **Channel B** (append to the last task's body or
`docs/scratch/{id}-auditor.md`). Include: commits made (with hashes), tasks archived,
tasks rejected, remaining items.

Your return to the caller is **Channel A only** — the signal line(s). No commit tables,
no summaries in the return text.
