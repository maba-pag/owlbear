---
task_id: 1606
agent: builder
request_type: decision
created: '2026-05-17'
response: pending
---

Status quo: #1606 AC tests (shell-layout-1606.spec.ts) are fully green (15/15), but overlapping durable suite responsive-layout-1391.spec.ts still fails on two mobile reachability assertions.

Problem: One failing assertion is outside #1606 shell scope and requires KanbanBoard behavior change:
- board column container overflow at 320px expects no internal horizontal scrolling, but current container is 1400px scrollWidth vs 320px clientWidth (KanbanBoard grid: repeat(7, minmax(200px, 1fr))).
- detail-placeholder at 320px is null when mobile sheet is closed by default (selectedTaskId=null).

Decision needed:
1) Keep #1606 scope strict (shell-only) and remove/relax overlapping 1391 mobile reachability gate for this task.
2) Expand #1606 scope to include KanbanBoard mobile behavior and sidecar-detail visibility changes.
3) Create follow-up task for KanbanBoard/mobile reachability contract while allowing #1606 to close on its own AC evidence.

Recommendation: Option 1 or 3. #1606 AC lines are satisfied; enforcing 1391 mobile board-scroller behavior in this task couples unrelated domain scope and creates recurring false-negative review loops.

Evidence:
- quality-runner task-local: shell-layout-1606.spec.ts => 15 passed, 0 failed
- quality-runner overlap: responsive-layout-1391.spec.ts => 2 failed
- failing values: board container clientWidth=320, scrollWidth=1400; detail-placeholder boundingBox=null at 320px.