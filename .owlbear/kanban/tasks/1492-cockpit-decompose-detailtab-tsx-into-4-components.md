---
id: 1492
title: 'Cockpit: Decompose DetailTab.tsx into 4 components'
status: todo
priority: important
created: 2026-05-11T23:15:07.557623+00:00
updated: 2026-05-12T14:33:03.165870+00:00
tags:
  - cockpit
  - frontend
  - refactor
  - quality
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Split 598-line DetailTab.tsx into focused components.

## Acceptance Criteria
- DetailTab.tsx → ~80 LOC container
- TaskFieldsEditor.tsx (~200 LOC) — title, priority, body, deps, parent, block_reason editing
- ConflictBanner.tsx + useConflictDraft.ts (~120 LOC) — OCC conflict detection, draft preservation, merge UI
- TaskActions.tsx (~80 LOC) — claim/release/archive buttons
- HistorySubtab.tsx stays as-is (already separated)

## Source
Cockpit audit 2026-05-11, Finding F2
2026-05-12T03:05:24+00:00
## Planning

Decomposed into 3 sequential subtasks at `research` status:

| # | ID | Title | Deps | ~LOC |
|---|-----|-------|------|------|
| 1 | #1506 | Extract useConflictDraft + ConflictBanner | #1493 | ~120 |
| 2 | #1507 | Extract useTaskMutation + TaskActions | #1493, #1506 | ~130 |
| 3 | #1508 | Extract TaskFieldsEditor + reduce DetailTab | #1493, #1506, #1507 | ~260 |

Dependency graph:
```
#1493 (API centralization)
  └─► #1506 (conflict hook+banner)
        └─► #1507 (mutation hook+actions)
              └─► #1508 (fields editor + container reduction)
```

All tasks: priority=needed, parent=#1492, tags=cockpit,frontend,refactor, status=research.
2026-05-12T03:05:54+00:00
## Research
- Research doc: .owlbear/research/cockpit-detailtab-decomposition.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useCleanupFlow pattern, #1493 research, ConfirmDialog precedent)
- Recommendation: Custom hooks + components (Option B) — confidence 0.85
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: #1506, #1507, #1508 (sequential decomposition)
- Challenge: skipped — established pattern, no trade-off ambiguity
2026-05-12T08:54:22+00:00

## Refined Acceptance Criteria (Tracker)
_Supersedes original AC. Parent tracker task — implementation AC lives in child tasks #1506, #1507, #1508._

- AC-1 (P2): Child task #1506 (useConflictDraft + ConflictBanner extraction) reaches `done` status
- AC-2 (P2): Child task #1507 (useTaskMutation + TaskActions extraction) reaches `done` status
- AC-3 (P2): Child task #1508 (TaskFieldsEditor + DetailTab container reduction) reaches `done` status

Proof bundle: skip

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tracker for DetailTab decomposition feature |
| Interface clarity | PASS | AC references child task completion, not implementation details |
| Dependency correctness | PASS | Removed redundant depends_on [1493] — children #1506-#1508 carry that dependency transitively |
| Module layering | N/A | No code produced by tracker |
| TDD compliance | N/A | No code produced; children carry implementation AC. Each child gates on "All 7 existing DetailTab test files pass unchanged" — existing tests serve as consolidation regression gate |
| KISS/YAGNI | PASS | Minimal tracker semantics |
| Premise challenge | PASS | DetailTab.tsx is ~630 LOC monolith with 4 distinct concerns (conflict handling, mutation, field editing, actions). Decomposition follows established useCleanupFlow/useRepairFlow patterns in hooks/ |
| Pattern consistency | PASS | Standard parent/tracker task pattern. Children follow established hook extraction pattern (useRepairFlow, useCleanupFlow precedent) |
| Security surface | N/A | No code produced |
| Single domain | PASS | Frontend component domain |

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: skip (parent/tracker task, no code produced)
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Notes
- Lesson from #1493: tracker tasks with child-completion AC and proof bundle skip advance cleanly through test-writer and builder as pass-throughs. AC-1..AC-3 are verifiable at the reviewer/auditor stage via show_task status checks on children.
- Removed direct depends_on [1493] from parent — all three children already depend on #1493 (API centralization). Transitive dependency is sufficient; direct dependency was redundant.
- Consolidation-test gap: NOT APPLICABLE. Each child AC requires existing DetailTab test files to pass unchanged. These 7 test files serve as the integration/regression gate across the sequential decomposition. No separate consolidation test task needed.
- Children #1506 (backlog), #1507 (research), #1508 (research) will receive individual architecture reviews as they reach backlog.

