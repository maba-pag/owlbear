---
id: 1948
title: 'P1-12: Cockpit memory purge HTTP contract'
status: collect
priority: medium
created: 2026-07-17T03:04:20.271457+02:00
updated: 2026-07-17T17:11:07.088903+02:00
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

[[2026-07-17T16:31:13+02:00]]
## Builder Notes

Change envelope: implement the Cockpit memory purge HTTP contract only; strict request validation, typed response envelopes, route delegation, and no filter fields.

Files changed: `serve/cockpit/src/owlbear_cockpit/routes/memory.py`.

Change Module Map deviations: none. Existing `serve/memory` engine already owns eligibility, locking, cache mutation, and typed `PurgePreview`/`PurgeResult`; no engine changes were needed.

Proof selected: focused Cockpit memory route suite plus Ruff on the touched module. `uv run ruff check serve/cockpit/src/owlbear_cockpit/routes/memory.py` passed. Builder challenger exercised valid and invalid purge payloads and reported `uv run pytest tests/test_cockpit_memory_routes.py -q` with 51 passed. The initial direct pytest command was unavailable in this shell; the challenger provided the successful focused suite result.

Durable-test justification: no tests added; existing route coverage and challenger endpoint exercise protect the contract.

Builder-challenger result: pass; no concrete blockers.

Follow-up risks: none identified. Required owned commit helper was not available in the exposed toolset, so no commit was created.

[[2026-07-17T17:11:07+02:00]]
## Verify Notes

Verdict: PASS.

Evidence reviewed:
- Contract authority checked: `openspec/changes/purge-deleted-memories/design.md`, Decision 3 requires `POST /api/memories/purge/preview` and `POST /api/memories/purge`, a strict non-negative integer `min_age_days`, forbidden extra fields, no filter criteria, and typed core count responses.
- Change Module Map checked: implementation is limited to `serve/cockpit/src/owlbear_cockpit/routes/memory.py`, the shaped Cockpit memory-route owner. `main.py` already assembles the router at `/api`; no module-map or public-interface deviation.
- Source review: `PurgeRequest` uses `ConfigDict(extra="forbid")` and `StrictInt` with `ge=0`; preview delegates to `MemoryEngine.preview_purge`, while execution delegates to `MemoryEngine.purge`. No filesystem path or filter field is exposed.

Normal-path boundary exercised:
- Ephemeral assembled FastAPI `TestClient` probe replaced only `get_memory_engine` below HTTP. It verified preview at 30 returns `{deleted_total: 2, eligible: 1, too_recent: 1}`, leaves engine state unchanged, and calls `preview_purge(30)`.
- The same probe verified purge at 0 returns `{purged: 1, skipped: 1, failed: 0}`, changes lower-engine state, and calls `purge(0)`.
- For both routes, `-1`, `1.5`, empty, nonnumeric, and an extra `state` filter payload returned HTTP 422 without an additional engine call.

Checks run:
- `uv --directory /Users/markus/Projects/owlbear-dev run pytest /Users/markus/Projects/owlbear-dev/tests/test_cockpit_memory_routes.py -q -o addopts=''` -> 51 passed (one external Starlette TestClient deprecation warning).
- `uv --directory /Users/markus/Projects/owlbear-dev run ruff check /Users/markus/Projects/owlbear-dev/serve/cockpit/src/owlbear_cockpit/routes/memory.py` -> All checks passed.
- `uv --directory /Users/markus/Projects/owlbear-dev run ruff format --check /Users/markus/Projects/owlbear-dev/serve/cockpit/src/owlbear_cockpit/routes/memory.py` completed without findings.
- `git -C /Users/markus/Projects/owlbear-dev diff --check` completed without whitespace findings.

Findings: no implementation defect, scope drift, or unresolved AC. Root pytest defaults currently attempt a missing `serve/kanban` workspace path and collect zero tests for this file; the explicit absolute-path focused invocation above bypassed that unrelated runner configuration issue.

Patches applied: none.

Verifier-challenger result: pass. It confirmed authority alignment, valid assembled HTTP proof with only the lower engine replaced, AC completeness, and no need for a new durable test.

Final route: PASS -> collect.

