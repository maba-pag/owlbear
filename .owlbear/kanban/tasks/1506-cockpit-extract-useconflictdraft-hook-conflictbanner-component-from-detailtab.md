---
id: 1506
title: 'Cockpit: Extract useConflictDraft hook + ConflictBanner component from DetailTab'
status: backlog
priority: needed
created: 2026-05-12T03:04:43.984524+00:00
updated: 2026-05-12T09:13:34.667842+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on:
  - 1493
blocked: false
block_reason:
claimed_at: 2026-05-12T09:13:34.667842+00:00
archival_reason:
archival_refs: []
---

## Objective
Extract conflict-detection state and UI from DetailTab.tsx into two focused modules (~120 LOC total).

## Scope
- **useConflictDraft.ts** (hooks/): manages conflictLocalDraft, conflictRemoteTask, showConflict, showConflictOverwrite, conflictChangedFields, conflictRemoteValues/conflictLocalValues
- **ConflictBanner.tsx** (components/): conflict diff display, acknowledge/discard/force-save buttons

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `useConflictDraft.ts` exists in `hooks/` and exports the hook
- [ ] `ConflictBanner.tsx` exists in `components/` and renders conflict diff + action buttons
- [ ] `DetailTab.tsx` imports and delegates to both new modules
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint
2026-05-12T08:28:18+00:00
## Research
- Research doc: .owlbear/research/cockpit-conflict-hook-extraction.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useRepairFlow/useCleanupFlow patterns, conflict test files)
- Recommendation: Extract using action-function pattern (not raw setters), matching useRepairFlow/useCleanupFlow precedent — confidence 0.88
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: none needed — #1506 is the implementation task, siblings #1507/#1508 exist
- Decision requests: none

## Challenge Results
- Challenge: skipped — T1 pure refactoring, no option selection, established in-repo patterns
- Key findings: useEffect boundary split (field-restore vs conflict-cleanup) is the main implementation subtlety; hook exposes clearConflictIfTaskChanged(taskId) action for DetailTab's effect to call; ConflictBanner preserves all data-testid attributes for zero test impact