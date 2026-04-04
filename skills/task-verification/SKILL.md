---
name: task-verification
description: "Exit gate verification workflow: verify AC with evidence → score confidence → archive or reject → commit. Use when closing completed tasks."
user-invocable: false
---

# Task Verification Workflow

Step-by-step process for the exit gate (done → archived).

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| Append audit | `kanban\kanban-md.exe edit {id} -a "## Audit\n{content}" -t --claim <agent>` |
| Archive (pass) | `kanban\kanban-md.exe archive {id}` then `kanban\kanban-md.exe edit {id} --release` |
| Reject (fixable) | `kanban\kanban-md.exe edit {id} --status review --release` |
| Reject (fundamental) | `kanban\kanban-md.exe edit {id} --status backlog --block "reason" --release` |
| Claim + show task (MCP) | `start_work {id}` |
| Append to task body (MCP) | `edit_task {id}` |
| Advance + release (MCP) | `end_work {id}` |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Read and claim the task

Read the dispatched task and claim it:

```powershell
kanban\kanban-md.exe show {id}
kanban\kanban-md.exe edit {id} --claim <agent>
```

> **MCP equivalent:** `start_work(task_id="{id}")` — claim + read in one call.

## Step 2 — Verify each task

As 3rd-line defense (see agent-common → **Defense-in-depth**), the auditor focuses on
**cross-task integration** and **architect quality**. Trust the reviewer's code-level
verdict and spot-check rather than re-verify:

- **Read reviewer evidence:** Check the `## Review Evidence` section in the task body.
  If the reviewer produced a detailed evidence table with PASS verdict, accept its
  code-level findings. If the section is missing or thin, escalate confidence penalty.
- **File exists:** `read_file` — quick sanity check that deliverables exist
- **Changed files align with AC scope:** Use `get_changed_files` with `sourceControlState: ["staged", "unstaged"]` to list files changed by the builder and writer. Verify every changed file is within the task's domain. Flag unexpected files outside the task's domain as potential scope creep.
- **Code matches AC (spot-check):** Verify 1–2 key AC items rather than every line.
  The reviewer already mapped every AC item to evidence.
- **Tests pass (FULL suite):** Run the full suite plain (see `pytest-and-linting` skill):

  ```powershell
  uv run pytest tests/ -m "not api" -q --tb=short
  ```

  **NOTE:** Unlike the reviewer (who scopes tests to task-specific files), the auditor
  intentionally runs the FULL test suite. As 3rd-line defense, the auditor checks for
  cross-task regressions that scoped runs would miss. This is by design and is the
  auditor's primary unique value.

- **Lint clean:** Run `uv run ruff check src/ tests/` once
- **AC deviations (major only):** Flag missing functionality or incomplete features.
  Minor deviations (better naming, improved path) that the reviewer already accepted
  are fine.

## Step 2a — Research task verification

When auditing a task tagged `research`, verify:

1. A research doc exists at `docs/research/{slug}.md`
2. Follow-up tasks were **created on the board** at `ideation` (or higher) status, OR the
   research doc explicitly states "no action needed" with justification, OR a decision
   request exists in `docs/decisions/pending/`
3. Follow-up tasks link back to the research doc (task body references
   `docs/research/{slug}.md`)
4. If none of the above, **reject to review** — the follow-up task creation step was missed

## Step 2.5 — Architect quality audit

Evaluate whether the **architect** did its job well. The reviewer checks test-writer
and builder quality; the auditor checks architect quality. This is the only place in
the pipeline where the architect's work is evaluated.

For the task:

1. **AC specificity:** Were the AC lines specific enough to verify? Flag vague AC that
   "passed" because the tests and implementation were equally vague (e.g., AC says
   "handle errors gracefully" with no measurable criterion).
2. **Edge case coverage:** Did the AC miss obvious edge cases that the builder or
   reviewer had to improvise around? Check builder notes and reviewer evidence for
   signs of AC gaps (e.g., builder added `TestBuilderDiscovered` tests for scenarios
   the AC should have specified, or reviewer flagged MISSING in its test-writer audit).
3. **Design direction:** If the architect left design notes in the task body, did they
   lead the builder in a productive direction? Or did the builder need to deviate
   significantly from the architect's suggested approach?
4. **AC quality score:** Rate 1–5:
   - **5** — AC was specific, complete, and led to a clean implementation
   - **4** — AC was adequate, minor gaps filled by builder/reviewer
   - **3** — AC had notable gaps requiring significant builder improvisation
   - **2** — AC was vague enough that the implementation may not match intent
   - **1** — AC was essentially useless or misleading

Low scores (≤ 2) = flag as a curator lesson
(write to `/memories/repo/inbox/`). Systemic AC quality issues indicate the architect
needs calibration.

## Step 3 — Score and decide

**Deduction rubric:** Start at 1.0, deduct per criterion:

| Criterion | Deduction |
|-----------|-----------|
| Per AC line with no specific evidence | -.02 |
| Lint issues (ruff violations) | -.05 |
| AC quality score at 3 or below | -.03 |
| Missing reviewer evidence section | -.02 |
| Full-suite test failures in task scope | -.05 |

Thresholds from agent-common → **Confidence thresholds** (single source of truth):

| Score | Meaning | Action |
|-------|---------|--------|
| `1.0` | Every AC verified, no deviations | Archive |
| `.95` | All AC met, minor naming/path deviations | Archive |
| `.90` | Most AC met, trivial cosmetic deviation | Reject to review |
| `.85` | Functional, minor non-trivial deviation | Reject to review |
| `< .85` | Incomplete or unverifiable | Reject to backlog |

- **≥ .95:** `kanban\kanban-md.exe archive {id}` then `kanban\kanban-md.exe edit {id} --release`
  > **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="success")` — archive + release in one call.
- **< .95 fixable:** `kanban\kanban-md.exe edit {id} --status review --release`
  > **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="reject")`
- **< .95 fundamental:** `kanban\kanban-md.exe edit {id} --status backlog --block "reason" --release`
  > **MCP equivalent:** `edit_task(task_id="{id}", status="backlog", block="reason", release=true)`

## Step 4 — Audit report

| ID | Title | Evidence summary | Confidence | Action |
|----|-------|-----------------|------------|--------|
| {id} | {title} | {summary} | {score} | {archived/rejected} |

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

1. `git status --short` — identify uncommitted files related to this task
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

## Verification checklist

- [ ] Each task's AC verified with specific evidence (not self-reports)
- [ ] Reviewer evidence section present and evaluated
- [ ] Architect quality score assigned (1–5)
- [ ] Full test suite passed (cross-task regressions checked)
- [ ] Confidence score calculated using deduction rubric
- [ ] Audit report appended to task body (Channel B)
- [ ] Upstream commits verified; leftover files committed
- [ ] Channel A signal returned as final output
