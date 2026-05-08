---
name: w-code-review
description: "Workflow: Code review — evidence-based verification of implementation quality"
user-invocable: false
---

# Code Review

Evidence-based review of a completed implementation task. Run tests, lint, read code, verify AC, and produce a verdict.

Review model: batch-all-findings (no first-failure gating). Collect all Review Evidence findings before issuing a final verdict.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

Note every AC line from the task body — each will be verified individually.

## Step 1 — Check Source Control Changes

Use `git diff --name-only <commit>~1 <commit>` (with the builder's commit hash from the task body to scope the diff) to list files changed by the builder. If no commit hash is available, reconstruct the changed-file list from the builder notes, task scope, and direct file inspection. Record the changed file list — use it to scope subsequent steps.

For any changed function or class signatures, use `vscode_listCodeUsages` to trace all callers and assess downstream impact.

### Step 1.1 — Dirty-Tree Contamination Check

After identifying the scoped files (builder's changed files + task test files), check for uncommitted modifications:

```shell
git status --porcelain -- <changed_files> <test_files>
```

**Exclude** `.owlbear/kanban/tasks/` from this check — task files are always dirty (pipeline ephemera) and do not affect code correctness.

Interpret results:

- **Clean** (empty output): proceed normally — test evidence will be reliable.
- **Dirty and overlapping with review scope**: the working tree contains uncommitted changes to files this review must assess. Test results run against this tree may reflect uncommitted code rather than the builder's committed work. **FAIL immediately** with an actionable diagnosis:

  ```
  FAIL #{id} -> in-progress | dirty-tree contamination: uncommitted changes in {files} overlap with review scope. Builder's commit may be incomplete or another agent's crash left residue. Builder retry needed to commit properly.
  ```

  Route to `in-progress` (not backlog) — the builder needs to re-commit, not start over. Include Required Follow-up in `end_work` note:

  ```
  ### Required Follow-up
  | # | Target Agent | Action Required | File(s) | Evidence |
  |---|-------------|----------------|---------|----------|
  | 1 | builder | Commit all task-scoped changes that are currently uncommitted | {dirty files} | git status --porcelain output |
  ```

- **Dirty but unrelated** (modified files are outside review scope): proceed normally — unrelated dirty state does not contaminate evidence for this task.

## Step 2 — Evidence Gathering

Read the builder's quality-runner output first. Re-run checks independently only when the existing evidence is missing, inconsistent, or otherwise not cost-justified.

Use this scoped 3-item checklist to structure evidence review:

1. AC→code mapping
2. test→AC alignment
3. proof sufficiency (including key boundary examples)

**Depth-aware dispatch:** Check AC lines for `(td:N)` annotations. Determine the task's max depth (highest td value across all AC lines; default td:1 if no annotations).

| Max depth | quality-runner | code-reader | TestFromAC audit (§5.0) | Coverage (Step 4) |
|-----------|---------------|-------------|------------------------|-------------------|
| td:0 | lint only | skip | skip | skip |
| td:1 | scoped tests + lint | skip | yes | yes |
| td:2 | scoped tests + lint + coverage | yes | yes | yes |

For **td:0 tasks**: dispatch quality-runner with lint only (no test paths, no coverage). Skip code-reader. Skip Steps 3–5 sequential fallback. Proceed directly to Step 8 with lint results.

For **td:1 tasks** (default): dispatch quality-runner with scoped tests + lint. Skip code-reader. Proceed to Step 8.

For **td:2 tasks**: dispatch quality-runner AND code-reader **in the same tool-call batch** — both subagents are independent and must execute concurrently. Do NOT wait for quality-runner results before dispatching code-reader.

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}_{task_id}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["workspace/{package}/src/", "tests/test_{module}_{task_id}.py"]
```

```
agentName: code-reader
prompt: |
  task_id: {id}
  ac_lines: ["{ac line 1}", "{ac line 2}"]
  changed_files: ["{file1}", "{file2}"]
  test_files: ["tests/test_{module}_{task_id}.py"]
```

Collect both reports before continuing to Step 8. If either subagent returns an **execution error** (crash, timeout, exception — not a FAIL verdict), run the full sequential workflow (steps 3–7). Note in Channel B: "Parallel fan-out failed: {reason}. Fell back to sequential."

For td:0/td:1 tasks where code-reader is skipped, proceed to Step 8 with quality-runner results only.

### Code-Reader Consumer Contract

Code-reader is a read-only adversarial subagent invoked from this workflow. Consumers (reviewer) must pass:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Kanban task ID for correlation |
| `ac_lines` | string[] | Every AC line from the task body — source of truth for coverage assessment |
| `changed_files` | string[] | Files modified by the builder — scope for all checks |
| `test_files` | string[] | Test files for the task — scope for test integrity and quality |

Code-reader mirrors the same 3-item checklist model as this workflow and returns exactly these 8 sections, each populated with findings + evidence or an explicit "No issues found" with brief justification:

```
## test_writer-audit
## security_review
## test_integrity
## test_quality
## data_safety
## test_gaps
## necessity_check
## informational
```

The reviewer synthesises the final verdict from code-reader's 8-section report plus quality-runner's report.

## Step 3 — Validate Builder Evidence

Use builder-provided quality-runner output as the primary evidence source for tests, lint, and coverage.

Re-run checks independently only when evidence is missing, contradictory, or otherwise not cost-justified.

If independent re-run is needed, use quality-runner and keep scope narrow:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}_{task_id}.py"]
  coverage_modules: ["{module}"]
  lint_paths: ["workspace/{package}/src/", "tests/test_{module}_{task_id}.py"]
```

## Step 4 — Apply the Scoped 3-Item Checklist

This checklist is the operative review workflow.

### 4.1 AC→Code Mapping

For each AC line, verify concrete implementation evidence in changed files.

### 4.2 Test→AC Alignment

For each AC line, verify mapped tests prove the intended behavior and would fail if violated.

### 4.3 Proof Sufficiency (Boundary Examples)

Verify the available proof includes key boundary examples for changed behavior (success + failure/edge where applicable). If boundaries are absent, record a factual deficiency in Review Evidence.

### Informational Checks

These never block a PASS verdict by themselves: style/readability, doc wording, naming, and minor test-tightening opportunities.

## Step 5 — Verify AC Compliance

Build an evidence table — every AC line needs specific proof:

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| {line} | {file:line, test name, output} | {test} | PASS/FAIL |

"It looks fine" is NOT evidence. Cite specific line numbers, test names, or output.

> **Research-task evidence:** AC lines with "test"/"validate"/"verify"/"confirm" require recorded command output or observable artifacts — not just prose or external doc citations.

**Verify every citation.** Read actual files and confirm. Fabricated line references are a recurring failure mode.

## Step 6 — Produce Verdict

Confidence threshold: 0.90 = PASS (see `r-pipeline-protocol` → Confidence Thresholds).

Apply a batch-all-findings review pass: do not stop at first failure. Gather all Review Evidence findings, then decide PASS/FAIL once the full checklist is complete.

Finding vs opinion rule:

- `Review Evidence` items must cite an AC line or factual deficiency.
- If an item has no citation, move it to `Observations`.
- Observations never affect verdict.

PASS confirmation line (required when no findings):

`Verified: AC→code mapping complete, test→AC alignment confirmed, proof sufficiency met. Zero findings.`

**Scope constraint — don't invent requirements:** The reviewer proves what AC declares, including its natural branches and edge cases. The reviewer does NOT invent requirements AC doesn't mention. If you find a gap that is not traceable to any AC line (even by reasonable implication), classify it as INFORMATIONAL — it cannot contribute to a FAIL verdict. Optionally create a follow-up task for genuinely important non-AC findings. Example: AC says "defaults to research, validated in statuses" → testing that validation rejects invalid values is fair (natural branch). Demanding an explicit "omission-path test" for what happens when the field isn't provided at all is an invention (Pydantic handles it implicitly).

If code-reader was dispatched (td:2), build a unified **AC compliance table** by cross-walking code-reader AC coverage findings against builder/quality-runner evidence per AC line. Note any divergence between subagent findings and your own analysis.

**PASS** (zero Review Evidence findings): advance via `end_work` (moves to `docs` + releases claim).

**FAIL** (one or more Review Evidence findings): list every failing criterion with evidence. Choose target based on issue type:

- **Implementation issue** → `in-progress` (builder fixes directly)
- **Test gap** → `todo` (tests insufficient but implementation is correct — test-writer adds missing coverage)
- **Test quality or AC interpretation** → `backlog` (architect re-evaluates)
- **2nd+ review FAIL on same task** → `backlog` (loop-breaker)

Check the task body for prior `## Review Evidence` sections to detect repeat failures.

Reject via `end_work(outcome="reject", move_to="{target_status}")` where target status depends on the failure type above.

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to task body before advancing:

```
## Review Evidence
### Test Results
- quality-runner (builder evidence): {summary}
- independent rerun (only if cost-justified): {summary or "not needed"}

### Lint
- {clean / N errors}

### Coverage
- {module}: {X}% (or N/A for non-code tasks)

### Review Evidence
- Findings that cite AC lines or factual deficiencies only.
- If one or more findings exist, verdict is FAIL.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |

### Confidence: {.XX}
### Verdict: {PASS/FAIL}

## Observations
- Non-blocking opinions only; no citation = Observations.
- Observations never affect verdict.

### Required Follow-up
(Only on FAIL. See r-pipeline-protocol §3 — Required Follow-up format.)
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | {role} | {imperative verb + object} | {paths} | {Pass 1 check reference} |
```

## Verification Checklist

- [ ] Scoped 3-item checklist executed (AC→code mapping, test→AC alignment, proof sufficiency)
- [ ] Evidence table has specific proof for every AC line (not self-reports)
- [ ] Confidence score derived from explicit criteria, not gut feeling
- [ ] Builder quality-runner evidence reviewed first; independent re-run only when cost-justified
- [ ] Coverage recorded when task scope includes code changes
- [ ] Citations verified — file:line references read and confirmed
- [ ] Verdict matches confidence threshold (0.90+)
- [ ] Review evidence included in `end_work` note
- [ ] Channel A signal returned as final output

## Known Pitfalls

- **Skipping builder evidence:** Always read builder quality-runner output before deciding whether independent re-execution is cost-justified.
- **Gut-feeling confidence:** If your score is .91–.95 without explicit deductions, recalculate with the rubric.
- **Independent rerun overuse:** Re-running every task by default violates the trust-the-builder model and adds cost without new evidence.
- **Coverage measurement:** Invoke the `quality-runner` subagent when coverage is needed — do not load pytest skills or retry flag variations directly.
- **Suppression over-application:** Suppressions are for intentional patterns only. Do not suppress genuine issues using the suppression list as justification.
