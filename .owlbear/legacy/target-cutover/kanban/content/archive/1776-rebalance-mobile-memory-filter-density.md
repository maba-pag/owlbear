---
id: 1776
title: Rebalance mobile Memory filter density
status: archived
priority: medium
created: 2026-05-24T00:36:29.337556+02:00
updated: 2026-05-24T10:50:02.305955+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - mobile
  - memory
  - discussion
  - stress-note
parent: 1773
depends_on:
  - 1773
ac:
  - Memory mobile first screen makes the current content/result list value
    visible without requiring excessive filter scanning.
  - Filters remain discoverable and useful for repeated Memory workflows.
  - Evidence confirms whether this is an actual usability drag or acceptable for
    a filter-heavy admin view before implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
#1773 fresh sweep shows `320-memory-rest` and `390-memory-rest` dominated by State, Category, Agent, and Search filters before memory content. The first result starts low on 320px, and the visual value of the tab is less immediate than Kanban, Decisions, and Ideas.

## Value Question
Memory is likely a review/curation workflow. Filters matter, but if they consume the first screen on mobile, users may not immediately see what memory item they are acting on.

## Current Interpretation
Reclassified after #1779: observed mobile stress evidence below the 1024px Cockpit support floor, not current product harm. No implementation is approved from this task.

## Decision
Closed as a stress note. Memory density should be judged at 1024px+ and normal desktop widths before considering layout changes.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-320-memory-rest.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-390-memory-rest.png`