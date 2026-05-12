---
name: w-task-verification
description: "Workflow: Exit gate verification — AC evidence, confidence scoring, commit integrity"
user-invocable: false
---

# Task Verification

Step-by-step exit gate process (done → archived).

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Run full-suite regression tests (cross-task, not scoped).
- AC spot-check one to two key items (not full mapping).
- Architect quality scoring (1-5).
- Confidence scoring with deduction rubric.
- Research task verification (doc + follow-ups exist).
- Commit kanban/decision files after archival.

### Out of Scope

- Re-verifying code-level detail — reviewer already did (`w-code-review`).
- Fixing code — builder (`w-tdd-green`).
- Writing tests — test-writer (`w-tdd-red`).
- Documentation updates — doc-writer (`w-doc-update`).
- AC quality validation — architect (`w-arch-review`).
- Security scanning — CI/SAST (D2), monitored by auditor (`w-task-verification`).

## Step 0 — Setup

Read the `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

## Step 1 — Verify the task

As 3rd-line defense, verify four pillars. Trust the reviewer's code-level verdict and do not duplicate reviewer-only checks:

1. **Regression detection:** Run the full suite (not scoped to task files) via Quality-Runner:

  ```
  agentName: quality-runner
  prompt: |
    mode: full
    task_id: {id}
  ```

  Confirm `failed: []` and `clean: true` from the Quality-Runner report. Unlike the reviewer (who scopes tests), the auditor runs the FULL suite to catch cross-task regressions. This is the auditor's primary unique value.

  **Two-tier awareness:** Task-scoped tests (`test_{module}_{task_id}.py`) are verified during the active pipeline. Module-level tests (`test_{module}.py`) are managed by the test-curator post-archive. The auditor does not gate on module-level test existence — if a module-level file doesn’t exist yet for the module, that’s expected.

2. **Intent verification (domain-level only):**
   - Verify changed files stay within the task's intended domain and scope.
   - Verify implementation direction matches stated task purpose.
   - Flag extraneous scope.
   - Do **not** read individual functions to verify behavior and do **not** re-map AC lines to code. That is reviewer territory.

3. **Architect quality scoring:** Execute Step 2 as-is.

4. **Commit integrity:** Execute Step 4 as-is.

Also check `## Review Evidence` in the task body. If detailed with a PASS verdict, accept code-level findings. If missing or thin, apply rubric deductions.

## Step 1a — Research task verification

For tasks tagged `research`:

1. Research doc exists at `.owlbear/research/{slug}.md`
2. Follow-up tasks created at `research` or higher, OR doc states "no action needed" with justification, OR a decision request exists
3. Follow-up tasks reference the research doc
4. If none of the above, reject to backlog — follow-up creation was missed

## Step 2 — Architect quality audit

Evaluate the architect's upstream work. This is the only pipeline stage where architect quality is assessed.

1. **AC specificity:** Were AC lines specific enough to verify? Flag vague AC that "passed" because tests and implementation were equally vague.
2. **Edge case coverage:** Did AC miss obvious edge cases? Check builder/reviewer notes for missing-coverage handback signs or reviewer MISSING flags.
3. **Design direction:** If architect left design notes, did they help or hinder?
4. **AC quality score (1-5):**
   - **5** — Specific, complete, clean implementation path
   - **4** — Adequate, minor gaps filled by builder/reviewer
   - **3** — Notable gaps requiring significant builder improvisation
   - **2** — Vague enough that implementation may not match intent
   - **1** — Useless or misleading

Score ≤ 2: write lesson to `/memories/repo/inbox/{task-id}-auditor.md` and delegate an architect-calibration follow-up via planner using `Plan and create:` (single-task shortcut at `backlog`).

## Step 3 — Score and decide

Start at 1.0, deduct per criterion:

| Criterion | Deduction |
|-----------|-----------|
| Intent mismatch (scope/purpose misalignment) | -.05 |
| Evidence integrity concern | -.05 |
| Lint violations | -.05 |
| AC quality score ≤ 3 | -.03 |
| Missing reviewer evidence section | -.03 |
| Regression failures | -.10 |

Thresholds (source of truth in `r-pipeline-protocol` → Confidence Thresholds):

