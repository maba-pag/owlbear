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

Code-reader executes Critical Checks §5.0–5.7 and Informational Checks §6.1–6.4 (defined below) and returns exactly these 8 sections, each populated with findings + evidence or an explicit "No issues found" with brief justification:

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

The reviewer synthesises the final verdict from code-reader's 8-section report plus quality-runner's 5-section report.

## Step 3 — Run Lint

Invoke Quality-Runner for lint if not already done in Step 2 report:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: []
  lint_paths: ["workspace/{package}/src/", "tests/test_{module}_{task_id}.py"]
```

Record: `clean: true/false` and any `violations` from the `## Lint` section.

## Step 4 — Run Coverage

Invoke Quality-Runner for coverage:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}_{task_id}.py"]
  coverage_modules: ["{module}"]
  lint_paths: []
```

Verify touched modules have 90% coverage or higher from the `## Coverage` section.

**Scoping rule:** The 90% gate applies to lines CHANGED by the builder in this task (diff-scoped), not the entire module. If the module has low overall coverage but the builder's changes are fully exercised, that is a PASS. Note module-level coverage as INFORMATIONAL context only — if it's genuinely low, create a follow-up test-curation task rather than rejecting the current task.

## Step 5 — Pass 1: CRITICAL Checks

Any finding in Pass 1 = automatic FAIL verdict. These are non-negotiable.

### 5.0 Test-Writer Audit — AC-to-Test Coverage

> **Conditional:** Skip when no `TestFromAC_*` classes exist.

1. For each AC line, find the corresponding `TestFromAC_*` test(s).
2. For each mapped test: would it fail if the AC were violated?
3. Produce a coverage table:

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| {line} | {test or "none"} | {Yes/No — reasoning} | COVERED / MISSING / LAX |

**Any MISSING = FAIL.** LAX = note. Builder-authored compensating tests are not part of the target process.

### 5.1 Security Review

Check changed code against OWASP Top 10 patterns:

1. **Hardcoded secrets** — grep for tokens, passwords, API keys.
2. **Injection** — unsanitized input in SQL, shell commands, templates.
3. **Path traversal** — user-controlled input in file paths without validation.
4. **Insecure deserialization** — `pickle.loads`, `yaml.load` without SafeLoader, `eval()`/`exec()`.
5. **Missing input validation** — at system boundaries.
6. **Dependency risk** — new dependencies well-maintained and not known-vulnerable?
7. **Secret leakage** — error messages or logs exposing credentials/PII.

Any vulnerability = FAIL.

### 5.2 Test Integrity — TestFromAC Comparison

> **Conditional:** Only when `TestFromAC_*` classes exist.

Compare each `TestFromAC_*` test method against the test-writer's original intent and verify behavioral equivalence.

Compare each `TestFromAC_*` test method against the test-writer's original intent. Produce a comparison table:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| {test} | {description} | PRESERVED / CHANGED_WITH_JUSTIFICATION / NEEDS_REVIEW |

Canonical weakened-assertion patterns: relaxed comparison, broadened exception, removed edge case, reduced boundary coverage, weakened assertion count, added `pytest.skip`/`xfail` without justification.

### 5.3 Test Quality

Evaluate each dimension: **STRONG** / **ADEQUATE** / **WEAK**.

1. **Assertion specificity** — flag lazy assertions: `assert result`, `assert result is not None`.
2. **Negative/error-path coverage** — for every happy-path test, where is the error test?
3. **Manual mutation reasoning** — if you flipped `>` to `>=` or removed a return, would a test catch it?
4. **Test independence** — no shared mutable state between tests.
5. **Descriptive test names** — `test_1`, `test_it_works` are unacceptable.

Any WEAK rating = automatic FAIL.

### 5.4 Data Safety

1. **Unvalidated LLM output** persisted without sanitization.
2. **Race conditions** in shared mutable state.
3. **Missing atomicity** in multi-step operations.
4. **Unbounded input** to resource-intensive operations.

Any data safety issue = FAIL.

### 5.5 Implementation-Aware Test Gap Analysis

Read the builder's actual code. For each significant code path, check whether a test exercises it:

- Branches, error-handling, retry logic, state machines, configuration-dependent behavior.
- Untested defensive code (validation, fallback logic, error recovery).

Significant untested paths = FAIL. Trivial getters or obvious pass-through code = no flag.

### 5.6 Necessity Check

> **Conditional:** Only for tasks adding new dependencies, integrations, tools, or external capabilities. Skip for bug fixes, refactors, renames, config.

1. **Already provided?** IDE, runtime, or installed extension provides this capability?
2. **Tooling overlap?** Existing project tooling solves this need?
3. **Presumptive feature?** Building for speculated future need?

If yes to any = FAIL with evidence.

### 5.7 Builder Process Quality (Loop Detection)

Read the full task body via `show_task`. Check builder notes for loop patterns:

1. Count `## Builder Notes` sections (including retries).
2. Verify approach variation across retries.
3. Check for tier-3 violation (3+ retries without handoff/block).

