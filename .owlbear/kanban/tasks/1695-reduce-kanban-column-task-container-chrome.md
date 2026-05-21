---
id: 1695
title: Reduce kanban column task container chrome
status: done
priority: important
created: 2026-05-21T20:21:27.887459+02:00
updated: 2026-05-21T23:27:17.265042+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - visual-system
parent:
depends_on: []
ac:
  - Audit populated Kanban columns for nested task-list container chrome.
  - Classify whether the white box/border is useful grouping or current visual 
    clutter.
  - Recommend remove/soften/keep with screenshot evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
In a Kanban column with tasks, the column shows a white box behind the tasks that forms a border around them. This feels like a lot and may not be needed. User explicitly does not want to decide this yet; bring it into analysis.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual-weight concern.
- Value question: does the inner task-list box help group cards or just add nested chrome inside already framed columns?
- Screenshot target: Kanban columns with and without tasks, especially Research/Todo with multiple cards.

## Acceptance Criteria
- Audit the visual value of the inner card-list background/border in populated columns.
- Compare it against the overall cockpit density and premium feel.
- Recommend whether to remove, soften, or keep the container chrome with screenshot evidence.

[[2026-05-21T23:27:11+02:00]]
## Builder Evidence
- Classification: observed current visual-weight concern, not theoretical. Screenshots showed Kanban lanes as framed boxes inside an already framed board, with dashed empty-state boxes adding a second nested container layer.
- Impact: hurt Cockpit now by making the primary task surface feel heavier and less premium; it also hurt the plan for a card-forward board because lane chrome competed with actual task cards.
- Decision: follow user-selected direction: drop boxes and soften columns into quiet lanes. Keep lane headers/counts, scroll body, card layout, and drag/drop success feedback.
- Implementation: removed outer lane contrast border/shadow, reduced the top accent to a quiet separator, removed density-based body color switching, and changed empty states from dashed boxes to quiet centered text.
- Screenshot evidence: `.owlbear/scratch/1680-route-kanban-desktop.png`, `.owlbear/scratch/1680-route-kanban-mobile.png`.
- Validation: `npm test -- --run src/__tests__/Column.test.tsx src/__tests__/BoardVisualDesign.test.tsx src/__tests__/KanbanBoard.test.tsx --reporter=dot` (64 passed); `npm run build` passed with existing Vite chunk-size warning; `npm run test:e2e:all -- e2e/accessibility-sweep.spec.ts --grep "board view" --reporter=line` (1 passed); `npx eslint src/components/Column.tsx src/__tests__/Column.test.tsx` passed.
