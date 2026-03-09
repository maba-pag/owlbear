---
name: code-review
description: "Evidence-based code review workflow: run tests → lint → read code → verify AC → verdict. Use when verifying implementation quality."
---

# Code Review Workflow

Step-by-step process for reviewing a completed implementation task.

## Step 1 — Read the task

1. `kanban\kanban-md.exe show {id}` — read full acceptance criteria
2. Note every AC line — each will be verified individually

## Step 2 — Run tests independently

Do NOT rely on what the builder reported. Run yourself.

**IMPORTANT — always scope test runs.** The full suite has hundreds of tests and will
time out. Always target the specific test file(s) relevant to the task under review.

**Always use terminal pytest** — do NOT use the `runTests` tool. It funnels through a
single VS Code execution queue and deadlocks when multiple agents run in parallel.

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

For verbose output or specific test names:

```powershell
uv run pytest tests/test_{module}.py -v --tb=short
uv run pytest tests/test_{module}.py -k "test_name" -q --tb=short
```

Record: passed/failed counts, any failures, any warnings.

## Step 3 — Run lint

```powershell
uv run ruff check src/ tests/
```

Record: errors/warnings or "All checks passed!"

## Step 4 — Run coverage (if applicable)

Run coverage per the `pytest-and-linting` skill (read it with `read_file` if not already loaded)
(bare `--cov`, `--cov-fail-under=0`, run plain — never pipe). Replace
`{module_path}` with a substring matching the source files under review
(e.g., `intake` or `memory\knowledge`).

Verify touched modules have ≥ 90% coverage.

## Step 5 — Read changed files

Use `read_file` to examine the actual code:

- Type hints present on all signatures?
- Docstrings on public classes and functions?
- `from __future__ import annotations` at top?
- Follows existing patterns in the project?
- No unused imports, dead code, missing error handling?

For agent/prompt files: valid YAML frontmatter, required sections present.

## Step 5a — Evaluate test quality

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

## Step 5b — Security review

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

## Step 5c — Test Writer vs Builder Comparison

> **Conditional:** Only perform this step when `TestFromAC_*` classes exist in the
> test file. If no such classes are present (e.g., older single-agent TDD tasks),
> skip to Step 6.

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

## Step 6 — Verify AC compliance

Build an evidence table — every AC line needs specific proof:

| AC Line | Evidence | Status |
|---------|----------|--------|
| ... | file path + line, test name, command output | PASS/FAIL |

"It looks fine" is NOT evidence. Cite specific line numbers, test names, or output.

Additionally, verify that every AC line maps to at least one **specific, meaningful** test.
General coverage is not enough — if AC says "reject negative numbers", show the exact test
that supplies a negative number and asserts on the rejection.

## Step 7 — Produce verdict

**PASS** (all criteria met):

- `kanban\kanban-md.exe move {id} docs`
- Your job ends here — writer owns the docs gate

**FAIL** (any criterion unmet):

- List every failing criterion with evidence
- `kanban\kanban-md.exe move {id} todo --block "reason"`

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

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG/ADEQUATE/WEAK | {examples} |
| Negative/error paths | STRONG/ADEQUATE/WEAK | {examples} |
| Mutation reasoning | STRONG/ADEQUATE/WEAK | {reasoning} |
| Test independence | STRONG/ADEQUATE/WEAK | {evidence} |
| Descriptive names | STRONG/ADEQUATE/WEAK | {examples} |

### Security Review
- {findings or "No security issues found"}

### Test Writer vs Builder Comparison (if TestFromAC classes exist)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| {TestFromAC_Class::method} | {description or "No change"} | PRESERVED / WEAKENED / REMOVED / STRENGTHENED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|

### Verdict: PASS / FAIL

### Action Taken
- kanban command executed
```
