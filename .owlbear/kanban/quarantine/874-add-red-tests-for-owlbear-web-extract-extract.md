---
id: 874
title: Add RED tests for owlbear.web_extract.extract_markdown
status: archived
priority: nice-to-have
created: 2026-03-20T14:58:49.003187+01:00
updated: 2026-03-21T06:00:39.9759429+01:00
started: 2026-03-21T05:59:59.5024556+01:00
completed: 2026-03-21T05:59:59.5024556+01:00
tags:
    - test
    - type:test
    - scope:core
    - phase-9
    - dry
class: standard
---

TDD RED phase for #868. Add focused tests for src/owlbear/web_extract.py covering successful markdown extraction, url forwarding, empty-string fallback when trafilatura.extract returns None or raises, and actionable ImportError behavior when trafilatura is missing. Source: docs/research/leaf-markdown-extraction-helper.md. AC: (1) focused helper tests exist, (2) success and url-forwarding cases patch the helper's trafilatura seam and assert markdown + url behavior, (3) None/exception paths assert empty-string fallback, (4) missing-dependency path asserts actionable ImportError, (5) scoped tests fail before #868 is implemented.

[[2026-03-20]] Fri 16:31

## Research

- Research doc: docs/research/web-extract-extract-markdown-red-task.md
- External attribution updated: docs/sources/overview.md
- Key finding: #874 already targets the correct helper boundary; helper tests should own the trafilatura markdown/include_links/url assertions plus the empty-string fallback and actionable ImportError coverage.
- Key finding: #875 is missing a paired RED task because tests/test_content_extractor.py still asserts the soon-to-be-replaced raw trafilatura seam.
- Follow-up created: #881 - Update content_extractor tests to mock extract_markdown delegation
- Command executed: kanban\kanban-md.exe create Update content_extractor tests to mock extract_markdown delegation -> #881

[[2026-03-20]] Fri 17:46

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |

|---------|------------|--------|

| 1. Focused helper tests exist | PARTIAL - the task identified the correct helper boundary, but it did not pin the test file or explicitly exclude downstream caller rewires. | Refined the binding contract below to target tests/test_web_extract.py and keep #875, #825, and #873 out of scope. |

| 2. Success and url-forwarding cases patch the helper seam | PARTIAL - the seam was correct, but the exact call shape and default-url behavior were still implicit. | Refined below to require one helper-local trafilatura.extract(...) call plus separate default-url and provided-url assertions. |

| 3. None/exception paths assert empty-string fallback | SOUND - this matches the helper contract defined for #868. | Kept and made both fallback branches explicit in the binding contract below. |

| 4. Missing-dependency path asserts actionable ImportError | PARTIAL - the boundary was correct, but the import-denial seam and install-hint expectation needed to stay narrow and explicit. | Refined below to require a helper-boundary import-denial seam and actionable install hint. |

| 5. Scoped tests fail before #868 is implemented | SOUND - this is the correct RED gate for a type:test task paired to #868. | Kept as an explicit current-HEAD failure requirement. |

### Refined AC Contract

1. tests/test_web_extract.py adds focused tests for extract_markdown(html, url=None) at the helper boundary and does not broaden into downstream caller rewires tracked separately by #875, #825, and #873.

2. Success-path cases patch the helper-local trafilatura lookup used by extract_markdown() and assert one call to trafilatura.extract(html, output_format=markdown, include_links=True, url=url) plus raw markdown return behavior.

3. A default-url case asserts the helper forwards url=None, and a url-forwarding case asserts a provided URL is passed through unchanged.

4. trafilatura.extract returning None and trafilatura.extract raising an exception each yield an empty string from extract_markdown() without surfacing the extraction error.

5. A missing-dependency case uses a narrow import-denial seam at the helper boundary and asserts extract_markdown() raises an actionable ImportError with the install hint expected by #868.

6. The newly added cases fail against current HEAD before #868 is implemented.

### Architecture Notes

Leaf-module precedent already exists in src/owlbear/paths.py and tests/test_paths.py, so a dedicated helper test file is the correct seam.

src/owlbear/tools/browser/content_extractor.py currently owns the raw trafilatura markdown call plus metadata and wrapping behavior, and tests/test_content_extractor.py currently pins that call shape; #874 should move only the helper-owned raw extraction assertions to the new helper suite while #881 keeps the downstream delegation rewrite separate.

tests/test_bookmark_pipeline.py already shows the narrow actionable ImportError pattern that this helper-boundary RED task should follow.

### Changes Made

- Approved the task with a binding refined AC contract captured in this review section.

