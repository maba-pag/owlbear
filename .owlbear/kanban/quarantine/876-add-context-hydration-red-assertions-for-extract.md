---
id: 876
title: Add context_hydration RED assertions for extract_markdown url forwarding
status: archived
priority: nice-to-have
created: 2026-03-20T15:26:17.9701885+01:00
updated: 2026-03-23T15:31:24.4668834+01:00
started: 2026-03-23T15:30:54.6990885+01:00
completed: 2026-03-23T15:30:54.6990885+01:00
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

TDD RED supplement for #873 after #868. Add caller-level fetch_url success-path assertions in tests/test_context_hydration.py and tests/test_content_safety_integration.py. Patch owlbear.core.context_hydration.extract_markdown at the caller site, keep helper-return values raw, and prove that fetch_url() forwards both resp.text and url=url into the helper without re-testing helper-internal trafilatura kwargs. Sources: docs/research/context-hydration-web-extract-migration.md and docs/research/context-hydration-url-forwarding-red-task.md.

## AC

- tests/test_context_hydration.py contains at least one successful fetch_url() case that patches owlbear.core.context_hydration.extract_markdown, returns a raw markdown string from the mock, and asserts the helper is called exactly once with the fetched HTML body plus url=<requested URL>.
- tests/test_content_safety_integration.py contains at least one fetch_url()-related success-path case that patches the same module-local helper, returns a raw markdown string from the mock, and asserts the helper is called exactly once with the fetched HTML body plus url=<requested URL> while keeping the existing wrapping or contrast assertion meaningful.
- This task stays at the caller boundary: it does not add helper-internal trafilatura kwarg assertions, which remain owned by #874 and tests/test_web_extract.py.
- The updated scoped tests fail against pre-#873 context_hydration.py and pass once #873 imports and calls extract_markdown(resp.text, url=url).

[[2026-03-21]] Sat 05:45

## Research

- Research doc: docs/research/context-hydration-url-forwarding-red-task.md
- External attribution updated: docs/sources/overview.md
- Key finding: #869 moves the seam to context_hydration.extract_markdown but does not explicitly prove that fetch_url() forwards resp.text and url=url into the helper.
- Key finding: #874 already owns helper-internal trafilatura kwarg coverage, so #876 should stay caller-level and assert only helper forwarding plus raw helper-return behavior.
- Key finding: the current task scope is valid, but architect should tighten the AC so both tests/test_context_hydration.py and tests/test_content_safety_integration.py remain in scope instead of at least one scoped test.
- Follow-up: no new task created because #876 already captures the concrete RED supplement; splitting it further would duplicate the board action.

## Architecture Review

**Verdict:** Approved

### AC Assessment

- Scope and inline AC: valid concept, but the acceptance criteria were embedded in prose and easy to misread. Action: rewrote them into explicit RED-phase bullets.
- Single scoped test language: too loose because it could satisfy only one file and miss the direct plus integration coverage split. Action: rewrote the task so one scoped success-path assertion is required in each target file.
- Helper call contract: correct requirement, but it needed caller-boundary wording so the task does not duplicate helper-level kwarg coverage from #874. Action: kept and narrowed it to caller to helper forwarding only.
- Raw helper-return requirement: architecturally important because fetch_url still owns local wrapping and the tests must avoid double-wrap false positives. Action: kept and tied it to the scoped success-path assertions.
- RED handoff: correct RED and GREEN pairing, but it needed the concrete implementation trigger spelled out. Action: kept and tied it to extract_markdown(resp.text, url=url).

### Architecture Notes

- Current production seam in src/owlbear/core/context_hydration.py is still a direct trafilatura.extract(...) call inside fetch_url(), so this task must stay at the caller boundary and prove only the forwarded extract_markdown(resp.text, url=url) contract.
- tests/test_context_hydration.py currently contains 4 direct sys.modules trafilatura patch sites, and tests/test_content_safety_integration.py currently contains 5 fetch_url-related sites. #869 owns the broad seam migration, while #876 remains the narrow forwarding supplement.
- tests/test_web_extract.py already owns helper-internal trafilatura kwargs from #874, so this task must not add duplicate assertions about output_format, include_links, or helper internals.
- Failure mode map skipped: test-only task, no new production codepath.

