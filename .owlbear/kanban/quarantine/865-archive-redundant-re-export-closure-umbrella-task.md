---
id: 865
title: Archive redundant re-export closure umbrella task
status: archived
priority: nice-to-have
created: 2026-03-20T13:46:24.8852977+01:00
updated: 2026-03-20T17:08:15.1128319+01:00
started: 2026-03-20T17:08:15.1128319+01:00
completed: 2026-03-20T17:08:15.1128319+01:00
tags:
    - audit
    - scope:core
claimed_by: builder
claimed_at: 2026-03-20T17:08:03.2158816+01:00
class: standard
---

Board cleanup only. This task retires redundant umbrella task #865 without modifying #823 or #837. #837 already contains atomic self-closure AC, #823 already records its closure outcome and must be cleaned up in its own task, and #549 remains the source of truth for the re-export workstream. Append a one-line closure note to #865 documenting that relationship, then archive #865. Do not modify any other task files, src/, or tests/. See docs/research/re-export-closure-umbrella-task.md.

## AC

- [ ] Append a one-line closure note to #865 stating that #837 remains the task-local closure path, #823 must be resolved in its own task, and #549 is the source of truth for the re-export workstream
- [ ] The closure note cites docs/research/re-export-closure-umbrella-task.md
- [ ] Archive #865 after appending the note
- [ ] No other task files, src/, or tests/ are modified

[[2026-03-20]] Fri 14:57

## Research

Doc: docs/research/re-export-closure-umbrella-task.md

Summary: #549 already records the resolved re-export state. #837 is already an atomic self-closure task, and #823 already records its closure outcome but still needs task-local cleanup. Recommendation (.93): do not execute #865 as a bundled cleanup task because agent-common.instructions.md forbids editing tasks outside the dispatched assignment.

Follow-up: no new tasks created. Existing tasks #823 and #837 are the concrete cleanup actions; creating another umbrella task would duplicate board work.

Attribution: no new external sources; research used internal task, decision, research, and instruction files only.

[[2026-03-20]] Fri 15:27

## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Append a one-line closure note to #865 stating that #837 remains the task-local closure path, #823 must be resolved in its own task, and #549 is the source of truth for the re-export workstream | Verifiable self-contained board action that removes cross-task edits while preserving the closure map | Keep |
| The closure note cites docs/research/re-export-closure-umbrella-task.md | Verifiable provenance for why #865 is redundant | Keep |
| Archive #865 after appending the note | Clear terminal state for the redundant umbrella task | Keep |
| No other task files, src/, or tests/ are modified | Keeps the task in a single board-cleanup domain and compliant with the cross-task edit rule | Keep |

### Architecture Notes

Current board evidence shows #549 already archived as the source of truth, #837 already rewritten as an atomic self-closure task, and #823 already records its closure outcome. The only sound action left for #865 is to retire itself rather than instruct a later agent to edit other tasks.

This follows the existing closure-task pattern used on #837 and avoids violating agent-common.instructions.md, which forbids modifying tasks outside the dispatched assignment. No TDD predecessor is required because this is a closure/verification task with no application-code or test changes.

### Changes Made

- Rewrote #865 as an atomic self-closure task instead of a bundled cross-task cleanup
- kanban\kanban-md.exe edit 865 --status backlog --claim architect
- kanban\kanban-md.exe edit 865 --claim architect --title Archive redundant re-export closure umbrella task --body ...
- kanban\kanban-md.exe edit 865 --status todo --release
- kanban\kanban-md.exe edit 865 --claim architect --body ...

### Dependencies

- Added/Removed/Verified: verified #549 archived as source of truth, #837 already carries task-local closure AC, #823 remains a separate task-local cleanup item; no code dependencies and no TDD task required

[[2026-03-20]] Fri 16:09

## Test-Writer Notes\n- Non-implementation task (board cleanup / kanban archival) — no src/ or tests/ changes involved.\n- Architecture Review explicitly states: no TDD predecessor required.\n- Passing through to builder

[[2026-03-20]] Fri 17:08

## Closure Note

# 837 remains the task-local closure path for its own re-export audit item; #823 must be resolved in its own task; #549 is the source of truth for the re-export workstream. See docs/research/re-export-closure-umbrella-task.md

## Builder Notes

- Non-implementation task — board closure only; no src/ or tests/ changes made.
- Closure note appended above, citing docs/research/re-export-closure-umbrella-task.md.
- Archiving #865 per AC.
