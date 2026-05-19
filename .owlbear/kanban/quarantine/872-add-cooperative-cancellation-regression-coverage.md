---
id: 872
title: Add cooperative cancellation regression coverage for knowledge pipelines
status: archived
priority: nice-to-have
created: 2026-03-20T14:01:01.7596195+01:00
updated: 2026-03-26T16:16:10.1525523+01:00
tags:
    - scope:core
    - type:test
depends_on:
    - 870
    - 871
blocked: true
block_reason: 'Redundant: all 4 AC items already covered by tests from sibling tasks #870, #871, #880, #1000, #1006. Recommend closing or deleting.'
class: standard
---

**Source:** #733 cooperative-cancellation research

Add regression coverage for cooperative early-exit across the knowledge pipelines and daemon shutdown composition.

**AC:**

1. Tests cover `RefreshOrchestrator.refresh_all()` stopping before the next source or item when the cancellation signal is set.
2. Tests cover `BookmarkPipeline.process()` and/or `IngestPipeline._run_extract()` exiting at stage or chunk boundaries without swallowing outer `CancelledError`.
3. Tests cover daemon-shutdown composition or linked cancellation for a pipeline entry point.
4. Tests verify partial completed work is preserved and no orphan background enrichment tasks remain after cancellation.

[[2026-03-26]] Thu 12:21

## Architecture Review

**Verdict:** BLOCK -> ideation (redundant)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: refresh_all stops at source/item boundaries | Already covered by TestFromAC_RefreshCancellation (4 tests) in test_refresh_orchestrator.py | No new work needed |
| AC2: BookmarkPipeline/IngestPipeline stage/chunk exits | Already covered by TestFromAC_BookmarkCancellation (4 tests) + TestFromAC_IngestCancellation (3 tests) | No new work needed |
| AC3: daemon-shutdown composition / linked cancellation | Already covered by TestFromAC_870_BootstrapShutdownSignalWiring (2 tests) in test_bootstrap.py | No new work needed |
| AC4: partial work preserved, no orphan enrichment tasks | Already covered by bookmark stage-preservation tests, GraphEnricherCancelSignal tests, drain/shutdown tests (#871/#1000), cancel threading (#1006) | No new work needed |

### Architecture Notes

All four AC items map exactly to tests already written during the TDD RED/GREEN cycles of sibling tasks from the same #733 research lineage: #870 (CancelSignal protocol + bootstrap wiring), #871 (drain/shutdown), #880 (ingest cancellation), #1000 (enrichment cancellation), #1006 (cancel threading to enricher). This task is fully redundant and should be closed or deleted.

### Changes Made

- Blocked to ideation: work already done by sibling tasks

### Dependencies

- #733 (research): archived
- #870, #871, #880, #1000, #1006: all completed the test coverage this task describes

[[2026-03-26]] Thu 16:15

## Research

Researcher validated the architect's redundancy finding (2026-03-26).

**Finding:** All 4 AC items are covered at the unit-test level by tests from sibling tasks #870, #871, #880, #1000, #1006. The existing research doc (docs/research/cancellation-regression-coverage.md) identified 6 cross-module integration gaps (G1-G6), which are tracked by follow-up task #1007 (ideation). No work remains for #872 itself.

**Disposition:** Redundant. Recommend closing or deleting. Follow-up #1007 captures the only remaining gaps.

Test inventory across sibling tasks: ~54 tests covering cooperative cancellation (13 protocol, 4 refresh, 3 crawl, 3 ingest, 4 bookmark, 3 hook, 2 bootstrap, 14 enricher cancellation, 4 drain noop, 4 cancel threading).
