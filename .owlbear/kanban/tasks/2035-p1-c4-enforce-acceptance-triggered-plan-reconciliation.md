---
id: 2035
title: 'P1-C4: Enforce acceptance-triggered plan reconciliation'
status: build
priority: high
created: 2026-07-25T02:46:46.300991+02:00
updated: 2026-07-25T02:46:46.300991+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-003
  - node:DN-004
  - corrective
  - scope:core
  - runtime
  - reconciliation
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2033
  - 2034
ac:
  - 'AC1: Given an initial plan job for a dependent node before predecessor implementation,
    native start eligibility permits the plan when authority, request, claim, and
    writer gates pass; predecessor acceptance is not a plan prerequisite.'
  - 'AC2: Given `finish_plan` with one bounded packet DAG, one recoverable transaction
    writes the isolated plan, plan receipt, build jobs, accept job, and immutable
    attempt event; replay duplicates no artifact and conflicting plan identity returns
    a stable diagnostic.'
  - 'AC3: Given a dependent build without current predecessor accept receipts, start
    returns `ERR_START_PREDECESSOR_INVALID` without mutation; after predecessor acceptance
    and a current superseding plan receipt, the dependency-ready build can start.'
  - 'AC4: Given successful `finish_accept`, one transaction issues the accept receipt,
    creates or releases dependent plan work, and prevents prior-plan builds from starting
    until superseding plan receipts are current.'
  - 'AC5: Given invalidation of a predecessor accept receipt, dependent reconciled
    plan/build closure becomes stale and minimum corrective plan work is created;
    a node outside that dependency closure retains current evidence.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Publish isolated plans and causally reconcile dependent plans before build, with minimum invalidation closure.

## Scope
In scope: `finish_plan`, build/accept creation, initial plan eligibility, predecessor-accept build gating, `finish_accept` dependent-plan release, currentness, invalidation, and query projection.

Out of scope: planner-agent policy, dispatch ordering/profile assignment, MCP transport, and full DN-006 completion.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-032; DEC-033; DN-003; IF-003; IF-004; PROOF-003; engine-side support for REQ-025.

Complexity waiver: five AC cover one causal lifecycle matrix; splitting its transaction and currentness assertions would bypass the public runtime boundary.

Proof guidance: run one native-runtime scenario from initial plan through publication, predecessor acceptance, reconciliation, build release, accept invalidation, and replay.