### Changes Made

- Rewrote the task body into explicit per-file RED acceptance criteria.
- Added depends_on: #868 to preserve the existing after #868 prerequisite in a machine-checkable form.
- Kept #869 as a verified complement in notes rather than a hard dependency because kanban dependency filters unblock only at done or archived.

### Dependencies

- Added or verified: added #868; verified complementary scope with #869 and GREEN consumer #873

[[2026-03-23]] Mon 07:10

## Test-Writer Notes

- Test file: tests/test_context_hydration.py (TestFromAC_FetchUrlExtractMarkdownForwarding)
- Test file: tests/test_content_safety_integration.py (TestFromAC_FetchUrlExtractMarkdownSeam)
- Classes: TestFromAC_FetchUrlExtractMarkdownForwarding, TestFromAC_FetchUrlExtractMarkdownSeam
- Tests per category: happy 3, edge 0, error 0, boundary 0
- Total: 3 tests, all FAIL (AssertionError: called 0 times) ✓
- ruff: clean
- AC coverage:

  | AC Line | Test(s) | Category |
  |---------|---------|----------|
  | test_context_hydration.py: extract_markdown called with html+url | test_forwards_html_body_and_url_to_extract_markdown | happy |
  | test_context_hydration.py: raw helper return propagates | test_helper_return_propagates_to_fetch_url_result | happy |
  | test_content_safety_integration.py: seam + wrapping | test_fetch_url_forwards_to_helper_and_wraps_output | happy |

[[2026-03-23]] Mon 09:16

## Builder Notes

- Files changed: src/owlbear/core/context_hydration.py
- Tests: 3 TestFromAC passed (47 total in test_context_hydration.py), 1 TestFromAC passed in test_content_safety_integration.py
- Coverage: 96% on context_hydration.py
- Lint: ruff clean
- Evidence: fetch_url now calls module-level extract_markdown(resp.text, url=url); moved import to module top level so patch(owlbear.core.context_hydration.extract_markdown) intercepts correctly
- Fixes applied: replaced lazy trafilatura.extract() call with top-level import + extract_markdown delegation

[[2026-03-23]] Mon 12:05

## Review Evidence

### Review: #876 - Add context_hydration RED assertions for extract_markdown url forwarding

### Test Results

- Scoped AC run: uv run pytest tests/test_context_hydration.py::TestFromAC_FetchUrlExtractMarkdownForwarding tests/test_content_safety_integration.py::TestFromAC_FetchUrlExtractMarkdownSeam -q --tb=short -> 8 passed, 0 failed, 2 optional-dependency warnings.
- Wider file-scope context run: uv run pytest tests/test_context_hydration.py tests/test_content_safety_integration.py -q --tb=short -> 58 passed, 2 failed, 2 warnings.
- The 2 failures are in TestFromACWebReadWrapping and target patch(owlbear.tools.web_search.trafilatura). #876 commit b32ef27 changes only context_hydration, so these are out-of-scope baseline failures.

### Lint Results

- Repo run: uv run ruff check src/ tests/ -> Found 232 errors (230 fixable), all RUF100 baseline debt.
- Task-scope run: uv run ruff check src/owlbear/core/context_hydration.py tests/test_context_hydration.py tests/test_content_safety_integration.py -> All checks passed.

### Coverage

