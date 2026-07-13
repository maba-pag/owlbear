---
id: 1930
title: Document auto-staged collector archive recovery
status: verify
priority: medium
created: 2026-07-14T01:12:22.720349+02:00
updated: 2026-07-14T01:14:20.958871+02:00
tags:
  - agent
  - kanban
  - type:docs
parent:
depends_on: []
ac:
  - Safe exact-path auto-stage recovery is documented
  - Ambiguous staged ownership is never silently unstaged
  - Collector lifecycle links the recovery procedure
  - Focused regression guard covers the contract
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Define the safe recovery procedure when collector archival is auto-staged before `commit-owned` runs.

## Acceptance Criteria
- Governance requires inspection of both owned task/archive paths before unstaging.
- Recovery unstages only the verified task-owned paths and retries `commit-owned`.
- Ambiguous or mixed owned-path content routes to `COMMIT_FAILED` rather than being unstaged.
- Collector-facing lifecycle guidance points to the procedure.
- A focused regression assertion prevents removal of the recovery contract.

[[2026-07-14T01:14:20+02:00]]
## Builder Notes

- Change envelope: document safe recovery when collector archive paths are auto-staged before `commit-owned`.
- Added `Owned Auto-Staging Recovery` to workspace governance: exact two-path cached diff inspection, strict ownership/rename check, `COMMIT_FAILED` on ambiguity, exact-path reset, and scoped retry.
- Clarified that `git reset` may list unrelated unstaged paths without modifying their index state.
- Added collector-facing lifecycle pointer and focused static assertions.
- Proof: `uv run pytest tests/test_skill_authority_wiring.py -q` -> 4 passed; Ruff clean; all 23 agent files validate; diff check clean.
- Builder challenger: pass; no concrete blocker.
