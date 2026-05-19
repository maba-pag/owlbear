---
id: 880
title: Tests for operation-scoped cancellation signal in knowledge pipelines (RED)
status: archived
priority: nice-to-have
created: 2026-03-20T16:14:55.3851471+01:00
updated: 2026-03-23T01:23:01.54402+01:00
started: 2026-03-23T01:21:51.7432653+01:00
completed: 2026-03-23T01:21:51.7432653+01:00
tags:
    - scope:core
    - type:test
class: standard
---

**Source:** #870 (implementation task), docs/research/operation-scoped-cancellation-signal.md

Write RED-phase tests for the operation-scoped cancellation seam in the current knowledge pipeline entry points.

**AC:**

1. `tests/test_refresh_orchestrator.py` adds tests that `RefreshOrchestrator.refresh_all(cancel=...)` stops before the next source and `RefreshOrchestrator._ingest_items(..., cancel=...)` stops before the next item when the signal is set between iterations, returning only work completed before cancellation.
2. `tests/test_crawl_integration.py` adds tests that `crawl_and_ingest(..., cancel=...)` stops before the next crawled page when the signal is set between page ingests and returns only `IngestResult` values produced before cancellation.
3. `tests/test_knowledge_ingest.py` adds tests that `IngestPipeline.ingest_text(..., cancel=...)` threads the signal into `IngestPipeline._run_extract(..., cancel=...)`, `_run_extract()` stops before the next chunk when the signal is set between extraction calls, and an outer `asyncio.CancelledError` raised by the extractor still propagates instead of being translated into a cooperative stop.
4. `tests/test_bookmark_pipeline.py` adds tests that `BookmarkPipeline.process(..., cancel=...)` checks cancellation before extract, evaluate, ingest, and store boundaries; cancellation before extract or evaluate leaves `evaluation` and `bookmark` unset, cancellation before ingest preserves the completed `evaluation` while skipping ingest and store, and cancellation before store leaves `bookmark` unset while preserving any completed earlier-stage state.
5. `tests/test_retrospective_hook.py` adds a focused test on the current daemon-owned ingest path in `RetrospectiveHook` that asserts the hook composes a per-operation cancellation signal with daemon shutdown before calling `ingest_text()`, without broadening coverage into the separate tool/runtime shutdown propagation tracked by #877.
6. The newly added cases fail against current HEAD before #870 is implemented.

[[2026-03-20]] Fri 17:38

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. RefreshOrchestrator cancellation tests | SOUND - `tests/test_refresh_orchestrator.py` already exercises source ordering and per-item aggregation around `src/owlbear/memory/knowledge/refresh.py`; the future `cancel=` call surface just needed to be explicit. | Rewrote to pin `refresh_all(cancel=...)` and `_ingest_items(..., cancel=...)`. |
| 2. Crawl integration cancellation tests | SOUND - `tests/test_crawl_integration.py` already isolates per-page sequencing in `src/owlbear/tools/browser/integration.py`; the AC needed the cancel kwarg and partial-result contract stated directly. | Rewrote to pin `crawl_and_ingest(..., cancel=...)` and pre-cancel results only. |
| 3. Ingest extraction cancellation tests | PARTIAL - chunk-boundary stopping and `CancelledError` propagation were clear, but the AC did not identify which future call surface should prove the thread-through contract. | Rewrote to pin `ingest_text(..., cancel=...)` forwarding plus `_run_extract(..., cancel=...)` behavior. |
| 4. Bookmark stage-boundary cancellation tests | PARTIAL - the stage list was clear, but the returned `BookmarkResult` state after cooperative exit was still implicit. | Rewrote to preserve only earlier-stage state and leave `bookmark` unset on cooperative exit. |
| 5. RetrospectiveHook daemon-composition test | PARTIAL - the intent was correct, but it needed to stay narrow to the current hook-owned ingest path in `src/owlbear/core/retrospective_hook.py` rather than drift into the broader runtime work tracked by #877. | Rewrote to focus only on the current daemon-owned ingest path. |
| 6. RED failure requirement | SOUND - this is the correct gate for a `type:test` backlog task. | Clarified that the new cases fail against current HEAD before #870. |

### Architecture Notes

