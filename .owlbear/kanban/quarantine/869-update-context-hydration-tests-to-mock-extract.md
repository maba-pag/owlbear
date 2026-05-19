---
id: 869
title: Update context_hydration tests to mock extract_markdown instead of trafilatura
status: archived
priority: nice-to-have
created: 2026-03-20T14:00:24.2631055+01:00
updated: 2026-03-23T22:45:56.903861+01:00
started: 2026-03-23T22:44:48.4152491+01:00
completed: 2026-03-23T22:44:48.4152491+01:00
tags:
    - test
    - type:test
    - scope:core
    - phase-9
    - dry
depends_on:
    - 868
class: standard
---

TDD RED phase for #873 after #868. Update fetch_url-related tests in tests/test_context_hydration.py and tests/test_content_safety_integration.py so they patch owlbear.core.context_hydration.extract_markdown instead of patching trafilatura through sys.modules. Preserve wrapping assertions by returning raw markdown from helper mocks; #868 keeps helper output raw and unwrapped. Source: docs/research/context-hydration-extract-markdown-test-seam.md.

## AC

- All 4 direct trafilatura mocks in tests/test_context_hydration.py are replaced with module-local extract_markdown mocks
- All 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced with the same module-local extract_markdown mocks
- Existing fetch_url wrapping and contrast assertions continue to use raw markdown return values rather than wrapped helper output
- All updated tests FAIL against current pre-#873 code

[[2026-03-20]] Fri 14:48

## Research

- Research doc: docs/research/context-hydration-extract-markdown-red-task.md
- External attribution updated: docs/sources/overview.md
- Key finding: #869 is the correct RED seam after #868 because tests should patch the name used by context_hydration.py, not keep patching sys.modules[trafilatura].
- Key finding: raw helper-return mocks preserve the current wrapping and contrast assertions because fetch_url() still owns the local wrapping branch.
- Key finding: #869 was missing a valid GREEN partner because #826 remains blocked on the illegal core -> tools extract_content plan.
- Follow-up created: #873 - Migrate context_hydration.py to use web_extract.extract_markdown
- Recommendation: architect should pair #869 with #868 and #873, not with stale task #826.
- Command executed: kanban\kanban-md.exe create Migrate context_hydration.py to use web_extract.extract_markdown -> #873

[[2026-03-20]] Fri 15:21

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| All 4 direct trafilatura mocks in tests/test_context_hydration.py are replaced with module-local extract_markdown mocks | Precise and mechanically checkable; matches the 4 live sys.modules seams in tests/test_context_hydration.py and the module-local patching rule from unittest.mock. | Keep |
| All 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced with the same module-local extract_markdown mocks | Precise and bounded to the fetch_url-related sites; excludes unrelated web_search and bookmark assertions in the same file. | Keep |
| Existing fetch_url wrapping and contrast assertions continue to use raw markdown return values rather than wrapped helper output | Verifiable and architecture-relevant: preserves the current ownership split where fetch_url() wraps locally while the helper remains raw. | Keep |
| All updated tests FAIL against current pre-#873 code | Correct RED-phase criterion for a type:test task; replaces the incorrect GREEN-style pass condition and mirrors task #842's migration pattern. | Rewrote |

### Architecture Notes

- Current production seam is still the local trafilatura import in src/owlbear/core/context_hydration.py::fetch_url, so the RED task must target the future module-local helper seam rather than keep patching sys.modules.
- Existing precedent is task #842 and tests/test_web_search.py: once a caller migrates to a helper import, tests patch the name used by the caller module.
- #826 remains blocked because core cannot import from tools; #873 is the valid GREEN partner for this RED task.
- This stays single-domain and test-only. No new security surface or cross-layer dependency is introduced by the task itself.
- Failure mode map skipped: test-only task, no new production codepath.

### Changes Made

- Rewrote task body to pair the RED work with #873 instead of stale task #826
- Replaced the final AC line with an explicit RED-phase failure criterion
- Added depends_on: #868 so the helper contract is treated as a prerequisite
- Appended architecture review notes
- Prepared task for backlog -> todo transition

### Dependencies

- Added: #868 as prerequisite helper task
- Verified: #873 exists as the legal GREEN successor for this RED task
- Verified: #826 remains blocked and must not be treated as the implementation partner

[[2026-03-23]] Mon 12:22

