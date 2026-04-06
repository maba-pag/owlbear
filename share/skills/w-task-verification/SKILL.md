---
name: w-task-verification
description: "Workflow: Exit gate verification — AC evidence, confidence scoring, commit integrity"
user-invocable: false
---

# Task Verification

Step-by-step exit gate process (done → archived).

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read the `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

## Step 1 — Verify the task

As 3rd-line defense, focus on **cross-task integration** and **architect quality**. Trust the reviewer's code-level verdict and spot-check rather than re-verify:

- **Read reviewer evidence:** Check the `## Review Evidence` section in the task body (retrieved by `start_work`, or via `show_task` if needed again). If detailed with PASS verdict, accept code-level findings. If missing or thin, escalate confidence penalty.
- **File exists:** Quick sanity check that deliverables exist.
- **Scope check:** Verify changed files align with AC scope. Flag unexpected files outside the task's domain.
- **AC spot-check:** Verify 1-2 key AC items rather than every line (the reviewer already mapped them all).
- **Full test suite:** Run the full suite (not scoped to task files) via Quality-Runner:

  ```
  agentName: quality-runner
  prompt: |
    mode: full
    task_id: {id}
  ```

  Confirm `failed: []` and `clean: true` from the Quality-Runner report. Unlike the reviewer (who scopes tests), the auditor runs the FULL suite to catch cross-task regressions. This is the auditor's primary unique value.

  #### Fallback: Quality-Runner Unavailable

  If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

  ```powershell
  uv run pytest tests/ -m "not api" -q --tb=short
  uv run ruff check serve/ tests/
  ```

  See `h-pytest-and-linting` for flags and known pitfalls.

- **Lint:** Included in Quality-Runner `mode=full` report. If running fallback, use `uv run ruff check serve/ tests/`.
- **AC deviations:** Flag missing functionality or incomplete features. Minor deviations the reviewer already accepted are fine.

## Step 1a — Research task verification

For tasks tagged `research`:

1. Research doc exists at `.owlbear/research/{slug}.md`
2. Follow-up tasks created at `ideation` or higher, OR doc states "no action needed" with justification, OR a decision request exists
3. Follow-up tasks reference the research doc
4. If none of the above, reject to backlog — follow-up creation was missed

## Step 2 — Architect quality audit

Evaluate the architect's upstream work. This is the only pipeline stage where architect quality is assessed.

1. **AC specificity:** Were AC lines specific enough to verify? Flag vague AC that "passed" because tests and implementation were equally vague.
2. **Edge case coverage:** Did AC miss obvious edge cases? Check builder/reviewer notes for improvisation signs (TestBuilderDiscovered tests, reviewer MISSING flags).
3. **Design direction:** If architect left design notes, did they help or hinder?
4. **AC quality score (1-5):**
   - **5** — Specific, complete, clean implementation path
   - **4** — Adequate, minor gaps filled by builder/reviewer
   - **3** — Notable gaps requiring significant builder improvisation
   - **2** — Vague enough that implementation may not match intent
   - **1** — Useless or misleading

Score ≤ 2: write lesson to `/memories/repo/inbox/{task-id}-auditor.md` and create follow-up task for architect calibration via `create_task`.

## Step 3 — Score and decide

Start at 1.0, deduct per criterion:

| Criterion | Deduction |
|-----------|-----------|
| AC line with no specific evidence | -.02 each |
| Lint violations | -.05 |
| AC quality score ≤ 3 | -.03 |
| Missing reviewer evidence section | -.02 |
| Full-suite test failures in task scope | -.05 |

Thresholds (source of truth in `r-pipeline-protocol` → Confidence Thresholds):

| Score | Action |
|-------|--------|
| ≥ .95 | Archive |
| < .95 | Reject to backlog — if auditor catches it, the gap is structural |

## Step 4 — Verify commits and commit leftovers

Upstream agents should have committed their deliverables. Verify and clean up.

**Verify upstream commits:** For each task's deliverable files, confirm they appear in recent commits via `git log --oneline -5 -- <files>`. Uncommitted deliverables are a quality gap — note in the audit report.

**Commit leftovers:** Stage and commit remaining files (kanban board changes, orphaned deliverables). Follow commit format in `r-project-standards` → Commit Discipline.

Before committing: `git status --short` and `git diff --cached` to verify only task-related files are staged. Unstage unexpected files with `git reset HEAD <file>`.

## Step 5 — Advance

Include the audit section in your `end_work` note.

Then advance based on confidence:

- **≥ .95 — Archive:** via `end_work` (advances status + releases claim).

- **< .95 — Reject to backlog:** via `end_work(outcome="reject", move_to="backlog")`.

Return Channel A signal as final output — nothing else after it.

## Output Template

Append to task body before returning:

```
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| {line} | {file:line, test name, or output} | PASS/FAIL |

### Test Results
- pytest: {summary}
- ruff: {summary}

### Architect Quality: {score}/5
### Deduction Breakdown
{list each criterion applied}
### Confidence: {.XX}
### Action: {archive/reject-to-backlog}
```

If the audit section exceeds ~1500 tokens, write to `.owlbear/scratch/{id}-auditor.md` and reference it.

After committing, append commit log:

```
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| {hash} | {type} | {files} | #{id} |
```

## Verification Checklist

- [ ] Each AC line verified with specific evidence (not self-reports)
- [ ] Reviewer evidence section present and evaluated
- [ ] Architect quality score assigned (1-5)
- [ ] Full test suite passed (cross-task regressions checked)
- [ ] Confidence score calculated using deduction rubric (not gut feeling)
- [ ] Audit section included in `end_work` note
- [ ] Upstream commits verified; leftover files committed per `r-project-standards`
- [ ] Channel A signal returned as final output — nothing after it

## Known Pitfalls

- **Scoped tests instead of full suite:** The auditor's primary value is cross-task regression detection. Always run `uv run pytest tests/ -m "not api"` — never scope to task-specific files.
- **Gut-feeling confidence (.93–.97):** If your score lands in this range without an explicit deduction calculation, recalculate. Scores here are unreliable without itemized deductions.
- **VS Code auto-staging:** VS Code silently re-serializes `.agent.md` files. Run `git diff --cached agents/` before committing and unstage unexpected changes with `git reset HEAD`.
- **Monolithic commits:** Each task gets its own commit. Never batch multiple tasks into one commit.
- **Body content parsing:** Avoid `->` arrows and `--flag` patterns in body text passed to `end_work` — use prose equivalents (see `h-mcp-kanban`).
