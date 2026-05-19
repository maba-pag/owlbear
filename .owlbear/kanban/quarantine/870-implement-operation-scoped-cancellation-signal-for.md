---
id: 870
title: Implement operation-scoped cancellation signal for knowledge pipelines
status: archived
priority: nice-to-have
created: 2026-03-20T14:00:48.8902452+01:00
updated: 2026-03-25T05:04:17.1173937+01:00
started: 2026-03-25T05:03:52.3053965+01:00
completed: 2026-03-25T05:03:52.3053965+01:00
tags:
    - scope:core
    - type:build
depends_on:
    - 880
class: standard
---

**Source:** #733 cooperative-cancellation research

**Depends on:** #880 (test task)

Implement the per-operation cooperative cancellation seam recommended in docs/research/operation-scoped-cancellation-signal.md.

**AC:**

1. Add `src/owlbear/memory/knowledge/cancellation.py` with a tiny `CancelSignal` protocol that exposes only `is_set() -> bool`, plus a linked adapter that composes multiple `asyncio.Event` sources without importing daemon code into `memory/`.
2. Thread an optional cancellation signal through `RefreshOrchestrator.refresh`, `RefreshOrchestrator.refresh_all`, `RefreshOrchestrator._ingest_items`, `crawl_and_ingest()`, `IngestPipeline.ingest`, `IngestPipeline.ingest_text`, `IngestPipeline._ingest_from_intake`, `IngestPipeline._run_extract`, and `BookmarkPipeline.process` while keeping current callers valid when the argument is omitted.
3. `RefreshOrchestrator`, `crawl_and_ingest()`, `IngestPipeline._run_extract`, and `BookmarkPipeline.process` check `cancel.is_set()` before starting each next source, item, page, chunk, or bookmark stage and stop cooperatively by returning only work completed before cancellation instead of starting new work.
4. Do not catch or translate outer `asyncio.CancelledError`; cancellation raised by awaited dependencies must still propagate to the caller.
5. Compose the per-operation signal only in the current direct daemon-owned ingest path associated with `RetrospectiveHook`; tool-invoked refresh, bookmark, or ingest shutdown composition stays out of scope for this task and remains #877.
6. All #880 tests pass, and any builder-discovered cancellation coverage stays scoped to the existing related modules under `tests/test_refresh_orchestrator.py`, `tests/test_crawl_integration.py`, `tests/test_knowledge_ingest.py`, `tests/test_bookmark_pipeline.py`, or `tests/test_retrospective_hook.py`.

## Research

Doc: docs/research/operation-scoped-cancellation-signal.md
Attribution: docs/sources/overview.md updated.

Key findings:

- Recommend a tiny protocol-based cancel signal with `is_set()` only, plus a linked adapter that composes multiple sources once at the call site.
- Keep the first implementation knowledge-local (`src/owlbear/memory/knowledge/`) and thread optional cancellation through RefreshOrchestrator, crawl ingest, IngestPipeline, and BookmarkPipeline.
- Check cancellation only at source/item/page/chunk/stage boundaries; preserve partial work and never swallow outer `asyncio.CancelledError`.
- The current direct daemon-owned ingest caller is `RetrospectiveHook`; broader daemon-to-tool propagation is a separate runtime concern because `OwlBearDeps` and tool bootstrap still expose no shutdown-aware dependency surface.
- Existing follow-up split remains #871 (GraphEnricher cancellation), #872 (regression coverage), and #877 (tool/runtime shutdown propagation).

[[2026-03-20]] Fri 16:17

## Architecture Review

**Verdict:** SPLIT

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Abstraction under `memory/` or `memory/knowledge/` | PARTIAL - placement is too wide; current callers are all knowledge-local and the research recommends a knowledge-local module. | Rewrote to `src/owlbear/memory/knowledge/cancellation.py` with a tiny protocol plus linked adapter. |
| 2. Thread optional signal through refresh, crawl, ingest, and bookmark flows | PARTIAL - the affected surfaces were named, but the contract did not require preserving current callers when the new argument is omitted. | Rewrote with the exact public and private surfaces plus optional threading. |
| 3. Check cancellation before each new unit of work | PARTIAL - the boundary list was clear, but the expected exit behavior and `CancelledError` propagation were coupled together. | Split into cooperative partial-result behavior and a separate propagation rule. |
| 4. Compose with daemon shutdown where work runs under daemon control | VAGUE - current code has one direct daemon-owned ingest path (`src/owlbear/core/retrospective_hook.py`), while tool-invoked knowledge flows have no shutdown-aware dependency surface in `src/owlbear/core/deps.py`. | Rewrote to the concrete hook-owned path and left broader runtime propagation to #877. |
| 5. Existing tests pass and add focused coverage | INVALID for a `type:build` task under this board's TDD rules - #870 had no preceding RED task, and #872 is later regression coverage rather than the missing predecessor. | Split out RED task #880 and made #870 depend on it. |