The primary concern is still one logical RED task for the knowledge-pipeline cancellation seam, even though the matching suites touch `memory/`, `tools/`, and the hook integration in `core/`. The cross-layer surfaces are the same bounded contract described in `docs/research/operation-scoped-cancellation-signal.md`, and #870 already depends on this task as its TDD predecessor.
Existing seams are already isolated in the matching suites: `tests/test_refresh_orchestrator.py` for source and item loops in `src/owlbear/memory/knowledge/refresh.py`, `tests/test_crawl_integration.py` for page loops in `src/owlbear/tools/browser/integration.py`, `tests/test_knowledge_ingest.py` for extraction loops in `src/owlbear/memory/knowledge/ingest.py`, `tests/test_bookmark_pipeline.py` for stage orchestration in `src/owlbear/memory/knowledge/bookmark_pipeline.py`, and `tests/test_retrospective_hook.py` for the current daemon-owned ingest caller wired from `src/owlbear/bootstrap/__init__.py`.
`src/owlbear/core/deps.py` still exposes no shutdown-aware dependency field, so the hook coverage must stay focused on the current direct daemon-owned ingest path. Broader tool and runtime shutdown propagation remains #877.

### Changes Made

- Rewrote #880 AC to make the future `cancel=` entry points explicit.
- Tightened bookmark cancellation expectations so cooperative exit preserves only earlier-stage state and leaves `bookmark` unset.
- Narrowed the hook test scope to the current `RetrospectiveHook` daemon-owned ingest path and kept #877 out of scope.
- Advanced #880 from `backlog` to `todo`.

### Dependencies

- Verified: #870 depends on #880 as its required RED predecessor.
- Verified: #877 remains the separate tool and runtime shutdown-propagation follow-up.
- Verified: the existing five suites already provide the intended RED seams, so no further split is required.

[[2026-03-20]] Fri 18:46

## Test-Writer Notes

- Test files: tests/test_refresh_orchestrator.py, tests/test_crawl_integration.py, tests/test_knowledge_ingest.py, tests/test_bookmark_pipeline.py, tests/test_retrospective_hook.py
- Classes: TestFromAC_RefreshCancellation, TestFromAC_CrawlCancellation, TestFromAC_IngestCancellation, TestFromAC_BookmarkCancellation, TestFromAC_RetrospectiveHookCancellation
- Tests per category: happy 0, edge 3, error 1, boundary 12
- Total: 16 tests, all FAIL (TypeError: unexpected keyword argument 'cancel' / 'shutdown_event') âœ“
- ruff: clean on all new code; 6 pre-existing D403 in untouched lines
- AC coverage: all 6 AC lines covered; full table in docs/scratch/880-test-writer.md

[[2026-03-20]] Fri 19:23

## Builder Notes

- Files changed: refresh.py, ingest.py, bookmark_pipeline.py, integration.py, retrospective_hook.py
- Tests: 15/16 TestFromAC_ passed; 1 fails from pre-existing numpy environment bug (numpy.isscalar removed in NumPy 2.x breaks pytest.approx) - same as 2 pre-existing non-TestFromAC failures; implementation is correct.
- Coverage: bookmark_pipeline 100%, ingest 100%, integration 100%, retrospective_hook 100%, refresh 99%
- Lint: ruff clean (TC003 fixed via TYPE_CHECKING blocks, TRY301/PLR0911 via noqa)
- Changes: added cancel=asyncio.Event|None to refresh_all,_ingest_items, crawl_and_ingest, ingest_text, _ingest_from_intake,_run_extract, BookmarkPipeline.process; shutdown_event= to RetrospectiveHook.**init**

[[2026-03-21]] Sat 02:49

## Review Evidence

- test append probe

[[2026-03-21]] Sat 02:49

## Review Evidence

Review #880

Test Results

- pytest scoped: 200 passed, 3 failed (numpy.isscalar AttributeError in bookmark tests)
- pytest TestFromAC only: 15 passed, 1 failed (TestFromAC_BookmarkCancellation::test_cancel_before_ingest_preserves_evaluation_and_skips_ingest_and_store)

Lint

- ruff scoped source+tests: 6 D403 in pre-existing untouched test docstrings
- ruff source-only touched files: all checks passed

Coverage

- retrospective_hook 100
- bookmark_pipeline 100
- ingest 100
- refresh 99
- integration 100

Pass 1 Critical

- Security: no issues found.
- TestFromAC integrity: builder commit c5313e3 changed only source files; no TestFromAC edits, no weakened/removed assertions.
- Data safety: no new integrity/race/atomicity concerns found.

AC Compliance

