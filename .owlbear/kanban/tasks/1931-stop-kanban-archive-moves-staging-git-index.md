---
id: 1931
title: Stop Kanban archive moves staging Git index
status: verify
priority: high
created: 2026-07-14T01:58:13.250853+02:00
updated: 2026-07-14T02:09:51.727188+02:00
tags:
  - kanban
  - git
  - type:build
parent:
depends_on: []
ac:
  - Engine archive moves leave Git index untouched
  - No-overwrite and rollback behavior remains intact
  - Git still detects the staged delete/add as a rename
  - Focused tests and lint pass
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Replace Kanban's `git mv` archive operation with a filesystem-only move so board mutations never alter the user's Git index.

## Context
`_move_file` currently invokes `git mv`. Reproduction proves this creates cached `R100` plus unstaged collector content (`RM`), causing `commit-owned` to reject collector closure. Git does not store rename identity; it infers renames from delete/add similarity.

## Acceptance Criteria
- Kanban task/archive/quarantine moves do not modify the Git index.
- Existing filesystem move, no-overwrite, and rollback behavior remains intact.
- A Git-backed engine regression proves the index stays clean after archive movement.
- Staging both paths after the move remains rename-detectable with Git similarity detection.
- Focused Kanban tests and lint pass.

[[2026-07-14T02:09:51+02:00]]
## Builder Notes

- Root cause: Kanban `_move_file` deliberately used `git mv`, which stages a cached rename in the user's index. `commit-owned` correctly rejected that pre-staged path; VS Code was not involved.
- Change: `_move_file` now uses only guarded `Path.replace` and no longer imports or invokes subprocess/Git.
- Preserved behavior: no-overwrite collision guard, filesystem move semantics, archive rollback, and activity atomicity.
- Durable regression: public `KanbanEngine.move_task` archive in a temporary Git repo must leave the cached index empty; after explicitly staging both paths, Git `-M` must report a rename.
- Proof: regression failed before fix on non-empty cached index and passes after fix; 80 focused archive/atomicity tests passed; full Kanban domain 882 passed; Ruff and format clean; diff check clean.
- Builder challenger: pass; no concrete blocker.
