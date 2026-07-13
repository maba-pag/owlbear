---
id: 1735
title: Improve Kanban active-work initial positioning
status: archived
priority: medium
created: 2026-05-23T04:24:00+0200
updated: 2026-05-24T10:50:01.743104+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - layout
parent:
depends_on: []
ac:
  - Reproduce the current Kanban first viewport showing active In Progress work
    as the fourth column while earlier empty lanes dominate the screen.
  - Adjust initial horizontal alignment so the first active non-empty work lane
    is prominent without hiding useful adjacent context.
  - Preserve horizontal scrolling to all configured columns and preserve the
    previous no-leading-sliver fix.
  - Add or update focused tests for the initial scroll alignment policy.
  - Capture after-fix screenshot or metrics evidence at the desktop viewport.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## User Feedback Context
The post-memory visual sweep now shows the repaired task ledger, but the Kanban first viewport still spends most of its width on empty Research, Backlog, and Todo lanes. The active In Progress lane is visible but not visually anchored as the current work focus.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1733-kanban-desktop.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1733-desktop-sweep-metrics.json` reports 58 task cards and no document overflow, so this is an initial-positioning issue rather than a page sizing regression.

## Evaluation Notes
- Classification: observed current usability issue.
- Current harm: the primary task board opens with the user's current in-progress work visually de-emphasized behind empty setup lanes.
- Product value: improving first-glance task focus makes Cockpit more useful for exactly the ongoing polish workflow.

## Evidence After Fix
- Kanban initial alignment now keeps one leading context lane before the first non-empty work lane, unless the first lane itself is the first non-empty lane.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1735-kanban-active-position-after.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1735-kanban-active-position-after-metrics.json` reports document height 1000px, strip `overflowX: auto`, In Progress visible with task count 1, Done visible with task count 58, and `leadingFragment: null`.
- Focused Vitest passed: `src/__tests__/KanbanBoard.test.tsx`, 40 tests.
- ESLint passed for `src/KanbanBoard.tsx` and `src/__tests__/KanbanBoard.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.