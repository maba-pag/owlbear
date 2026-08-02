---
id: 1809
title: Match memory metadata to task metadata
status: archived
priority: medium
created: 2026-05-24T07:33:29.083387+02:00
updated: 2026-05-24T10:50:02.749968+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - memory
  - metadata
  - discussion
parent: 1773
depends_on: []
ac:
  - Expanded Memory detail metadata appears in a bordered section with a clear
    heading, matching Kanban task detail metadata as closely as practical.
  - Memory metadata no longer appears as a loose unframed list inside the
    expanded detail.
  - Memory detail action spacing remains comfortable after the metadata block
    change.
  - Memory display and edit workflows remain unchanged.
  - Screenshot proof captures an expanded memory detail at the 1024px support
    floor.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback: expanded Memory details list metadata directly rather than presenting it in a metadata block. It should be almost identical to the Kanban task detail metadata block.

## Current Interpretation
Memory triage should use the same metadata section grammar as task details so users can scan identity/state/source fields consistently across Cockpit.

## User Direction
Implement this now along with the Memory action spacing fix.

[[2026-05-24T07:48:02+02:00]]
Implemented task-style Memory metadata: the loose metadata list is now a bordered `Metadata` section with `PHeading size="small"`, text-sm grid fields, and no line-heavy divider treatment. Display/edit workflows remain unchanged. Verified focused Memory/Decision/Shell suites (213 tests passed), ESLint, production build, DOM metrics, and real-click screenshot proof at `.owlbear/scratch/1716-wide-cockpit/1809-memory-click-open-1024.png` showing content, metadata, and action spacing together at the 1024px support floor.