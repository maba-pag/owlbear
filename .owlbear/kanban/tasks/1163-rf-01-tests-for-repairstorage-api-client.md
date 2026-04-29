---
id: 1163
title: 'RF-01: Tests for repairStorage API client'
status: backlog
priority: nice-to-have
created: 2026-04-28T17:38:24.600049+00:00
updated: 2026-04-28T17:40:41.047314+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:test
parent:
depends_on:
- 1162
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Backend: `POST /api/tasks/repair` returns `list[RepairOutcome]` where each has:
- `task_id: int | None`
- `file_path: str`
- `code: str`
- `action: "fixed" | "quarantined" | "failed"`
- `detail: str | None`

Existing API client pattern: `serve/cockpit/web/src/api/` (fetch wrappers).

## Acceptance Criteria

- [ ] Test: `repairStorage()` sends POST to `/api/tasks/repair` with no body
- [ ] Test: successful response returns typed `RepairOutcome[]` array
- [ ] Test: network/server error rejects with meaningful error
- [ ] Test: `RepairOutcome` TypeScript type matches backend schema (action is union literal, task_id nullable)

## Scope

- **In scope:** API client function tests, TypeScript type definition
- **Out of scope:** Hook logic, UI components, backend changes