## Test-Writer Notes

- Test file (context_hydration): tests/test_context_hydration.py
- Test file (content_safety): tests/test_content_safety_integration.py
- Classes: TestFromAC_ExtractMarkdownSeam (context_hydration), TestFromAC_FetchUrlWrapsByExtractMarkdown (content_safety)
- Tests per category: happy 5, edge 0, error 2, boundary 2
- Total: 9 tests
- ruff: clean
- Implementation note: Task #876 (committed as b32ef27) implemented the
  extract_markdown delegation in context_hydration.py BEFORE these RED tests
  were written.  The tests pass immediately against current code.
  They would fail with AttributeError against pre-#876 code (no create=True).
  That is the intended RED failure mode — the seam now exists.

AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| 4 trafilatura mocks in test_context_hydration.py replaced | TestFromAC_ExtractMarkdownSeam (4 tests) | happy+error |
| 5 fetch_url trafilatura mocks in test_content_safety_integration.py replaced | TestFromAC_FetchUrlWrapsByExtractMarkdown (5 tests) | happy+error+boundary |
| Raw markdown from helper preserves wrapping assertions | test_wraps_raw_extract_markdown_output, test_wrapping_disabled... | happy |
| Tests FAIL pre-#873 code | All 9 fail with AttributeError if import missing (no create=True) | RED |

[[2026-03-23]] Mon 17:04

## Review Evidence

## Review: #869 - Update context_hydration tests to mock extract_markdown instead of trafilatura

### Test Results

- pytest (task files): `uv run pytest tests/test_context_hydration.py tests/test_content_safety_integration.py -q --tb=short` -> 68 passed, 2 failed.
  - Failing tests are unrelated to #869 AC classes: `tests/test_content_safety_integration.py::TestFromACWebReadWrapping::{test_wraps_return_value,test_skips_wrapping_when_disabled}` fail with `AttributeError` patching `owlbear.tools.web_search.trafilatura`.
- pytest (AC-scoped): `uv run pytest tests/test_context_hydration.py::TestFromAC_ExtractMarkdownSeam tests/test_content_safety_integration.py::TestFromAC_FetchUrlWrapsByExtractMarkdown -q --tb=short` -> 9 passed, 0 failed.

### Lint Results

- task-scoped ruff: `uv run ruff check tests/test_context_hydration.py tests/test_content_safety_integration.py` -> All checks passed.
- full ruff (informational): `uv run ruff check src/ tests/` -> 216 errors (`RUF100` unused `noqa` directives; pre-existing broad lint debt outside this task scope).

### Coverage

- command: `uv run pytest tests/test_context_hydration.py::TestFromAC_ExtractMarkdownSeam tests/test_content_safety_integration.py::TestFromAC_FetchUrlWrapsByExtractMarkdown --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/core/context_hydration.py`: 32%
- `src/owlbear/web_extract.py`: 69%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All 4 direct trafilatura mocks in `tests/test_context_hydration.py` replaced with module-local extract_markdown mocks | `tests/test_context_hydration.py::TestFromAC_ExtractMarkdownSeam` (4 tests) | **No**. Legacy direct trafilatura patches still exist at `tests/test_context_hydration.py:163`, `:252`, `:585`, `:622`; tests do not assert those old seams were removed. | **MISSING** |
| All 5 fetch_url-related trafilatura mocks in `tests/test_content_safety_integration.py` replaced with module-local extract_markdown mocks | `tests/test_content_safety_integration.py::TestFromAC_FetchUrlWrapsByExtractMarkdown` (5 tests) | **No**. Legacy fetch_url-related trafilatura patches still remain at `tests/test_content_safety_integration.py:270`, `:298`, `:327`, `:336`, `:379`, `:449`. | **MISSING** |
| Existing fetch_url wrapping and contrast assertions continue to use raw markdown return values | `TestFromAC_FetchUrlWrapsByExtractMarkdown::{test_wraps_raw_extract_markdown_output,test_fetch_url_wraps_while_bookmark_does_not_contrast,test_none_from_extract_markdown_not_wrapped}` | Yes. Tests set raw helper returns and assert wrapping/contrast behavior directly (`tests/test_content_safety_integration.py:576-704`). | COVERED |
| All updated tests FAIL against current pre-#873 code | module-local patches without `create=True` in new #869 classes | Yes. Pre-#873 module does not expose `extract_markdown` (`git show b32ef27^:src/owlbear/core/context_hydration.py` has no symbol; `git show b32ef27:...` adds import/call), so patching module-local name would raise `AttributeError`. | COVERED |

