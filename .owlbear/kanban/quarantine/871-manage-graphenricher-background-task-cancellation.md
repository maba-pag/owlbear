---
id: 871
title: Manage GraphEnricher background-task cancellation and draining
status: archived
priority: nice-to-have
created: 2026-03-20T14:01:00.5343875+01:00
updated: 2026-03-26T11:52:45.981754+01:00
started: 2026-03-26T11:52:01.9642337+01:00
completed: 2026-03-26T11:52:01.9642337+01:00
tags:
    - scope:core
    - type:build
depends_on:
    - 870
    - 1000
class: standard
---

**Source:** #733 cooperative-cancellation research
See docs/research/graphenricher-cancellation-draining.md for full analysis.

**Depends on:** #870 (done), #1000 (TDD RED tests)

Make GraphEnricher cancellation-aware, following the HookWorkerSupervisor pattern (core/hook_worker_supervisor.py).
Target file: src/owlbear/memory/knowledge/enrichment.py

**AC:**

1. Add `_shutdown: bool = False` flag to `GraphEnricher.__init__`.
2. `schedule_graph_enrichment` and `schedule_inter_doc_enrichment` accept optional `cancel: CancelSignal | None` parameter (from `owlbear.memory.knowledge.cancellation`); return early (no-op) when `_shutdown is True` or `cancel.is_set()` returns `True`.
3. Add `async shutdown()` that sets `_shutdown = True`, cancels all tracked tasks via `task.cancel()`, gathers with `return_exceptions=True`, and leaves `_background_tasks` empty on return. Mirrors `HookWorkerSupervisor.shutdown()`.
4. Add `async drain()` that sets `_shutdown = True`, awaits all tracked tasks **without** cancelling, and leaves `_background_tasks` empty on return. For graceful completion of in-flight enrichment.
5. Subsequent `schedule_*` calls are no-ops after either `shutdown()` or `drain()` has been called.
6. Preserve existing `_background_tasks` set bookkeeping, `_bg_semaphore` concurrency control, and `task.add_done_callback(self._background_tasks.discard)` pattern.

[[2026-03-25]] Wed 05:56

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. _shutdown flag in **init** | Precise, mirrors HookWorkerSupervisor._shutdown | Keep |
| 2. cancel: CancelSignal param on schedule_* | Verifiable: new param, early-return behavior, type from cancellation.py | Refined from vague original |
| 3. async shutdown() | Precise: sets flag, cancels, gathers, empties set. Matches HookWorkerSupervisor exactly | Refined from vague original |
| 4. async drain() | Precise: sets flag, awaits without cancel, empties set. New vs HookWorkerSupervisor but justified by research | Refined from vague original |
| 5. No-op after shutdown/drain | Verifiable pass/fail check | Refined |
| 6. Preserve existing bookkeeping | Constraint on implementation, not a deliverable. Verifiable | Keep |

### Architecture Notes

