---
id: 1164
title: 'RF-02: Implement repairStorage API client'
status: backlog
priority: nice-to-have
created: 2026-04-28T17:38:24.612604+00:00
updated: 2026-04-28T17:40:41.097718+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on:
- 1163
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Implements the API client for `POST /api/tasks/repair`.
Backend returns `list[RepairOutcome]` — see #1163 for full schema.

## Acceptance Criteria

- [ ] `repairStorage()` function exported from API client module
- [ ] TypeScript `RepairOutcome` type exported (action as `"fixed" | "quarantined" | "failed"`, task_id nullable)
- [ ] All #1163 tests pass

## Scope

- **In scope:** API client function, TypeScript type, fetch call
- **Out of scope:** Hook logic, UI components, error retry