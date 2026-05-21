---
id: 1688
title: Redesign decisions workspace workflow
status: research
priority: important
created: 2026-05-21T19:52:44.922500+02:00
updated: 2026-05-21T19:52:44.922500+02:00
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
archival_reason:
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