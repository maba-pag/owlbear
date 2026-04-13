---
id: 841
title: Fix stale TestFromAC_TaskSummaryExcludes tests (created/updated in exclusion
  set)
status: backlog
priority: needed
created: '2026-04-12T15:36:21.009577+00:00'
updated: '2026-04-12T17:21:04.750541+00:00'
tags:
- type:test
- scope:mcp-kanban
parent: null
depends_on:
- 851
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `_EXCLUSION_FIELDS` in `test_tasksummary_model_801.py` removes `created` and `updated` (TaskSummary intentionally includes timestamps per model docstring)
- `test_excluded_fields_absent_from_schema` passes — exclusion set is `{"body", "claimed_by", "claimed_at", "file"}` only
- `test_temporal_fields_not_in_construction_output` is removed or rewritten to assert `created` and `updated` ARE present in `model_dump()` (matching actual model intent)
- Module-level docstring AC2 comment corrected to reflect actual exclusion set
- All `TestFromAC_TaskSummaryExcludes` tests pass after fix
- No other tests regress

## Context

Root cause: TaskSummary model (serve/kanban/src/owlbear_kanban/models.py:90-114) includes `created` and `updated` fields by design (docstring: "excludes body and claimed_by"). Tests written for task #801 incorrectly listed timestamps in `_EXCLUSION_FIELDS`.

Same root cause as #851 but different file/class scope.

File: `tests/test_tasksummary_model_801.py` (lines 60-160)
[[2026-04-12]]
Claimed in error — start_work returned a different backlog task (Fix stale TestFromAC_TaskSummaryExcludes / depends_on:[851]) instead of the expected review task (RED — Tests for BrowserContentFetcher + HttpxContentFetcher). Task left in backlog unchanged. Review proceeding via parent #830 which contains full build history and context.