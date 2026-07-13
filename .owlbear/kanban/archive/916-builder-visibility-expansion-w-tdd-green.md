---
id: 916
title: Builder visibility expansion — w-tdd-green
status: archived
priority: medium
created: 2026-04-17T11:52:08.039917+00:00
updated: 2026-04-17T20:04:08.516283+00:00
tags:
- test-quality
- type:docs
- scope:copilot
parent: 912
depends_on:
- 914
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #912

## AC

- `w-tdd-green` updated: test-run step instructs builder to run both task-scoped test file AND module-level test file (`test_{module}.py`) for affected module
- Not full-suite — scoped to affected module only
- Handles missing module-level file gracefully (skip with note, no error)
- Rationale documented: early cross-task regression signal without full-suite cost
