---
id: 1709
title: Fix invisible kanban tag overflow
status: archived
priority: medium
created: 2026-05-21T23:23:14.191883+02:00
updated: 2026-05-24T10:50:01.361568+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - cards
  - bug
parent:
depends_on: []
ac:
  - Reproduce the Kanban card tag visibility/overflow mismatch with browser
    evidence.
  - Fix tag preview layout so visible tags and overflow count remain truthful.
  - Validate card tag behavior across expanded/collapsed sidebar and wide/narrow
    widths.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
On Kanban task cards there seem to be invisible tags. When removing the sidebar on high resolution, a third tag can be seen in some tasks while the `+x` tag stays the same.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current rendering/overflow bug.
- Value question: tag previews should show a truthful visible count; overflow indicators must match actually hidden tags.
- Impact: hurts Cockpit now by making card metadata untrustworthy.
- Screenshot target: task cards with 3+ tags across sidebar collapsed/expanded and wide/narrow viewports.

## Acceptance Criteria
- Reproduce tag preview/overflow mismatch in browser screenshots.
- Make visible tag count and `+x` overflow count truthful across responsive widths.
- Ensure no hidden tag is counted as visible or vice versa.

[[2026-05-21T23:49:42+02:00]]
## Builder Evidence
- Classification: observed current rendering bug, not theoretical. Browser repro at 390px showed `card-tags` had `overflowX=hidden` and `whiteSpace=nowrap`; only the first preview tag was fully visible while two rendered preview tags were clipped and the overflow badge still read `+2`.
- Impact: hurt Cockpit now by making card metadata counts untrustworthy; it also hurt the plan for dense, scannable cards because hidden rendered tags looked like data loss.
- Repro evidence: `.owlbear/scratch/1709-tags-repro.png`; metrics: group width 207px, clippedCount=2, `scope:cockpit-web` and `ux-feedback` clipped.
- Implementation: changed the tag preview wrapper from clipped nowrap text to a wrapping flex row. The card still renders at most three preview tags, and `+x` now refers only to tags intentionally not rendered.
- Browser proof: `.owlbear/scratch/1709-tags-proof.png`; metrics after fix: `overflowX=visible`, `whiteSpace=normal`, group width 207px, clippedCount=0 for all three preview tags.
- Validation: focused Vitest passed (5 files, 84 tests); `npm run build` passed with existing Vite chunk-size warning; `npm run test:e2e:all -- e2e/card-density.spec.ts --grep "tag" --reporter=line` passed (10 tests); `npx eslint src/components/Card.tsx src/__tests__/Card.visual-treatment.test.tsx` passed.
