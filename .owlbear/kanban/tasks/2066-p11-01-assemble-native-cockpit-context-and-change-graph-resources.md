---
id: 2066
title: 'P11-01: Assemble native Cockpit context and change graph resources'
status: collect
priority: high
created: 2026-07-25T22:30:50.098738+02:00
updated: 2026-07-25T22:48:24.605385+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - change
  - graph
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-001
  - interface:IF-011
parent: 1987
depends_on: []
ac:
  - 'AC-1: Given loaded and malformed sibling packages, `GET /api/changes` returns
    identity-ordered typed entries with admitted digest or diagnostics; a missing
    changes directory returns an empty list.'
  - 'AC-2: Given an admitted change ID, `GET /api/changes/{change_id}` and `/graph`
    return joined authority and current isolated plans; missing or malformed authority
    returns a stable 404 or 422 envelope without filesystem paths.'
  - 'AC-3: Repeated requests reuse context only for the matching revision; a changed
    digest replaces cached authority, while runtime assembly failure returns a stable
    error without work-store or proof-checkout mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-001`.

## Outcome
Cockpit owns a cached per-change native context and typed change and graph HTTP resources over admitted modular authority.

## Envelope
In: backend dependency assembly, response models, change listing/detail, joined graph and isolated-plan projection, cache invalidation, stable load diagnostics.

Out: work/evidence routes, controls, SSE, legacy inventory, frontend, cutover.

Proof guidance: exercise public FastAPI routes with TestClient and a temporary lower engine store; do not bypass Cockpit dependency assembly.

[[2026-07-25T22:42:42+02:00]]
## Builder Notes
DONE

Implemented the cached native Cockpit context and typed change/graph resources within the shaped module map.

Changed files: `serve/cockpit/src/owlbear_cockpit/deps.py`, `serve/cockpit/src/owlbear_cockpit/native_models.py`, `serve/cockpit/src/owlbear_cockpit/routes/native_changes.py`, `serve/cockpit/src/owlbear_cockpit/main.py`, and `tests/test_cockpit_native_changes.py`.

AC-1: public `GET /api/changes` proof covers identity ordering, admitted digest, malformed sibling diagnostics, and an absent changes root. AC-2: public detail/graph proof covers joined modular authority, isolated plans, and stable sanitized 404/422 envelopes. AC-3: public requests prove same-revision reuse and changed-digest replacement; injected assembly failure proves the prior cache and native work-store file set remain unchanged.

Evidence: `uv run pytest -q tests/test_cockpit_native_changes.py` -> 6 passed; `uv run pytest -q tests/test_cockpit_*.py -m "not api"` -> 296 passed; `uv run --package owlbear-tools lint-all` -> passed with only four unrelated TODO notices. Builder challenger: pass.

[[2026-07-25T22:48:24+02:00]]
## Verify Notes
PASS

Verified builder SHA `9f954b3776f6918e010aaa9ed8cae59178dcaf89` against all three AC and the current admitted modular package. The builder commit owns exactly the shaped five-file product/proof slice plus task record, with no post-commit product drift.

Verifier strengthened the existing public graph assertion to require the real current `DN-001` isolated plan and `DN-001-PK-001` packet. After an initial challenger failure, the AC-3 proof was repaired to change the digest, construct a real replacement `NativeRuntime`/history/proof manager, fail at `DispatchRuntime`, and assert the stable 503, old cache identity, work-store file set, and proof-root file set remain unchanged.

Evidence: `uv run pytest -q tests/test_cockpit_native_changes.py` -> 6 passed; `uv run pytest -q tests/test_cockpit_*.py -m "not api"` -> 296 passed; focused verifier lint passed. Verifier challenger after repair: pass.
