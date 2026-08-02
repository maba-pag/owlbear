---
id: 1688
title: Redesign decisions workspace workflow
status: archived
priority: medium
created: 2026-05-21T19:52:44.922500+02:00
updated: 2026-05-24T10:50:01.091312+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - decisions
parent:
depends_on: []
ac:
  - Audit the Decisions workspace against the user goal of understanding and
    deciding on DRs.
  - Define the minimum information architecture for a high-quality decision
    workflow.
  - Redesign the page and action path using PDS where it helps and custom dense
    rows where needed.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
The Decisions page is not ready for real feedback: it appears to have no functionality and no real design, fonts feel wrong, structure is missing. Think about what is needed for the user to understand the decision request and make a decision; `requested by` is definitely not enough.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current page-level product deficiency.
- Value question: the Decisions workspace should help a user understand context, stakes, options, recommended response, and action path quickly.
- Screenshot target: Decisions route with realistic pending DRs, resolve modal/page flow, empty state.

## Acceptance Criteria
- Define the intended Decisions workspace workflow from notification to resolution.
- Surface DR context, task link, request type, options, recommendation, and consequences clearly.
- Replace weak metadata emphasis such as `requested by` if it does not help decision quality.

[[2026-05-21T21:53:03+02:00]]
## Builder Evidence
- Classification: observed current page-level product deficiency, not theoretical. The old Decisions route exposed weak metadata (`requested by`) without enough context/options/stakes for actual resolution.
- Impact: hurt Cockpit now and hurt the route-owned Decisions plan, because `/decisions` is the primary decision-resolution workspace after removing the global DR menu.
- Implementation: pending DR rows now render a decision brief with request type, task, age/agent, context, options, recommendation, consequence, and a clear Resolution action path into the existing ResolveModal.
- Design decision: full resolution remains in ResolveModal; the route row previews the decision quality information so the list stays dense and scannable.
- Screenshot evidence: `.owlbear/scratch/1680-route-decisions-desktop.png`, `.owlbear/scratch/1680-route-decisions-mobile.png`.
- Validation: `npm test -- --run src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/DecisionsPage_1645.test.tsx src/__tests__/DecisionsTab.integration.test.tsx --reporter=dot` (54 passed); `npm run build` passed with existing Vite chunk-size warning; `npm run test:e2e:all -- e2e/accessibility-sweep.spec.ts --reporter=line` passed on final rerun (10 passed); `npm run test:e2e:all -- e2e/accessibility-dual-theme.spec.ts --reporter=line` (26 passed); `npm run test:e2e:all -- e2e/shell-sidecar-inspector.spec.ts --reporter=line` (18 passed); `npm run test:e2e:all -- e2e/overlay-behavior.spec.ts --reporter=line` (21 passed).