- Scoped coverage run on the two TestFromAC classes: 8 passed.
- Relevant module totals from that run:
  - [src/owlbear/core/context_hydration.py](src/owlbear/core/context_hydration.py#L1): 83%
  - [src/owlbear/web_extract.py](src/owlbear/web_extract.py#L1): 69%
- Changed behavior line is exercised: [src/owlbear/core/context_hydration.py](src/owlbear/core/context_hydration.py#L115).

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| tests/test_context_hydration.py includes successful fetch_url seam assertion (helper called once with html body + url) and raw helper return behavior | TestFromAC_FetchUrlExtractMarkdownForwarding::test_forwards_html_body_and_url_to_extract_markdown; TestFromAC_FetchUrlExtractMarkdownForwarding::test_helper_return_propagates_to_fetch_url_result | Yes. First test enforces exact call args at [tests/test_context_hydration.py](tests/test_context_hydration.py#L594). Second test enforces helper-return propagation at [tests/test_context_hydration.py](tests/test_context_hydration.py#L631). | COVERED |
| tests/test_content_safety_integration.py includes successful fetch_url seam assertion with meaningful wrapping assertion | TestFromAC_FetchUrlExtractMarkdownSeam::test_fetch_url_forwards_to_helper_and_wraps_output | Yes. Exact helper args at [tests/test_content_safety_integration.py](tests/test_content_safety_integration.py#L459); wrapping invariant at [tests/test_content_safety_integration.py](tests/test_content_safety_integration.py#L461). | COVERED |
| Caller-boundary scope only (no helper-internal trafilatura kwarg assertions added in #876 tests) | TestFromAC seam tests above + patch scan | Yes for caller forwarding; scope is confirmed by diff scan: git show 566976d with Select-String output_format|include_links returned no matches. | COVERED |
| Scoped tests fail pre-change and pass after extract_markdown(resp.text, url=url) delegation | Same 3 TestFromAC tests | Yes. Pre-change code in commit 566976d used direct trafilatura.extract(...) and never called helper; now delegation exists at [src/owlbear/core/context_hydration.py](src/owlbear/core/context_hydration.py#L115), and scoped tests pass 8/8. Task body Test-Writer notes also recorded RED failures (called 0 times). | COVERED |

#### Security Review

- No security issues found in #876 scope. Diff b32ef27 only replaces direct trafilatura call with helper delegation in [src/owlbear/core/context_hydration.py](src/owlbear/core/context_hydration.py#L115).

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_FetchUrlExtractMarkdownForwarding::test_forwards_html_body_and_url_to_extract_markdown | No change between 566976d and b32ef27 (git diff -> NO_TEST_DIFF) | PRESERVED |
| TestFromAC_FetchUrlExtractMarkdownForwarding::test_helper_return_propagates_to_fetch_url_result | No change between 566976d and b32ef27 (git diff -> NO_TEST_DIFF) | PRESERVED |
| TestFromAC_FetchUrlExtractMarkdownSeam::test_fetch_url_forwards_to_helper_and_wraps_output | No change between 566976d and b32ef27 (git diff -> NO_TEST_DIFF) | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact assert_called_once_with argument checks and explicit wrapping marker checks. |
| Negative/error paths | ADEQUATE | Existing fetch_url suite covers timeout/status/http error paths in [tests/test_context_hydration.py](tests/test_context_hydration.py#L171). New AC tests are focused on seam success-path behavior. |
| Mutation reasoning | STRONG | Removing helper delegation, swapping args, or bypassing helper-return propagation breaks mapped assertions. |
| Test independence | STRONG | Tests isolate AsyncClient and helper mocks; no shared mutable state. |
| Descriptive names | STRONG | Names state scenario and expectation clearly. |

#### Data Safety

- No data safety issues found in #876 scope.

#### Implementation-Aware Test Gaps

- No significant untested paths introduced by the one-line delegation change. Existing tests cover helper forwarding and wrapped-result behavior, and legacy fetch_url error paths remain covered.

### Pass 2 - INFORMATIONAL

- Workspace currently has an unstaged formatting-only change in [tests/test_content_safety_integration.py](tests/test_content_safety_integration.py#L461) that is not part of builder commit b32ef27 and does not alter behavior.
- Coverage of touched module in scoped run is below 90% overall, but changed line behavior is directly exercised by AC tests.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| tests/test_context_hydration.py has success-path helper forwarding + raw helper return assertions | Class and assertions at [tests/test_context_hydration.py](tests/test_context_hydration.py#L553), [tests/test_context_hydration.py](tests/test_context_hydration.py#L594), [tests/test_context_hydration.py](tests/test_context_hydration.py#L631) | TestFromAC_FetchUrlExtractMarkdownForwarding::* | PASS |
| tests/test_content_safety_integration.py has success-path helper forwarding + meaningful wrapping assertion | Class and assertions at [tests/test_content_safety_integration.py](tests/test_content_safety_integration.py#L408), [tests/test_content_safety_integration.py](tests/test_content_safety_integration.py#L459), [tests/test_content_safety_integration.py](tests/test_content_safety_integration.py#L461) | TestFromAC_FetchUrlExtractMarkdownSeam::test_fetch_url_forwards_to_helper_and_wraps_output | PASS |
| Caller-boundary only (no helper-internal trafilatura kwargs asserted) | Task #876 test-writer patch scan returned no output_format/include_links matches | TestFromAC seam tests (caller-only assertions) | PASS |
| Scoped tests fail pre-change and pass with helper delegation | Pre-change code uses direct trafilatura.extract in commit 566976d; current delegation at [src/owlbear/core/context_hydration.py](src/owlbear/core/context_hydration.py#L115); scoped pytest command passed 8/8 | Three TestFromAC seam tests | PASS |

### Verdict: PASS

- Confidence: .92

### Action Taken

- kanban\\kanban-md.exe edit 876 --status docs --release

[[2026-03-23]] Mon 13:01

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal delegation refactor: fetch_url signature and external behavior unchanged; no new API or convention |
| 2 | Docstrings complete | Yes | Pass | fetch_url docstring at context_hydration.py:103 says via trafilatura - still accurate; extract_markdown internally delegates to trafilatura; no update needed |
| 3 | docs/sources/overview.md | Yes | Pass | Section Context Hydration URL Forwarding RED Coverage (Task #876) at line 1877 already present - added in research phase |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research docs linked | Yes | Pass | docs/research/context-hydration-url-forwarding-red-task.md and docs/research/context-hydration-web-extract-migration.md both exist and linked in task body |

### Files Updated

- None

### Scratch Files Cleaned

- Deleted docs/scratch/876-test-run.txt

[[2026-03-23]] Mon 13:01

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal delegation refactor: fetch_url signature and external behavior unchanged; no new API or convention |
| 2 | Docstrings complete | Yes | Pass | fetch_url docstring at context_hydration.py:103 says via trafilatura - still accurate; extract_markdown internally delegates to trafilatura; no update needed |
| 3 | docs/sources/overview.md | Yes | Pass | Section Context Hydration URL Forwarding RED Coverage (Task #876) at line 1877 already present - added in research phase |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research docs linked | Yes | Pass | docs/research/context-hydration-url-forwarding-red-task.md and docs/research/context-hydration-web-extract-migration.md both exist and linked in task body |

### Files Updated

- None

### Scratch Files Cleaned

- Deleted docs/scratch/876-test-run.txt

[[2026-03-23]] Mon 15:30

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| test_context_hydration.py: extract_markdown called with html+url, raw return propagates | TestFromAC_FetchUrlExtractMarkdownForwarding at L553, assert_called_once_with at L594, distinctive marker at L631 | PASS |
| test_content_safety_integration.py: seam + wrapping assertion | TestFromAC_FetchUrlExtractMarkdownSeam at L408, assert_called_once_with at L459, _OPEN_TAG at L461 | PASS |
| Caller-boundary only (no helper-internal kwargs) | Reviewer patch scan confirmed no output_format/include_links in #876 tests | PASS |
| Scoped tests fail pre-change, pass with delegation | Commits 566976d (RED) and b32ef27 (GREEN) confirm TDD cycle; test-writer notes record 0-call failures | PASS |

### Test Results

- Scoped: 67 passed, 3 failed (all 3 pre-existing out-of-scope: TestFromACWebReadWrapping patches missing trafilatura attr, TestFromAC_BookmarkExtractMarkdownContrast RED for #825)
- ruff: clean on task-scoped files

### Upstream Commits

- 566976d test: add failing tests (#876, test-writer)
- b32ef27 feat: delegate fetch_url to extract_markdown helper (#876, builder)

### Uncommitted Changes

- tests/test_content_safety_integration.py and tests/test_context_hydration.py have unstaged changes from other tasks (#867, #869, #825); NOT #876 scope

### Architect Quality

- AC specificity: 4/5 â€” clear per-file requirements after architect rewrite
- Edge case coverage: adequate for test-only supplement
- Design direction: correct caller-boundary focus
- AC quality score: 4

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 15:31

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 937dbff | chore | kanban/tasks/876-*.md | #876 |