- AC1 PASS: refresh cancellation tests present and pass.
- AC2 PASS: crawl cancellation tests present and pass.
- AC3 PASS: ingest cancellation tests present and pass.
- AC4 FAIL: one AC-mapped bookmark cancellation test fails at runtime due numpy.isscalar AttributeError from pytest.approx.
- AC5 PASS: retrospective hook cancellation composition tests present and pass.
- AC6 PASS: pre-implementation signatures in c5313e3^ lack cancel/shutdown_event kwargs, matching RED expectation.

Rejection

- Gap: AC4 not fully verifiable because 1 TestFromAC case fails in current environment.
- Required fix: stabilize that bookmark assertion path under current environment and rerun scoped pytest + TestFromAC subset.

Verdict: FAIL
Confidence: .78

[[2026-03-22]] Sun 19:27

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about 1 broken test assertion (pytest.approx(0.85) triggers numpy.isscalar removed in NumPy 2.x), not missing tests.
- Fix: replaced pytest.approx(0.85) with direct equality == 0.85 in TestFromAC_BookmarkCancellation::test_cancel_before_ingest_preserves_evaluation_and_skips_ingest_and_store.
- All 16 TestFromAC_ tests: 16 passed (uv run pytest -k TestFromAC on 5 files).
- ruff: clean (tests/test_bookmark_pipeline.py).
- Preserved: 16 existing tests (all PASS against builder implementation).

[[2026-03-22]] Sun 23:04

## Builder Notes (retry)

- Files changed: tests/test_refresh_orchestrator.py, tests/test_crawl_integration.py, tests/test_knowledge_ingest.py, tests/test_bookmark_pipeline.py, tests/test_retrospective_hook.py
- All 16 TestFromAC_ tests: 16 passed
- 2 pre-existing non-TestFromAC failures (TestBookmarkPipelineHappyPath, TestBookmarkPipelineThreshold) from numpy.isscalar removal in NumPy 2.x — unrelated to this task, same as previous builder notes
- Coverage: retrospective_hook 100%, bookmark_pipeline 100%, ingest 100%, refresh 99%, integration 100%
- Lint: ruff clean on all touched files
- Source impl already committed at c5313e3; this commit adds test files only (commit 3d28346)
- Retry reason: test-writer replaced pytest.approx(0.85) with == 0.85 in TestFromAC_BookmarkCancellation::test_cancel_before_ingest_preserves_evaluation_and_skips_ingest_and_store

[[2026-03-22]] Sun 23:28

## Review Evidence

### Review: #880 - Tests for operation-scoped cancellation signal in knowledge pipelines (RED)

### Test Results

- `uv run pytest tests/test_refresh_orchestrator.py tests/test_crawl_integration.py tests/test_knowledge_ingest.py tests/test_bookmark_pipeline.py tests/test_retrospective_hook.py -q --tb=short` -> 201 passed, 2 failed, 2 warnings.
- Failing tests:
  - `tests/test_bookmark_pipeline.py::TestBookmarkPipelineHappyPath::test_full_pipeline_high_score`
  - `tests/test_bookmark_pipeline.py::TestBookmarkPipelineThreshold::test_low_score_skips_ingest`
- Failure mode is pre-existing environment debt (`pytest.approx` hitting `numpy.isscalar` removal in NumPy 2.x), not introduced by #880; the failing assertion lines are from commit `4a2e128` (`git blame` lines 227 and 373).
- `uv run pytest tests/test_refresh_orchestrator.py tests/test_crawl_integration.py tests/test_knowledge_ingest.py tests/test_bookmark_pipeline.py tests/test_retrospective_hook.py -q --tb=short -k TestFromAC` -> 16 passed, 187 deselected, 2 warnings.

### Lint Results

- `uv run ruff check src/ tests/` -> 257 errors (repo baseline; examples: `RUF100`, `E501`, `SIM117`).
- `uv run ruff check` on touched #880 files only -> All checks passed.

### Coverage

