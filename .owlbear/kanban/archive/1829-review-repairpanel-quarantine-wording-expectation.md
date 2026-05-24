---
id: 1829
title: Review RepairPanel quarantine wording expectation
status: archived
priority: important
created: 2026-05-24T11:19:10.413939+02:00
updated: 2026-05-24T23:22:55.558390+02:00
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
claimed_at:
archival_reason: completed
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

[[2026-05-24T23:22:55+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 2327 passed, 4 failed (all unrelated timeouts in DetailTab, MemoryTab_1672, PdsMigration, Shell.card-selection — none attributable to a one-word copy change in RepairPanel.tsx), lint clean.

### Intent Verification
Changed files: `RepairPanel.tsx` (one string literal) and `HealthBadgeRepair.test.tsx` (matching assertions). Entirely within `scope:cockpit-web` domain. Implementation adds "the quarantine folder" before the destination path — matches stated purpose exactly. No extraneous scope.

### Architect Quality
Score: 4/5. ACs are clear and well-constrained for a copy review task. AC3 provides a specific verifiable constraint (destination path must remain accurate).

### Commit Integrity
Builder deliverables committed in `8e58f235` (feat: complete cockpit interaction batch #1773). Kanban state consistent.

### Confidence
No deductions. Score: 1.00. Action: archive.
