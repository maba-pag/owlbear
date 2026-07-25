---
id: 2034
title: 'P1-C3: Replace native shape identity with plan admission'
status: build
priority: high
created: 2026-07-25T02:46:39.499546+02:00
updated: 2026-07-25T02:46:39.499546+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-002
  - node:DN-003
  - corrective
  - scope:core
  - admission
  - runtime
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2032
ac:
  - 'AC1: Given one admitted 14-node revision, `AdmissionTransaction` publishes one
    admission receipt plus 14 plan jobs in authored node order; interrupted publication
    recovers both participants or exposes neither.'
  - 'AC2: Given active native job, receipt, request, corrective-route, and query parsing,
    `plan` is accepted where node planning applies and `shape` returns the existing
    kind or schema diagnostic; historical snapshot bytes remain inspectable without
    becoming current records.'
  - 'AC3: Public Python exports and runtime requests expose `PlanJob`, `FinishPlanRequest`,
    and plan-job generation; maintained active source and fixtures contain no `ShapeJob`,
    `FinishShapeRequest`, `plan_shape_jobs`, shape job kind, or shape receipt discriminator.'
  - 'AC4: Given replay of the same admission identity, the stored plan-job generation
    is returned without duplication; changed digest, evidence, or job identities return
    the stable admission conflict or validation result without mutation.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Make active native job, receipt, request, corrective-route, query, and admission contracts plan-only while preserving legacy bytes as inert history.

## Scope
In scope: `PlanJob`, job and receipt kinds, `FinishPlanRequest`, admission generation, corrective routes, request/query projections, exports, maintained fixtures, and focused tests.

Out of scope: isolated plan write wiring, reconciliation, dispatch, and MCP.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-033; MIG-004; DN-002; DN-003; IF-002; IF-003; PROOF-002; PROOF-003.

Proof guidance: run focused admission atomicity/replay plus active-schema and legacy-history checks.