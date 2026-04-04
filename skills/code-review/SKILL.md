---
name: code-review
description: "Evidence-based code review workflow: run tests → lint → read code → verify AC → verdict. Use when verifying implementation quality."
user-invocable: false
---

# Code Review Workflow

Step-by-step process for reviewing a completed implementation task.

## kanban-md Commands

| Action | Command |
|--------|---------|
| Read task | `kanban\kanban-md.exe show {id}` |
| Claim | `kanban\kanban-md.exe edit {id} --claim <agent>` |
| Append evidence | `kanban\kanban-md.exe edit {id} -a "## Review Evidence\n{content}" -t --claim <agent>` |
| PASS (advance) | `kanban\kanban-md.exe edit {id} --status docs --release` |
| FAIL (reject) | `kanban\kanban-md.exe edit {id} --status todo --release` |
| Claim + show task (MCP) | `start_work {id}` |
| Append to task body (MCP) | `edit_task {id}` |
| Advance + release (MCP) | `end_work {id}` |

No other kanban-md commands needed. See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Read and claim the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. `kanban\kanban-md.exe edit {id} --claim <agent>` — claim by ID (never use `pick`)

> **MCP equivalent:** `start_work(task_id="{id}")` — claim + read in one call (replaces steps 1–2).

3. Note every AC line — each will be verified individually

## Step 2 — Check source control changes

Use `get_changed_files` to list files changed by the builder before proceeding.
Call with `sourceControlState: ["staged", "unstaged"]` to capture all local changes.
Record the changed file list — use it to scope subsequent steps (tests, lint, code reading).

For any changed function or class signatures, use `vscode_listCodeUsages` to trace all callers and assess downstream impact before proceeding. Note: the tool does not find dynamic calls (e.g., `getattr`).

## Step 3 — Run tests independently

Do NOT rely on what the builder reported. Run yourself.

**Always use terminal pytest** (never `runTests` — it deadlocks with parallel agents).
Scope to task-specific files to avoid timeouts:

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

Record: passed/failed counts, any failures, any warnings.

## Step 4 — Run lint

```powershell
uv run ruff check src/ tests/
```

Record: errors/warnings or "All checks passed!"

## Step 5 — Run coverage (if applicable)

> **Prerequisite:** Load the `pytest-and-linting` skill with `read_file` before running coverage commands. It defines the exact flags, output handling approach, and known pitfalls.

Use bare `--cov` with `--cov-fail-under=0`. Replace `{module_path}` with a substring
matching the source files under review (e.g., `intake` or `memory\knowledge`).

Verify touched modules have ≥ 90% coverage.

## Step 6 — Pass 1: CRITICAL checks

Any finding in Pass 1 = automatic FAIL verdict. These are non-negotiable.

### 6.0 Test-writer audit — AC-to-test coverage

Before evaluating the builder's work, verify the test-writer did its job correctly.
The test-writer wrote tests from the AC before the builder implemented — did it cover
everything?

1. Read every AC line from the task body.
2. For each AC line, find the corresponding `TestFromAC_*` test(s).
3. For each mapped test, ask: **would this test fail if the AC were violated?** A test
   that asserts `result is not None` for an AC line saying "return sorted results" does
   NOT adequately cover the AC.
4. Flag **MISSING** (AC line with no test at all) and **LAX** (test exists but wouldn't
   catch a subtle violation of the AC).

**Produce a test-writer coverage table:**

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| "Reject negative amounts" | `TestFromAC_Transfer::test_negative_raises` | Yes — asserts `ValueError` | COVERED |
| "Return sorted results" | _(none)_ | — | **MISSING** |
| "Cache expires after TTL" | `TestFromAC_Cache::test_expiry` | No — only checks key exists | **LAX** |

**Any MISSING = FAIL.** Return to `todo` so the test-writer can fill the gap.
**Any LAX = note in review, does not auto-FAIL** (the builder may have added
compensating tests in `TestBuilderDiscovered`). If no compensating test exists,
escalate to FAIL.

> **Conditional:** Skip this step when no `TestFromAC_*` classes exist (older tasks).

### 6.1 Security review

Check the changed code for common security vulnerabilities. This is not an exhaustive
audit — it targets the OWASP Top 10 patterns most likely to appear in Python code.

1. **Hardcoded secrets** — grep for strings resembling tokens, passwords, API keys, connection
   strings. Flag any non-placeholder credential in source or test code.
