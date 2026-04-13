---
id: 781
title: Tests — Content safety predicate inversion
status: review
priority: needed
created: '2026-04-10T12:30:43.995109+00:00'
updated: '2026-04-13T01:45:36.701228+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: true
block_reason: 'Quality-Runner fatal environment error — pytest import chain interrupted
  by KeyboardInterrupt during anyio module load on two consecutive attempts. Cannot
  independently run tests. Critical rule: always run tests yourself. Unblock when
  environment is restored.'
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `wrap_untrusted_content()` wraps content for source types: `url_list`, `authenticated_web`, and any unknown future type
- Tests verify `wrap_untrusted_content()` does NOT wrap content for `file`, `text`, `file_glob`
- Tests verify idempotency (no double-wrap) is preserved
- File: `tests/test_content_safety_inversion_775.py`

## Context
- WS-B: Pipeline Quality
- Scope item 8 from #775
- See research F4: defense-in-depth, safe to ship independently

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only the content safety predicate inversion behavior |
| Interface clarity | PASS (minor note) | AC references `wrap_untrusted_content()` but the source-type predicate is actually `should_wrap(source_type)` in `content_safety.py`; `wrap_untrusted_content()` takes no `source_type` param. Intent is clear — test-writer should verify via `should_wrap()` for AC1/AC2 and `wrap_untrusted_content()` for AC3 (idempotency). |
| Dependency correctness | PASS | No deps — this is the TDD test task. No upstream implementation dependency needed. |
| Module layering | PASS | Tests import from `owlbear_knowledge.content_safety` — correct layer |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Minimal, focused scope |
| Premise challenge | PASS (note) | Tests already exist at `tests/test_content_safety_inversion_775.py` (10 tests for `should_wrap()`). Idempotency covered in `tests/test_content_safety_735.py:test_idempotency_guard_no_double_wrap`. Test-writer should verify existing coverage is adequate rather than writing duplicate tests. |
| Pattern consistency | PASS | Uses `TestFromAC_*` class pattern consistent with codebase |
| Security surface | N/A | Test file only |
| Single domain | PASS | Knowledge domain only |

### Codebase Evidence

- Implementation: `serve/knowledge/src/owlbear_knowledge/content_safety.py` — `should_wrap()` (L26-43), `wrap_untrusted_content()` (L46-69), `_TRUSTED_SOURCE_TYPES = frozenset({"file", "file_glob", "text"})` (L23)
- Existing tests: `tests/test_content_safety_inversion_775.py` — 10 tests covering should_wrap for url_list, authenticated_web, unknown types (AC1), and file, text, file_glob, None, empty (AC2)
- Idempotency: `tests/test_content_safety_735.py:test_idempotency_guard_no_double_wrap` (AC3)
- Integration point: `serve/knowledge/src/owlbear_knowledge/ingest.py` L207-235 — calls both `should_wrap()` and `wrap_untrusted_content()` in the pipeline

### AC Precision Note

AC1/AC2 name `wrap_untrusted_content()` but the function under test for source-type decisions is `should_wrap(source_type)`. The existing test file correctly tests `should_wrap()`. AC3 (idempotency) correctly applies to `wrap_untrusted_content()`.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Advanced to todo. Tests already exist and pass — test-writer should verify existing coverage is adequate for all 3 AC lines rather than writing duplicates.
[[2026-04-12]]
## Test-Writer Notes
- Non-implementation pass-through: task tagged `type:test`, tests already exist and are verified adequate.
- Test file: `tests/test_content_safety_inversion_775.py` (11 tests, all PASS)
- Idempotency (AC3): `tests/test_content_safety_735.py::test_idempotency_guard_no_double_wrap` (PASS)

### AC Coverage Table

| AC | Tests | File | Result |
|----|-------|------|--------|
| AC1 — url_list, authenticated_web, unknown → `True` | `test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` | `test_content_safety_inversion_775.py` | ✓ |
| AC2 — file, text, file_glob → `False` | `test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false` (+None+empty boundary) | `test_content_safety_inversion_775.py` | ✓ |
| AC3 — idempotency (no double-wrap) | `test_idempotency_guard_no_double_wrap` | `test_content_safety_735.py` | ✓ |

- Total: 27 tests across both files — 27 passed, 0 failed.
- Existing coverage is adequate; no duplicate tests written per arch review verdict (APPROVE with note).
- Arch review note verified: `should_wrap()` is the correct function under test for AC1/AC2; `wrap_untrusted_content()` is tested for AC3 idempotency.
[[2026-04-12]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-13]]
## Review Evidence

### Quality-Runner Execution
- Invocation: `mode: scoped, task_id: 781, test_paths: [test_content_safety_inversion_775.py, test_content_safety_735.py], coverage_modules: [owlbear_knowledge.content_safety], lint_paths: [test_content_safety_inversion_775.py]`
- Result: FATAL ERROR — pytest import chain interrupted by KeyboardInterrupt during anyio module load (2 consecutive attempts). Process cleanup also hanging. Possible Windows asyncio/execnet deadlock.
- pytest exit code: 1, 0 tests run, lint not executed.

### Pre-Read Static Analysis (performed before test execution)

**Test file read:** `tests/test_content_safety_inversion_775.py` — 11 tests in `TestFromAC_ShouldWrapPredicate`. Structure well-formed. `TestFromAC_*` class present. All assertions use `is True` / `is False` (strict bool, not truthy). Descriptive test names. No shared mutable state.

**AC3 test read:** `tests/test_content_safety_735.py::test_idempotency_guard_no_double_wrap` — wraps once, wraps twice, asserts `wrapped_twice == wrapped_once`. Strong assertion.

**What could not be verified due to environment failure:**
- Tests actually pass (cannot trust builder self-report)
- Lint clean (ruff not run)
- Coverage on `owlbear_knowledge.content_safety`

### Verdict
BLOCKED — environment failure prevents independent test execution. Per critical rules, cannot issue PASS without running tests myself.