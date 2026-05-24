---
id: 1693
title: Emphasize memory detail content
status: archived
priority: important
created: 2026-05-21T19:53:24.732852+02:00
updated: 2026-05-24T10:50:01.154070+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - information-architecture
parent:
depends_on: []
ac:
  - Audit expanded Memory detail hierarchy with realistic entry content.
  - Make actual memory text visually primary relative to metadata.
  - Preserve metadata availability without letting it dominate the detail view.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Memory page looks and works pretty good, but actual memory text in the detail view could be more prominent. It is hard to quickly differentiate the memory content from metadata.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current information hierarchy issue.
- Value question: memory content is the primary payload; metadata should support trust/filtering without visually competing.
- Screenshot target: expanded Memory accordion detail with realistic long and short entries.

## Acceptance Criteria
- Audit detail view hierarchy between content and metadata.
- Make memory content the primary visual block in expanded rows.
- Keep metadata scannable but secondary.

## Builder Evidence
- Product audit: expanded Memory rows now render the markdown memory body first in a bordered `memory-content-panel` with larger body rhythm, then render provenance fields in a compact secondary `memory-metadata-grid`.
- Metadata remains available for ID, source agent, scope agents, categories, confidence, state, created, updated, and approved timestamps without sharing the same visual block as the memory text.
- Regression coverage: focused detail hierarchy test passed (`9 passed, 68 skipped`); broader Memory route/detail suites passed (`127 passed`).
- Quality gates: diagnostics clean for `MemoryTab.tsx` and `MemoryTab_1672.test.tsx`; ESLint passed for both files; `npm run build` passed with the known Vite chunk-size warning.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/memory-detail-content-1693.png`; browser capture reported 0 console errors, 0 page errors, 0 request failures, and 0 response errors.
