---
id: 2068
title: 'P11-03: Expose native request resolution and claim release conflicts'
status: verify
priority: high
created: 2026-07-25T22:31:02.444553+02:00
updated: 2026-07-25T23:31:05.395969+02:00
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
archival_reason:
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