### Verdict: REFINE + APPROVE
### Action Taken: Rewrote implementation-level AC as tracker-level process criteria, tagged `quality` for pipeline pass-through, removed redundant depends_on [1493], set proof bundle skip, advanced to todo.

2026-05-12T08:54:27+00:00
Architecture review complete. REFINE + APPROVE: Rewrote implementation-level AC as tracker-level process criteria (child-completion gates for #1506, #1507, #1508). Tagged `quality` for pipeline pass-through, removed redundant depends_on [1493] (children carry it transitively), proof bundle: skip. Challenger: SKIPPED (skip bundle). Consolidation-test gap: N/A — existing DetailTab test suite (7 files) gates each subtask.
2026-05-12T09:12:06+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/tracker task — all implementation AC lives in child tasks #1506, #1507, #1508.
- Passing through to builder.
2026-05-12T09:54:51+00:00
## Builder Notes

Tracker/pass-through task (`Proof bundle: skip`) evaluated with no code changes.

AC gate check for #1492:
- AC-1 requires child #1506 at `done` -> current status: `in-progress`
- AC-2 requires child #1507 at `done` -> current status: `in-progress`
- AC-3 requires child #1508 at `done` -> current status: `research`

Result: AC not yet satisfiable, so builder cannot advance #1492 to review.

Files changed: none
Tests run: none (pass-through tracker task)
Lint: not run (no code changes)
Evidence summary: child completion gate unmet; return to `todo` until #1506, #1507, #1508 reach `done`.
2026-05-12T10:09:16+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/tracker task — all implementation AC lives in child tasks #1506, #1507, #1508.
- Child status at pass-through: #1506 review, #1507 in-progress, #1508 backlog.
- Passing through to builder.
2026-05-12T10:56:38+00:00
## Builder Notes

Tracker/pass-through task (`Proof bundle: skip`) evaluated with no code changes.

AC gate check for #1492:
- AC-1 requires child #1506 at `done` -> current status: `in-progress`
- AC-2 requires child #1507 at `done` -> current status: `review`
- AC-3 requires child #1508 at `done` -> current status: `todo`

Result: AC not yet satisfiable, so builder cannot advance #1492 to review.

Files changed: none
Tests run: none (pass-through tracker task)
Lint: not run (no code changes)
Evidence summary: child completion gates unmet; return to `todo` until #1506, #1507, #1508 reach `done`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Re-run tracker pass-through once child task #1506 reaches `done` | .owlbear/kanban/tasks/1506.md | #1492 AC-1 gate unmet (child status `in-progress`) |
| 2 | builder | Re-run tracker pass-through once child task #1507 reaches `done` | .owlbear/kanban/tasks/1507.md | #1492 AC-2 gate unmet (child status `review`) |
| 3 | builder | Re-run tracker pass-through once child task #1508 reaches `done` | .owlbear/kanban/tasks/1508.md | #1492 AC-3 gate unmet (child status `todo`) |
2026-05-12T11:31:38+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/tracker task — all implementation AC lives in child tasks #1506, #1507, #1508.
- Child status at pass-through: #1506 in-progress (builder returned), #1507 review, #1508 todo.
- Passing through to builder.
2026-05-12T12:00:19+00:00
## Builder Notes

Tracker/pass-through task (`Proof bundle: skip`) evaluated with no code changes.

AC gate check for #1492:
- AC-1 requires child #1506 at `done` -> current status: `backlog`
- AC-2 requires child #1507 at `done` -> current status: `review`
- AC-3 requires child #1508 at `done` -> current status: `review`

Result: AC not yet satisfiable, so builder cannot advance #1492 to review.

Files changed: none
Tests run: none (pass-through tracker task)
Lint: not run (no code changes)
Evidence summary: child completion gates unmet; return to `todo` until #1506, #1507, #1508 reach `done`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Re-run tracker pass-through once child task #1506 reaches `done` | .owlbear/kanban/tasks/1506.md | #1492 AC-1 gate unmet (child status `backlog`) |
| 2 | builder | Re-run tracker pass-through once child task #1507 reaches `done` | .owlbear/kanban/tasks/1507.md | #1492 AC-2 gate unmet (child status `review`) |
| 3 | builder | Re-run tracker pass-through once child task #1508 reaches `done` | .owlbear/kanban/tasks/1508.md | #1492 AC-3 gate unmet (child status `review`) |
2026-05-12T12:39:59+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/tracker task — all implementation AC lives in child tasks #1506, #1507, #1508.
- Child status at pass-through: #1506 backlog, #1507 review, #1508 review.
- Passing through to builder.
2026-05-12T13:10:22+00:00
## Builder Notes

Tracker/pass-through task (`Proof bundle: skip`) evaluated with no code changes.

AC gate check for #1492:
- AC-1 requires child #1506 at `done` -> current status: `review`
- AC-2 requires child #1507 at `done` -> current status: `todo`
- AC-3 requires child #1508 at `done` -> current status: `review`

Result: AC not yet satisfiable, so builder cannot advance #1492 to review.

Files changed: none
Tests run: none (pass-through tracker task)
Lint: not run (no code changes)
Evidence summary: child completion gates unmet; return to `todo` until #1506, #1507, #1508 reach `done`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Re-run tracker pass-through once child task #1506 reaches `done`. | .owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md | AC-1 gate unmet (child status `review`) |
| 2 | builder | Re-run tracker pass-through once child task #1507 reaches `done`. | .owlbear/kanban/tasks/1507-cockpit-extract-usetaskmutation-hook-taskactions-component-from-detailtab.md | AC-2 gate unmet (child status `todo`) |
| 3 | builder | Re-run tracker pass-through once child task #1508 reaches `done`. | .owlbear/kanban/tasks/1508-cockpit-extract-taskfieldseditor-reduce-detailtab-to-container.md | AC-3 gate unmet (child status `review`) |
2026-05-12T13:43:47+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/tracker task — all implementation AC lives in child tasks #1506, #1507, #1508.
- Child status at pass-through: #1506 review, #1507 todo, #1508 review.
- Passing through to builder.
2026-05-12T14:33:03+00:00
## Builder Notes

Tracker/pass-through task (`Proof bundle: skip`) evaluated with no code changes.

AC gate check for #1492:
- AC-1 requires child #1506 at `done` -> current status: `docs`
- AC-2 requires child #1507 at `done` -> current status: `docs`
- AC-3 requires child #1508 at `done` -> current status: `todo`

Result: AC not yet satisfiable, so builder cannot advance #1492 to review.

Files changed: none
Tests run: none (pass-through tracker task)
Lint: not run (no code changes)
Evidence summary: child completion gates unmet; return to `todo` until #1506, #1507, #1508 each reach `done`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Re-run tracker pass-through once child task #1506 reaches `done`. | .owlbear/kanban/tasks/1506-cockpit-extract-useconflictdraft-hook-conflictbanner-component-from-detailtab.md | AC-1 gate unmet (child status `docs`) |
| 2 | builder | Re-run tracker pass-through once child task #1507 reaches `done`. | .owlbear/kanban/tasks/1507-cockpit-extract-usetaskmutation-hook-taskactions-component-from-detailtab.md | AC-2 gate unmet (child status `docs`) |
| 3 | builder | Re-run tracker pass-through once child task #1508 reaches `done`. | .owlbear/kanban/tasks/1508-cockpit-extract-taskfieldseditor-reduce-detailtab-to-container.md | AC-3 gate unmet (child status `todo`) |