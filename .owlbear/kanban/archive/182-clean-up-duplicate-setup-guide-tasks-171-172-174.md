---
id: 182
title: 'Clean up duplicate setup-guide tasks (#171 #172 #174 #175)'
status: archived
priority: medium
created: 2026-03-29 20:13:44.401074+02:00
updated: 2026-03-30 03:15:25.615314+02:00
started: 2026-03-29 20:29:33.084876+02:00
completed: 2026-03-30 03:14:38.071593+02:00
tags:
- phase-2
- scope:build
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Remove duplicate tasks created by overlapping kanban-md create executions from #25 research.

## Acceptance Criteria
- [ ] Delete tasks #171, #172, #174, #175 using kanban-md delete --yes (4 tasks, all confirmed duplicates of #169)
- [ ] Verify #169 is the only remaining setup-guide docs task (search for title containing "setup" or "sharing guide")
- [ ] Update #169 body to reference all 3 research docs: docs/research/setup-and-sharing-docs.md, docs/research/multi-project-doc-guide.md, docs/research/multi-project-setup-docs.md
See docs/research/duplicate-setup-guide-cleanup.md for details.

[[2026-03-29]] Sun 21:16
## Test-Writer Notes
- Non-implementation task -- all AC lines describe kanban-md CLI operations (delete, verify, update body).
- No Python module, function, or interface is produced.
- Passing through to builder.

[[2026-03-29]] Sun 23:14
## Review Evidence

### Non-code task: no tests or lint applicable

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Delete #171-175 using `kanban-md delete --yes` | Files still exist on disk: confirmed via Get-ChildItem. Tasks show `status: archived`. kanban-md has separate `archive` (soft-delete, preserves file) and `delete` (hard-delete, removes file) commands; builder used archive, not delete. | **FAIL** |
| Verify #169 is the only remaining setup-guide task | `list --search setup` and `list --search sharing` do not surface #171-175. #169 is the only active match. | PASS |
| Update #169 body with all 3 research docs | `show 169` body contains Research Docs Reference section listing all 3 docs. All 3 files confirmed present on disk. | PASS |

### Process Gaps
- No Builder Notes in task body.
- All AC checkboxes remain unchecked.

### Verdict: FAIL — confidence .95

AC Line 1 not met. AC requires `kanban-md delete --yes` (hard-delete). Builder used `archive` (soft-delete). Files remain in kanban/tasks/. Builder must run `kanban-md delete --yes` for #171, #172, #174, #175.

[[2026-03-29]] Sun 23:44
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about builder using archive instead of delete (wrong command), not missing tests.
- Existing pass-through preserved. Builder must run kanban-md delete --yes for #171 #172 #174 #175.

[[2026-03-30]] Mon 01:08
## Builder Notes (retry)
- AC 1: kanban-md delete --yes run for #171 (deleted), #172 (already archived), #174 (deleted), #175 (deleted). All 4 in archived status.
- Note: kanban-md delete = soft-delete in v0.33.0. No hard-delete exists. AC command executed as specified.
- AC 2: Active task list shows no setup-guide docs tasks. #169 is archived/completed.
- AC 3: #169 body has Research Docs Reference with all 3 docs.
- Lint: N/A

[[2026-03-30]] Mon 01:30
## Review Evidence

### Non-code task: no tests or lint applicable

### Context
Retry of previous FAIL cycle. Prior rejection was based on incorrect assumption that `kanban-md delete` = hard-delete. Confirmed via `kanban-md delete --help`: Soft-deletes a task by moving it to archived status. Both `archive` and `delete` produce identical outcomes (status: archived, file preserved). Builder claim is correct.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Delete #171-175 using `kanban-md delete --yes` | `kanban-md delete --help` confirms delete = soft-delete to archived. All 4 tasks (#171, #172, #174, #175) show status: archived. Files on disk with archived frontmatter. AC command is correct and outcome matches. | PASS |
| Verify #169 is the only remaining setup-guide docs task | `kanban-md list --search setup` and `--search sharing` return no active setup-guide docs tasks. Duplicates absent from active board. (#169 completed its own pipeline and archived.) | PASS |
| Update #169 body with all 3 research docs | `kanban-md show 169` Research Docs Reference section lists: setup-and-sharing-docs.md, multi-project-doc-guide.md, multi-project-setup-docs.md. All 3 files confirmed present on disk via Test-Path. | PASS |

### Verdict: PASS -- confidence .92

Previous reviewer FAIL (#1 cycle) was incorrect: `kanban-md delete` is documented as soft-delete (archive), not hard-delete. No hard-delete exists in v0.33.0. All AC lines met.

[[2026-03-30]] Mon 03:14
## Audit
AC 1 (delete duplicates): PASS. #171, #172, #174, #175 all archived.
AC 2 (verify #169 only): PASS. No active setup-guide tasks on board.
AC 3 (update #169 body): PASS. Research Docs Reference lists all 3 docs.
Tests: N/A (non-code task). Lint: N/A.
AC Quality: 4/5.
Confidence: .97
Action: archive

[[2026-03-30]] Mon 03:15
## Commits
be8e4a7 chore: archive duplicate setup-guide tasks (5 kanban files) #182
