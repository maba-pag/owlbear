---
id: 1805
title: Add memory detail action spacing
status: research
priority: needed
created: 2026-05-24T06:42:43.178804+02:00
updated: 2026-05-24T06:42:43.178804+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - memory
  - spacing
  - discussion
parent: 1773
depends_on: []
ac:
  - Expanded Memory detail action buttons have comfortable space above the lower
    detail border.
  - The spacing visually matches adjacent detail panels and does not create 
    excess vertical bulk.
  - Memory detail display mode and edit mode remain usable at the 1024px support
    floor.
  - Screenshot proof captures an expanded memory detail with the action row and 
    lower border visible.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback: on the Memory page, when looking at a memory detail, there is no space between the edit button/action row and the lower border. The sentence was clipped after 'similar to the', but the observed issue is clear enough to track.

## Current Interpretation
The expanded memory detail action row likely needs bottom spacing or a more intentional footer treatment so actions do not feel pinned to the border.

## Value
Memory triage should feel calm and deliberate; cramped action spacing makes the detail panel feel unfinished and harder to scan.

## Boundary
Discussion task only. Do not implement until explicitly approved. Clarify the desired comparison surface if needed before coding.