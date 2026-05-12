---
id: 1492
title: 'Cockpit: Decompose DetailTab.tsx into 4 components'
status: backlog
priority: important
created: 2026-05-11T23:15:07.557623+00:00
updated: 2026-05-12T03:05:54.295131+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent:
depends_on:
  - 1493
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