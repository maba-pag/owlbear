---
id: 1686
title: Clarify kanban lane color meaning
status: done
priority: important
created: 2026-05-21T19:52:28.209451+02:00
updated: 2026-05-21T23:09:27.063764+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - visual-system
parent:
depends_on: []
ac:
  - Audit current lane accent colors and their source/mapping.
  - Classify whether colors carry real semantics or decorative ambiguity.
  - Adopt a consistent lane color system with documented product meaning.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The colors above Kanban columns/lanes need explanation. Do those specific colors have meaning? If not, why are they varied but not a rainbow, increasing scale, or just Porsche red?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual-system ambiguity.
- Value question: lane color should communicate workflow/status meaning, reinforce brand, or disappear; decorative arbitrary color weakens trust.
- Screenshot target: full Kanban header/lane row across all lanes.

## Acceptance Criteria
- Identify current lane color mapping and whether it has semantic meaning.
- Choose a consistent visual system: semantic, restrained brand, or no lane accent.
- Document the rationale and ensure color does not imply false status meaning.

[[2026-05-21T23:09:17+02:00]]
## Builder Evidence
- Classification: observed current visual-system ambiguity, not theoretical. Screenshots showed each Kanban lane had a different top accent color while the UI provided no legend or behavior explaining the mapping.
- Impact: hurt Cockpit now by making decorative lane color look semantic; it also hurt the plan for a trustworthy cockpit visual system because warning/error/success-style colors should be reserved for real attention states.
- Audit finding: `Column.tsx` hard-coded per-status lane accent classes (`warning`, `error`, `primary`, `success`, and custom claimed tone). Those colors did not drive workflow behavior; actual workflow state is already visible through lane titles, counts, task cards, and drag/drop affordances.
- Implementation: neutralized lane accents to one restrained contrast tone while preserving drag/drop success feedback and card-level alert colors for blocked, pending decision, claimed, dependencies, and priority rail signals.
- Screenshot evidence: `.owlbear/scratch/1680-route-kanban-desktop.png`, `.owlbear/scratch/1680-route-kanban-mobile.png`.
- Validation: `npm test -- --run src/__tests__/Column.test.tsx src/__tests__/BoardVisualDesign.test.tsx --reporter=dot` (24 passed); `npm run build` passed with existing Vite chunk-size warning; `npm run test:e2e:all -- e2e/accessibility-sweep.spec.ts --grep "board view" --reporter=line` (1 passed); `npx eslint src/components/Column.tsx src/__tests__/Column.test.tsx` passed.