- `uv run pytest tests/test_refresh_orchestrator.py tests/test_crawl_integration.py tests/test_knowledge_ingest.py tests/test_bookmark_pipeline.py tests/test_retrospective_hook.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- Touched modules:
  - `src/owlbear/core/retrospective_hook.py`: 100%
  - `src/owlbear/memory/knowledge/bookmark_pipeline.py`: 100%
  - `src/owlbear/memory/knowledge/ingest.py`: 100%
  - `src/owlbear/memory/knowledge/refresh.py`: 99%
  - `src/owlbear/tools/browser/integration.py`: 100%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. RefreshOrchestrator `refresh_all(cancel=...)` and `_ingest_items(..., cancel=...)` boundary stop + partial results | `TestFromAC_RefreshCancellation::{test_refresh_all_stops_before_next_source_when_cancel_set_between_iterations,test_refresh_all_returns_only_results_produced_before_cancellation,test_ingest_items_stops_before_next_item_when_cancel_set_between_iterations,test_ingest_items_result_counts_only_work_completed_before_cancel}` | Yes - assertions pin stop counts (`await_count`, `len(results)`) and result counters | COVERED |
| 2. `crawl_and_ingest(..., cancel=...)` stops before next page and returns only pre-cancel results | `TestFromAC_CrawlCancellation::{test_stops_before_next_page_when_cancel_is_set_between_page_ingests,test_returns_only_ingest_results_produced_before_cancellation,test_cancel_set_before_first_page_returns_empty_list}` | Yes - asserts exact result length/order and `assert_not_awaited()` for pre-cancel | COVERED |
| 3. `ingest_text(..., cancel=...)` threads to `_run_extract(..., cancel=...)`, chunk-boundary stop, `CancelledError` propagation | `TestFromAC_IngestCancellation::{test_run_extract_stops_before_next_chunk_when_cancel_is_set_between_calls,test_cancelled_error_from_extractor_propagates_through_ingest_text,test_ingest_text_threads_cancel_into_extraction_stopping_at_chunk_boundary}` | Yes - asserts extract call counts and explicit `pytest.raises(asyncio.CancelledError)` | COVERED |
| 4. `BookmarkPipeline.process(..., cancel=...)` stage-boundary behavior and preserved partial state | `TestFromAC_BookmarkCancellation::{test_cancel_before_extract_leaves_evaluation_and_bookmark_unset,test_cancel_before_evaluate_leaves_evaluation_and_bookmark_unset,test_cancel_before_ingest_preserves_evaluation_and_skips_ingest_and_store,test_cancel_before_store_leaves_bookmark_unset_preserving_earlier_stage_state}` | Yes - asserts stage-specific state (`evaluation`, `ingested`, `bookmark`) and awaited/not-awaited calls | COVERED |
| 5. RetrospectiveHook composes per-operation cancel signal with daemon shutdown before `ingest_text()` | `TestFromAC_RetrospectiveHookCancellation::{test_hook_passes_cancel_kwarg_to_ingest_text_composed_with_shutdown,test_cancel_signal_is_set_when_daemon_shutdown_fires}` | Yes - asserts `cancel` kwarg is passed and set when shutdown event is set | COVERED |
| 6. New tests fail pre-#870 implementation | Test classes above + pre-implementation signature check via `git show c5313e3^:...` | Yes - pre-`c5313e3` signatures lacked `cancel`/`shutdown_event` kwargs, so these call sites would fail with unexpected keyword errors | COVERED |

#### Security Review

- No hardcoded secrets, injection sinks, unsafe deserialization, or path-traversal additions in the #880 implementation scope.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RefreshCancellation::*` | Introduced in `3d28346`; no later weakening/removal detected | PRESERVED |
| `TestFromAC_CrawlCancellation::*` | Introduced in `3d28346`; no later weakening/removal detected | PRESERVED |
| `TestFromAC_IngestCancellation::*` | Introduced in `3d28346`; no later weakening/removal detected | PRESERVED |
| `TestFromAC_BookmarkCancellation::*` | Introduced in `3d28346`; no later weakening/removal detected | PRESERVED |
| `TestFromAC_RetrospectiveHookCancellation::*` | Introduced in `3d28346`; no later weakening/removal detected | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact counts, object identity checks, stage-state assertions, and explicit kwarg assertions; no lazy truthiness-only checks in TestFromAC cases |
| Negative/error paths | STRONG | Includes pre-cancel entry, mid-iteration cancel, and extractor-raised `asyncio.CancelledError` propagation |
| Mutation reasoning | STRONG | Removing cancel checks or threading would break precise `await_count`, length, and exception assertions |
| Test independence | STRONG | Uses isolated mocks/events per test; no cross-test shared mutable state reliance |
| Descriptive names | STRONG | Method names encode scenario + expected outcome at boundary granularity |

#### Data Safety

- No data integrity or atomicity regressions found in reviewed cancellation paths.

#### Implementation-Aware Test Gaps

- No significant untested behavioral branches found in the #880 cancellation seam.

### Pass 2 - INFORMATIONAL

