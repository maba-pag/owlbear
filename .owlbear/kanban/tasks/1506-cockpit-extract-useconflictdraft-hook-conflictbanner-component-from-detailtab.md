---
id: 1506
title: 'Cockpit: Extract useConflictDraft hook + ConflictBanner component from DetailTab'
status: research
priority: needed
created: 2026-05-12T03:04:43.984524+00:00
updated: 2026-05-12T03:05:16.512676+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on:
  - 1493
blocked: false
block_reason:
claimed_at:
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