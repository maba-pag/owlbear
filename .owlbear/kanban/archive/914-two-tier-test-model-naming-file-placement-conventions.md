---
id: 914
title: Two-tier test model naming + file placement conventions
status: archived
priority: critical
created: 2026-04-17T11:51:47.986875+00:00
updated: 2026-04-17T20:04:08.498937+00:00
tags:
- test-quality
- type:docs
- scope:copilot
parent: 912
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #912

## AC

- `r-project-standards` § File Placement updated: test row replaced with two-tier naming — task-scoped `test_{module}_{task_id}.py` (transient) and module-level `test_{module}.py` (durable)
- `h-python-conventions` updated: two-tier test model section added — tier definitions (task-scoped vs module-level), lifespan rules (transient vs permanent), authority (who creates/modifies each tier)
- No other files changed
