---
id: 1954
title: 'P1-18: Cockpit memory lifecycle HTTP contract'
status: verify
priority: high
created: 2026-07-17T04:53:58.085320+02:00
updated: 2026-07-17T05:39:05.773004+02:00
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

[[2026-07-17T05:39:05+02:00]]
## Builder Notes
- Change envelope: extend the existing Cockpit memory route adapter for the shaped operator projection and human exceptional-state resolve mutation; no MCP, frontend, or domain-engine changes.
- Files changed: `serve/cockpit/src/owlbear_cockpit/routes/memory.py`, `tests/test_cockpit_memory_routes.py`.
- Change Module Map deviations: none; the existing Cockpit memory route owns response shaping and mutation forwarding, while `MemoryEngine.resolve` and existing FastAPI exception handlers remain authoritative.
- Implementation: added `outstanding_count`, `score`, and `contested_by_task` to the explicit 14-field response projection; retained omission of `unremarkable_count` and `didnt_use_count`; added `POST /api/memories/{entry_id}/resolve` with forbidden extras and OCC forwarding to `engine.resolve`.
- Proof selected: focused route boundary tests plus real engine-to-Cockpit integration and Ruff.
- Durable-test justification: added exact projection allowlist/omission coverage and resolve success, invalid-transition, and conflict envelope checks; these protect the new public HTTP contract and are cheaper than repeated manual verification.
- Commands run: `uv run --project . pytest tests/test_cockpit_memory_routes.py -q` -> 51 passed; `uv run --project . pytest serve/cockpit/tests/test_memory_integration.py -q` -> 7 passed; `uv run --project . ruff check serve/cockpit/src/owlbear_cockpit/routes/memory.py tests/test_cockpit_memory_routes.py` -> All checks passed.
- Builder-challenger: pass; no concrete blocker, scope drift, or proof deficiency reported.
- Follow-up risks: Starlette emitted an existing httpx deprecation warning during TestClient runs; no task-scope failure.
