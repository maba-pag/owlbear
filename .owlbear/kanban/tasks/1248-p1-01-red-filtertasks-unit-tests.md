---
id: 1248
title: 'P1-01: RED — filterTasks unit tests'
status: research
priority: critical
created: 2026-05-01T04:34:42.374850+00:00
updated: 2026-05-01T04:37:37.037120+00:00
tags:
- phase-1
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test suite in Vitest covering filterTasks:
  - Text dimension: case-insensitive substring match on task.title; empty string passes all
  - Priority dimension: exact match on task.priority; empty string passes all
  - Tags dimension: AND semantics — task must have ALL selected tags; empty array passes all
  - Blocked dimension: when true, only blocked tasks pass; when false, all pass
  - AND combination: multiple active dimensions all apply simultaneously
  - Edge cases: task with empty tags array vs non-empty filter; task with undefined fields
- All tests fail (RED) — no filterTasks implementation exists yet
- FilterState type interface exported for downstream consumers

## In Scope
- Unit test file for filterTasks
- FilterState type definition

## Out of Scope
- filterTasks implementation (next task)
- React components
- Integration with KanbanBoard

Brief: see parent #1247