2. **Injection** — look for unsanitized input in: SQL queries (string formatting/f-strings instead
   of parameterized), shell commands (`subprocess` with `shell=True` + user input), HTML/template
   rendering.
3. **Path traversal** — user-controlled input used in file paths without validation. Check for
   `..` traversal and null-byte injection.
4. **Insecure deserialization** — `pickle.loads`, `yaml.load` (without `SafeLoader`),
   `eval()`/`exec()` on external input.
5. **Missing input validation** — at system boundaries (user input, external API responses,
   file content), are inputs validated before use?
6. **Dependency risk** — any new dependency added? Check if it's well-maintained and not
   known-vulnerable.
7. **Secret leakage in logs/errors** — do error messages or log statements expose tokens,
   passwords, or PII?

Any vulnerability found = FAIL. Security issues are non-negotiable.

### 6.2 Test integrity — TestFromAC comparison

> **Conditional:** Only perform this step when `TestFromAC_*` classes exist in the
> test file. If no such classes are present (e.g., older single-agent TDD tasks),
> skip to 5.3.

The test-writer agent writes `TestFromAC_*` tests before the builder implements.
The builder must never modify these classes. Your job is to verify that.

**Procedure:**

1. Read every `TestFromAC_*` class and its test methods in the builder's final test file.
2. Compare each method against the test-writer's original intent (method names,
   assertions, error types, boundary values).
3. For each test method, assess: was it preserved exactly, strengthened (stricter),
   weakened, or removed?

**Canonical weakened-assertion patterns:**

| Pattern | Example |
|---------|---------|
| Relaxed comparison | `==` changed to `in`, exact match changed to `contains` |
| Broadened exception | `ValueError` changed to `Exception`, specific error message check removed |
| Removed edge case | A boundary or negative-path test method deleted entirely |
| Reduced boundary coverage | Boundary values softened (e.g., `0` → `1`, off-by-one guards removed) |
| Weakened assertion count | Multiple specific assertions replaced by a single loose check |
| Added `pytest.skip` / `xfail` | Test disabled without justification |