#### Security Review

- No security regressions found (test-only scope).

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing legacy `TestFromACFetchUrl` / `TestFromAC_FetchUrlExtractMarkdownForwarding` tests | No weakening/removal detected; legacy tests remain present with direct trafilatura seams | PRESERVED |
| New #869 class in `tests/test_context_hydration.py` | Added as **unstaged** working-tree diff (`git diff -- tests/test_context_hydration.py`) rather than committed artifact | PRESERVED (with provenance gap) |
| Existing `TestFromAC_FetchUrlExtractMarkdownSeam` in `tests/test_content_safety_integration.py` | Formatting-only assert line change in commit `9326eb4`; semantics unchanged | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | New #869 tests assert concrete call args, marker propagation, wrap tags, and empty-string behavior. |
| Negative/error paths | ADEQUATE | Includes `None` helper return and wrap-disabled path coverage. |
| Mutation reasoning | **WEAK** | If old direct trafilatura seams remain (current state), #869 tests still pass; no assertion enforces replacement/removal contract. |
| Test independence | STRONG | Isolated mocks/fixtures, no cross-test shared state dependency seen. |
| Descriptive names | STRONG | Scenario-oriented names in #869 classes clearly map to expected behavior. |

#### Data Safety

- No data-safety issues found (test-only changes).

#### Implementation-Aware Test Gaps

- AC is replacement-oriented, but implementation currently adds parallel #869 tests without removing legacy trafilatura seam tests. This leaves old seam behavior still represented and fails the explicit replacement requirement.

### Pass 2 - INFORMATIONAL

- Broad two-file pytest run has 2 unrelated failures in older web_search wrapping tests; #869 AC-scoped classes pass.
- Full-repo ruff currently has broad pre-existing `RUF100` debt not tied to #869-scoped files.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Replace all 4 direct trafilatura mocks in `tests/test_context_hydration.py` | Legacy direct mocks still present at `tests/test_context_hydration.py:163,252,585,622` | `TestFromAC_ExtractMarkdownSeam` | **FAIL** |
| Replace all 5 fetch_url-related trafilatura mocks in `tests/test_content_safety_integration.py` | Legacy fetch_url-related direct mocks still present at `tests/test_content_safety_integration.py:270,298,327,336,379,449` | `TestFromAC_FetchUrlWrapsByExtractMarkdown` | **FAIL** |
| Preserve wrapping/contrast assertions using raw helper return values | Raw mock returns used and wrapped/contrast behavior asserted in #869 class (`tests/test_content_safety_integration.py:576-704`) | `TestFromAC_FetchUrlWrapsByExtractMarkdown` | PASS |
| Updated tests fail against pre-#873 code | Pre-#873 module lacks `extract_markdown` symbol; #869 tests patch module-local seam without `create=True` | #869 classes in both files | PASS |

### Verdict: FAIL

### Action Taken

- Move task from `review` to `todo` for AC1/AC2 replacement gaps and uncommitted #869 artifact in `tests/test_context_hydration.py`.

