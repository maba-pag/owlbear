---
id: 781
title: Tests — Content safety predicate inversion
status: archived
priority: medium
created: '2026-04-10T12:30:43.995109+00:00'
updated: '2026-04-14T09:37:41.997925+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
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
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: all tests passed in batch run (`test_content_safety_inversion_775.py`). Unblocked for review continuation.
[[2026-04-14]]
## Review Evidence

### Quality-Runner Results
- **Tests:** 27 passed, 0 failed, 0 skipped (exit 0)
- **Lint:** clean, 0 violations (ruff exit 0)
- **Coverage:** `owlbear_knowledge.content_safety` = **100%**

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 — url_list, authenticated_web, unknown → wraps | `should_wrap("url_list") is True`, `should_wrap("authenticated_web") is True`, `should_wrap("rss_feed") is True`, `should_wrap("some_future_source") is True` | `test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` | PASS |
| AC2 — file, text, file_glob → no wrap | `should_wrap("file") is False`, `should_wrap("text") is False`, `should_wrap("file_glob") is False` + None/empty boundary tests | `test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false`, `test_none_returns_false`, `test_empty_string_returns_false` | PASS |
| AC3 — idempotency (no double-wrap) | `wrapped_twice == wrapped_once` — strong equality assertion on actual `wrap_untrusted_content()` output | `test_idempotency_guard_no_double_wrap` (`test_content_safety_735.py:L70`) | PASS |

### Pass 1 Critical Checks

| Check | Result | Notes |
|-------|--------|-------|
| 5.0 AC-to-Test coverage | PASS | All 3 AC lines mapped to `TestFromAC_*` tests; no missing coverage |
| 5.1 Security | PASS | Test file only; implementation is a frozenset membership check with no injection surface |
| 5.2 TestFromAC integrity | PASS | No `TestFromAC_*` modifications detected — pass-through task |
| 5.3 Test quality | STRONG | Strict `is True`/`is False` booleans throughout; deny-list inversion would break ≥4 tests on mutation; imports scoped per-test; descriptive names |
| 5.4 Data safety | PASS | No shared mutable state; no persistence |
| 5.5 Implementation-aware gap analysis | PASS | Both branches of `should_wrap()` (`if not source_type → False`; `not in _TRUSTED_SOURCE_TYPES`) exercised; idempotency guard path exercised; 100% coverage confirmed |
| 5.6 Necessity | N/A | Test task, no new dependencies |
| 5.7 Builder process | CLEAN | Single builder notes section, clean pass-through |

### Deductions
None.

### Verdict
Confidence: **.97** → **PASS #781 -> docs | confidence .97**
[[2026-04-14]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only task (type:test); no production code changed. `content_safety.py` untouched. `copilot-instructions.md` not affected. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Pass-through task — tests already existed in `test_content_safety_inversion_775.py`. |
| 3 | External attribution | No | N/A | No external repos, articles, or docs used. Standard assertions against an existing frozenset predicate. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research doc produced for #781. "See research F4" in context references upstream parent #775 — no new `.owlbear/research/781*.md` exists. |

### Files Updated
- None

### Scratch Files Cleaned
- None (`.owlbear/scratch/781-*` — no matches found)

[[2026-04-14]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — url_list, authenticated_web, unknown → wraps | `test_url_list_returns_true`, `test_authenticated_web_returns_true`, `test_unknown_future_type_returns_true`, `test_arbitrary_invented_string_returns_true` — all assert `should_wrap() is True` | PASS |
| AC2 — file, text, file_glob → no wrap | `test_file_returns_false`, `test_text_returns_false`, `test_file_glob_returns_false` + None/empty boundary | PASS |
| AC3 — idempotency (no double-wrap) | `test_content_safety_735.py::test_idempotency_guard_no_double_wrap` — `wrapped_twice == wrapped_once` | PASS |
| AC4 — File: test_content_safety_inversion_775.py | File exists, committed at `045aa682` | PASS |

### Test Results
- pytest (scoped): 27 passed, 0 failed (4.80s)
- pytest (full suite): 4195 passed, 362 failed, 8 skipped — no failures in task scope (`test_content_safety_inversion_775.py`, `test_content_safety_735.py`)
- ruff: 1 violation (E501 in `serve/kanban/src/owlbear_kanban/engine.py:472`) — outside task scope, clean in scope

### Architect Quality: 4/5
AC lines are concrete and testable. Minor imprecision (AC names `wrap_untrusted_content()` but the function under test for source-type decisions is `should_wrap()`), caught and clarified by architect in review. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 PASS) → 0
- Lint violations (in scope): 0 → 0
- AC quality ≤ 3: No (4/5) → 0
- Missing reviewer evidence: No (detailed, two rounds) → 0
- Full-suite failures in scope: 0 → 0

### Confidence: 1.00
### Action: archive