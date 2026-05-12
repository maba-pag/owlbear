---
id: 1508
title: 'Cockpit: Extract TaskFieldsEditor + reduce DetailTab to container'
status: research
priority: needed
created: 2026-05-12T03:04:44.051072+00:00
updated: 2026-05-12T03:05:16.547795+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on:
  - 1493
  - 1506
  - 1507
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract field editing UI and reduce DetailTab.tsx to a thin container (~260 LOC extraction, ~80 LOC remaining).

## Scope
- **TaskFieldsEditor.tsx** (components/): field inputs (title, priority, body, deps, parent, block_reason) + parsers + isDirty + readControlValue + body edit toggle
- **DetailTab.tsx** reduced to ~80 LOC container wiring hooks → components
- Re-export TaskDetail type from DetailTab.tsx for backward compat

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `TaskFieldsEditor.tsx` exists in `components/` and handles all field editing
- [ ] `DetailTab.tsx` ≤ 100 LOC (container only)
- [ ] `TaskDetail` type re-exported from `DetailTab.tsx` for backward compatibility
- [ ] `Shell.tsx` import of DetailTab unchanged
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint