---
id: 2070
title: 'P11-05: Prove the complete graph-aware FastAPI contract'
status: verify
priority: high
created: 2026-07-25T22:31:15.592752+02:00
updated: 2026-07-26T00:06:50.321051+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - integration
  - proof
  - type:test
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-005
  - interface:IF-011
  - proof:PROOF-015
parent: 1987
depends_on:
  - 2069
ac:
  - 'AC-1: An admitted modular fixture journey through the assembled app populates
    and reads change, graph, job, request, attempt, finding, receipt, invalidation,
    activity, health, and legacy resources with strict OpenAPI schemas and bounded
    pagination.'
  - 'AC-2: Request resolution and claim release success, replay, and conflict are
    observed through HTTP plus `native-changed` SSE invalidation without bypassing
    app dependency assembly.'
  - 'AC-3: Route inventory and HTTP requests prove arbitrary task mutation and old
    lifecycle paths absent; malformed, missing, stale, and core-failure cases return
    stable HTTP envelopes with no partial store mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-005`.

## Outcome
Maintained PROOF-015 integration coverage proves IF-011 through the assembled FastAPI application.

## Envelope
In: admitted modular fixture, native resource journey, control/replay/conflict, SSE invalidation, OpenAPI contract, old-route absence.

Out: frontend, setup/cutover, complete-system proof.

Proof guidance: exercise the real FastAPI app and native engine with only a temporary engine store replacement.

[[2026-07-26T00:06:50+02:00]]
## Builder Notes
DONE: Added maintained PROOF-015 integration coverage for IF-011 through the assembled FastAPI application at delivery digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

Artifact:
- `tests/test_cockpit_native_integration.py` creates a fresh temporary Git repository, copies the admitted modular authority, seeds canonical stores through real core owners, overrides only `get_engine`, and leaves `get_native_context_cache`, runtime, dispatch, OpenAPI, uvicorn, and watchfiles assembly real.

AC evidence:
- AC-1: one assembled journey reads change, graph/plan, paged jobs, request, attempt, finding, receipt, invalidation, native activity, work/change health, and legacy inventory; asserts strict control/legacy OpenAPI schemas, max-100 pagination, stable malformed/missing/stale envelopes, and byte-for-byte read non-mutation.
- AC-2: live uvicorn plus real watchfiles captures request and release `native-changed` SSE events after HTTP controls, then proves exact replay, changed-identity/non-owner conflicts, current digest, and complete-state preservation. A real findings-path probe synchronizes watcher readiness and is removed after each stream.
- AC-3: malformed control and non-owner release fail without mutation; missing and stale reads use stable envelopes; assembled public requests prove generic board/task/activity/session/request and mutation paths return 404.

Validation:
- `uv run pytest -q tests/test_cockpit_native_integration.py`: 2 passed.
- `uv run pytest -q tests/test_cockpit_*`: 168 passed.
- `uv run --package owlbear-tools lint-all`: passed.
- Editor diagnostics: clean.
- Builder challenger: pass; accepted fixture seeding, sole dependency override, real assembly boundaries, SSE synchronization, cleanup, test rent, and full AC/resource/old-route coverage.

Builder memories were assessed before closure.