[[2026-03-23]] Mon 17:17

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL cited MISSING for AC1/AC2 — new tests added for replacement enforcement
- New test file: tests/test_869_seam_contract.py
- Classes: TestFromAC_ReplacedTrafilaturaSeamContextHydration, TestFromAC_ReplacedTrafilaturaSeamContentSafety
- Tests per category: error 9 (all asserting absence of legacy seam)
- Total new: 9 tests, all FAIL (AssertionError) against current code
- ruff: clean
- Approach: AST-based meta-tests that inspect peer test files; FAIL while legacy sys.modules trafilatura patches exist; PASS once builder removes them
- Preserved: existing TestFromAC_ExtractMarkdownSeam / TestFromAC_FetchUrlWrapsByExtractMarkdown tests (9 from prior cycle, all PASS)
- AC coverage:
  AC1 (4 replaced in test_context_hydration.py):
    TestFromACFetchUrl::test_successful_fetch_returns_content -> test_ac1_fetch_url_success_no_sys_modules_trafilatura (FAIL)
    TestFromACFetchUrl::test_url_checker_allows_url -> test_ac1_fetch_url_checker_allows_no_sys_modules_trafilatura (FAIL)
    TestFromAC_FetchUrlExtractMarkdownForwarding::test_forwards_html_body -> test_ac1_forwarding_html_url_no_sys_modules_trafilatura (FAIL)
    TestFromAC_FetchUrlExtractMarkdownForwarding::test_helper_return_propagates -> test_ac1_forwarding_result_propagates_no_sys_modules_trafilatura (FAIL)
  AC2 (5 replaced in test_content_safety_integration.py):
    TestFromACFetchUrlWrapping::test_wraps_return_value -> test_ac2_wraps_return_value_no_sys_modules_trafilatura (FAIL)
    TestFromACFetchUrlWrapping::test_wraps_with_source_url_attribute -> test_ac2_wraps_source_url_no_sys_modules_trafilatura (FAIL)
    TestFromACFetchUrlWrapping::test_skips_wrapping_when_disabled -> test_ac2_skips_wrapping_when_disabled_no_sys_modules_trafilatura (FAIL)
    TestFromACBookmarkPipelineExcluded::test_default_web_read_does_not_wrap -> test_ac2_bookmark_contrast_has_module_local_for_fetch_url_side (FAIL)
    TestFromAC_FetchUrlExtractMarkdownSeam::test_fetch_url_forwards_to_helper -> test_ac2_extract_markdown_seam_no_sys_modules_trafilatura (FAIL)

[[2026-03-23]] Mon 18:10

## Builder Notes

- Files changed: tests/test_context_hydration.py, tests/test_content_safety_integration.py
- Changes: Replaced 4 sys.modules trafilatura patches in test_context_hydration.py and 5 in test_content_safety_integration.py with module-local patch('owlbear.core.context_hydration.extract_markdown') without create=True
- Tests: 9 seam contract tests passed (test_869_seam_contract.py); full file runs: 68 passed / 2 pre-existing failures in TestFromACWebReadWrapping (unrelated, pre-existing: owlbear.tools.web_search.trafilatura AttributeError)
- Coverage: seam contract tests pass; AC-scoped TestFromAC classes all pass
- Lint: ruff clean (tests/test_context_hydration.py, tests/test_content_safety_integration.py, tests/test_869_seam_contract.py)
- Evidence: all 9 TestFromAC_ReplacedTrafilaturaSeam* tests green; commit 3ea0413
- Fixes applied: replaced 4+5 legacy sys.modules trafilatura seams with module-local extract_markdown patches; removed create=True from forwarding tests; removed dangling mock_trafilatura vars

[[2026-03-23]] Mon 18:34

## Review Evidence

## Review: #869 - Update context_hydration tests to mock extract_markdown instead of trafilatura

### Test Results

