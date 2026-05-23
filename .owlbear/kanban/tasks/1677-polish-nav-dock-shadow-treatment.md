---
id: 1677
title: Polish nav dock shadow treatment
status: done
priority: important
created: 2026-05-21T19:51:06.666942+02:00
updated: 2026-05-23T01:27:54+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - nav-rail
parent:
depends_on: []
ac:
  - Assess current nav dock shadow with realistic desktop screenshots.
  - Remove or tune any halo/clipped-shadow effect that weakens the premium 
    cockpit feel.
  - Record observed-vs-theoretical classification and visual evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The left menu icon group has a weird shadow around the group, especially around the topmost and bottommost icons.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI issue.
- Value question: does the dock container help orientation enough to justify any visible shadow, or should it become quieter/flatter?
- Screenshot target: desktop Cockpit with the left nav rail visible, light and dark if relevant.

## Acceptance Criteria
- Assess whether the current nav dock shadow hurts the intended premium cockpit feel.
- If changed, top and bottom icons should not look haloed, clipped, or visually heavier than middle icons.
- Document before/after screenshot evidence and rationale.

[[2026-05-21T20:02:46+02:00]]
## Implementation Evidence
- Classification: confirmed user-observed polish issue. Screenshot review showed the previous `shadow-lg` dock/`shadow-md` active item created a heavier halo around the grouped icon rail than the premium cockpit goal warrants.
- Change: removed the dock shadow and active-item shadow while preserving the rounded frosted custom rail surface, because PDS v4 does not provide a dense vertical app-rail primitive with badges.
- Screenshot proof: `.owlbear/scratch/1672-nav-dock-audit/root-1440x1000-nav-dock.png` after the change shows the dock without the top/bottom halo effect.
- Verification: `npm run test:e2e:all -- e2e/shell-layout-1606.spec.ts --grep "start sidebar" --reporter=line` passed 2 tests; `npm test -- --run src/__tests__/Shell.test.tsx src/__tests__/PdsMigration.test.tsx --reporter=dot` passed 94 tests / 3 skipped.

[[2026-05-23T01:27:54+02:00]]
## Status Reconciliation
- Re-audit: this task already had implementation evidence and verification but was still marked `research`.
- Current classification: done. No additional product change was needed before continuing with the newer Cockpit polish feedback.