### Architecture Notes

Current code supports a single logical cancellation seam across `src/owlbear/memory/knowledge/refresh.py`, `src/owlbear/memory/knowledge/ingest.py`, `src/owlbear/memory/knowledge/bookmark_pipeline.py`, and `src/owlbear/tools/browser/integration.py` without inverting layering: `tools/` may depend on `memory/`, while `memory/` stays daemon-agnostic per the architecture standards and `src/owlbear/core/deps.py`.
The only concrete daemon-owned ingest caller currently wired is `src/owlbear/core/retrospective_hook.py` via `src/owlbear/bootstrap/__init__.py`; `src/owlbear/bootstrap/knowledge.py` does not expose a shutdown-aware tool/runtime surface, and `crawl_and_ingest()` is not currently wired into `RefreshOrchestrator`. That is why the daemon-composition AC is narrowed to the direct hook-owned path and #877 remains the separate tool/runtime follow-up.
This remains one logical change. The cross-layer edits outside `memory/knowledge/` are thin integration seams for the same cancellation concern rather than a second domain.

### Changes Made

- Created #880 at backlog as the missing `type:test` predecessor for #870.
- Rewrote #870 AC to pin the cancellation module to `src/owlbear/memory/knowledge/`, make `CancelledError` propagation explicit, and narrow daemon composition to the current direct hook-owned path.
- Added depends_on: [880] to #870.

### Dependencies

- Added: #880 (RED test task) as the required predecessor for #870.
- Verified: #871 stays the follow-up for `GraphEnricher` background-task cancellation and draining.
- Verified: #872 remains later regression coverage across #870 and #871, not the missing RED task.
- Verified: #877 remains the separate tool/runtime shutdown-propagation task.

[[2026-03-23]] Mon 23:55

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Add cancellation.py with CancelSignal protocol + LinkedCancelSignal in memory/knowledge/ | Precise. Module does not exist yet. Protocol shape (is_set() -> bool) is explicit. Placement respects YAGNI â€” only knowledge consumers today. | Approved as written. |
| 2. Thread optional cancel through refresh, refresh_all,_ingest_items, crawl_and_ingest, ingest, ingest_text, _ingest_from_intake,_run_extract, BookmarkPipeline.process | Precise. refresh() and ingest() lack cancel today. refresh_all,_ingest_items, and crawl_and_ingest have cancel but do not thread it to downstream calls yet. The listed surfaces are exactly the gaps. | Approved as written. |
| 3. Check cancel.is_set() at source/item/page/chunk/stage boundaries; return partial work | Precise and mechanically testable. Existing boundary checks in refresh_all,_ingest_items, crawl_and_ingest,_run_extract, BookmarkPipeline.process follow this pattern already for a subset. | Approved as written. |
| 4. Do not catch or translate outer asyncio.CancelledError | Precise. _ingest_from_intake already re-raises CancelledError from_run_extract via asyncio.gather. Builder must preserve this and not introduce new catch sites. | Approved as written. |
| 5. Compose only in RetrospectiveHook daemon-owned path; tool paths stay #877 | Precise scope boundary. See Architecture Notes for bootstrap wiring guidance. | Approved with notes. |
| 6. All #880 tests pass; builder-discovered coverage stays in listed test modules | Clear gate with file-scope restriction. | Approved as written. |

### Architecture Notes