- Kept downstream caller rewires out of scope because they already have separate tasks (#875, #825, #873, and RED follow-up #881).

- Advanced #874 from backlog to todo.

### Dependencies

- Verified: #868 already depends on #874 as its RED predecessor.

- Verified: #881 covers the later content_extractor delegation seam after #875.

- Verified: package-root leaf precedent exists in src/owlbear/paths.py and tests/test_paths.py.

[[2026-03-20]] Fri 18:34

## Test-Writer Notes

- Test file: tests/test_web_extract.py
- Classes: TestFromAC_ExtractMarkdownSuccess, TestFromAC_ExtractMarkdownUrlForwarding, TestFromAC_ExtractMarkdownFallback, TestFromAC_ExtractMarkdownMissingDependency
- Tests per category: happy 3, edge 2, error 3, boundary 4 (url cases + missing dep)
- Total: 13 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear.web_extract') ✓
- ruff: clean (N801 added to tests per-file-ignores in pyproject.toml)
- AC coverage:
  AC1: class scope restricts to tests/test_web_extract.py helper boundary only
  AC2: TestFromAC_ExtractMarkdownSuccess — patches owlbear.web_extract.trafilatura, asserts single call with output_format=markdown, include_links=True, url=url, and raw string return
  AC3: TestFromAC_ExtractMarkdownUrlForwarding — url=None default and provided URL forward each get dedicated assert_called_once_with assertions
  AC4: TestFromAC_ExtractMarkdownFallback — None return and raised exception both assert result == '' and no re-raise
  AC5: TestFromAC_ExtractMarkdownMissingDependency — builtins.**import** denial seam; asserts ImportError with owlbear[search] and uv in message
  AC6: all tests fail against current HEAD before #868 is implemented ✓

[[2026-03-21]] Sat 04:32

## Builder Notes

- Files changed: src/owlbear/web_extract.py (new, 52 lines)
- Tests: 13 passed, 100% coverage on src/owlbear/web_extract.py (17 stmts, 0 missed)
- Lint: ruff clean (src + tests)
- Evidence: 13 passed in 0.10s; web_extract.py 17 stmts 0 miss 100%
- Design: module-level try/except sets trafilatura=None when not installed; function captures module global (_traf=trafilatura) so @patch works; lazy import only when_traf is None for builtins.**import** denial seam
- Fixes applied: None — all 13 TestFromAC_* tests pass as written

[[2026-03-21]] Sat 04:53

## Review Evidence

## Review: #874 - Add RED tests for owlbear.web_extract.extract_markdown

### Test Results

- pytest command: uv run pytest tests/test_web_extract.py -q --tb=short
- Result: 13 passed, 2 warnings in 0.10s.
- Warning detail: optional qdrant tests skipped because qdrant_client is not installed.

### Lint Results

- ruff command: uv run ruff check src/owlbear/web_extract.py tests/test_web_extract.py --output-format=full
- Result: All checks passed.

### Coverage

- coverage command: uv run pytest tests/test_web_extract.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: src/owlbear/web_extract.py -> 17 statements, 0 missed, 100% coverage.
- Note: an initial foreground coverage run ended with a transient KeyboardInterrupt in coverage sqlite write; rerun in an isolated background terminal completed cleanly with exit code 0.

### Pass 1 - CRITICAL

#### Security Review

- Hardcoded secrets: none found in src/owlbear/web_extract.py or tests/test_web_extract.py.
- Injection/path traversal/deserialization/eval/exec: none found; function only forwards html/url into trafilatura.extract.
- Input validation and boundary safety: no dangerous sinks introduced; html/url are forwarded as plain values.
- Dependency risk: no new dependencies introduced by this task.
- Secret leakage in errors/logs: ImportError message contains install guidance only (no secrets/PII).

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ExtractMarkdownSuccess::test_returns_extracted_markdown | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownSuccess::test_calls_trafilatura_with_correct_kwargs | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownSuccess::test_exactly_one_trafilatura_extract_call | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownUrlForwarding::test_default_url_is_none | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownUrlForwarding::test_provided_url_forwarded_unchanged | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownUrlForwarding::test_url_forwarding_does_not_affect_return_value | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_returns_empty_string_when_extract_returns_none | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_returns_empty_string_when_extract_raises | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_does_not_surface_extraction_exception | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownFallback::test_empty_string_not_none_on_none_extract | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownMissingDependency::test_raises_import_error_when_trafilatura_missing | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownMissingDependency::test_import_error_contains_owlbear_search_install_hint | No change observed against test-writer contract | PRESERVED |
| TestFromAC_ExtractMarkdownMissingDependency::test_import_error_message_references_uv | No change observed against test-writer contract | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact kwargs checks (tests/test_web_extract.py:41, tests/test_web_extract.py:69, tests/test_web_extract.py:82) and exact fallback assertions (tests/test_web_extract.py:110, tests/test_web_extract.py:117); one supplemental broad assertion remains in tests/test_web_extract.py:134. |
| Negative/error paths | STRONG | Dedicated None, exception, and missing-dependency paths (tests/test_web_extract.py:106, tests/test_web_extract.py:113, tests/test_web_extract.py:146, tests/test_web_extract.py:162, tests/test_web_extract.py:177). |
| Mutation reasoning | STRONG | Mutating extract kwargs/output_format/include_links/url or dropping empty-string fallback would fail call/assertion tests and fallback tests. |
| Test independence | STRONG | Per-test patch contexts isolate state; no shared mutable fixtures. |
| Descriptive names | STRONG | Test names encode scenario and expectation across all four TestFromAC classes. |

#### Data Safety

- No data-safety issues found: no persistence, no transaction/state mutation, no concurrency primitives, and no unbounded resource loops introduced.

### Pass 2 - INFORMATIONAL

- Missing-dependency tests are environment-sensitive to whether trafilatura is available at module import time. To make these tests deterministic across environments with search extras installed, consider patching owlbear.web_extract.trafilatura to None inside the missing-dependency tests before invoking extract_markdown.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Focused helper tests exist in tests/test_web_extract.py and stay at helper boundary | Module docstring explicitly scopes to helper boundary and excludes downstream rewires (tests/test_web_extract.py:1) | TestFromAC_* classes in tests/test_web_extract.py | PASS |
| 2. Success path patches helper-local trafilatura and asserts one extract call with markdown/include_links/url plus raw return | Patched helper seam and exact kwargs/call count assertions (tests/test_web_extract.py:29, tests/test_web_extract.py:41, tests/test_web_extract.py:49); implementation call shape (src/owlbear/web_extract.py:49, src/owlbear/web_extract.py:50, src/owlbear/web_extract.py:51) | test_returns_extracted_markdown; test_calls_trafilatura_with_correct_kwargs; test_exactly_one_trafilatura_extract_call | PASS |
| 3. Default url=None and provided URL are forwarded unchanged | Dedicated url=None and provided-url assertions (tests/test_web_extract.py:65, tests/test_web_extract.py:69, tests/test_web_extract.py:77, tests/test_web_extract.py:82) | test_default_url_is_none; test_provided_url_forwarded_unchanged | PASS |
| 4. None return and raised exception both produce empty string without surfacing extraction error | Exact empty-string assertions and no re-raise test (tests/test_web_extract.py:106, tests/test_web_extract.py:110, tests/test_web_extract.py:113, tests/test_web_extract.py:117, tests/test_web_extract.py:120); implementation fallback (src/owlbear/web_extract.py:53, src/owlbear/web_extract.py:54) | test_returns_empty_string_when_extract_returns_none; test_returns_empty_string_when_extract_raises; test_does_not_surface_extraction_exception | PASS |
| 5. Missing dependency path asserts actionable ImportError install hint | Import-denial seam and ImportError assertions for owlbear[search] and uv (tests/test_web_extract.py:146, tests/test_web_extract.py:162, tests/test_web_extract.py:175, tests/test_web_extract.py:177, tests/test_web_extract.py:190); actionable message in implementation (src/owlbear/web_extract.py:42) | test_raises_import_error_when_trafilatura_missing; test_import_error_contains_owlbear_search_install_hint; test_import_error_message_references_uv | PASS |
| 6. Added cases failed before #868 implementation | Task history Test-Writer Notes records: Total 13 tests, all FAIL with ModuleNotFoundError before implementation | Entire TestFromAC suite (historical RED evidence in task body) | PASS |

### Verdict: PASS

- Confidence: .94

[[2026-03-21]] Sat 05:59

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Focused helper tests in tests/test_web_extract.py | Module docstring L1-7 scopes to helper boundary, excludes downstream. 4 TestFromAC classes, 13 tests. | PASS |
| 2. Success path patches trafilatura, asserts kwargs + return | Tests L29-56 assert extract(html, output_format=markdown, include_links=True, url=url), call_count==1, raw return. Impl L49-51 matches. | PASS |
| 3. Default url=None and provided URL forwarded | Tests L65-90: default_url_is_none assert url=None; provided_url_forwarded_unchanged asserts exact URL passthrough. | PASS |
| 4. None/exception fallback to empty string | Tests L106-134: 4 tests cover None return, RuntimeError, ValueError, type check. Impl L48-55 try/except + or-empty. | PASS |
| 5. Missing-dependency import-denial seam | Tests L146-192: 3 tests deny builtins.**import**, assert ImportError with owlbear[search] and uv. Impl L38-43 matches. | PASS |
| 6. Tests failed before #868 implementation | Task body TW notes: 13 FAIL with ModuleNotFoundError before impl. RED gate confirmed. | PASS |

### Test Results

- pytest tests/test_web_extract.py: 13 passed, 0 failed (0.10s)
- Full suite (--ignore=test_security_audit_log.py): 3689 passed, 92 failed (all pre-existing)
- ruff: All checks passed

### Confidence: .97

### Action: archive

[[2026-03-21]] Sat 06:00

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 165702d | feat | src/owlbear/web_extract.py, tests/test_web_extract.py | #874 |
