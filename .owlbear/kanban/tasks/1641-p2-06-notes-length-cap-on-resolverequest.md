---
id: 1641
title: 'P2-06: Notes length cap on ResolveRequest'
status: research
priority: important
created: 2026-05-18T00:49:02.572224+02:00
updated: 2026-05-18T00:49:02.572224+02:00
tags:
  - phase-2
  - scope:cockpit
  - backend
parent: 1638
depends_on:
- 1590
ac:
  - ResolveRequest.notes field has max_length=10_000 via Pydantic Field 
    constraint
  - POST /api/decisions/{id}/resolve returns 422 with a validation error when 
    notes exceeds 10,000 characters
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Add `max_length=10_000` to `ResolveRequest.notes` in `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`.

**Out:** Pydantic response model (P2-05), frontend changes.

## Context

`ResolveRequest` currently defines `notes: str | None = None` with no length constraint. This task adds a `Field(max_length=10_000)` guard to prevent unbounded input.