- Two non-AC bookmark tests currently fail under NumPy 2.x due `pytest.approx` -> `numpy.isscalar` removal (`tests/test_bookmark_pipeline.py` lines 227 and 373; blame to `4a2e128`). This is pre-existing baseline debt and unrelated to #880 TestFromAC cancellation coverage.
- Repo-wide lint debt (257 errors) remains outside this task's touched files.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1 | `src/owlbear/memory/knowledge/refresh.py` adds `cancel` to `refresh_all` (line 119) and `_ingest_items` (line 213) with boundary checks (lines 139, 227) | `TestFromAC_RefreshCancellation::*` | PASS |
| 2 | `src/owlbear/tools/browser/integration.py` adds `cancel` to `crawl_and_ingest` (line 22) with pre-page check (line 53) | `TestFromAC_CrawlCancellation::*` | PASS |
| 3 | `src/owlbear/memory/knowledge/ingest.py` threads `cancel` from `ingest_text` (line 182) to `_ingest_from_intake` (line 240) to `_run_extract` (line 264), with `CancelledError` re-raise (lines 267-268) and loop boundary check (line 340) | `TestFromAC_IngestCancellation::*` | PASS |
| 4 | `src/owlbear/memory/knowledge/bookmark_pipeline.py` adds stage-boundary cancel checks (lines 117, 131, 138, 159) with partial-state return before store (line 161) | `TestFromAC_BookmarkCancellation::*` | PASS |
| 5 | `src/owlbear/core/retrospective_hook.py` accepts `shutdown_event` (line 89), builds per-operation cancel (line 194), and passes `cancel` to `ingest_text` (line 204) | `TestFromAC_RetrospectiveHookCancellation::*` | PASS |
| 6 | Pre-implementation signatures in `c5313e3^` lacked `cancel`/`shutdown_event` kwargs (verified via `git show c5313e3^:...`) | TestFromAC call sites that now pass these kwargs | PASS |

### Verdict

- PASS (confidence .93)

### Action Taken

- Pending status move to `docs` with claim release.

[[2026-03-23]] Mon 00:24

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added cancel param note to Knowledge tech-stack row (all major pipeline entry points accept cancel: asyncio.Event) |
| 2 | Docstrings | Yes | Updated | Added cancel param doc to ingest_text (ingest.py) and BookmarkPipeline.process (bookmark_pipeline.py); refresh_all and crawl_and_ingest already documented; private helpers are 1-line summary only |
| 3 | docs/sources/overview.md | Yes | Updated | Added section for #880/#870: asyncio task-cancellation docs, AnyIO cancellation docs (rejected prior art), .NET cancellation-token docs (primary prior art) |
| 4 | README.md | No | N/A | No CLI command changes |
| 5 | Research doc | Yes | Pass | docs/research/operation-scoped-cancellation-signal.md exists; linked in task body |
| 6 | No impact | No | N/A | Items 1-3 apply |

### Files Updated

- .github/copilot-instructions.md
- docs/sources/overview.md
- src/owlbear/memory/knowledge/ingest.py (docstring only)
- src/owlbear/memory/knowledge/bookmark_pipeline.py (docstring only)

### Scratch Files Cleaned

- Deleted docs/scratch/880-test-writer.tmp (gitignored)

[[2026-03-23]] Mon 01:21

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. RefreshOrchestrator cancel tests | 4 TestFromAC_RefreshCancellation pass; cancel= at refresh.py L123,L218 | PASS |
| 2. crawl_and_ingest cancel tests | 3 TestFromAC_CrawlCancellation pass | PASS |
| 3. IngestPipeline cancel tests | 3 TestFromAC_IngestCancellation pass; cancel threading + CancelledError propagation | PASS |
| 4. BookmarkPipeline stage-boundary cancel | 4 TestFromAC_BookmarkCancellation pass; cancel checks at 4 boundaries in bookmark_pipeline.py | PASS |
| 5. RetrospectiveHook composition | 2 TestFromAC_RetrospectiveHookCancellation pass; shutdown_event at retrospective_hook.py L89 | PASS |
| 6. RED failure pre-#870 | Commit history confirms c5313e3 added cancel kwargs; pre-impl signatures lacked them | PASS |

### Test Results

- pytest TestFromAC: 16 passed, 0 failed
- pytest full suite: 3774 passed, 93 failed (all pre-existing: numpy 2.x, RED-phase tests for unimplemented features)
- ruff: clean on all touched files

### AC Quality Score: 5

AC was specific (exact method signatures, stage boundaries, partial-result contracts), complete (edge cases included), and led to clean implementation.

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 01:23

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 866eeb7 | chore | kanban/tasks/880-*.md | #880 |