**Module layering for LinkedCancelSignal instantiation.**
CancelSignal protocol and LinkedCancelSignal in memory/knowledge/cancellation.py is correct. However, core/retrospective_hook.py cannot import from memory/ at runtime per architecture standards. The composition site for AC 5 should be bootstrap/**init**.py (_wire_post_model_hooks), which can import from all layers. Concretely:

- _wire_post_model_hooks() needs to accept shutdown_event (currently not passed).
- Bootstrap creates LinkedCancelSignal(shutdown_event) and passes it to RetrospectiveHook.**init** as a pre-composed cancel signal.
- RetrospectiveHook stores the signal and forwards it to ingest_text() calls.
- RetrospectiveHook imports CancelSignal only under TYPE_CHECKING for annotation.
- Note: retrospective_hook.py already has a runtime import from memory.usage (record_agent_usage) â€” a pre-existing layering bend in this boundary module. Prefer the bootstrap injection approach over adding another core->memory runtime import.

**shutdown_event temporal ordering.**
shutdown_event is created inside run_daemon() in daemon.py, AFTER bootstrap() returns. Two viable approaches: (a) create shutdown_event earlier in the CLI command/daemon setup and pass it through bootstrap, or (b) have run_daemon() post-inject it into the hook via a setter. Approach (a) is cleaner â€” pass shutdown_event as a kwarg through bootstrap ->_wire_post_model_hooks -> RetrospectiveHook.

**Type annotation migration.**
Existing cancel: asyncio.Event | None annotations (added by #880's builder) should migrate to cancel: CancelSignal | None. asyncio.Event satisfies the protocol via is_set(), so all #880 tests continue to pass with the type change.

**Internal method threading.**
AC 2 lists top-level surfaces. Internal handlers (_handle_url_list,_handle_file_glob, _handle_crawl) also need cancel threaded to _ingest_items; this is implied by the refresh -> _ingest_items chain and does not require separate AC.

**Existing patterns.**
GraphEnricher in memory/knowledge/enrichment.py owns _background_tasks + Semaphore â€” local precedent for task-set ownership. The CancelSignal protocol is complementary (polling at loop boundaries) not overlapping.

**Failure mode map.**
CancelSignal.is_set() is a pure read with no exception risk. No new failure modes introduced â€” the cancel check is best-effort cooperative (skip remaining work), and CancelledError propagation is explicitly preserved.

### Changes Made

- Verified refined AC against codebase state: confirmed refresh() and ingest() lack cancel, confirmed threading gaps in refresh_all->refresh,_ingest_items->pipeline.ingest, crawl_and_ingest->pipeline.ingest_text.
- Verified bootstrap wiring does not currently pass shutdown_event to RetrospectiveHook (gap for AC 5 that builder must address).
- Approved #870 for the GREEN phase.

### Dependencies

- Verified: #880 (RED test task) is archived. TDD compliance satisfied.
- Verified: #871 (GraphEnricher cancellation) at ideation, depends on #870.
- Verified: #872 (regression coverage) at ideation, depends on #870 and #871.
- Verified: #877 (tool/runtime shutdown propagation) at ideation, depends on #870.

[[2026-03-24]] Tue 01:04

## Test-Writer Notes

- Test file (new): tests/test_cancellation.py

- Test files (extended): tests/test_retrospective_hook.py, tests/test_bootstrap.py

- Classes (new): TestFromAC_CancelSignalProtocol, TestFromAC_LinkedCancelSignal

- Classes (extended): TestFromAC_870_RetrospectiveHookLinkedSignal, TestFromAC_870_BootstrapShutdownSignalWiring

- Tests per category: happy 5, edge 5, error 1, boundary 5

- Total: 16 tests, all FAIL

- ruff: clean

- AC coverage:

- AC 1 (cancellation.py + CancelSignal protocol + LinkedCancelSignal): test_cancellation.py::TestFromAC_CancelSignalProtocol (4 tests), TestFromAC_LinkedCancelSignal (9 tests)

- AC 5 (bootstrap shutdown_event wiring + live propagation): TestFromAC_870_RetrospectiveHookLinkedSignal (1 test), TestFromAC_870_BootstrapShutdownSignalWiring (2 tests)

- AC 2-4 and AC 6: covered by existing #880 tests (already passing against #880 implementation)

[[2026-03-24]] Tue 02:38

## Builder Notes

- Files changed: src/owlbear/memory/knowledge/cancellation.py, src/owlbear/memory/knowledge/refresh.py, src/owlbear/memory/knowledge/ingest.py, src/owlbear/memory/knowledge/bookmark_pipeline.py, src/owlbear/tools/browser/integration.py, src/owlbear/core/retrospective_hook.py, src/owlbear/bootstrap/**init**.py
- Tests: 32 passed on required #870/#880 cancellation contract suite; 231 passed on broadened touched-module regression suite.
- Coverage: scoped bare --cov run passed; touched-file percentages in scoped report were cancellation.py 100%, refresh.py 64%, ingest.py 64%, bookmark_pipeline.py 73%, integration.py 80%, retrospective_hook.py 55%, bootstrap/**init**.py 34% (repo-wide source accounting in scoped runs).
- Lint: ruff clean on all changed files.
- Evidence: `uv run pytest tests/test_cancellation.py tests/test_refresh_orchestrator.py::TestFromAC_RefreshCancellation tests/test_crawl_integration.py::TestFromAC_CrawlCancellation tests/test_knowledge_ingest.py::TestFromAC_IngestCancellation tests/test_bookmark_pipeline.py::TestFromAC_BookmarkCancellation tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookCancellation tests/test_retrospective_hook.py::TestFromAC_870_RetrospectiveHookLinkedSignal tests/test_bootstrap.py::TestFromAC_870_BootstrapShutdownSignalWiring -q --tb=short` -> 32 passed; `uv run pytest tests/test_cancellation.py tests/test_refresh_orchestrator.py tests/test_crawl_integration.py tests/test_knowledge_ingest.py tests/test_bookmark_pipeline.py tests/test_retrospective_hook.py tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring tests/test_bootstrap.py::TestFromAC_870_BootstrapShutdownSignalWiring -q --tb=short` -> 231 passed; `uv run ruff check src/owlbear/memory/knowledge/cancellation.py src/owlbear/memory/knowledge/refresh.py src/owlbear/memory/knowledge/ingest.py src/owlbear/memory/knowledge/bookmark_pipeline.py src/owlbear/tools/browser/integration.py src/owlbear/core/retrospective_hook.py src/owlbear/bootstrap/__init__.py` -> all checks passed.
- Fixes applied: Added CancelSignal/LinkedCancelSignal module, threaded optional cancel signals through refresh/crawl/ingest/bookmark seams while preserving omit-cancel callers, and wired bootstrap/RetrospectiveHook shutdown composition with live cancel propagation.

[[2026-03-24]] Tue 03:25

## Review Evidence

### Test Results

- `uv run pytest tests/test_cancellation.py tests/test_refresh_orchestrator.py::TestFromAC_RefreshCancellation tests/test_crawl_integration.py::TestFromAC_CrawlCancellation tests/test_knowledge_ingest.py::TestFromAC_IngestCancellation tests/test_bookmark_pipeline.py::TestFromAC_BookmarkCancellation tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookCancellation tests/test_retrospective_hook.py::TestFromAC_870_RetrospectiveHookLinkedSignal tests/test_bootstrap.py::TestFromAC_870_BootstrapShutdownSignalWiring -q --tb=short` -> 32 passed, 2 warnings (`qdrant_client` optional-dependency skips from `tests/conftest.py`).
- `uv run pytest tests/test_cancellation.py tests/test_refresh_orchestrator.py tests/test_crawl_integration.py tests/test_knowledge_ingest.py tests/test_bookmark_pipeline.py tests/test_retrospective_hook.py tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring tests/test_bootstrap.py::TestFromAC_870_BootstrapShutdownSignalWiring -q --tb=short` -> 231 passed, 1 failed (`tests/test_bookmark_pipeline.py::TestFromAC_DefaultWebReadExtractMarkdownSeam::test_extract_called_with_url_forwarded` from #867; noted here but not the rejection basis for #870).
- `uv run ruff check src/owlbear/memory/knowledge/cancellation.py src/owlbear/memory/knowledge/refresh.py src/owlbear/memory/knowledge/ingest.py src/owlbear/memory/knowledge/bookmark_pipeline.py src/owlbear/tools/browser/integration.py src/owlbear/core/retrospective_hook.py src/owlbear/bootstrap/__init__.py tests/test_cancellation.py tests/test_refresh_orchestrator.py tests/test_crawl_integration.py tests/test_knowledge_ingest.py tests/test_bookmark_pipeline.py tests/test_retrospective_hook.py tests/test_bootstrap.py` -> All checks passed.
- `uv run pytest ... --cov --cov-report=term-missing --cov-fail-under=0` -> `src/owlbear/memory/knowledge/cancellation.py` 100%, `src/owlbear/memory/knowledge/refresh.py` 64%, `src/owlbear/memory/knowledge/ingest.py` 64%, `src/owlbear/memory/knowledge/bookmark_pipeline.py` 73%, `src/owlbear/tools/browser/integration.py` 80%, `src/owlbear/core/retrospective_hook.py` 55%, `src/owlbear/bootstrap/__init__.py` 34% (scoped bare `--cov`; lower totals are unrelated branches in larger modules and are not the rejection basis).

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC line | Mapped test(s) | Would fail if AC were violated? | Verdict |
| --- | --- | --- | --- |
| 1. Add `cancellation.py` with `CancelSignal` + linked adapter | `tests/test_cancellation.py:16`, `tests/test_cancellation.py:60` | Yes - import/runtime-protocol/live-link assertions would fail. | COVERED |
| 2. Thread optional cancel through refresh/crawl/ingest/bookmark surfaces while keeping omit-cancel callers valid | `tests/test_refresh_orchestrator.py:658`, `tests/test_crawl_integration.py:222`, `tests/test_knowledge_ingest.py:2083`, `tests/test_bookmark_pipeline.py:878`; widened file suites also exercise legacy no-`cancel` callers | Yes for cooperative threading; existing no-`cancel` callers still execute in the widened slice. | COVERED |
| 3. Boundary checks return only completed work | Same classes as AC2 | Yes - result length/count assertions fail if extra work starts after cancellation. | COVERED |
| 4. Outer `asyncio.CancelledError` still propagates | `tests/test_knowledge_ingest.py:2111` | Yes - explicit `pytest.raises(asyncio.CancelledError)`. | COVERED |
| 5. Compose only in the direct `RetrospectiveHook` daemon-owned path | `tests/test_retrospective_hook.py:942`, `tests/test_retrospective_hook.py:966`, `tests/test_retrospective_hook.py:1014`, `tests/test_bootstrap.py:3258`, `tests/test_bootstrap.py:3281` | Functional linkage is covered, but the task's architecture note required bootstrap-owned composition without adding a new `core -> memory` runtime import. The implementation violates that note. | FAIL |
| 6. #880 tests pass; builder coverage stays in allowed modules | Task suite above passed; `git show --stat --name-only --format=fuller 6fa7c85` lists only source files | Yes. | COVERED |

#### Security Review

- No security issues found in the reviewed cancellation paths.

#### Test Integrity

| Original test | Change made | Assessment |
| --- | --- | --- |
| `tests/test_cancellation.py`, `tests/test_refresh_orchestrator.py`, `tests/test_crawl_integration.py`, `tests/test_knowledge_ingest.py`, `tests/test_bookmark_pipeline.py`, `tests/test_retrospective_hook.py`, `tests/test_bootstrap.py` | `git show --stat --name-only --format=fuller 6fa7c85` shows the #870 builder commit touched only source files; no tests were modified. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | STRONG | Boundary tests assert exact result lengths/counts and live `is_set()` behavior, not loose truthiness. |
| Negative / error paths | STRONG | Cancel-pre-set, cancel-between-iterations, and `asyncio.CancelledError` propagation are all covered. |
| Manual mutation reasoning | ADEQUATE | Removing boundary `cancel.is_set()` checks or swallowing `CancelledError` trips the targeted suite, although the architecture-layer rule is not test-enforced. |
| Test independence | STRONG | Fresh `asyncio.Event`, mocks, and temporary paths per test. |
| Descriptive names | STRONG | Test names describe the boundary and expected cooperative-stop behavior clearly. |

#### Data Safety

- No data safety issues found in the reviewed code.

#### Implementation-Aware Test Gaps

- No significant silent-behavior gaps found in the cooperative cancellation loops. The rejection is architectural: bootstrap already owns linked-signal construction at `src/owlbear/bootstrap/__init__.py:125` and `src/owlbear/bootstrap/__init__.py:133`, but `src/owlbear/core/retrospective_hook.py:22` adds a second concrete `memory` import and `src/owlbear/core/retrospective_hook.py:136` composes the linked signal inside `core`, which the task notes at `kanban/tasks/870-implement-operation-scoped-cancellation-signal-for.md:99`, `:104`, and `:105` explicitly forbade.

### Pass 2 - INFORMATIONAL

- The widened touched-module regression slice is not currently clean because `tests/test_bookmark_pipeline.py:840` still fails in the touched bookmark file. That appears to belong to task #867 rather than #870 and is not the rejection basis here.
- `src/owlbear/bootstrap/__init__.py:133` already injects a linked signal, so `RetrospectiveHook._compose_cancel()` is redundant even aside from the layer violation.

### AC Compliance

| AC line | Evidence | Mapped test | Status |
| --- | --- | --- | --- |
| 1. Add `cancellation.py` with `CancelSignal` + linked adapter | `src/owlbear/memory/knowledge/cancellation.py:9`, `src/owlbear/memory/knowledge/cancellation.py:20` | `tests/test_cancellation.py:16`, `tests/test_cancellation.py:60` | PASS |
| 2. Thread optional cancel through refresh/crawl/ingest/bookmark surfaces | `src/owlbear/memory/knowledge/refresh.py:94`, `:124`, `:233`, `:268`, `:281`; `src/owlbear/memory/knowledge/ingest.py:121`, `:189`, `:254`, `:341`; `src/owlbear/tools/browser/integration.py:22`, `:78`; `src/owlbear/memory/knowledge/bookmark_pipeline.py:93`, `:209` | cancellation classes above | PASS |
| 3. Boundary checks stop before next unit and return partial work | `src/owlbear/memory/knowledge/refresh.py:124`, `:233`; `src/owlbear/tools/browser/integration.py:22`; `src/owlbear/memory/knowledge/ingest.py:341`; `src/owlbear/memory/knowledge/bookmark_pipeline.py:93` | `tests/test_refresh_orchestrator.py:658`, `tests/test_crawl_integration.py:222`, `tests/test_knowledge_ingest.py:2083`, `tests/test_bookmark_pipeline.py:878` | PASS |
| 4. Outer `CancelledError` propagates | `src/owlbear/memory/knowledge/ingest.py:254`, `:341`; explicit propagation test at `tests/test_knowledge_ingest.py:2111` | `tests/test_knowledge_ingest.py:2111` | PASS |
| 5. Compose only in current direct daemon-owned ingest path | Functional wiring present at `src/owlbear/bootstrap/__init__.py:128`, `:132`, `:133` and `src/owlbear/core/retrospective_hook.py:120`, `:136`, `:250`, but `src/owlbear/core/retrospective_hook.py:22` introduces a forbidden runtime `core -> memory` import despite the task note at `kanban/tasks/870-implement-operation-scoped-cancellation-signal-for.md:99-105` | `tests/test_retrospective_hook.py:942`, `tests/test_retrospective_hook.py:966`, `tests/test_retrospective_hook.py:1014`, `tests/test_bootstrap.py:3258`, `tests/test_bootstrap.py:3281` | FAIL |
| 6. #880 tests pass and builder coverage stays scoped | Task suite passed 32 tests; builder commit `6fa7c85` touched no tests | task suite above | PASS |

### Verdict

FAIL. `src/owlbear/core/retrospective_hook.py:22` adds a new concrete `core -> memory` runtime dependency on `LinkedCancelSignal`, violating the repo architecture rule that `core/` never imports from `memory/` and contradicting the task's architecture note that bootstrap must own this composition.

### Action Taken

- `kanban\kanban-md.exe edit 870 --status todo --release`

[[2026-03-24]] Tue 13:13

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL cited missing test - AC5 had no test enforcing the no core to memory runtime import constraint.
- Added: 1 new failing test in tests/test_cancellation.py::TestFromAC_870_CoreLayerConstraint
  - test_retrospective_hook_has_no_runtime_memory_knowledge_imports
  - Fails because retrospective_hook.py:22 has from owlbear.memory.knowledge.cancellation import LinkedCancelSignal at top level
- Preserved: 13 existing tests (all PASS)
- ruff: clean
- Builder must move LinkedCancelSignal usage out of retrospective_hook.py and into bootstrap/**init**.py (composition owner)

[[2026-03-25]] Wed 02:54

## Builder Notes

- Files changed: src/owlbear/core/retrospective_hook.py
- Tests: 33 passed across scoped cancellation suites for test_cancellation, test_retrospective_hook cancellation classes, test_bootstrap shutdown wiring class, and #880 cancellation classes in refresh orchestrator, crawl integration, ingest, and bookmark pipeline.
- Coverage: Bare coverage run completed on test_cancellation and test_retrospective_hook; retrospective_hook.py measured 95 percent line coverage.
- Lint: ruff clean on src/owlbear/core/retrospective_hook.py.
- Evidence: RED baseline reproduced with one failing test in TestFromAC_870_CoreLayerConstraint before the fix; all targeted suites passed after the fix.
- Fixes applied: Removed top level runtime import from core retrospective hook into memory knowledge cancellation and resolved cancel signal selection by preferring injected cancel, then shutdown event, then a local unset asyncio event fallback.

[[2026-03-25]] Wed 03:40

## Review Evidence

### Review: #870 - Implement operation-scoped cancellation signal for knowledge pipelines

### Test Results

- Scoped cancellation slice returned 33 passed, 63 warnings.
- Covered suites: tests/test_cancellation.py, TestFromAC_RefreshCancellation, TestFromAC_CrawlCancellation, TestFromAC_IngestCancellation, TestFromAC_BookmarkCancellation, TestFromAC_RetrospectiveHookCancellation, TestFromAC_870_RetrospectiveHookLinkedSignal, and TestFromAC_870_BootstrapShutdownSignalWiring.
- Warnings were PytestUnknownMarkWarning for legacy pytest.mark.anyio decorators in tests/test_knowledge_ingest.py under disabled plugin autoload; the reviewed slice had no failures.
- Bare coverage slice on tests/test_cancellation.py plus the retrospective-hook and bootstrap cancellation classes returned 19 passed. cancellation.py reported 100 percent and retrospective_hook.py reported 54 percent. Per repo guidance this whole-file percentage is informational only because the slice exercises the task seam inside a larger module.

### Lint Results

- ruff: All checks passed on src/owlbear/core/retrospective_hook.py, src/owlbear/bootstrap/**init**.py, src/owlbear/memory/knowledge/cancellation.py, tests/test_cancellation.py, tests/test_retrospective_hook.py, and tests/test_bootstrap.py.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC line | Mapped test(s) | Would fail if AC violated? | Verdict |
| --- | --- | --- | --- |
| 1. Add cancellation.py with CancelSignal protocol and linked adapter | tests/test_cancellation.py:18, 62 | Yes. Import, runtime protocol, and live-link behavior assertions would fail. | COVERED |
| 2. Thread optional cancel through refresh, crawl, ingest, and bookmark seams while keeping omit-cancel callers valid | tests/test_refresh_orchestrator.py:658, tests/test_crawl_integration.py:222, tests/test_knowledge_ingest.py:2083, tests/test_bookmark_pipeline.py:878, tests/test_retrospective_hook.py:938 | Yes. These tests assert cancel threading into downstream calls and cooperative stop behavior. | COVERED |
| 3. Boundary checks stop before the next unit of work and return partial work | same classes as AC2 | Yes. Result-count and stage-boundary assertions fail if extra work starts after cancellation. | COVERED |
| 4. Outer asyncio.CancelledError still propagates | tests/test_knowledge_ingest.py:2114, 2123 | Yes. Explicit raises check. | COVERED |
| 5. Compose only in the direct RetrospectiveHook daemon-owned path without a runtime core to memory knowledge import | tests/test_cancellation.py:165, 185; tests/test_retrospective_hook.py:1000, 1014; tests/test_bootstrap.py:3244, 3258, 3279 | Yes. The AST constraint test fails on any top-level memory knowledge import in retrospective_hook.py, while the hook and bootstrap tests fail if live linked shutdown propagation is not injected from bootstrap. | COVERED |
| 6. #880 tests pass and coverage stays in allowed modules | scoped cancellation slice above; commit ddb2440 touches only src/owlbear/core/retrospective_hook.py | Yes. All task-owned suites passed and the retry commit stayed in scope. | COVERED |

#### Security Review

- No security issues found. The retry removes a layer violation and only selects between injected cancel signals and asyncio.Event instances.

#### Test Integrity

| Original test | Change made | Assessment |
| --- | --- | --- |
| tests/test_cancellation.py, tests/test_retrospective_hook.py, tests/test_bootstrap.py | Retry commit ddb2440 changed only src/owlbear/core/retrospective_hook.py. No test file changed in the builder fix. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | STRONG | The new AC5 test performs an AST import scan, and the hook and bootstrap tests assert live cancel state rather than loose truthiness. |
| Negative or error paths | STRONG | Coverage includes cancel pre-set, cancel during iteration, and explicit CancelledError propagation. |
| Mutation reasoning | STRONG | Reintroducing a top-level memory knowledge import, snapshotting shutdown instead of live linking, or swallowing CancelledError would fail the mapped tests. |
| Test independence | STRONG | Fresh asyncio.Event instances, tmp_path roots, and isolated mocks per test. |
| Descriptive names | STRONG | Test names describe the exact cancellation and layer-constraint behavior under review. |

#### Data Safety

- No data-safety issues found. The change preserves cooperative cancellation and does not introduce new shared mutable state or persistence hazards.

#### Implementation-Aware Test Gaps

- No significant silent-behavior gaps found. bootstrap now owns LinkedCancelSignal construction at src/owlbear/bootstrap/**init**.py:129 and 137-139, while retrospective_hook.py keeps the knowledge cancellation import under TYPE_CHECKING at lines 24 and 32, stores the resolved cancel signal at line 145, and forwards it to ingest_text at line 298.

### Pass 2 - INFORMATIONAL

- The current workspace includes unstaged retry test-writer drift in tests/test_cancellation.py, tests/test_retrospective_hook.py, and tests/test_bootstrap.py plus whitespace drift in src/owlbear/memory/knowledge/cancellation.py. The review was run against the current workspace state. The builder retry commit ddb2440 itself touched only src/owlbear/core/retrospective_hook.py.

### AC Compliance

| AC line | Evidence | Mapped test | Status |
| --- | --- | --- | --- |
| 1. Add cancellation.py with CancelSignal protocol and linked adapter | src/owlbear/memory/knowledge/cancellation.py:9, 20, 26 | tests/test_cancellation.py:18, 62 | PASS |
| 2. Thread optional cancel through refresh, crawl, ingest, and bookmark surfaces | src/owlbear/memory/knowledge/refresh.py:95, 123, 149, 159, 183, 231, 265, 278; src/owlbear/memory/knowledge/ingest.py:121, 187, 249, 335; src/owlbear/tools/browser/integration.py:27; src/owlbear/memory/knowledge/bookmark_pipeline.py:96; src/owlbear/core/retrospective_hook.py:135, 136, 145 | tests/test_refresh_orchestrator.py:658; tests/test_crawl_integration.py:222; tests/test_knowledge_ingest.py:2083; tests/test_bookmark_pipeline.py:878; tests/test_retrospective_hook.py:938 | PASS |
| 3. Boundary checks stop cooperatively before the next unit of work | src/owlbear/memory/knowledge/refresh.py:137, 240; src/owlbear/tools/browser/integration.py:49; src/owlbear/memory/knowledge/ingest.py:340; src/owlbear/memory/knowledge/bookmark_pipeline.py:126, 140, 147, 173 | tests/test_refresh_orchestrator.py:658; tests/test_crawl_integration.py:222; tests/test_knowledge_ingest.py:2083; tests/test_bookmark_pipeline.py:878 | PASS |
| 4. Outer asyncio.CancelledError propagates | src/owlbear/memory/knowledge/ingest.py:267; tests/test_knowledge_ingest.py:2114, 2123 | tests/test_knowledge_ingest.py:2114 | PASS |
| 5. Compose only in the direct daemon-owned RetrospectiveHook path | src/owlbear/bootstrap/**init**.py:129, 137, 139, 241; src/owlbear/core/retrospective_hook.py:24, 32, 145, 152, 298 | tests/test_cancellation.py:165, 185; tests/test_retrospective_hook.py:1000, 1014; tests/test_bootstrap.py:3244, 3258, 3279 | PASS |
| 6. #880 tests pass and retry stays in scope | scoped cancellation slice returned 33 passed; git show ddb2440 lists only src/owlbear/core/retrospective_hook.py | task-owned cancellation slice | PASS |

### Verdict

PASS

### Confidence

.93

### Action Taken

- Review evidence appended.
- Advancing task to docs.

[[2026-03-25]] Wed 03:48

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Knowledge row: cancel type updated from asyncio.Event to CancelSignal; added protocol, LinkedCancelSignal, and bootstrap injection note |
| 2 | Docstrings | Yes | Updated | cancellation.py docstrings complete (new module). cancel param description in refresh.py, ingest.py x2, bookmark_pipeline.py, integration.py corrected from asyncio.Event to CancelSignal protocol |
| 3 | docs/sources/overview.md | Yes | Pass | Section Task 880/870 at line 2000 already present with attribution rows |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Pass | docs/research/operation-scoped-cancellation-signal.md exists and linked from task body |

### Files Updated

- .github/copilot-instructions.md
- src/owlbear/memory/knowledge/refresh.py (docstring)
- src/owlbear/memory/knowledge/ingest.py (docstrings x2)
- src/owlbear/memory/knowledge/bookmark_pipeline.py (docstring)
- src/owlbear/tools/browser/integration.py (docstring)

### Scratch Files Cleaned

- None (no docs/scratch/870-* files existed before this run)

### Commit

7713745 docs: update CancelSignal docstrings and copilot-instructions (#870, writer)

[[2026-03-25]] Wed 03:48

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Knowledge row: cancel type updated from asyncio.Event to CancelSignal; added protocol, LinkedCancelSignal, and bootstrap injection note |
| 2 | Docstrings | Yes | Updated | cancellation.py docstrings complete (new module). cancel param description in refresh.py, ingest.py x2, bookmark_pipeline.py, integration.py corrected from asyncio.Event to CancelSignal protocol |
| 3 | docs/sources/overview.md | Yes | Pass | Section Task 880/870 at line 2000 already present with attribution rows |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Pass | docs/research/operation-scoped-cancellation-signal.md exists and linked from task body |

### Files Updated

- .github/copilot-instructions.md
- src/owlbear/memory/knowledge/refresh.py (docstring)
- src/owlbear/memory/knowledge/ingest.py (docstrings x2)
- src/owlbear/memory/knowledge/bookmark_pipeline.py (docstring)
- src/owlbear/tools/browser/integration.py (docstring)

### Scratch Files Cleaned

- None (no docs/scratch/870-* files existed before this run)

### Commit

7713745 docs: update CancelSignal docstrings and copilot-instructions (#870, writer)

[[2026-03-25]] Wed 05:03

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. cancellation.py with CancelSignal + LinkedCancelSignal | src/owlbear/memory/knowledge/cancellation.py:9,20 verified | PASS |
| 2. Thread optional cancel through listed surfaces | Reviewer mapped all 8 surfaces with line refs; spot-checked refresh.py, ingest.py | PASS |
| 3. Boundary checks return partial work | Reviewer covered with result-count assertions | PASS |
| 4. Outer CancelledError propagates | Reviewer: tests/test_knowledge_ingest.py:2114 explicit raises check | PASS |
| 5. Compose only in daemon-owned path, no core runtime import | retrospective_hook.py:24,32 under TYPE_CHECKING; bootstrap/**init**.py:129,137 owns LinkedCancelSignal | PASS |
| 6. #880 tests pass, coverage in allowed modules | Scoped suite 33 passed; builder commits touched only allowed files | PASS |

### Test Results

- pytest full suite: 37 failed (all pre-existing RED-phase or unrelated), 4339 passed, 2 skipped
- Zero failures in #870 modules (cancellation, refresh, crawl, ingest, bookmark, retrospective_hook, bootstrap)
- ruff: clean on all #870 source files

### Architect Quality: 5/5

AC was specific, complete, and led to clean implementation. Two-round refinement (SPLIT then APPROVED) produced precise surface list, explicit layering rules, and clear bootstrap composition guidance.

### Confidence: .97

### Action: archive

[[2026-03-25]] Wed 05:04

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| cf5642e | chore | kanban/tasks/870-*.md | #870 |