| Assessment | Criteria | Action |
|------------|----------|--------|
| **CLEAN** | 1 retry max, or all retries vary approach | Note, no action |
| **FRICTION** | 2 retries with approach variation | Informational only |
| **LOOP** | Identical approaches, or tier-3 triggered without handoff | Automatic FAIL |

> **Code-reader delegation:** For complex reviews, delegate deep code reading to the **code-reader** agent. The code-reader provides detailed analysis of specific files or functions. The reviewer retains verdict authority.

## Step 6 — Pass 2: INFORMATIONAL Checks

Findings noted but do NOT block a PASS verdict.

### 6.1 Code Reading — style, type hints, patterns, naming, dead code

### 6.2 Documentation — missing/stale docstrings, contradictory comments

### 6.3 Minor Test Improvements — tighter assertions, simplified setup

### 6.4 Code Structure — flat-vs-nested, function length, extraction opportunities

### Suppressions

Do NOT flag: threshold constants without justification, redundant readability guards, tests exercising multiple guards, already-addressed diff items, style-only consistency changes, regex edge cases for constrained inputs, `from __future__ import annotations` in test files, agent/skill markdown formatting nits, coverage gaps in untouched code.

## Step 7 — Verify AC Compliance

Build an evidence table — every AC line needs specific proof:

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| {line} | {file:line, test name, output} | {test} | PASS/FAIL |

"It looks fine" is NOT evidence. Cite specific line numbers, test names, or output.

> **Research-task evidence:** AC lines with "test"/"validate"/"verify"/"confirm" require recorded command output or observable artifacts — not just prose or external doc citations.

**Verify every citation.** Read actual files and confirm. Fabricated line references are a recurring failure mode.

## Step 8 — Produce Verdict

Confidence threshold: 0.90 = PASS (see `r-pipeline-protocol` → Confidence Thresholds).

Apply a batch-all-findings review pass: do not stop at first failure. Gather all Review Evidence findings, then decide PASS/FAIL once the full checklist is complete.

Finding vs opinion rule:

- `Review Evidence` items must cite an AC line or factual deficiency.
- If an item has no citation, move it to `Observations`.
- Observations never affect verdict.

PASS confirmation line (required when no findings):

`Verified: AC→code mapping complete, test→AC alignment confirmed, proof sufficiency met. Zero findings.`

**Scope constraint — don't invent requirements:** The reviewer proves what AC declares, including its natural branches and edge cases. The reviewer does NOT invent requirements AC doesn't mention. If you find a gap that is not traceable to any AC line (even by reasonable implication), classify it as INFORMATIONAL — it cannot contribute to a FAIL verdict. Optionally create a follow-up task for genuinely important non-AC findings. Example: AC says "defaults to research, validated in statuses" → testing that validation rejects invalid values is fair (natural branch). Demanding an explicit "omission-path test" for what happens when the field isn't provided at all is an invention (Pydantic handles it implicitly).

If code-reader was dispatched (td:2), build a unified **AC compliance table** by cross-walking Code-Reader's AC coverage assessment against Quality-Runner's test pass/fail status per AC line. Automatic FAIL triggers: any MISSING or WEAK finding from Code-Reader; any test failure reported by Quality-Runner; any security finding from Code-Reader. Note any divergence between subagent findings and your own analysis.

**PASS** (all Pass 1 criteria met): advance via `end_work` (moves to `docs` + releases claim).

**FAIL** (any Pass 1 criterion unmet): list every failing criterion with evidence. Choose target based on issue type:

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
- pytest: {N} passed, {M} failed

### Lint: {clean / N errors}

### Coverage: {module}: {X}%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|

#### Security Review
- {findings or "No issues"}

#### Test Integrity
| Original Test | Change Made | Assessment |

#### Test Quality
| Dimension | Rating | Evidence |

#### Data Safety
- {findings or "No issues"}

#### Implementation-Aware Gaps
- {findings or "No untested paths"}

#### Builder Process Quality
| Metric | Value |
| Builder Notes sections | {count} |
| Approach variation | {Yes/No/N/A} |
| Assessment | {CLEAN/FRICTION/LOOP} |

### Pass 2 — INFORMATIONAL
- {findings or "None"}

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

- [ ] All Pass 1 checks executed (5.0–5.7), conditionals applied correctly
- [ ] Evidence table has specific proof for every AC line (not self-reports)
- [ ] Confidence score derived from explicit criteria, not gut feeling
- [ ] Tests run independently, not trusting builder output
- [ ] Coverage measured on touched modules
- [ ] Citations verified — file:line references read and confirmed
- [ ] Verdict matches confidence threshold (0.90+)
- [ ] Review evidence included in `end_work` note
- [ ] Channel A signal returned as final output

## Known Pitfalls

- **Skipping builder evidence:** Always read builder quality-runner output before deciding whether independent re-execution is cost-justified.
- **Gut-feeling confidence:** If your score is .91–.95 without explicit deductions, recalculate with the rubric.
- **Terminal runTests tool:** Deadlocks with parallel agents. Always use `uv run pytest` in terminal.
- **Coverage measurement:** Invoke the `quality-runner` subagent for coverage measurement — do not load pytest skills or retry flag variations directly.
- **Suppression over-application:** Suppressions are for intentional patterns only. Do not suppress genuine issues using the suppression list as justification.
