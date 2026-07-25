---
id: 2032
title: 'P1-C1: Establish modular change-package primitives'
status: build
priority: high
created: 2026-07-25T02:46:24.792896+02:00
updated: 2026-07-25T02:46:24.792896+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-001
  - corrective
  - scope:core
  - authority
  - storage
  - type:build
  - rigor:thorough
parent: 1968
depends_on: []
ac:
  - 'AC1: Given equivalent monolithic and modular fixture content, the modular parser
    returns the same delivery digest, stable identities, authored sequence order,
    and accepted-decision projection; the focused parity check compares both results.'
  - 'AC2: Given a missing, duplicate, malformed, symlinked, or escaping delivery participant,
    the parser returns the declared `ERR_CHANGE_*` diagnostic and no `ChangeRevision`;
    focused checks exercise the five classes.'
  - 'AC3: Given a loaded digest and receipts directory, admission discovery selects
    `receipts/admission-<digest-prefix>.yaml`; absent or ambiguous current receipts
    produce a health finding, while older-digest receipts remain inspectable stale
    history.'
  - 'AC4: Given a node ID and plan mapping, `NodePlanStore` prepares one contained
    OCC participant for `plans/<node-id>.yaml`; replayed bytes are idempotent and
    conflicting bytes leave the stored plan unchanged.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Provide the typed modular authority and isolated-plan storage primitives required by MIG-004 without registering a compatibility fallback.

## Scope
In scope: joined delivery parser/model, canonical digest parity, current-admission discovery from the digest-named receipt, contained `NodePlanStore` OCC participants, and path/schema/identity diagnostics.

Out of scope: live package cutover, runtime plan completion, lifecycle vocabulary, reconciliation, dispatch, and MCP.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-030; MIG-004; DN-001; IF-001; PROOF-001.

Proof guidance: run focused modular parity/path checks plus isolated-plan transaction replay, conflict, and recovery checks.