| Score | Action |
|-------|--------|
| ≥ .95 | Archive |
| < .95 | Reject to backlog — if auditor catches it, the gap is structural |

## Step 4 — Verify upstream commits

Upstream agents should have committed their deliverables before advancing.

**Verify upstream commits:** For each task's deliverable files, confirm they appear in recent commits via `git log --oneline -5 -- <files>`. Uncommitted source deliverables are a quality gap — note in the audit report and flag as a process concern (do NOT silently commit other agents' source code).

Do not commit kanban state yet. The archive or reject mutation happens in Step 5, and the kanban files do not reflect the final auditor action until `end_work` returns.

## Step 5 — Advance

Include the audit section in your `end_work` note.

Then advance based on confidence:

- **≥ .95 — Archive:** via `end_work` (because the task is already in `done`, this archives it and releases the claim).

- **< .95 — Reject to backlog:** via `end_work(outcome="reject", move_to="backlog")`.

## Step 6 — Commit kanban state

After `end_work` returns, stage and commit kanban board state plus any resolved decision files changed during the audit cycle. For archive, this captures the removed `done` task and the archived task file. For reject, this captures the updated active task file.

```shell
git add .owlbear/kanban/ && git commit -m "chore: archive tasks {list} (auditor)"
```

Include resolved decision files if they changed state during this audit cycle. Stage only kanban/decision files — never source code or test files belonging to upstream agents.

Before committing: verify with `git diff --cached --name-only` that only kanban/decision paths are staged.

Return Channel A signal as final output — nothing else after it.

## Output Template

Append to task body before returning:

```
## Audit
### Regression Detection
- quality-runner mode full: {summary}
- regression verdict: PASS/FAIL

### Intent Verification
- scope alignment: {PASS/FAIL} ({evidence})
- purpose match: {PASS/FAIL} ({evidence})
- extraneous scope: {none/list}
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: {score}/5
### Commit Integrity
- upstream commit presence: {PASS/FAIL} ({evidence})
- kanban commit packaging: {PASS/FAIL} ({evidence})

### Deduction Breakdown
{list each criterion applied}
### Confidence: {.XX}
### Action: {archive/reject-to-backlog}
### Required Follow-up
(Only on reject. See r-pipeline-protocol §3 — Required Follow-up format.)
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | {role} | {imperative verb + object} | {paths} | {deduction reference} |
```

If the audit section exceeds ~1500 tokens, write to `.owlbear/scratch/{id}-auditor.md` and reference it.

After committing, include the commit hash in Channel A or the final report. Do not reopen an archived task solely to append commit metadata.

```
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| {hash} | {type} | {files} | #{id} |
```

## Verification Checklist

- [ ] 4 pillars completed: regression detection, intent verification, architect quality, commit integrity
- [ ] Intent boundary respected (domain/purpose only; no function-level behavior verification)
- [ ] Reviewer evidence section present and evaluated
- [ ] Architect quality score assigned (1-5)
- [ ] Full test suite passed (cross-task regressions checked)
- [ ] Confidence score calculated using deduction rubric (not gut feeling)
- [ ] Audit section included in `end_work` note
- [ ] Upstream commits verified; kanban/decision files committed after archival
- [ ] Channel A signal returned as final output — nothing after it

## Known Pitfalls

- **Scoped tests instead of full suite:** The auditor's primary value is cross-task regression detection. Always invoke `quality-runner` with `mode: full` — never scope to task-specific files.
- **Role overlap drift:** Re-checking function-level behavior or per-AC implementation evidence duplicates reviewer responsibility. Keep auditor intent checks at domain and purpose level.
- **Gut-feeling confidence (.93–.97):** If your score lands in this range without an explicit deduction calculation, recalculate. Scores here are unreliable without itemized deductions.
- **VS Code auto-staging:** VS Code silently re-serializes `.agent.md` files. Run `git diff --cached agents/` before committing and unstage unexpected changes with `git reset HEAD`.
- **Monolithic commits:** Each task gets its own commit. Never batch multiple tasks into one commit.
- **Body content parsing:** Avoid `->` arrows and `--flag` patterns in body text passed to `end_work` — use prose equivalents (see `h-mcp-kanban`).
