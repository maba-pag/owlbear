---
id: 1492
title: 'Cockpit: Decompose DetailTab.tsx into 4 components'
status: in-progress
priority: important
created: 2026-05-11T23:15:07.557623+00:00
updated: 2026-05-12T09:12:06.902548+00:00
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