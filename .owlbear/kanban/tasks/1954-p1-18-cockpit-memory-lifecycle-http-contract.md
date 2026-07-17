---
id: 1954
title: 'P1-18: Cockpit memory lifecycle HTTP contract'
status: build
priority: high
created: 2026-07-17T04:53:58.085320+02:00
updated: 2026-07-17T04:54:49.616071+02:00
tags:
  - phase-1
  - scope:cockpit-backend
  - api
  - memory
parent: 1958
depends_on:
  - 1952
  - 1953
ac:
  - 'AC-1: Given memory entries in pending, curated, approved, contested, disputed,
    stale, or deleted state, GET /api/memories returns the documented 14-field operator
    projection and omits unremarkable_count and didnt_use_count.'
  - 'AC-2: Given a contested, disputed, or stale entry ID and its current expected_updated_at,
    POST /api/memories/{id}/resolve returns the domain result in approved state; a
    pending, curated, approved, or deleted source returns MEM_INVALID_TRANSITION without
    mutation.'
  - 'AC-3: Given an outdated expected_updated_at on resolve, the endpoint returns
    HTTP 409 with MEM_CONFLICT without mutation; given a current exceptional entry
    on edit, the edit endpoint returns the updated entry in its preserved exceptional
    state.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Cockpit receives the operator-relevant memory projection and a human resolve mutation with established optimistic-concurrency and transition errors.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirements: Operator-relevant memory details, Complete lifecycle-state visibility, Human-only exceptional-state resolution, Detail-aligned editing

## Scope
- In scope: Cockpit FastAPI memory response, edit/resolve routes, and existing memory error envelope.
- Out of scope: MCP tools, frontend rendering, and domain transition implementation.

## Contract
The list and mutation projection includes `id`, `title`, `content`, `categories`, `confidence`, `state`, `outstanding_count`, `score`, `scope_agents`, `source_agent`, `created_at`, `updated_at`, `approved_at`, and `contested_by_task`. It excludes `unremarkable_count` and `didnt_use_count`.

Proof guidance: exercise endpoints through the FastAPI application boundary with persistence replaceable below the route; reuse existing exception-envelope checks.