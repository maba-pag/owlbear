---
id: 1705
title: Clarify priority color semantics
status: archived
priority: medium
created: 2026-05-21T20:23:43.490277+02:00
updated: 2026-05-24T10:50:01.310650+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - visual-system
parent:
depends_on: []
ac:
  - Audit current priority color mapping and token usage.
  - Classify whether blue `important` communicates the intended priority
    meaning.
  - Align priority color semantics across Cockpit surfaces.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Why is the `important` priority bubble blue?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current color-semantic confusion.
- Value question: priority color should have an intentional scale or be neutral; blue may imply selected/info rather than importance.
- Screenshot target: priority chips in card and detail surfaces across priority values.

## Acceptance Criteria
- Audit current priority color mapping and what blue means in the cockpit token system.
- Decide whether priority should use neutral, severity scale, or no chip color.
- Align priority color semantics across card and detail surfaces.

## Outcome
- Audit: `important` and `needed` both mapped to PDS `info` in `priorityToVariant`, which made the task-detail priority chip blue. Cockpit already uses blue/info for status-like flow states such as backlog, in-progress, and review, so blue read as informational/selection state rather than priority meaning.
- Decision: priority color is an escalation scale, not a generic category color. `someday`, `nice-to-have`, and `important` are neutral secondary; `needed` is warning; `critical` is error.
- Alignment: task-detail priority chips use the updated shared `priorityToVariant` mapping, and ready Kanban card rails now use the same threshold: neutral for `important`, warning for `needed`, error for `critical`.

## Evidence
- Red proof: `npx vitest run src/__tests__/CardVariants.test.ts src/__tests__/Card.visual-treatment.test.tsx --testNamePattern="priorityToVariant|important cards|needed cards"` failed because `important`/`needed` still returned blue `info` and ready `important` cards used warning rail semantics.
- Focused green: same command passed after the mapping and rail update, 12 passed tests.
- Affected regression: `npx vitest run src/__tests__/CardVariants.test.ts src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx src/__tests__/CardSignalModel.test.tsx src/__tests__/Shell.test.tsx` passed, 112 tests.
- Quality: `npx eslint src/utils/cardVariants.ts src/components/Card.tsx src/__tests__/CardVariants.test.ts src/__tests__/Card.visual-treatment.test.tsx`, `npm run lint:css`, and `npm run build` passed. Build retained only the known Vite chunk-size warning.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/priority-semantics-1705.png` at 2560x1440 shows task #1705 with neutral gray `Important` chip; browser diagnostics were empty and DOM evidence reported `variant="secondary"` for `Important` plus `border-l-contrast-medium` for the ready card rail.
