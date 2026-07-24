---
id: 2024
title: 'P4-03: Isolate exact-commit proof checkouts'
status: build
priority: high
created: 2026-07-24T16:50:58.417043+02:00
updated: 2026-07-24T16:50:58.417043+02:00
tags:
  - phase-4
  - scope:core
  - runtime
  - proof-checkout
  - containment
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-004
  - packet:DN-004-PK-003
parent: 1980
depends_on:
  - 1979
ac:
  - 'AC-1: Given an eligible `accept | audit` job and resolvable commit, `ProofCheckoutManager.materialize`
    returns a contained job-specific checkout at that commit; tracked files reject
    writes and its manifest records job, target, commit, environment facts, and declared
    replacements.'
  - 'AC-2: Given traversal identity, a symlinked proof path, missing commit, or failed
    Git setup, materialization returns `ERR_PROOF_PATH_UNSAFE | ERR_PROOF_COMMIT_MISSING
    | ERR_PROOF_SETUP_FAILED` and leaves no usable checkout outside the proof root.'
  - 'AC-3: Cleanup of a materialized checkout is idempotent. A contained checkout
    left after interrupted cleanup appears as `ERR_WORK_PROOF_CHECKOUT_ORPHAN` in
    bounded work health, and orphan cleanup removes it without changing unrelated
    paths.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `DN-004-PK-003`. Resolve normative behavior from `DN-004`, `IF-005`, `RISK-004`, `PROOF-014`, and accepted `DEC-018`; this record is not specification authority.

## Outcome
Add a deep `ProofCheckoutManager` that owns contained exact-commit materialization, read-only tracked files, environment/replacement manifests, idempotent cleanup, and bounded orphan health/cleanup.

## Envelope
In: new `serve/kanban/src/owlbear_kanban/proof_checkout.py`, work-health integration, exports, focused temporary-repository tests. Out: acceptor/auditor behavior, dispatch waves, MCP, Cockpit, and cutover removal.

Proof guidance: real temporary Git repository; replace no Git or filesystem behavior. Prove exact HEAD, containment/no-follow policy, read-only tracked files, cleanup, and orphan health.