- Follows established HookWorkerSupervisor pattern (core/hook_worker_supervisor.py): _shutdown flag, no-op after shutdown, cancel+gather in shutdown().
- drain() extends pattern for graceful enrichment completion (research-justified, enrichment results are valuable).
- CancelSignal from memory/knowledge/cancellation.py (already exists via #870). TYPE_CHECKING import only to avoid runtime cross-layer deps.
- Single domain: memory (enrichment.py only). Bootstrap wiring is separate task #998.
- Existing test file: tests/test_enrichment.py has comprehensive coverage of current behavior.

### Failure Mode Map

| Codepath | Failure mode | Exception | Handled? | User impact |
|----------|-------------|-----------|----------|-------------|
| shutdown() | In-flight task raises during cancel | Any | Yes, gather(return_exceptions=True) | None, errors absorbed |
| drain() | In-flight task raises during await | Any | Yes, gather(return_exceptions=True) | None, errors logged |
| schedule_* after_shutdown | Silent no-op | N/A | N/A | None, expected |
| schedule_* with cancel.is_set() | Silent no-op | N/A | N/A | None, expected |

### Changes Made

- Rewrote AC from vague 4-line original to precise 6-line verifiable AC (absorbed #997 scope)
- Deleted #997 (redundant, identical scope to refined #871)
- Added depends_on #1000 (TDD compliance: test task precedes impl)
- Fixed #998, #999 deps: removed stale #997, added #871
- Removed incorrect #1000 dep on #871 (test precedes impl, not the reverse)

### Dependencies

- #870 (archived, done): CancelSignal and LinkedCancelSignal exist
- #1000 (ideation, TDD RED): test task must precede this impl task
- Downstream: #998 (bootstrap wiring), #999 (IngestPipeline threading) depend on #871
- Note for #1000 architect review: AC6 tests bootstrap wiring (belongs to #998 scope, not #871)

[[2026-03-26]] Thu 10:59

## Builder Notes

- Files changed: src/owlbear/memory/knowledge/enrichment.py
- Tests: 4 passed in test_871_graphenricher_drain_noop.py; 12 passed and 2 deselected in GraphEnricher subset of test_enrichment_cancellation.py; 42 passed in combined enrichment test run
- Coverage: 94 percent on src/owlbear/memory/knowledge/enrichment.py
- Lint: ruff check passed for touched implementation and related tests
- Evidence: drain now sets shutdown flag before awaiting tracked tasks, so schedule methods are no-op after drain
- Fixes applied: Set self._shutdown to True at start of GraphEnricher.drain

[[2026-03-26]] Thu 10:59

## Builder Notes

- Files changed: src/owlbear/memory/knowledge/enrichment.py
- Tests: 4 passed in test_871_graphenricher_drain_noop.py; 12 passed and 2 deselected in GraphEnricher subset of test_enrichment_cancellation.py; 42 passed in combined enrichment test run
- Coverage: 94 percent on src/owlbear/memory/knowledge/enrichment.py
- Lint: ruff check passed for touched implementation and related tests
- Evidence: drain now sets shutdown flag before awaiting tracked tasks, so schedule methods are no-op after drain
- Fixes applied: Set self._shutdown to True at start of GraphEnricher.drain

[[2026-03-26]] Thu 11:14

## Review Evidence

## Review: #871 - Manage GraphEnricher background-task cancellation and draining

### Test Results

- pytest: 42 passed, 0 failed.
- Evidence: tests/test_871_graphenricher_drain_noop.py ran 4 passed; tests/test_enrichment_cancellation.py ran 14 passed; tests/test_enrichment.py ran 24 passed.

### Lint Results

- ruff: clean on src/owlbear/memory/knowledge/enrichment.py and the related test files.

### Coverage

- src/owlbear/memory/knowledge/enrichment.py: 94 percent on the combined scoped run.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 Add _shutdown flag in **init**: covered by TestFromAC_GraphEnricherShutdownFlag::test_enricher_has_shutdown_flag_initialized_false; this would fail if the attribute were missing or initialized incorrectly.
- AC2 schedule_graph_enrichment and schedule_inter_doc_enrichment accept optional cancel and no-op on_shutdown or cancel.is_set(): covered by TestFromAC_GraphEnricherCancelSignal::test_schedule_graph_enrichment_is_noop_when_cancel_set, TestFromAC_GraphEnricherCancelSignal::test_schedule_inter_doc_enrichment_is_noop_when_cancel_set, TestFromAC_GraphEnricherShutdownFlag::test_shutdown_flag_set_directly_prevents_schedule_graph_enrichment, and TestFromAC_GraphEnricherShutdownFlag::test_shutdown_flag_set_directly_prevents_schedule_inter_doc_enrichment.
- AC3 shutdown cancels tracked tasks, gathers cleanup, and leaves _background_tasks empty: covered by TestFromAC_GraphEnricherShutdown::test_shutdown_cancels_running_tracked_task, TestFromAC_GraphEnricherShutdown::test_shutdown_leaves_background_tasks_empty, and TestFromAC_GraphEnricherShutdown::test_shutdown_with_no_tasks_returns_immediately.
- AC4 drain sets _shutdown, awaits running tasks without cancelling, and leaves_background_tasks empty: covered by TestFromAC_GraphEnricherDrain::test_drain_awaits_task_to_normal_completion, TestFromAC_GraphEnricherDrain::test_drain_leaves_background_tasks_empty, TestFromAC_DrainSetsShutdownFlag::test_drain_sets_shutdown_flag_when_no_tasks_pending, and TestFromAC_DrainSetsShutdownFlag::test_drain_sets_shutdown_flag_after_task_completes.
- AC5 schedule methods are no-op after shutdown or drain: covered by TestFromAC_GraphEnricherScheduleAfterShutdown::test_schedule_graph_enrichment_is_noop_after_shutdown, TestFromAC_GraphEnricherScheduleAfterShutdown::test_schedule_inter_doc_enrichment_is_noop_after_shutdown, TestFromAC_ScheduleNoopAfterDrain::test_schedule_graph_enrichment_is_noop_after_drain, and TestFromAC_ScheduleNoopAfterDrain::test_schedule_inter_doc_enrichment_is_noop_after_drain.
- AC6 Preserve _background_tasks bookkeeping, _bg_semaphore concurrency control, and task tracking behavior: covered by TestGraphEnricherOwnership::test_owns_background_tasks_set, TestGraphEnricherOwnership::test_owns_bg_semaphore, TestScheduleGraphEnrichment::test_schedules_task, TestScheduleInterDocEnrichment::test_schedules_task, TestEnricherSemaphoreBounds::test_enrich_graph_bounded, and TestEnricherSemaphoreBounds::test_enrich_inter_doc_bounded.

#### Security Review

- No security issues found in task scope. The change adds only shutdown and cancellation gating around background task lifecycle management.

#### Test Integrity

- Builder commit 41c9c1b modified only src/owlbear/memory/knowledge/enrichment.py.
- tests/test_871_graphenricher_drain_noop.py was not changed in the #871 builder commit; TestFromAC_DrainSetsShutdownFlag and TestFromAC_ScheduleNoopAfterDrain were preserved.
- tests/test_enrichment_cancellation.py was not changed in the #871 builder commit; the TestFromAC_GraphEnricher* classes were preserved.

#### Test Quality

- Assertion specificity: STRONG. Tests assert exact _shutdown state, cancellation and completion flags, builder call counts, and exact_background_tasks sizes.
- Negative and error paths: STRONG. Coverage includes empty-task shutdown, cancel.is_set(), direct_shutdown gating, shutdown cancellation, drain non-cancellation, no builder, no entities, and inter-doc min-document guards.
- Mutation reasoning: STRONG. Removing self._shutdown = True from drain, dropping cancel handling, skipping task.cancel(), or breaking semaphore bounds would be caught by named tests in the scoped runs.
- Test independence: STRONG. Tests use isolated in-memory sqlite fixtures, per-test events, and fresh GraphEnricher instances.
- Descriptive names: STRONG. Method names describe the scenario and expected behavior precisely.

#### Data Safety

- No new data safety issues found. Setting _shutdown before copying tracked tasks prevents new scheduling during drain or shutdown, and return_exceptions=True ensures cleanup completes even if a task errors during teardown.

#### Implementation-Aware Test Gaps

- No significant untested paths found in task scope. The new branches in schedule_graph_enrichment, schedule_inter_doc_enrichment, drain, and shutdown are exercised by the dedicated cancellation and drain tests plus existing enrichment regression tests.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

- AC1: implemented in GraphEnricher.**init**; verified by the shutdown-flag initialization test and the source review.
- AC2: both schedule methods now accept cancel and return early on _shutdown or cancel.is_set(); verified by the cancel-signal and direct-shutdown-flag tests.
- AC3: shutdown sets _shutdown, cancels tracked tasks, gathers with return_exceptions=True, and empties the tracked set; verified by the shutdown cancellation and empty-set tests.
- AC4: drain sets _shutdown, awaits tasks without cancelling, and empties the tracked set; verified by the drain completion, drain empty-set, and drain shutdown-flag tests.
- AC5: both schedule methods are no-op after shutdown or drain; verified by the post-shutdown and post-drain no-op tests.
- AC6: _background_tasks ownership, semaphore bounds, and task tracking behavior remain intact; verified by ownership, scheduling, and semaphore-bound regression tests.

### Verdict: PASS

- Confidence: .95

### Action Taken

- Appended review evidence.
- Moved task to docs and released claim.

[[2026-03-26]] Thu 11:51

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. _shutdown flag in **init** | enrichment.py L62: self._shutdown = False | PASS |
| 2. cancel param on schedule_* + early return | enrichment.py L67-76 (graph), L93-102 (inter-doc) | PASS |
| 3. shutdown() cancels, gathers, clears | enrichment.py L133-140, matches HookWorkerSupervisor | PASS |
| 4. drain() sets _shutdown, awaits, clears | enrichment.py L125-131 | PASS |
| 5. No-op after shutdown/drain | Both schedule_* guard on_shutdown at top | PASS |
| 6. Preserve bookkeeping | _background_tasks set, _bg_semaphore, add_done_callback intact | PASS |

### Test Results

- pytest: 4734 passed, 95 failed (all pre-existing RED-phase or known failures), 2 skipped. No regressions from #871.
- 4 failures in test_1006 are RED-phase for task #1006 (cancel threading to ingest pipeline), not regressions.
- ruff: clean on enrichment.py and test_871_graphenricher_drain_noop.py.

### Upstream Commits

- 39bae95 test: add failing tests for GraphEnricher drain AC 4/5 gap (#871, test-writer)
- 41c9c1b fix: set GraphEnricher drain shutdown gate (#871, builder)
- 32ccc3e docs: update schedule_* docstrings to reflect cancel/shutdown no-op guards (#871, writer)

### AC Quality Score: 4/5

AC was specific and verifiable after architect refinement (vague 4-line original rewritten to precise 6-line AC). Minor gap: initial framing needed rework.

### Confidence: .97

### Action: archive

[[2026-03-26]] Thu 11:51

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. _shutdown flag in **init** | enrichment.py L62: self._shutdown = False | PASS |
| 2. cancel param on schedule_* + early return | enrichment.py L67-76 (graph), L93-102 (inter-doc) | PASS |
| 3. shutdown() cancels, gathers, clears | enrichment.py L133-140, matches HookWorkerSupervisor | PASS |
| 4. drain() sets _shutdown, awaits, clears | enrichment.py L125-131 | PASS |
| 5. No-op after shutdown/drain | Both schedule_* guard on_shutdown at top | PASS |
| 6. Preserve bookkeeping | _background_tasks set, _bg_semaphore, add_done_callback intact | PASS |

### Test Results

- pytest: 4734 passed, 95 failed (all pre-existing RED-phase or known failures), 2 skipped. No regressions from #871.
- 4 failures in test_1006 are RED-phase for task #1006 (cancel threading to ingest pipeline), not regressions.
- ruff: clean on enrichment.py and test_871_graphenricher_drain_noop.py.

### Upstream Commits

- 39bae95 test: add failing tests for GraphEnricher drain AC 4/5 gap (#871, test-writer)
- 41c9c1b fix: set GraphEnricher drain shutdown gate (#871, builder)
- 32ccc3e docs: update schedule_* docstrings to reflect cancel/shutdown no-op guards (#871, writer)

### AC Quality Score: 4/5

AC was specific and verifiable after architect refinement (vague 4-line original rewritten to precise 6-line AC). Minor gap: initial framing needed rework.

### Confidence: .97

### Action: archive

[[2026-03-26]] Thu 11:52

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| e3e9560 | chore | kanban/tasks/871-*.md | #871 |
