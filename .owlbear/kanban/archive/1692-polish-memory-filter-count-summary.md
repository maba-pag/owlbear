---
id: 1692
title: Polish memory filter count summary
status: archived
priority: medium
created: 2026-05-21T19:53:18.742929+02:00
updated: 2026-05-24T10:50:01.141587+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
parent:
depends_on: []
ac:
  - Audit Memory count summary wording, order, and alignment with realistic
    counts.
  - Use concise count language that emphasizes what the user is seeing now.
  - Keep parse-error/filter context clear without text-heavy chrome.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Memory page count summary shows `109 entries / 94 shown`. This may be backwards, too text-heavy/verbose, and vertical alignment in the box is off.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI clarity/alignment issue.
- Value question: should the summary read as `94 of 109`, `94 shown`, or only appear when filters are active?
- Screenshot target: Memory header/filter count at realistic high entry counts.

## Acceptance Criteria
- Decide the most readable count order and when the count is valuable.
- Fix vertical alignment and reduce verbosity.
- Preserve clarity when filters hide entries or parse errors exist.

## Builder Evidence
- Product decision: the summary should lead with what the user is currently seeing. When filtering hides entries it now reads as one compact metric, e.g. `94 of 109 shown`; when every entry is visible it collapses to a simple total, e.g. `2 entries`.
- Parse-error context remains a separate compact header pill (`2 unreadable`) and the existing inline warning remains below filters, so unreadable files are visible without competing with the primary visible-count metric.
- Updated Memory header rendering to use a single `WorkspaceHeaderMetric` instead of detached `entries` and `shown` counters.
- Added tests for visible-of-total summary, all-visible total summary, parse-error context, and the existing PDS state-filter browser proof.
- Focused proof: `npx vitest run src/__tests__/MemoryTab_1671.test.tsx --testNamePattern="summary|PDS change|state filter" --reporter=dot` -> 6 passed, 0 failed.
- Browser proof: `npx playwright test e2e/memory-state-filter.spec.ts --project=chromium` -> 1 passed, 0 failed.
- Memory suite proof: `npx vitest run src/__tests__/MemoryTab_1671.test.tsx src/__tests__/MemoryTab_1672.test.tsx --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1692-vitest-memory-summary.json` -> 126 passed, 0 failed.
- Lint: `npx eslint src/pages/MemoryTab.tsx src/__tests__/MemoryTab_1671.test.tsx e2e/memory-state-filter.spec.ts` -> pass.
- Build: `npm run build` -> pass; existing Vite chunk-size warning only.
- Editor diagnostics clean for touched source, unit test, and e2e files.
- Desktop screenshot validation at 2560x1440: `.owlbear/scratch/1716-wide-cockpit/memory-count-summary-1692.png` shows `94 of 109 shown` with `2 unreadable` aligned in the Memory header. Capture reported 0 console errors, 0 page errors, and 0 request failures.