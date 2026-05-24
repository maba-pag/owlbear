---
id: 1829
title: Review RepairPanel quarantine wording expectation
status: done
priority: important
created: 2026-05-24T11:19:10.413939+02:00
updated: 2026-05-24T22:04:11.585236+02:00
tags:
  - scope:cockpit-web
  - repair
  - copy
  - discussion
parent: 1773
depends_on: []
ac:
  - RepairPanel confirmation copy is reviewed for whether the quarantine 
    destination is clear enough to users.
  - The decision records whether the stale regex or product wording should 
    change.
  - 'Any approved change keeps the destination path accurate: `.owlbear/kanban/quarantine`.'
blocked: false
block_reason:
claimed_at: 2026-05-24T22:04:11.585236+02:00
archival_reason:
archival_refs: []
---
## Observation
The full Cockpit frontend suite reported a SidecarUX failure around RepairPanel confirmation text. The dialog now says quarantined files move to `.owlbear/kanban/quarantine`, but the test regex expected wording such as `quarantine directory/path/folder` or `moved to quarantine`.

## Evidence
- Test: `serve/cockpit/web/src/__tests__/SidecarUX.test.tsx`
- Failure text includes: `quarantined files move to .owlbear/kanban/quarantine`

## Boundary
Treat this as a copy/test-alignment review. The product copy already names the concrete destination path; decide whether to adjust the test wording, product text, or no-op.

## User Decision
Approved direction: make a tiny copy improvement by adding an explicit `folder` or `path` word while keeping the concrete destination `.owlbear/kanban/quarantine`.

Implementation should stay minimal and preserve the exact destination path. Tests should follow the resulting product copy.

## Implementation Outcome
Completed with the minimal copy improvement: the confirmation text now says quarantined files move to the quarantine folder `.owlbear/kanban/quarantine`, preserving the concrete destination path.

Evidence: HealthBadgeRepair focused test file passed; affected bundle passed; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped.
