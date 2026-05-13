---
id: 1516
title: 'P1-02: Implement ac and proof_bundle model fields + storage canonical fields'
status: backlog
priority: critical
created: 2026-05-13T02:29:16.772741+00:00
updated: 2026-05-13T02:30:18.932988+00:00
tags:
  - phase-1
  - scope:kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1515
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle fields to Task, TaskSummary, TaskFull, DispatchEntry; add proof_bundle normalizing validator; update _CANONICAL_FIELDS
Out of scope: Engine behavior, MCP tools, migration

## Acceptance Criteria
- AC1: `Task(...)` constructor accepts `ac: list[str]` (default `[]`) and `proof_bundle: str | None` (default `None`); both round-trip through model serialization
- AC2: `TaskSummary` and `DispatchEntry` include `proof_bundle` but NOT `ac`; `TaskFull` inherits `proof_bundle` from `TaskSummary` and adds `ac: list[str]`
- AC3: `Task.proof_bundle` field_validator normalizes `"Behavioral+Challenge"` → `"behavioral+challenge"` and sorts modifiers alphabetically (`"critical+reader+challenge"` → `"critical+challenge+reader"`)
- AC4: `storage._CANONICAL_FIELDS` includes `"ac"` and `"proof_bundle"` positioned after `"depends_on"`

Proof bundle: behavioral