---
id: 1265
title: 'Fix stale test fixture in KanbanBoard_1242.test.tsx after #1227 API change'
status: backlog
priority: important
created: 2026-05-01T10:02:21.826578+00:00
updated: 2026-05-01T10:02:33.573956+00:00
tags:
- scope:frontend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Task #1227 changed KanbanBoard from internal-fetch to prop-based rendering. The task-scoped test file `serve/cockpit/web/src/__tests__/KanbanBoard_1242.test.tsx` still uses the old `renderBoard()` pattern that renders `<KanbanBoard />` with no props, causing all 8 tests to fail with "Loading…". The durable suite `KanbanBoard.test.tsx` was updated with a `Harness` component that passes `board`, `tasks`, `loading`, `error`, and `refetchTasks` as props.

Additionally, the test-writer retry added an 8th test (brief F3 timing-split proof, lines 367-480) that was never committed (only exists as an uncommitted working-tree change).

## Acceptance Criteria

- [ ] Update `renderBoard()` in `KanbanBoard_1242.test.tsx` to use the prop-based Harness pattern from the durable suite
- [ ] Commit the 8th test (brief F3 timing-split proof) or re-write it to work with the new pattern
- [ ] All 8 tests pass in the current codebase
- [ ] No regressions in the durable `KanbanBoard.test.tsx` suite