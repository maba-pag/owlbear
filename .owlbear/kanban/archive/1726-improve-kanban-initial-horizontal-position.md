---
id: 1726
title: Improve kanban initial horizontal position
status: archived
priority: important
created: 2026-05-23T02:51:20+0200
updated: 2026-05-24T10:50:01.618315+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - layout
parent:
depends_on: []
ac:
  - Reproduce the Kanban board opening with all populated task cards outside the
    initial viewport when only later columns contain work.
  - Improve the initial horizontal position or affordance so the first useful
    content is reachable without guesswork.
  - Preserve the desktop-only multi-column board layout and horizontal scrolling
    behavior.
  - Validate with focused checks and desktop screenshot evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback Context
The desktop Cockpit sweep showed the Kanban route opening on empty Research/Backlog/Todo/In Progress/Review columns while all 48 visible task cards are in Done off to the right.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/sweep-kanban-20260523.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/sweep-tabs-20260523.json` reports 48 visible task cards in the route text, but none are visible in the first viewport crop.

## Evaluation Notes
- Classification: current usability/layout issue.
- Product value: the board should lead users to useful content, especially when filters or workflow state concentrate cards in a later column.
- Possible directions: scroll to the first non-empty column on load/filter changes, add a compact overview/rail, or make empty leading columns collapse under certain filtered states.

## Evidence
- Kanban board now auto-aligns the horizontal column strip to the first non-empty column when that column would otherwise be outside the visible strip.
- The fix preserves all status columns and the existing desktop horizontal scroll behavior.
- Focused Vitest passed: `KanbanBoard.test.tsx` and `KanbanBoard.filter-e2e.test.tsx`, 2 files, 52 tests.
- ESLint passed for `KanbanBoard.tsx` and `KanbanBoard.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
- Existing Playwright board-scroll contract passed: `e2e/board-scroll.spec.ts`, 3 tests.
- Live board screenshot after fix: `.owlbear/scratch/1716-wide-cockpit/1726-kanban-auto-aligned-after-fix.png`.
- Mocked done-only edge-case screenshot: `.owlbear/scratch/1716-wide-cockpit/1726-kanban-done-only-after-fix.png`.
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1726-kanban-done-only-after-fix-metrics.json` reports `stripScrollLeft: 496`, `doneColumnVisible: true`, and `doneCardVisible: true`.
