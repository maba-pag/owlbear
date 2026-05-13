---
id: 1518
title: 'P2-02: Implement engine ac/proof_bundle in create_task, edit_task, and search'
status: backlog
priority: critical
created: 2026-05-13T02:29:31.968335+00:00
updated: 2026-05-13T02:30:18.963269+00:00
tags:
  - phase-2
  - scope:kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1517
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle params to create_task and edit_task; implement proof_bundle frozenset validation, dual AC mutation (full replacement OR atomic add/remove with mutual exclusion), AC guardrails, search extension
Out of scope: MCP tools, migration, skill files

## Acceptance Criteria
- AC1: `KanbanEngine.create_task()` accepts `ac` and `proof_bundle` params; rejects invalid `proof_bundle` values with `ValidationError` listing valid options
- AC2: `KanbanEngine.edit_task()` supports `ac` (full replacement), `add_ac` (append), and `remove_ac` (exact-match removal); raises `ValidationError` when `ac` and `add_ac`/`remove_ac` are both provided
- AC3: `KanbanEngine.edit_task()` rejects duplicate `add_ac` items with `ValidationError` listing existing duplicates
- AC4: `KanbanEngine.create_task()` and `edit_task()` enforce AC guardrails: max 20 items raises `ValidationError`; item exceeding 500 chars raises `ValidationError`
- AC5: `KanbanEngine.list_tasks(search="keyword")` matches tasks where `keyword` appears in frontmatter `ac` items

Proof bundle: behavioral