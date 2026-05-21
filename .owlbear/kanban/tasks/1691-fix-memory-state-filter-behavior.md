---
id: 1691
title: Fix memory state filter behavior
status: research
priority: important
created: 2026-05-21T19:53:12.805354+02:00
updated: 2026-05-21T19:53:12.805354+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - filters
  - behavior
parent:
depends_on: []
ac:
  - Reproduce the Memory state filter behavior with realistic mixed-state 
    entries.
  - Fix confirmed state-filter failures so visible rows match selected states.
  - Update shown counts and empty states consistently with the active filter.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Memory page: the state filter does not work.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current behavior defect.
- Value question: state filtering is central to memory review; if it fails, the filter panel loses trust and should be fixed before visual polish.
- Browser target: state filter with realistic entries across pending/curated/approved/deleted.

## Acceptance Criteria
- Reproduce the state filter failure in browser with realistic memory data.
- Fix confirmed behavior so selected states control visible entries.
- Ensure the shown count and empty states update with the active filter.