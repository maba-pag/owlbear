---
id: 2069
title: 'P11-04: Cut Cockpit backend to native SSE and legacy inventory'
status: collect
priority: high
created: 2026-07-25T22:31:09.091791+02:00
updated: 2026-07-25T23:54:59.030417+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - sse
  - legacy
  - cutover
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-004
  - interface:IF-011
  - migration:MIG-003
parent: 1987
depends_on:
  - 2067
  - 2068
ac:
  - 'AC-1: Given canonical authority or work-path create, modify, delete, or mixed
    batches, `/api/events` emits one `native-changed` event with sorted affected resource
    classes and a monotonic token; temporary noise is suppressed and disconnect or
    missing roots terminate cleanly.'
  - 'AC-2: Given empty or populated legacy task, request, and activity stores, `GET
    /api/legacy` returns bounded read-only inventory with provenance and no mutation
    links; write methods are absent.'
  - 'AC-3: The assembled app returns 404 or 405 for board, task, task activity/session,
    generic request, and task mutation paths, while native resources plus memory,
    ideas, and liveness remain registered.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-004`.

## Outcome
The assembled Cockpit backend emits native resource invalidations, exposes read-only legacy inventory, and unregisters its generic task surface.

## Envelope
In: SSE watch/classification, legacy reads, FastAPI router composition, old backend route absence.

Out: frontend migration, immutable legacy snapshot generation, repository-wide cutover.

Proof guidance: inspect assembled FastAPI route inventory and exercise SSE and legacy HTTP boundaries through TestClient.

[[2026-07-25T23:52:03+02:00]]
## Builder Notes
DONE: Cut the assembled Cockpit backend to native invalidation SSE plus bounded read-only legacy inventory for delivery digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

Product changes:
- `routes/events.py`: watches the shared ops root but classifies only canonical change authority and native jobs/attempts/findings/requests paths; suppresses legacy/temp/transaction noise; collapses mixed batches into one `native-changed` event with sorted resources and strictly increasing token; missing roots terminate without starting a watcher.
- `routes/legacy.py`: GET-only capped inventory for active/archive tasks, pending/resolved requests, and activity, each with source-store provenance and explicit truncation state.
- `main.py`: registers legacy inventory and native SSE, removes generic board/task/activity/session/request and task-health/repair route registration, and preserves native resources, memory, ideas, memory/ideas health, and liveness.

Proof and test curation:
- Added `tests/test_cockpit_native_cutover.py` with public SSE, legacy HTTP, non-mutation, missing-root, limit, method, and assembled-route proof.
- Retired eight durable suites whose maintained contracts were exactly the removed generic task/cache/mutation/request/task-health or old `tasks-changed` SSE surface.
- Updated surviving boundary health checks to `/health/live` and launch/removed-decisions tests to import `get_engine` from `deps.py`, its owner.

AC evidence:
- AC-1: native classifier covers create/modify/delete independently of watch kind, mixed sorted batches, temporary/legacy suppression, one event per batch, monotonic fixed-clock tokens, and clean missing-root termination.
- AC-2: populated and empty GET `/api/legacy` cases prove limit=1/100 bounds, provenance, truncation, no mutation links, POST 405, and byte-for-byte store preservation.
- AC-3: assembled OpenAPI has all native routes, GET-only `/api/legacy`, memory/ideas/liveness, and no `/api/tasks`, `/api/board`, `/api/activity`, `/api/sessions`, `/api/requests`, aggregate/task/request health, or task repair paths; public representative requests return 404.

Validation:
- `uv run pytest -q tests/test_cockpit_native_cutover.py`: 6 passed.
- `uv run pytest -q tests/test_cockpit_*`: 166 passed.
- `uv run --package owlbear-tools lint-all`: passed.
- Editor diagnostics: clean.
- Builder challenger: pass; independently ran 59 cutover/surviving tests and accepted watcher semantics, route absence, legacy bounds, architecture, and every retired test as obsolete.

Builder memories were assessed before closure.

[[2026-07-25T23:54:59+02:00]]
## Verify Notes
PASS: Builder commit `9b8a61437aa707797e7b1b339a6df4eab90d77c7` satisfies native SSE, legacy inventory, and assembled backend cutover.

Independent evidence:
- Direct disconnect probe invoked the public SSE endpoint with a native event ready and an already-disconnected request; the stream emitted zero chunks.
- `uv run pytest -q tests/test_cockpit_native_cutover.py tests/test_cockpit_native_changes.py tests/test_cockpit_native_work.py tests/test_cockpit_native_controls.py`: 23 passed across every native backend resource slice.
- Builder commit audit confirmed declared product/proof/test-retirement scope and clean owned product/proof paths.
- Assembled OpenAPI confirms GET-only `/api/legacy`, complete native resources and peer memory/ideas/liveness routes, with no generic board/task/activity/session/request prefixes.

AC judgment:
- AC-1: canonical authority/work classification is independent of watch kind, so create/modify/delete share behavior; mixed batching, sorted resources, monotonic tokens, temporary/legacy suppression, missing-root, and disconnect branches are proven.
- AC-2: inventory bounds all three collections, reports provenance/truncation, exposes no URLs or write method, and preserves source bytes.
- AC-3: route absence and preserved peer services are proven over assembled OpenAPI and representative HTTP requests.

Verifier challenger: pass; no architecture, deletion-semantics, token, inventory, route-completeness, or retired-test defect found. Verifier memories were assessed before closure.
