---
id: 1785
title: Auto-expand Kanban cards to show all tags
status: research
priority: important
created: 2026-05-24T01:57:03.560862+02:00
updated: 2026-05-24T02:06:42.264437+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - discussion
  - kanban
parent: 1773
depends_on:
  - 1779
ac:
  - All visible Kanban lanes use the same card tag visibility rule.
  - Cards grow vertically to show all tags rather than cutting tag rows off.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User clarified the Kanban issue is not horizontal scrolling. Horizontal scrolling is acceptable. The real issue is that task cards do not vertically expand automatically to show all tags; tags are cut off, especially noticed on the full-width board in the Done status.

## Current Interpretation
Observed UX issue worth investigating/fixing. Task cards should preserve tag visibility without making the board feel broken or hiding important metadata.

## Value
Tags are key scan metadata for task triage. If cards cut them off, users lose context and may need to open tasks just to understand category/scope.

## Discussion Questions
- Should cards expand to show all tags always, or only up to a reasonable max before a `+N` overflow indicator?
- Should this vary by lane density or viewport width?
- Does the Done lane need a denser treatment than active lanes?

## Boundary
Do not change horizontal board scrolling as part of this task unless later evidence shows it is directly required.

[[2026-05-24T02:06:42+02:00]]
## Decision
User chose: show all tags, auto-height cards, no lane-specific differences. Cards should grow vertically to fit wrapped tags in every visible lane.

## Note
Done is not technically the final status; it is the last visible board lane. Archived exists after Done and should not be forgotten in status-language or workflow design, though it does not change this tag-display decision.
