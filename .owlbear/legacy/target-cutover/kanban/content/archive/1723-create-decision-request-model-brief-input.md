---
id: 1723
title: Create decision request model brief input
status: archived
priority: medium
created: 2026-05-23T02:07:23+0200
updated: 2026-05-24T10:50:01.578333+02:00
tags:
  - cockpit-perfect-ui
  - scope:briefs
  - ux-feedback
  - decisions
  - mcp
  - ideation-input
parent:
depends_on: []
ac:
  - Capture the UX-driven gaps exposed by the Decisions route polish.
  - Create an ideation input file under `.owlbear/briefs/` for expanding the
    decision request data model, engine interface, and MCP interface.
  - Include decision vs action distinction, request IDs, full timestamp with
    timezone, structured options, confidence, response modes, and agent
    usability needs.
  - Keep the file usable as input for a later brief rather than presenting it as
    the final architecture.
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
The Decisions route needed frontend parsing hacks to produce good UX from request bodies. Create brief input so a future ideation run can design the backend model properly instead of relying on body parsing.

## Evaluation Notes
- Classification: real current product/design gap exposed by #1721.
- Product value: agents need a robust way to ask humans for decisions or actions, and Cockpit needs structured data to render the right resolver UI.
- This task produces an ideation input artifact, not the final implementation.

## Evidence
- Created `.owlbear/briefs/draft-decision-request-data-model/input/cockpit-ux-driven-decision-requests.md`.
- The input captures the current Cockpit body-parsing workaround, desired structured request concepts, candidate storage shape, engine methods, MCP tool surface, Cockpit UX implications, migration concerns, and ideation questions.
