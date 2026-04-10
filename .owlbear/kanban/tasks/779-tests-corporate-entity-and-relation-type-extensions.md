---
id: 779
title: Tests — Corporate entity and relation type extensions
status: backlog
priority: needed
created: '2026-04-10T12:30:43.945435+00:00'
updated: '2026-04-10T12:30:43.945435+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests assert `REQUIREMENT`, `SOLUTION`, `PROCEDURE`, `POLICY`, `STANDARD` are members of `EntityType`
- Tests assert `GOVERNS`, `SUPERSEDES_VERSION` are members of `RelationType`
- Tests verify new members appear in `", ".join()` type-list output
- File: `tests/test_models_entity_relation_775.py`

## Context
- WS-A: Schema + Models Foundation
- Scope items 6+7 from #775
- See research F3: entity/relation/prompt must ship atomically
