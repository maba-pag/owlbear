---
id: 1121
title: 'RED: archived-task edit persistence tests'
status: research
priority: important
created: 2026-04-24T23:20:26.935285+00:00
updated: 2026-04-24T23:20:26.935285+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent:
depends_on:
- 1070
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — extends #1120 research.
Module: `serve/kanban/tests/test_engine_archived_edit.py`

Test that `edit_task` on archived tasks persists correctly to the archive directory. Covers both AgentView and core engine paths.

## Acceptance Criteria

- [ ] `AgentView.edit_task(<archived>, archival_reason="dropped")` succeeds; re-read from archive shows updated reason
- [ ] `AgentView.edit_task(<archived>, archival_refs=[other_id])` succeeds; re-read shows updated refs
- [ ] `AgentView.edit_task(<archived>, append_body="Note")` succeeds; re-read shows appended body
- [ ] Core `engine.edit_task(<archived>, priority="critical")` succeeds; re-read shows updated priority
- [ ] File persists in `archive/` dir, NOT in `tasks/` dir (no duplicate)
- [ ] `updated` timestamp advances on successful edit
- [ ] S4 gate still enforced: `edit_task(<archived>, archival_reason="completed")` raises ValidationError
- [ ] All tests fail (RED phase)
