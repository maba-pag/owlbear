---
id: 1948
title: 'P1-12: Cockpit memory purge HTTP contract'
status: build
priority: medium
created: 2026-07-17T03:04:20.271457+02:00
updated: 2026-07-17T03:04:43.929056+02:00
tags:
  - phase-1
  - scope:cockpit-backend
  - api
  - memory
parent: 1951
depends_on:
  - 1947
ac:
  - 'AC-1: Given POST /api/memories/purge/preview with min_age_days=30, the assembled
    FastAPI route returns deleted_total, eligible, and too_recent and does not mutate
    the engine store.'
  - 'AC-2: Given POST /api/memories/purge with min_age_days=0, the assembled FastAPI
    route returns purged, skipped, and failed and the following GET /api/memories
    omits purged entries.'
  - 'AC-3: Given min_age_days values -1, 1.5, empty, or nonnumeric, or a request containing
    a filter field, each route returns HTTP 422 without invoking purge.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Cockpit exposes strict project-wide preview and execution routes backed by MemoryEngine.

## Scope
In scope: strict request validation, typed response envelopes, route delegation, and project-wide scope enforced by accepting no filter fields.

Out of scope: Memory MCP, frontend request state, and rendered UI.

## Contract Authorities
- Route prefix and router assembly: Cockpit `main.py` and memory router.
- Endpoint hierarchy: OpenSpec Design decision 3.
- Core behavior: tasks #1946 and #1947.

Proof guidance: run focused Cockpit pytest through the assembled FastAPI router with the engine dependency replaced below HTTP, then regress existing Memory routes.