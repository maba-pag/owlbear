---
id: 1729
title: Bound Kanban and Memory workspace height
status: done
priority: needed
type: bug
created: 2026-05-23T03:26:48+0200
updated: 2026-05-23T03:33:11+0200
assignee: copilot
tags:
  - cockpit
  - layout
  - ux-feedback
  - kanban
  - memory
---

## Problem
The post-markdown visual sweep shows Kanban and Memory expanding the entire document height instead of staying inside the Cockpit viewport with internal scroll regions. At a 1440x1000 viewport, Kanban produced a document height around 10,168px and Memory around 8,375px, while Decisions and Ideas stayed bounded at 1000px.

## Acceptance Criteria
- Kanban and Memory remain within the visible Cockpit workspace height at a 1440x1000 viewport.
- Long Kanban columns and the Memory entry list scroll inside their intended content regions rather than expanding the document.
- Decisions and Ideas keep their existing bounded behavior.
- Add or update focused frontend tests for the layout contract where practical.
- Capture after-fix screenshots and metrics for Kanban and Memory.

## Evidence Before Fix
- Screenshots: `.owlbear/scratch/1716-wide-cockpit/1728-kanban-desktop.png`, `.owlbear/scratch/1716-wide-cockpit/1728-memory-desktop.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1728-layout-depth-metrics.json`.

## Evidence After Fix
- PDS canvas host and shadow root/main are bounded to `100dvh` with hidden outer overflow so route content cannot expand the document.
- Kanban and Memory after-fix screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1729-kanban-bounded-after.png`
  - `.owlbear/scratch/1716-wide-cockpit/1729-memory-bounded-after.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1729-bounded-layout-after-metrics.json`.
- Metrics at 1440x1000: Kanban document height 1000px, Memory document height 1000px, Decisions document height 1000px, Ideas document height 1000px.
- Kanban column strip is bounded to 828px high; Memory list is bounded to 678px high with `overflow-y: auto` and scroll height 8053px.
- Focused Vitest passed: `src/__tests__/Shell.test.tsx`, 22 tests.
- ESLint passed for `src/Shell.tsx` and `src/__tests__/Shell.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
