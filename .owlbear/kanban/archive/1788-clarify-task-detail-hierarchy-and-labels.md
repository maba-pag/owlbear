---
id: 1788
title: Clarify task detail hierarchy and labels
status: archived
priority: medium
created: 2026-05-24T01:57:03.645306+02:00
updated: 2026-05-24T10:50:02.470203+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - discussion
parent: 1773
depends_on: []
ac:
  - Task detail title, status, priority, and tags have clear visual hierarchy
    and spacing.
  - Redundant labels are removed or reduced where context already explains the
    content.
  - The detail view remains scannable in read and edit modes.
  - No implementation begins until the user approves this task.
  - '`Task details` heading is removed or replaced by clearer structural hierarchy.'
  - '`Task body` label is removed unless later evidence shows it is needed for accessibility/orientation.'
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback on Kanban task detail hierarchy:
1. The tagging section is not clearly separated enough from the title; it does not need a whole new section, but needs a few pixels of whitespace.
2. `Task details` and `Task body` labels may be unnecessary because the modal already implies detail view and body content.

## Current Interpretation
Information hierarchy issue. The modal may be over-labeling obvious regions while under-separating the title/status/tag metadata that users scan first.

## Value
Task detail should feel calm and obvious: title, task metadata, editable fields, body, acceptance criteria, and history should have a readable hierarchy without redundant labels.

## Discussion Questions
- Which labels are helping orientation, and which are redundant visual noise?
- Should tags sit closer to status/priority or closer to editable metadata?
- How much spacing is enough without making the modal feel loose?

[[2026-05-24T03:04:25+02:00]]
## Decision
User selected `Remove redundant labels`. The task detail modal should not need `Task details` or `Task body` labels; the modal context, title, metadata, and markdown body should carry the hierarchy. Add enough spacing around title/status/tags so the tag area reads clearly without becoming a heavy separate section.

[[2026-05-24T03:42:50+02:00]]

## Implementation Proof
Implemented in Cockpit web as part of the approved small polish package. Removed the visible `Task details` section heading and the visible `Task body` label while preserving an accessible hidden `Body` label for the PDS textarea in edit mode.

Proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1788-task-detail-labels-after.png`

