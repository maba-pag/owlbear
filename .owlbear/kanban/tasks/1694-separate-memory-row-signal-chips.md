---
id: 1694
title: Separate memory row signal chips
status: done
priority: important
created: 2026-05-21T19:53:32.451580+02:00
updated: 2026-05-22T15:16:27+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - visual-system
parent:
depends_on: []
ac:
  - Audit Memory row chip grouping for tags, confidence, and state.
  - Separate content tags from workflow/trust signals visually or spatially.
  - Strengthen state distinction only when it improves scan speed and meaning.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Memory row bubbles for tags, confidence, and state are mixed together. Tags together are fine, but confidence and state blend in too much. Separate them or give them stronger color difference; differences between states could help.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current scanability issue.
- Value question: tags classify content, confidence expresses trust, and state expresses workflow; they should not read as the same kind of chip.
- Screenshot target: Memory list rows with mixed states, confidence values, and multiple tags.

## Acceptance Criteria
- Audit current row chip grouping and color semantics.
- Visually separate tags, confidence, and state by grouping, placement, or tone.
- Use state differences where they improve scan speed without becoming noisy.

## Builder Evidence
- Product audit: categories now stay with the row context in `memory-entry-category-group`, while confidence and workflow state render in a separate `memory-entry-signal-group` with a desktop divider.
- Trust/workflow distinction: confidence now carries an explicit `Confidence` label, and state uses PDS `PTag` variants (`pending=info`, `curated=secondary`, `approved=success`, `deleted=primary`) instead of sharing the same neutral chip treatment.
- Regression coverage: focused row signal tests passed (`6 passed, 45 skipped`); broader Memory route/detail suites passed (`128 passed`).
- Quality gates: diagnostics clean for `MemoryTab.tsx` and `MemoryTab_1671.test.tsx`; ESLint passed for both files; `npm run build` passed with the known Vite chunk-size warning.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/memory-row-signals-1694.png`; browser capture reported 0 console errors, 0 page errors, 0 request failures, and 0 response errors.
