---
id: 1507
title: 'Cockpit: Extract useTaskMutation hook + TaskActions component from DetailTab'
status: research
priority: needed
created: 2026-05-12T03:04:44.023243+00:00
updated: 2026-05-12T03:05:16.531733+00:00
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