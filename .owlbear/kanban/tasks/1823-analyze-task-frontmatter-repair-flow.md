---
id: 1823
title: Analyze task frontmatter repair flow
status: done
priority: important
created: 2026-05-24T10:17:50+02:00
updated: 2026-05-24T10:32:41+02:00
tags:
  - scope:cockpit
  - scope:kanban-engine
  - defect
  - discussion
parent:
depends_on: []
ac:
  - The corrupt frontmatter report for task 1813 is traced to the concrete YAML parse failure.
  - The Cockpit repair action path is inspected to explain why clicking repair appears to do nothing.
  - Findings are presented with options before any implementation.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The workspace status reports `.owlbear/kanban/tasks/1813-repair-kanban-list-sessions-active-filter.md` with `ERR_CORRUPT_YAML_PARSE`. User suspects the `ac` entry that starts with a backticked identifier. Clicking repair in the UI appears to do nothing.

## Boundary
Do not implement a fix until the user approves one of the presented options.

## Findings
- Read-only parse reproduction confirms both ruamel and PyYAML raise `ScannerError` on frontmatter line 16, where an unquoted `ac` item starts with a backtick.
- `detect_corruption()` reports `ERR_CORRUPT_YAML_PARSE`; `read_task()` raises the same corruption code for the same file.
- The Cockpit Repair button opens a PDS confirmation modal; it does not immediately run repair on the first click.
- The backend `repair_storage()` path would quarantine `ERR_CORRUPT_YAML_PARSE` files rather than quote the malformed YAML in place.
- The Repair confirmation copy says quarantine files move to `.owlbear/scratch/quarantine`, but backend storage moves them to `.owlbear/kanban/quarantine`.

## Decision
User approved fixing the #1813 data and aligning the RepairPanel quarantine copy with the backend path.

## Resolution
- Quoted the #1813 `ac` entries that contain leading inline-code markers so the task parses as valid YAML.
- Updated the RepairPanel confirmation copy to point to `.owlbear/kanban/quarantine`.
- Aligned stale frontend tests with the current PDS destructive-confirm behavior and corrected quarantine path.

## Verification
- Read-only `detect_corruption()` on #1813 -> no issue.
- `read_task()` on #1813 -> task id 1813, 4 acceptance criteria.
- `npm test -- --run src/__tests__/HealthBadgeRepair.test.tsx src/__tests__/RepairPanel.test.tsx src/__tests__/PModal.migration.test.tsx` -> 3 files passed, 113 tests passed.
- `npm run build` -> TypeScript and Vite build passed.