**Produce a comparison table:**

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_Foo::test_negative_raises` | No change | PRESERVED |
| `TestFromAC_Foo::test_boundary_zero` | `==` changed to `>=` | WEAKENED |
| `TestFromAC_Foo::test_empty_input` | Method removed | REMOVED |
| `TestFromAC_Foo::test_returns_list` | Added stricter length check | STRENGTHENED |

Assessment values: **PRESERVED**, **WEAKENED**, **REMOVED**, **STRENGTHENED**.

**Any WEAKENED or REMOVED assessment = automatic FAIL.** Include a structured
rejection naming the specific test methods and the nature of the weakening.
The builder must restore the original test-writer assertions or file a BLOCK
if the interface is genuinely infeasible.

### 6.3 Test quality

**Your job is to find weak tests, not confirm they exist.** A test suite that passes
is worthless if it would also pass with a broken implementation.

Read every test file for the task and evaluate:

1. **Assertion specificity** — flag lazy assertions: `assert result`, `assert result is not None`,
   `assert len(items) > 0`. Tests must check *specific values, types, and structures*. Every AC
   item deserves an assertion that would fail if the behavior were subtly wrong.
2. **Negative / error-path coverage** — for every happy-path test, ask: where is the test for
   invalid input? Missing data? Boundary values? Permission denied? If AC says "reject X", there
   must be a test that supplies X and verifies rejection.
3. **Manual mutation reasoning** — for each AC item, mentally flip the implementation:
   "If I changed `>` to `>=`, removed a return, or swapped two arguments, would a test catch it?"
   If the answer is "probably not", the tests are too permissive. Flag it as WEAK.
4. **Test independence** — no shared mutable state between tests, proper setup/teardown. A test
   that passes only when run after another test is not a test.
5. **Descriptive test names** — `test_1`, `test_it_works`, `test_basic` are unacceptable. Test
   names must describe the scenario and expected outcome (e.g., `test_negative_amount_raises_value_error`).

Rate each dimension: **STRONG** / **ADEQUATE** / **WEAK**.
Any WEAK rating = automatic FAIL verdict (builder must improve tests before re-review).

### 6.4 Data safety

Check the changed code for data integrity risks:

1. **Unvalidated LLM output** — LLM-generated content persisted to disk or database without
   validation or sanitization.
2. **Race conditions** — shared mutable state accessed from multiple coroutines or threads
   without synchronization.
3. **Missing atomicity** — multi-step operations (file writes, DB transactions) that can
   leave inconsistent state on partial failure.
4. **Unbounded input** — user or external input passed to resource-intensive operations
   (regex, recursion, large allocations) without size limits.

Any data safety issue found = FAIL.

### 6.5 Implementation-aware test gap analysis

Go beyond the AC. The builder's implementation may introduce complexity that the AC
didn't anticipate and the test-writer couldn't have known about. Read the builder's
actual code and ask: **given what was built, what tests are missing?**

1. **Read the implementation.** Identify branches, error-handling paths, retry logic,
   state machines, configuration-dependent behavior, and edge cases that the code
   actually handles.
2. **Compare to test coverage.** For each significant code path, check whether a test
   exercises it. Focus on paths that would silently produce wrong results if broken
   (not paths that would crash obviously).
3. **Check for untested defensive code.** If the builder added input validation,
   fallback logic, or error recovery, verify there are tests that trigger those paths.
4. **Flag gaps.** Any implementation complexity without corresponding test coverage is
   a potential gap.

**This is a CRITICAL check:** If the implementation has significant untested paths
(retry logic with no failure test, validation code with no invalid-input test,
branching logic where only the happy path is tested), FAIL the review. The builder
must add `TestBuilderDiscovered` tests to cover these paths.

**This is NOT about style preferences.** Only flag genuinely untested behavioral paths
that could mask bugs. Don't flag missing tests for trivial getters or obvious
pass-through code.

### 6.6 Necessity check

> **Conditional:** Only perform this step when the task adds a new dependency,
> integration, tool, server, or external capability. Skip for bug fixes, refactors,
> renames, config tweaks, or test improvements.

Before verifying *how* a feature was built, ask whether it *needed to be built at all*.
Answer these three questions:

1. **Already provided?** Does the IDE, runtime, or an installed extension already
   provide this capability without additional code?
2. **Tooling overlap?** Does existing project tooling (libraries, utilities, MCP
   servers, scripts) already solve this need?
3. **Presumptive feature?** Is this building for a speculated future need rather than
   a confirmed current requirement?

If yes to any question: FAIL with evidence citing the existing provider or the
absence of a confirmed requirement. Document the specific overlap found.

### 6.7 Builder process quality (loop detection)

Read the full task body via `kanban\kanban-md.exe show {id}` (MCP: `show-task(task_id="{id}")`). Check builder notes for loop patterns:

1. **Count retry sections.** Count `## Builder Notes` headers (including suffixed retries like `Builder Notes (retry)`, `Builder Notes (retry 2)`). Record the count.
2. **Check approach variation.** For each retry, verify the builder describes a different diagnosis, changed approach, or new strategy. Identical approaches across retries = loop pattern.
3. **Check for tier-3 violation.** If 3+ retries at the same logical goal exist without a handoff/block statement, the builder violated the loop detection escalation rules in `agent-common.instructions.md`.
4. **Produce a process-quality assessment:**

| Assessment | Criteria | Action |
|------------|----------|--------|
| **CLEAN** | ≤ 1 retry, or all retries show approach variation | Note, no action |
| **FRICTION** | 2 retries with approach variation — correct escalation behavior | Informational only, does not block PASS |
| **LOOP** | Identical approaches across retries, or tier-3 triggered without handoff/block | Automatic FAIL |

**Any LOOP assessment = automatic FAIL.** FRICTION is informational only — it does not block PASS.

## Step 7 — Pass 2: INFORMATIONAL checks

Findings in Pass 2 are noted in the review but do NOT block a PASS verdict.
Include them as suggestions for the builder to consider in future work.

### 7.1 Code reading

Use `read_file` to examine the actual code for style and convention adherence:

- Type hints present on all signatures?
- `from __future__ import annotations` at top?
- Follows existing patterns in the project?
- Naming conventions consistent with the codebase?
- No unused imports or dead code?

For agent/prompt files: valid YAML frontmatter, required sections present.

### 7.2 Documentation

- Missing or stale docstrings on public classes and functions
- Comments that contradict the code
- Missing module-level docstring

### 7.3 Minor test improvements

- Could-be-tighter assertions that already cover behavior adequately
- Redundant test setup that could be simplified
- Test helper extraction opportunities

### 7.4 Code structure

- Flat-vs-nested suggestions
- Function length (>50 lines)
- Opportunities for extraction or simplification

## Suppressions

DO NOT flag these patterns — they are intentional or harmless:

1. **Threshold/constant values without justification comments** — tuned empirically; comments rot faster than the values change.
2. **Redundant guards that aid readability** — harmless defensive checks (e.g., `if x is not None` before an operation that would already handle `None`).
3. **Test exercises multiple guards simultaneously** — valid integration-style testing; not every guard needs isolated unit coverage.
4. **Already-addressed items in the diff** — if the issue appears earlier in the diff and is fixed later, do not flag it.
5. **Style-only consistency changes** — renaming for consistency across the codebase is not a defect and not worth flagging.
6. **Regex edge cases for constrained inputs** — when the input domain is known and bounded, regex edge cases that cannot occur in practice are not worth flagging.
7. **`from __future__ import annotations` presence in test files** — this is a project convention, not a defect to flag repeatedly.
8. **Agent/skill markdown formatting nits** — formatting is fluid during active development; minor markdown style differences are not defects.
9. **Coverage gaps in code not touched by the task** — out of scope for task-scoped review; coverage is only evaluated on modules changed by the task.

## Step 8 — Verify AC compliance

> **Research-task evidence:** When reviewing a research or documentation task (no TestFromAC classes, no source code changes), any AC line that includes "test", "validate", "verify", or "confirm" requires a recorded command run log or observable artifact — not just prose in a research doc or a citation to external documentation. If the only evidence is "According to docs…", treat that AC line as **FAIL**.

Build an evidence table — every AC line needs specific proof:

| AC Line | Evidence | Status |
|---------|----------|--------|
| ... | file path + line, test name, command output | PASS/FAIL |

"It looks fine" is NOT evidence. Cite specific line numbers, test names, or output.

**Verify every citation.** When the builder claims "implemented at line X" or "test Y covers AC Z", read the actual file and confirm. Fabricated or stale line-number references are a recurring failure mode — never trust citations without checking.

**Document tooling gaps.** If coverage measurement, test tooling, or terminal output fails, state the gap explicitly in the review evidence. Never rate high confidence to paper over a verification you could not actually perform.

Additionally, verify that every AC line maps to at least one **specific, meaningful** test.
General coverage is not enough — if AC says "reject negative numbers", show the exact test
that supplies a negative number and asserts on the rejection.

## Step 9 — Produce verdict

Confidence threshold: ≥ .90 = PASS (see agent-common → **Confidence thresholds**).

**PASS** (all Pass 1 criteria met, no CRITICAL findings):

- `kanban\kanban-md.exe edit {id} --status docs --release`
  > **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="success")`
- Your job ends here — writer owns the docs gate

**FAIL** (any Pass 1 criterion unmet):

- List every failing criterion with evidence
- `kanban\kanban-md.exe edit {id} --status todo --release`
  > **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="reject")`

Pass 2 informational findings are included in the review body but do not affect the verdict.

## Review output format

```
## Review: #{id} — {title}

### Test Results
- pytest: {N} passed, {M} failed
- Evidence: {key output}

### Lint Results
- ruff: {clean / N errors}

### Coverage
- {module}: {X}%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage (if TestFromAC classes exist)
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| {AC line} | {TestFromAC_Class::method or "none"} | {Yes/No — reasoning} | COVERED / MISSING / LAX |

#### Security Review
- {findings or "No security issues found"}

#### Test Integrity (if TestFromAC classes exist)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| {TestFromAC_Class::method} | {description or "No change"} | PRESERVED / WEAKENED / REMOVED / STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG/ADEQUATE/WEAK | {examples} |
| Negative/error paths | STRONG/ADEQUATE/WEAK | {examples} |
| Mutation reasoning | STRONG/ADEQUATE/WEAK | {reasoning} |
| Test independence | STRONG/ADEQUATE/WEAK | {evidence} |
| Descriptive names | STRONG/ADEQUATE/WEAK | {examples} |

#### Data Safety
- {findings or "No data safety issues found"}

#### Implementation-Aware Test Gaps
- {untested code paths found, or "No significant untested paths"}

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | {count} |
| Approach variation across retries | {Yes / No / N/A} |
| Tier-3 violation (3+ retries without handoff) | {Yes / No} |
| Assessment | **CLEAN** / **FRICTION** / **LOOP** |

### Pass 2 — INFORMATIONAL
- {code reading notes}
- {documentation suggestions}
- {minor test improvements}
- {code structure suggestions}
- (or "No informational findings")

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|

### Verdict: PASS / FAIL

### Action Taken
- kanban command executed
```