- `uv run pytest tests/test_869_seam_contract.py -q --tb=short` -> 9 passed, 0 failed, 2 warnings.
- `uv run pytest tests/test_context_hydration.py::TestFromAC_ExtractMarkdownSeam tests/test_content_safety_integration.py::TestFromAC_FetchUrlWrapsByExtractMarkdown tests/test_869_seam_contract.py -q --tb=short` -> 18 passed, 0 failed, 2 warnings.
- `uv run pytest tests/test_context_hydration.py tests/test_content_safety_integration.py tests/test_869_seam_contract.py -q --tb=short` -> 77 passed, 2 failed, 2 warnings.
  - Unrelated failures (outside #869 AC classes): `TestFromACWebReadWrapping::test_wraps_return_value` and `TestFromACWebReadWrapping::test_skips_wrapping_when_disabled` still patch `owlbear.tools.web_search.trafilatura` and raise `AttributeError`.

### Lint Results

- Task-scoped: `uv run ruff check tests/test_context_hydration.py tests/test_content_safety_integration.py tests/test_869_seam_contract.py` -> All checks passed.
- Repo baseline: `uv run ruff check src/ tests/` -> 224 pre-existing `RUF100` findings in unrelated files.

### Coverage

- `uv run pytest tests/test_context_hydration.py::TestFromAC_ExtractMarkdownSeam tests/test_content_safety_integration.py::TestFromAC_FetchUrlWrapsByExtractMarkdown tests/test_869_seam_contract.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> 18 passed.
- Informational coverage snapshot from this scoped run: `src/owlbear/core/context_hydration.py` 32%, `src/owlbear/web_extract.py` 69%, overall 7% (bare `--cov` project-wide artifact).
- Coverage is informational here because #869 is test-only; no source modules were changed by builder commit `3ea0413`.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1: replace 4 direct trafilatura mocks in `tests/test_context_hydration.py` | `TestFromAC_ReplacedTrafilaturaSeamContextHydration::*` (`tests/test_869_seam_contract.py:115`, `:137`, `:156`, `:180`) | Yes. AST checks fail if any target method still has `patch.dict(sys.modules, {trafilatura: ...})` or lacks module-local seam patch. | COVERED |
| AC2: replace 5 fetch_url-related trafilatura mocks in `tests/test_content_safety_integration.py` | `TestFromAC_ReplacedTrafilaturaSeamContentSafety::*` (`tests/test_869_seam_contract.py:224`, `:243`, `:262`, `:282`, `:307`) | Yes. AST checks fail on legacy seam presence or missing module-local seam in named methods. | COVERED |
| AC3: preserve wrapping/contrast assertions with raw helper returns | `TestFromAC_FetchUrlWrapsByExtractMarkdown::*` (`tests/test_content_safety_integration.py:548`) | Yes. Tests assert wrapped default, raw when disabled, fetch_url-vs-bookmark contrast, and `None` -> empty string using raw helper returns. | COVERED |
| AC4: updated tests fail on pre-#873 code | Module-local patches without `create=True` in new AC classes (`tests/test_context_hydration.py:748`, `tests/test_content_safety_integration.py:548`) + historical source check `pre=0 post=2` for `extract_markdown` symbol in `context_hydration.py` around commit `b32ef27` | Yes. Without module attribute pre-#873, these patches raise `AttributeError` by design. | COVERED |

#### Security Review

- No security issues found. Scope is test-only and reduces risk by removing indirect seam patching in target fetch_url tests.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ReplacedTrafilaturaSeamContextHydration::*` | No change in builder commit `3ea0413` (file not touched) | PRESERVED |
| `TestFromAC_ReplacedTrafilaturaSeamContentSafety::*` | No change in builder commit `3ea0413` (file not touched) | PRESERVED |
| `TestFromACFetchUrl::test_successful_fetch_returns_content` (`tests/test_context_hydration.py:147`) | Seam changed from `sys.modules[trafilatura]` to module-local `extract_markdown`; assertions preserved | STRENGTHENED |
| `TestFromACFetchUrl::test_url_checker_allows_url` (`tests/test_context_hydration.py:230`) | Same seam replacement; assertions preserved | STRENGTHENED |
| `TestFromAC_FetchUrlExtractMarkdownForwarding::{test_forwards_html_body_and_url_to_extract_markdown,test_helper_return_propagates_to_fetch_url_result}` (`tests/test_context_hydration.py:562`, `:592`) | Removed legacy `sys.modules` backup and removed `create=True` fallback | STRENGTHENED |
| `TestFromACFetchUrlWrapping::{test_wraps_return_value,test_wraps_with_source_url_attribute,test_skips_wrapping_when_disabled}` (`tests/test_content_safety_integration.py:252`, `:279`, `:305`) | Replaced fetch_url-side seams with module-local `extract_markdown`; assertion intent preserved | STRENGTHENED |
| `TestFromACBookmarkPipelineExcluded::test_default_web_read_does_not_wrap_while_fetch_url_does` (`tests/test_content_safety_integration.py:358`) | Fetch_url side switched to module-local seam; bookmark-side contrast remains raw/no-wrap | STRENGTHENED |
| `TestFromAC_FetchUrlExtractMarkdownSeam::test_fetch_url_forwards_to_helper_and_wraps_output` (`tests/test_content_safety_integration.py:424`) | Removed legacy `sys.modules` backup and removed `create=True` | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Seam-contract tests assert exact method-level seam structure; behavior tests assert exact wrap tags, url attribute, and empty-string handling. |
| Negative/error paths | STRONG | Includes missing/None helper output, no-wrap mode, contrast path, and structural fail conditions for seam regressions. |
| Mutation reasoning | STRONG | Reintroducing legacy seam, removing module-local patch, or re-adding `create=True` would fail explicit seam-contract tests. |
| Test independence | STRONG | Tests rely on local fixtures/mocks and AST reads only; no order coupling observed. |
| Descriptive names | STRONG | Test names clearly encode seam replacement and expected behavior. |

#### Data Safety

- No data safety issues found. No runtime persistence or concurrency behavior changed.

#### Implementation-Aware Test Gaps

- No significant untested paths for #869's implemented scope. The replacement contract is now directly enforced by `tests/test_869_seam_contract.py` and behavior assertions remain covered in the fetch_url wrap/contrast classes.

### Pass 2 - INFORMATIONAL

- Two unrelated legacy wrapping tests in `tests/test_content_safety_integration.py` remain failing in broad file run due `owlbear.tools.web_search.trafilatura` patch target mismatch.
- Repo-wide `RUF100` debt remains outside #869 scope.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Replace 4 direct trafilatura mocks in `tests/test_context_hydration.py` | Target methods now patch `owlbear.core.context_hydration.extract_markdown` (`tests/test_context_hydration.py:161`, `:250`, `:583`, `:615`) | `TestFromAC_ReplacedTrafilaturaSeamContextHydration::*` | PASS |
| Replace 5 fetch_url-related trafilatura mocks in `tests/test_content_safety_integration.py` | Target methods now use module-local seam (`tests/test_content_safety_integration.py:268`, `:296`, `:325`, `:337`, `:383`, `:453`) | `TestFromAC_ReplacedTrafilaturaSeamContentSafety::*` | PASS |
| Preserve wrapping/contrast assertions with raw helper returns | Raw helper-return wrapping/contrast assertions in `TestFromAC_FetchUrlWrapsByExtractMarkdown` (`tests/test_content_safety_integration.py:548`) | `TestFromAC_FetchUrlWrapsByExtractMarkdown::*` | PASS |
| Updated tests fail on pre-#873 code | Historical source check: `context_hydration.py` `extract_markdown` refs `pre=0 post=2` around `b32ef27`; AC tests patch without `create=True` | AC classes in both files + seam-contract tests | PASS |

### Verdict: PASS

- Confidence: .94

### Action Taken

- Append review evidence and advance #869 from `review` to `docs`.

[[2026-03-23]] Mon 22:45

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| All 4 direct trafilatura mocks in test_context_hydration.py replaced | Builder commit 3ea0413; seam contract tests (TestFromAC_ReplacedTrafilaturaSeamContextHydration 4/4 pass) verify no sys.modules patches remain in target methods | PASS |
| All 5 fetch_url-related trafilatura mocks in test_content_safety_integration.py replaced | Same commit; seam contract tests (TestFromAC_ReplacedTrafilaturaSeamContentSafety 5/5 pass) verify replacement | PASS |
| Existing fetch_url wrapping and contrast assertions use raw markdown | TestFromAC_FetchUrlWrapsByExtractMarkdown (5 tests pass) covers wrap tags, source url, disabled mode, contrast, None handling | PASS |
| All updated tests FAIL against pre-#873 code | Module-local patches without create=True; pre-#876 code lacks extract_markdown symbol -> AttributeError by design | PASS |

### Test Results

- Full suite: 3963 passed, 91 failed (all pre-existing), 20 skipped
- AC-scoped (committed code, stashed working-tree changes): 18 passed, 0 failed
- No #869-specific regressions

### Lint Results

- Task-scoped ruff: all checks passed
- Repo-wide: 224 pre-existing RUF100 findings, not task-related

### Upstream Commits

- test-writer: 5ca88d5 (tests/test_869_seam_contract.py)
- builder: 3ea0413 (tests/test_context_hydration.py, tests/test_content_safety_integration.py)
- Both properly scoped to task files only

### Architect Quality

- AC specificity: Precise, mechanically checkable (specific mock counts, named files, explicit RED criterion)
- Edge case coverage: Correctly scoped to fetch_url mocks; hydrate-level mocks excluded by design
- Design direction: Correctly identified #873 as GREEN partner, rejected stale #826, added depends_on #868
- AC quality score: 5/5

### Uncommitted Working-Tree Note

- 2 task files have uncommitted working-tree edits from other work (test_869_seam_contract.py reformat, test_content_safety_integration.py bookmark_pipeline seam)
- Committed code verified separately via git stash; all 18 AC tests pass against committed state

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 22:45

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 42e7e1a | chore | kanban/tasks/869-*.md | #869 |
