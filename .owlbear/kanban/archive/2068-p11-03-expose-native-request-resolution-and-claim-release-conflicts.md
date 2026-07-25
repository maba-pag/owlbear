---
id: 2068
title: 'P11-03: Expose native request resolution and claim release conflicts'
status: archived
priority: high
created: 2026-07-25T22:31:02.444553+02:00
updated: 2026-07-25T23:35:13.401713+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - requests
  - conflict
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-003
  - interface:IF-011
parent: 1987
depends_on:
  - 2067
ac:
  - 'AC-1: Given a pending native request and matching revision and resolution identity,
    `POST` resolution returns local resume or material design reentry; replay returns
    the persisted result, while changed identity returns HTTP 409 with current authority.'
  - 'AC-2: Given an active job and matching claim identity, `POST` release appends
    one release event and clears coordination and checkout state; replay is stable,
    while stale, non-owner, terminal, or injected transaction failure preserves complete
    state and returns a stable conflict.'
  - 'AC-3: Malformed control payloads return HTTP 422 before runtime dispatch, and
    native diagnostics preserve code, detail, lower code, target, and current holder
    or digest fields in the HTTP envelope.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-003`.

## Outcome
Cockpit exposes only native intent-specific request resolution and matching-identity claim release controls with stable conflict responses.

## Envelope
In: request resolution, claim release, strict payloads, replay, ownership and transaction diagnostics.

Out: start/finish/reject/invalidate controls, generic task transitions, SSE, frontend, cutover.

Proof guidance: cross public TestClient routes; inject failures below the route/runtime boundary and compare complete store state.

[[2026-07-25T23:31:05+02:00]]
## Builder Notes
DONE: Exposed strict intent-specific native request resolution and matching-identity claim release at the public FastAPI boundary for delivery digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

Changed files:
- `serve/cockpit/src/owlbear_cockpit/native_models.py`: strict digest, resolution, and release request bodies.
- `serve/cockpit/src/owlbear_cockpit/native_http.py`: centralized stable 409 conflict envelopes with current authority and lower diagnostics.
- `serve/cockpit/src/owlbear_cockpit/routes/native_controls.py`: request-resolution and claim-release routes over `NativeRequestRuntime` and `DispatchRuntime`.
- `serve/cockpit/src/owlbear_cockpit/main.py`: native control router assembly.
- `serve/kanban/src/owlbear_kanban/native_runtime.py`: canonical fail-closed terminal release diagnostic.
- `tests/test_cockpit_native_controls.py`: durable public-route proof over real stores, coordination, Git history, and proof checkout.

AC evidence:
- AC-1: `uv run pytest -q tests/test_cockpit_native_controls.py` proves local resume, material design reentry, exact replay, changed-identity 409, and persisted current authority (8 passed total suite).
- AC-2: the same public suite proves one release event, exact replay, coordination/checkout cleanup, and byte-for-byte preservation for non-owner, terminal, stale coordination, and injected transaction conflict. Focused canonical release regression passed (3 tests); builder challenger independently ran control plus native runtime suites (59 passed).
- AC-3: public malformed-payload cases return 422 without state mutation; conflict assertions preserve code, detail, lower code, target, current holders, and current digest.

Regression and quality:
- `uv run pytest -q tests/test_cockpit_*`: 307 passed.
- Mapped Kanban regression: 1139 passed, 10 unrelated existing failures: eight legacy `graph.yaml` fixtures conflict with intentional legacy-authority rejection and two stale tests import removed `owlbear_mcp_kanban.server.pick_tasks`.
- `uv run --package owlbear-tools lint-all`: passed.
- Editor diagnostics: clean.
- Builder challenger: pass; scope, architecture, replay/atomicity proof, and durable-test rent accepted.

Recalled builder memories were assessed in one batch before closure.

[[2026-07-25T23:34:34+02:00]]
## Verify Notes
PASS: Builder commit `c9c8f80567b8852bf155b7eacd0082c54428cb0b` satisfies all #2068 controls at the public FastAPI boundary without expanding beyond request resolution and claim release.

Independent evidence:
- `uv run pytest -q tests/test_cockpit_native_controls.py serve/kanban/tests/test_runtime_requests.py serve/kanban/tests/test_dispatch_runtime.py -k 'request_resolution or material_request or release or local_and_material_resolution or writer_conflict_and_release'`: 12 passed.
- OpenAPI inspection: exactly the two new native `POST` routes are assembled; both control bodies set `additionalProperties: false` and require their identity fields.
- Commit audit: builder SHA contains only the six declared product files, one durable public-contract test, and the #2068 task record; owned product/proof paths are clean.
- Existing generic/legacy routes remain explicitly assigned to #2069 cutover, not this packet.

AC judgment:
- AC-1: local resume, material design reentry, persisted replay, changed identity, and current authority are directly asserted over `TestClient`.
- AC-2: one event, replay, real coordination and proof-checkout cleanup, plus complete-state preservation for stale, non-owner, terminal, and transaction-abort paths are directly asserted.
- AC-3: strict 422 rejection precedes runtime mutation, and 409 envelopes preserve domain/lower diagnostics, target, holders, and current digest.

Verifier challenger: pass; no hidden mutation/replay gap, architecture violation, test-rent issue, or scope drift found. Broad-suite unrelated failures are separated from the green changed slice. Verifier memories were assessed before closure.

[[2026-07-25T23:35:13+02:00]]
## Collect Notes
ARCHIVED: #2068 is complete and archive-ready.

Closure evidence:
- Builder commit `c9c8f80567b8852bf155b7eacd0082c54428cb0b` is an ancestor of HEAD and carries the strict native controls plus public proof.
- Verifier commit `5cf17721119c9e513dd16e969d01627a81f1ba75` is an ancestor of HEAD and records independent 12-test/OpenAPI verification plus verifier-challenger pass.
- Builder public suite: 8 passed; Cockpit regression: 307 passed; focused canonical release: 3 passed; builder challenger: 59 passed; verifier focused run: 12 passed; repository lint: passed.
- All ACs have direct route-level evidence, and unrelated broad Kanban failures are explicitly outside the changed slice.
- No unresolved request, block, follow-up, or uncommitted product/proof path remains.

Collector memories were assessed before archive.
