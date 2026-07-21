---
id: 1974
title: Recover Cockpit memory purge HTTP routes
status: collect
priority: high
created: 2026-07-21T16:06:13.126407+02:00
updated: 2026-07-21T16:25:33.200304+02:00
tags:
  - scope:cockpit-backend
  - api
  - memory
  - baseline-repair
parent:
depends_on:
  - 1973
ac:
  - 'AC-1: Given `POST /api/memories/purge/preview` with `min_age_days=30`, the assembled
    route returns deleted_total, eligible, and too_recent and delegates once to `MemoryEngine.preview_purge(30)`.'
  - 'AC-2: Given `POST /api/memories/purge` with `min_age_days=0`, the assembled route
    returns purged, skipped, and failed and delegates once to `MemoryEngine.purge(0)`.'
  - 'AC-3: Given `min_age_days` values -1, 1.5, empty, or nonnumeric, or a payload
    containing a filter field, each route returns HTTP 422 without invoking the engine.'
proof_bundle: behavioral+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The previously verified Cockpit backend work from archived task #1948 has durable commit ownership: strict project-wide preview and execution routes delegate to MemoryEngine.

## Scope
In scope: the existing dirty changes in `serve/cockpit/src/owlbear_cockpit/routes/memory.py`; strict request validation; typed responses; route delegation; project-wide scope through absence of filter fields.

Out of scope: core purge logic, frontend request state, rendered UI, Memory MCP behavior, and unrelated workspace cleanup.

## Contract Authorities
- Archived HTTP contract: #1948.
- Core dependency recovery: #1973.
- Cockpit memory router assembled under `/api`.

## Proof Guidance
Exercise the assembled FastAPI router with only the engine dependency replaced below HTTP, then run the maintained Cockpit memory route suite and Ruff on the owned module.

[[2026-07-21T16:22:49+02:00]]
## Builder Notes

Verdict: DONE.

Change envelope: adopted only the existing dirty Cockpit memory router change from archived #1948. Core purge, frontend, MCP, and unrelated workspace files were excluded.

Behavior: `PurgeRequest` requires a strict non-negative integer and forbids extra fields; assembled preview and execution routes delegate to `MemoryEngine` and return typed core count models. No filter field or path is exposed.

Proof: maintained Cockpit memory route suite passed 51 tests with one third-party Starlette deprecation warning; Ruff lint and format passed. A temporary assembled FastAPI probe replaced only the engine dependency below HTTP and verified valid envelopes/delegation plus 422 with no engine invocation for -1, 1.5, empty, nonnumeric, and extra `state` payloads on both routes. The probe was deleted.

Durable-test decision: no test added. Existing route regression coverage plus assembled task proof cover this compact contract; the untracked shallow frontend threshold test is unrelated and excluded.

Builder-challenger: decision pass; no blocker, scope drift, route-contract gap, or auto-fix.

[[2026-07-21T16:25:33+02:00]]
## Verify Notes

Verdict: PASS.

Exact revision: `3fe3281ab127ffaf4dea3699c5b16f7602e18f91` in the clean prepared worktree.

Authority: archived #1948 HTTP contract and archived dependency #1973.

Proof at exact revision: the maintained Cockpit memory route suite passed 51 tests with one third-party Starlette deprecation warning; Ruff lint and format passed. A fresh assembled FastAPI probe replaced only `get_memory_engine` below HTTP, verified typed preview/execution envelopes and exact delegation, then verified both routes reject -1, 1.5, empty, nonnumeric, and extra `state` payloads with 422 and no engine call. The probe was removed and the worktree returned clean.

No durable test was added; maintained route coverage plus exact assembled-boundary proof cover the compact contract.

Verifier-challenger: decision pass; no assembly, validation, response, scope, or unresolved-AC finding.
