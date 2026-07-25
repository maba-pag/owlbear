---
id: 2067
title: 'P11-02: Expose paged native work evidence and health resources'
status: archived
priority: high
created: 2026-07-25T22:30:56.487007+02:00
updated: 2026-07-25T23:05:04.550669+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - jobs
  - evidence
  - health
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-002
  - interface:IF-011
  - proof:PROOF-015
parent: 1987
depends_on:
  - 2066
ac:
  - 'AC-1: Given current native state plus cursor and limit inputs, nested jobs, attempts,
    findings, receipts, requests, activity, and health routes return core ordering
    and `next_cursor`; stale cursors return HTTP 409 `ERR_CURSOR_STALE`, and bad limits
    return 422.'
  - 'AC-2: Given a job, finding, or receipt identity, show routes return the authority-composed
    record; an absent identity returns its stable resource-specific 404 code without
    a filesystem path.'
  - 'AC-3: Given supersession receipts and corrective jobs, invalidation reads expose
    the affected closure, while work and change health expose bounded integrity and
    currentness findings without mutating authority or work stores.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-002`.

## Outcome
Cockpit exposes bounded typed reads for native jobs, attempts, findings, receipts, requests, history, invalidation closure, and health.

## Envelope
In: native read routes, show routes, cursor/limit validation, supersession projection, work and change health.

Out: lifecycle controls, SSE, legacy inventory, frontend, cutover.

Proof guidance: drive public TestClient routes over a real NativeRuntime with a temporary lower store.

[[2026-07-25T23:01:36+02:00]]
## Builder Notes
DONE

Implemented bounded typed native jobs, attempts, findings, receipts, requests, activity, invalidation, work-health, and change-health HTTP reads. Pages delegate to `NativeRuntime`; show routes delegate to canonical stores and `project_job`; invalidation is projected from the persisted supersession receipt and impact closure; canonical change health is bounded at the HTTP response boundary.

Changed files: `serve/cockpit/src/owlbear_cockpit/native_models.py`, `serve/cockpit/src/owlbear_cockpit/routes/native_changes.py`, `serve/cockpit/src/owlbear_cockpit/routes/native_work.py`, `serve/cockpit/src/owlbear_cockpit/main.py`, and `tests/test_cockpit_native_work.py`.

AC-1: public TestClient proof covers numeric job ordering, continuation, all nested `next_cursor` fields, stale 409, and limit 422. AC-2: job/finding/receipt/request show proof covers authority composition and resource-specific missing errors without paths. AC-3: a real supersession and corrective job expose receipt/impact closure; deliberate work and change defects produce bounded findings; byte snapshots prove all GETs leave work and authority files unchanged.

Evidence: focused suite 3 passed; Cockpit backend regression 299 passed; all-file lint passed. Builder challenger: pass.

[[2026-07-25T23:04:08+02:00]]
## Verify Notes
PASS

Verified builder SHA `9e2369d7710792caaa00acc976782ef62c70ace2` against the admitted authority and all three AC. Exact commit ownership matches the shaped source/proof slice, with no product drift or resolved requests.

Verifier added two test-only linkage assertions: the corrective job ID persisted in the supersession receipt must appear in the public job collection, and the custom bounded change-health route must itself return 409 `ERR_CURSOR_STALE` for a stale cursor. Both pass through public TestClient routes over the real seeded runtime.

Evidence: focused native-work suite 3 passed; builder Cockpit regression 299 passed; focused verifier lint passed. Verifier challenger: pass.

[[2026-07-25T23:05:04+02:00]]
## Collect Notes
ARCHIVED

Latest Verify Notes are PASS with every AC tied to public route evidence and verifier challenger pass. Collector reran `uv run pytest -q tests/test_cockpit_native_work.py` at verifier SHA `22f46accd07bc93ee04b0ec015ea0f099d89d68e`: 3 passed. Packet scope is closed; parent #1987 remains pending #2068-#2070.
