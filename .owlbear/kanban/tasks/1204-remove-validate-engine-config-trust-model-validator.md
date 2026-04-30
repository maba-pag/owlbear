---
id: 1204
title: Remove _validate_engine_config — trust model validator
status: backlog
priority: needed
created: '2026-04-30 15:29:06.178965+00:00'
updated: '2026-04-30 15:32:04.116418+00:00'
tags:
- audit-kanban
- dry
parent:
depends_on:
- 1200
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove redundant _validate_engine_config; trust model validator.

## Files
- engine.py (KanbanEngine.__init__, _validate_engine_config)

## Change
Delete `_validate_engine_config()` function. Remove its call from `KanbanEngine.__init__()`. BoardConfig._validate_semantics (model_validator mode=\"after\") already covers all the same checks.

## AC
- [ ] _validate_engine_config function deleted
- [ ] No call to it in __init__
- [ ] BoardConfig model_validator still catches invalid configs
- [ ] All tests pass

## Finding: 1.2
