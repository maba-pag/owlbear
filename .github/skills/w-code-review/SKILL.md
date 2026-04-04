---
name: w-code-review
description: "Workflow: Code review — evidence-based verification of implementation quality"
user-invocable: false
---

# Code Review

Evidence-based review of a completed implementation task. Run tests, lint, read code, verify AC, and produce a verdict.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved Decision Pre-flight.

> **MCP equivalent:** `start_work(task_id="{id}")`

Note every AC line from the task body — each will be verified individually.

## Step 1 — Check Source Control Changes

Use `get_changed_files` (with `sourceControlState: ["staged", "unstaged"]`) to list files changed by the builder. Record the changed file list — use it to scope subsequent steps.

For any changed function or class signatures, use `vscode_listCodeUsages` to trace all callers and assess downstream impact.

## Step 2 — Run Tests Independently

Do NOT rely on builder self-reports. Run yourself via Quality-Runner:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  lint_paths: ["tests/test_{module}.py"]
```

Record: passed/failed counts from the `## Tests` section of the Quality-Runner report.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Step 2.5 — Parallel Fan-Out Dispatch

For complex reviews, dispatch **quality-runner** and **code-reader** subagents in parallel to analyse the changed files independently. Each subagent returns a structured report. Synthesise their findings before proceeding to Step 3.

```
quality-runner: {task_id, changed_files}
code-reader: Analyze: {task_id, ac_lines, changed_files, test_files}
```

Collect both reports before continuing. If a subagent is unavailable, proceed solo and note the gap.

## Step 3 — Run Lint

Invoke Quality-Runner for lint if not already done in Step 2 report:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: []
  lint_paths: ["packages/{package}/src/", "tests/test_{module}.py"]
```

Record: `clean: true/false` and any `violations` from the `## Lint` section.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run ruff check packages/ tests/
```

See `h-pytest-and-linting` for flags and known pitfalls.

## Step 4 — Run Coverage

Invoke Quality-Runner for coverage:

```
agentName: quality-runner
prompt: |
  mode: scoped
  task_id: {id}
  test_paths: ["tests/test_{module}.py"]
  coverage_modules: ["{module}"]
  lint_paths: []
```

Verify touched modules have 90% coverage or higher from the `## Coverage` section.

#### Fallback: Quality-Runner Unavailable

If `quality-runner` is not in the calling agent's `agents:` array or subagent dispatch fails, run directly:

```powershell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
```

See `h-pytest-and-linting` for exact flags and known pitfalls.

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

**Any MISSING = FAIL.** LAX = note (does not auto-FAIL unless no compensating `TestBuilderDiscovered` test exists).

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

Compare each `TestFromAC_*` test method against the test-writer's original intent. Produce a comparison table:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| {test} | {description} | PRESERVED / WEAKENED / REMOVED / STRENGTHENED |

**Any WEAKENED or REMOVED = automatic FAIL.** The builder must restore original assertions.

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

> **MCP equivalent:** `show_task(task_id="{id}")`

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

### 6.1 Code Reading — style, type hints, patterns, naming, dead code.
### 6.2 Documentation — missing/stale docstrings, contradictory comments.
### 6.3 Minor Test Improvements — tighter assertions, simplified setup.
### 6.4 Code Structure — flat-vs-nested, function length, extraction opportunities.

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

If Step 2.5 was used, synthesise findings from the Quality-Runner and Code-Reader subagent reports into the verdict. Note any divergence between subagent findings and your own analysis.

**PASS** (all Pass 1 criteria met): advance via `end_work` (moves to `docs` + releases claim).

> **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="success")`

**FAIL** (any Pass 1 criterion unmet): list every failing criterion with evidence. Choose target based on issue type:

- **Implementation issue** → `in-progress` (builder fixes directly)
- **Test gap** → `todo` (tests insufficient but implementation is correct — test-writer adds missing coverage)
- **Test quality or AC interpretation** → `backlog` (architect re-evaluates)
- **3rd+ review FAIL on same task** → `backlog` (loop-breaker)

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
```

## Verification Checklist

- [ ] All Pass 1 checks executed (5.0–5.7), conditionals applied correctly
- [ ] Evidence table has specific proof for every AC line (not self-reports)
- [ ] Confidence score derived from explicit criteria, not gut feeling
- [ ] Tests run independently, not trusting builder output
- [ ] Coverage measured on touched modules
- [ ] Citations verified — file:line references read and confirmed
- [ ] Verdict matches confidence threshold (0.90+)
- [ ] Review evidence appended to task body via `edit_task`
- [ ] Channel A signal returned as final output

## Known Pitfalls

- **Trusting builder self-reports:** Always run tests yourself. "Builder said it passes" is not evidence.
- **Gut-feeling confidence:** If your score is .91–.95 without explicit deductions, recalculate with the rubric.
- **Terminal runTests tool:** Deadlocks with parallel agents. Always use `uv run pytest` in terminal.
- **Coverage measurement:** Load `h-pytest-and-linting` before attempting coverage. Flag variations without the skill cause repeated failures.
- **Suppression over-application:** Suppressions are for intentional patterns only. Do not suppress genuine issues using the suppression list as justification.
