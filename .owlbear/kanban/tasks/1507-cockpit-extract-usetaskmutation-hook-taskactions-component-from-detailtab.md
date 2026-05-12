---
id: 1507
title: 'Cockpit: Extract useTaskMutation hook + TaskActions component from DetailTab'
status: backlog
priority: needed
created: 2026-05-12T03:04:44.023243+00:00
updated: 2026-05-12T08:56:42.827553+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on:
  - 1493
  - 1506
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract mutation orchestration and action buttons from DetailTab.tsx into two focused modules (~130 LOC total).

## Scope
- **useTaskMutation.ts** (hooks/): wraps runMutation + previousStatus + serverValidationMessage management
- **TaskActions.tsx** (components/): unclaim/unblock/move-backward buttons + ConfirmDialog wiring

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `useTaskMutation.ts` exists in `hooks/` and exports the hook
- [ ] `TaskActions.tsx` exists in `components/` and renders action buttons with ConfirmDialog
- [ ] `DetailTab.tsx` imports and delegates to both new modules
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint
2026-05-12T08:56:35+00:00
## Research
- Research doc: .owlbear/research/cockpit-mutation-hook-extraction.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useRepairFlow/useCleanupFlow patterns, #1506 research, ConfirmDialog)
- Recommendation: Extract using action-callback pattern for conflict coupling, matching useRepairFlow/useCleanupFlow precedent — confidence 0.88
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: none needed — #1507 is the implementation task, sibling #1508 exists
- Decision requests: none

## Challenge Results
- Challenge: skipped — T1 pure refactoring, no option selection, established in-repo patterns
- Key findings: runMutation couples to conflict state via 3 action callbacks (clearConflict, setConflictDetected, setConflictDetectedNoRefetch); TaskActions owns confirmType state + focus management + ConfirmDialog wiring; ~80 LOC each
2026-05-12T08:56:42+00:00
Research complete. Identified precise extraction boundaries for useTaskMutation hook (~80 LOC: serverValidationMessage state, previousStatus function, runMutation with conflict action callbacks) and TaskActions component (~80 LOC: confirmType state, focus management, 3 action buttons, ConfirmDialog wiring). T1 pure refactoring following established patterns. Confidence 0.88. Doc: .owlbear/research/cockpit-mutation-hook-extraction.md