---
id: 784
title: Corporate entity and relation type extensions
status: backlog
priority: needed
created: '2026-04-10T12:31:05.162187+00:00'
updated: '2026-04-10T12:31:05.162187+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 779
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `models.py` `EntityType` enum includes 5 new members: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
- `models.py` `RelationType` enum includes 2 new members: GOVERNS, SUPERSEDES_VERSION
- All #779 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/models.py`

## Context
- WS-A: Schema + Models Foundation
- Scope items 6+7 from #775
- See research F3: entity/relation/prompt must ship atomically
