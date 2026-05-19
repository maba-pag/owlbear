---
id: 842
title: Update web_search tests to mock extract_content instead of trafilatura
status: archived
priority: nice-to-have
created: 2026-03-16T12:46:55.7254146+01:00
updated: 2026-03-17T00:11:39.4301927+01:00
started: 2026-03-17T00:10:52.5587253+01:00
completed: 2026-03-17T00:10:52.5587253+01:00
tags:
    - dry
    - scope:core
    - phase-9
    - type:test
class: standard
---

TDD RED phase for #824. Update tests in tests/test_web_search.py that mock owlbear.tools.web_search.trafilatura (7 test methods) to mock extract_content instead.
AC:
(1) All 7 trafilatura mocks in test_web_search.py replaced with extract_content mocks returning ExtractionResult
(2) Add test: success path does NOT double-wrap (extract_content already wraps)
(3) Add test: fallback path (empty .text) still applies wrap_untrusted_content to raw HTML
(4) All updated tests FAIL against current (pre-migration) code

[[2026-03-16]] Mon 14:54

## Test-Writer Notes\n- Test file: tests/test_web_search.py\n- Classes: TestFromAC_ExtractContentMigration (2 new tests) + 7 in-place updates\n- Total: 9 tests failing against pre-migration code\n- AC1: 7 trafilatura mocks replaced with extract_content returning ExtractionResult\n- AC2: test_success_path_does_not_double_wrap - asserts wrap_untrusted_content not called\n- AC3: test_fallback_path_applies_wrap_untrusted_content - asserts wrap called on fallback\n- AC4: all 9 fail with AttributeError (extract_content not present on web_search module)\n- ruff: clean

[[2026-03-16]] Mon 20:47

## Builder Notes

- Files changed: src/owlbear/tools/web_search.py
- Tests: 9/9 targeted migration tests passed; 37 passed in tests/test_web_search.py
- Coverage: src/owlbear/tools/web_search.py 98% (scoped run)
- Lint: ruff check passed
- Evidence: RED before fix (9 failed with AttributeError: missing extract_content); GREEN after fix (9 passed)
- Fixes applied: Replaced direct trafilatura.extract call with extract_content(...).text; prevent double-wrap on successful extraction; keep wrap_untrusted_content for raw-HTML fallback only

[[2026-03-16]] Mon 21:05

## Review Evidence

### Test Results

- pytest: 37 passed, 0 failed (tests/test_web_search.py)

### Lint Results

- ruff: All checks passed!

### Coverage

- src/owlbear/tools/web_search.py: 98% (lines 36, 155 uncovered â€” import fallback and re-raise, not task-related)

### Pass 1 â€” CRITICAL

#### Security Review

- No hardcoded secrets
- No injection risks (extract_content receives httpx response.text, URL safety check in place)
- No path traversal, insecure deserialization, or eval
- No new dependencies added (extract_content already in codebase)
- No secret leakage in logs/errors
- **No security issues found**

#### Test Integrity (TestFromAC classes)

Builder made **zero changes** to tests/test_web_search.py (confirmed via `git diff f5bff0c..8f9620d -- tests/test_web_search.py` = empty). All test modifications are by the test-writer in uncommitted changes. TestFromAC class untouched.

`| Original Test | Change Made | Assessment |`
`| TestFromAC_ExtractContentMigration::test_success_path_does_not_double_wrap | No builder change | PRESERVED |`
`| TestFromAC_ExtractContentMigration::test_fallback_path_applies_wrap_untrusted_content | No builder change | PRESERVED |`

#### Test Quality

`| Dimension | Rating | Evidence |`
`| Assertion specificity | STRONG | Exact value checks, mock_wrap.assert_not_called(), mock_wrap.assert_called_once(), specific ExtractionResult comparisons |`
`| Negative/error paths | ADEQUATE | Blocked URLs, empty extraction fallback, HTTP errors, timeout, rate limiting all covered |`
`| Mutation reasoning | STRONG | Early-return removal caught by assert_not_called; wrap removal caught by assert_called_once |`
`| Test independence | STRONG | Each test creates own toolset, monkeypatch for env overrides, no shared mutable state |`
`| Descriptive names | STRONG | test_success_path_does_not_double_wrap, test_fallback_path_applies_wrap_untrusted_content |`

#### Data Safety

- No LLM output persisted, no race conditions, no atomicity concerns
- max_length cap prevents unbounded output
- **No data safety issues found**

### Pass 2 â€” INFORMATIONAL

- Redundant `if not content:` guard after `if content: return ...` early return â€” always true at that point. Cosmetic; does not affect behavior.
- Double `content[:max_length]` truncation on fallback path (redundant but harmless).

### AC Compliance

`| AC Line | Evidence | Mapped Test | Status |`
`| (1) 7 trafilatura mocks replaced with extract_content mocks | git diff shows 7 mock swaps from trafilatura to extract_content returning ExtractionResult | All 7 TestWebRead/TestWebReadRetry tests | PASS |`
`| (2) Test: success path no double-wrap | test_success_path_does_not_double_wrap asserts mock_wrap.assert_not_called() | TestFromAC_ExtractContentMigration::test_success_path_does_not_double_wrap | PASS |`
`| (3) Test: fallback applies wrap_untrusted_content | test_fallback_path_applies_wrap_untrusted_content asserts mock_wrap.assert_called_once() | TestFromAC_ExtractContentMigration::test_fallback_path_applies_wrap_untrusted_content | PASS |`
`| (4) All updated tests FAIL pre-migration | Builder notes confirm 9 AttributeError failures pre-fix; all 9 pass post-fix | All 9 migration tests | PASS |`

### Verdict: PASS (.93)

### Action Taken

kanban edit 842 --status docs --release

[[2026-03-16]] Mon 21:37

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal refactoring; no new user-facing behavior or API |
| 2 | Docstrings | Yes | Pass | All public methods/classes in web_search.py have accurate docstrings: WebSearchToolset,_web_search,_web_read |
| 3 | sources/overview.md | No | N/A | Internal refactoring; no new external patterns adopted |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | TDD task; no research phase |

### Files Updated

- None

### Scratch Files Cleaned

- None (no scratch files created)

[[2026-03-17]] Tue 00:11

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| (1) 7 trafilatura mocks replaced with extract_content mocks returning ExtractionResult | grep confirms 0 `patch.*trafilatura` remain; 7 `patch(owlbear.tools.web_search.extract_content)` at lines 266, 301, 313, 372, 382, 480, 531; all return ExtractionResult | PASS |
| (2) Test: success path no double-wrap | `test_success_path_does_not_double_wrap` (L557) asserts `mock_wrap.assert_not_called()` | PASS |
| (3) Test: fallback applies wrap_untrusted_content | `test_fallback_path_applies_wrap_untrusted_content` (L575) asserts `mock_wrap.assert_called_once()` | PASS |
| (4) All updated tests FAIL pre-migration | Builder notes confirm 9 AttributeError failures pre-fix; all 9 pass post-fix (37 total passed) | PASS |

### Test Results

- pytest (tests/test_web_search.py): 37 passed, 0 failed (12.21s)
- Full suite: 6 collection errors from pre-existing circular import in owlbear.core.retry (task #814, commit 604b2df) â€” NOT caused by #842
- ruff: All checks passed

### Quality Gaps

- Test-writer did not commit tests/test_web_search.py â€” orphaned in working tree. Auditor will commit as leftover.

### Confidence: .97

### Action: archive
