---
id: 998
title: Wire GraphEnricher.shutdown into bootstrap cleanup
status: archived
priority: nice-to-have
created: 2026-03-25T04:37:09.944638+01:00
updated: 2026-03-26T13:27:05.0070094+01:00
started: 2026-03-26T13:27:04.3630326+01:00
completed: 2026-03-26T13:27:04.3630326+01:00
tags:
    - scope:core
    - type:build
depends_on:
    - 871
class: standard
---

[[2026-03-25]] Wed 04:37
Source: #871 research (docs/research/graphenricher-cancellation-draining.md).

AC:

1. bootstrap/knowledge.py registers enricher.shutdown in cleanup list when enricher is not None.
2. Daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup.
3. No orphaned enrichment tasks after daemon stop.

-t

[[2026-03-26]] Thu 03:14

## Research

**Finding: Already implemented (green on arrival).**

Commit 352c78a (#1000 builder, 2026-03-25) landed the bootstrap wiring as part of the broader GraphEnricher lifecycle controls:

- knowledge.py:183-184: appends enricher.shutdown to cleanup when enricher is not None
- toolsets.py:140-141: forwards cleanup kwarg to _build_knowledge_toolset
- enrichment.py:130-139: shutdown() sets _shutdown, cancels tracked tasks, gathers

Both RED tests (TestFromAC_GraphEnricherBootstrapCleanup) pass green.

**AC status:** All 3 items satisfied. No code changes needed. Task can fast-track through pipeline as no-op.

**Research checklist (trivial):** Prior art is HookWorkerSupervisor.shutdown (same codebase). Parent research: docs/research/graphenricher-cancellation-draining.md.

[[2026-03-26]] Thu 11:37

## Architecture Review

**Verdict:** Approve (green on arrival)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. bootstrap/knowledge.py registers enricher.shutdown in cleanup when enricher is not None | Verified: knowledge.py:183-184 does cleanup.append(enricher.shutdown) | No change |
| 2. Daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup | Verified: daemon.py:79-86 iterates result.cleanup, awaits each callback | No change |
| 3. No orphaned enrichment tasks after daemon stop | Verified: enrichment.py:140-149 shutdown() cancels+gathers all tracked tasks | No change |

### Architecture Notes

Green on arrival: commit 352c78a (#1000) already implemented all 3 AC items. Tests exist at test_enrichment_cancellation.py:548 (TestFromAC_GraphEnricherBootstrapCleanup). Module layering correct: bootstrap calls down into memory.knowledge.enrichment. Follows existing HookWorkerSupervisor.shutdown cleanup pattern. Single domain (scope:core). No new security surface.

### Dependencies

- Verified: #871 (parent research) at done status
- Verified: #1000 (builder that landed the implementation) committed

### Changes Made

- Approved to todo (fast-track no-op pipeline)

[[2026-03-26]] Thu 12:19

## Test-Writer Notes

- Green on arrival: commit 352c78a (#1000 builder) landed all 3 AC items before this task entered the test-writer slot.
- Existing test class: tests/test_enrichment_cancellation.py::TestFromAC_GraphEnricherBootstrapCleanup (line 548)
- Tests: 2 tests, both PASS against current HEAD
  - test_wire_knowledge_toolsets_registers_enricher_shutdown_when_inter_doc_enabled
  - test_wire_knowledge_toolsets_forwards_cleanup_kwarg_to_build_knowledge_toolset
- AC coverage:
  - AC 1 (bootstrap/knowledge.py registers enricher.shutdown in cleanup when enricher is not None): covered by both tests above
  - AC 2 (daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup): covered by existing test_cli.py::TestCleanupLoopAwaitsAsync (cleanup loop awaits async callables)
  - AC 3 (no orphaned enrichment tasks after daemon stop): covered by TestFromAC_GraphEnricherShutdown (cancels tasks, leaves_background_tasks empty)
- No new test file created - tests pre-exist from #1000 task cycle.
- Overtaken RED: builder landed implementation ahead of test-writer slot.

[[2026-03-26]] Thu 12:56

## Builder Notes

- Files changed: None (green on arrival no-op build).
- Tests: 6 passed in scoped AC verification.
- Coverage: src/owlbear/bootstrap/knowledge.py 18 percent; src/owlbear/bootstrap/toolsets.py 33 percent; src/owlbear/memory/knowledge/enrichment.py 53 percent; scoped total 21 percent.
- Lint: ruff check clean for AC-related files.
- Evidence: TestFromAC_GraphEnricherBootstrapCleanup, TestFromAC_GraphEnricherShutdown, and TestCleanupLoopAwaitsAsync all passed.
- Fixes applied: None. Implementation already existed from task 1000.

[[2026-03-26]] Thu 13:13

## Review Evidence

### Test Results

- pytest: 8 passed, 0 failed, 6 deselected in tests/test_enrichment_cancellation.py for TestFromAC_GraphEnricherBootstrapCleanup and TestFromAC_GraphEnricherShutdown.
- pytest: 1 passed, 0 failed, 30 deselected in tests/test_cli.py for TestCleanupLoopAwaitsAsync.
- Coverage run: 9 passed, 0 failed, 36 deselected. Reported whole-file percentages were 18% for src/owlbear/bootstrap/knowledge.py, 33% for src/owlbear/bootstrap/toolsets.py, 56% for src/owlbear/memory/knowledge/enrichment.py, and 37% for src/bearclaw/commands/daemon.py. These were not used as pass or fail gating because the scoped run reports whole-file values.

### Lint Results

- ruff: all checks passed for src/owlbear/bootstrap/knowledge.py, src/owlbear/bootstrap/toolsets.py, src/owlbear/memory/knowledge/enrichment.py, src/bearclaw/commands/daemon.py, tests/test_enrichment_cancellation.py, and tests/test_cli.py.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC 1. bootstrap/knowledge.py registers enricher.shutdown in cleanup list when enricher is not None. | tests/test_enrichment_cancellation.py::TestFromAC_GraphEnricherBootstrapCleanup::test_wire_knowledge_toolsets_registers_enricher_shutdown_when_inter_doc_enabled; tests/test_enrichment_cancellation.py::TestFromAC_GraphEnricherBootstrapCleanup::test_wire_knowledge_toolsets_forwards_cleanup_kwarg_to_build_knowledge_toolset | Yes. One test asserts the bound shutdown callback is appended to cleanup; the second asserts the same cleanup list object is forwarded into knowledge wiring. Both would fail if registration or forwarding broke. | COVERED |
| AC 2. Daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup. | tests/test_cli.py::TestCleanupLoopAwaitsAsync::test_async_cleanup_callable_is_awaited | Yes. The test fails if the daemon cleanup loop stops awaiting async callbacks because await_count stays zero. Combined with AC 1 evidence that GraphEnricher.shutdown is registered into cleanup, this covers invocation through BootstrapResult.cleanup. | COVERED |
| AC 3. No orphaned enrichment tasks after daemon stop. | tests/test_enrichment_cancellation.py::TestFromAC_GraphEnricherShutdown::test_shutdown_cancels_running_tracked_task; tests/test_enrichment_cancellation.py::TestFromAC_GraphEnricherShutdown::test_shutdown_leaves_background_tasks_empty; tests/test_enrichment_cancellation.py::TestFromAC_GraphEnricherShutdown::test_shutdown_with_no_tasks_returns_immediately | Yes. These tests fail if shutdown stops cancelling in-flight work, leaves tracked tasks behind, or hangs on empty state. | COVERED |

#### Security Review

- No security issues found in the reviewed path. The change surface is internal cleanup wiring and task cancellation; no new secrets, injection sinks, traversal, deserialization, or external input handling were introduced.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_GraphEnricherBootstrapCleanup::test_wire_knowledge_toolsets_registers_enricher_shutdown_when_inter_doc_enabled | No change since ff5024f, the latest commit touching tests/test_enrichment_cancellation.py. | PRESERVED |
| TestFromAC_GraphEnricherBootstrapCleanup::test_wire_knowledge_toolsets_forwards_cleanup_kwarg_to_build_knowledge_toolset | No change since ff5024f, the latest commit touching tests/test_enrichment_cancellation.py. | PRESERVED |
| TestFromAC_GraphEnricherShutdown::test_shutdown_cancels_running_tracked_task | No change since ff5024f, the latest commit touching tests/test_enrichment_cancellation.py. | PRESERVED |
| TestFromAC_GraphEnricherShutdown::test_shutdown_leaves_background_tasks_empty | No change since ff5024f, the latest commit touching tests/test_enrichment_cancellation.py. | PRESERVED |
| TestFromAC_GraphEnricherShutdown::test_shutdown_with_no_tasks_returns_immediately | No change since ff5024f, the latest commit touching tests/test_enrichment_cancellation.py. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | The bootstrap cleanup tests assert exact callback identity and exact forwarded list object. The shutdown tests assert CancelledError observation, explicit empty _background_tasks, and bounded return timing. |
| Negative and error paths | STRONG | The shutdown suite covers running-task cancellation and empty-state shutdown. The cleanup-loop test covers the async-callback path that would silently leak work if not awaited. |
| Mutation reasoning | STRONG | If cleanup forwarding were removed, callback registration changed, task.cancel() dropped, or difference_update(tasks) removed, the mapped tests would fail. |
| Test independence | STRONG | Each test constructs its own in-memory sqlite connection, mock builders, and GraphEnricher instance; no shared mutable state crosses tests. |
| Descriptive names | STRONG | Test names describe the exact scenario and expected outcome, including registration, forwarding, cancellation, emptiness, and await behavior. |

#### Data Safety

- No data safety issues found. GraphEnricher.shutdown sets the shutdown flag, cancels tracked tasks, awaits them with return_exceptions=True, and clears tracking references, which is the correct cleanup behavior for this async background-task owner.

#### Implementation-Aware Test Gaps

- No significant untested paths found for this task. Current code is straightforward and the relevant branches are exercised: cleanup forwarding in src/owlbear/bootstrap/toolsets.py line 174, cleanup callback registration in src/owlbear/bootstrap/knowledge.py line 183, async callback awaiting in src/bearclaw/commands/daemon.py lines 81-84, and GraphEnricher shutdown cancellation and cleanup in src/owlbear/memory/knowledge/enrichment.py lines 142-148.

### Pass 2 - INFORMATIONAL

- Coverage executed successfully, but the reported percentages are whole-file values from a scoped run and are not reliable task-only gate evidence for these large modules.
- No additional informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC 1. bootstrap/knowledge.py registers enricher.shutdown in cleanup list when enricher is not None. | src/owlbear/bootstrap/toolsets.py line 174 forwards cleanup into knowledge_kwargs; src/owlbear/bootstrap/knowledge.py line 183 appends enricher.shutdown when cleanup is provided and an enricher exists. | TestFromAC_GraphEnricherBootstrapCleanup::test_wire_knowledge_toolsets_registers_enricher_shutdown_when_inter_doc_enabled; TestFromAC_GraphEnricherBootstrapCleanup::test_wire_knowledge_toolsets_forwards_cleanup_kwarg_to_build_knowledge_toolset | PASS |
| AC 2. Daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup. | src/owlbear/bootstrap/_types.py line 117 defines BootstrapResult.cleanup; src/bearclaw/commands/daemon.py lines 81-84 iterate result.cleanup, call each callback, and await awaitables. | TestCleanupLoopAwaitsAsync::test_async_cleanup_callable_is_awaited | PASS |
| AC 3. No orphaned enrichment tasks after daemon stop. | src/owlbear/memory/knowledge/enrichment.py lines 142-148 set _shutdown, cancel tracked tasks, await them, and clear tracking references. | TestFromAC_GraphEnricherShutdown::test_shutdown_cancels_running_tracked_task; TestFromAC_GraphEnricherShutdown::test_shutdown_leaves_background_tasks_empty; TestFromAC_GraphEnricherShutdown::test_shutdown_with_no_tasks_returns_immediately | PASS |

### Verdict: PASS

### Action Taken

- Review evidence appended.
- Task advanced to docs and claim released.

[[2026-03-26]] Thu 13:26

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. bootstrap/knowledge.py registers enricher.shutdown in cleanup when enricher is not None | Spot-checked knowledge.py:183-184: cleanup.append(enricher.shutdown) guarded by if cleanup is not None. Confirmed via read_file. | PASS |
| 2. Daemon shutdown path invokes enricher.shutdown via BootstrapResult.cleanup | toolsets.py:174 forwards cleanup into knowledge_kwargs. Reviewer verified daemon.py:81-84 iterates and awaits cleanup callbacks. | PASS |
| 3. No orphaned enrichment tasks after daemon stop | Spot-checked enrichment.py:142-149: shutdown() sets _shutdown, cancels all tracked tasks, gathers with return_exceptions, clears tracking set. | PASS |

### Test Results

- pytest full suite: 4509 passed, 90 failed (all pre-existing RED-phase, none related to #998), 1 ignored (entity_extractor_corpus RED placeholder)
- ruff: all checks passed on AC-related files

### AC Quality Score: 4/5

AC was specific, file-referenced, and verifiable. Minor deduction: task was redundant since #1000 already implemented all 3 items (green on arrival).

### Reviewer Quality

Detailed Pass 1/Pass 2 evidence table with mapped tests, mutation reasoning, security review, and test integrity checks. High quality.

### Confidence: .97

### Action: archive
