---
id: 2005
title: 'P3-06: Link runtime requests to dependent work'
status: build
priority: medium
created: 2026-07-22T21:59:06.804749+02:00
updated: 2026-07-23T11:29:26.796193+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - requests
  - decisions
  - actions
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-006
parent: 1979
depends_on:
  - 2002
  - 2003
ac:
  - 'AC-1: Given decision or action input, request creation requires change/digest
    plus optional graph-target and job references; decision options preserve label,
    pros, cons, risks, recommendation, confidence, and rationale, while action requests
    preserve exact returned evidence and resume condition; unresolved references create
    no request or job link.'
  - 'AC-2: Given a pending request, only its linked jobs report request-blocked while
    unrelated jobs retain prior readiness; exact create replay and concurrent resolve
    produce one request identity and one immutable resolution without partial job
    links.'
  - 'AC-3: Given a local resolution, the transaction unblocks only the linked dependent
    slice and returns its invalidation intent; given a material authority resolution,
    it leaves linked jobs blocked or stale and returns design re-entry against the
    current change revision without mutating authority.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-006`

## Outcome
Structured decision and action requests attach to one change revision and optional graph target or job; pending requests block only linked work, and resolution either resumes that slice or records material design re-entry.

## Scope
In scope: native request and option/action contracts; pending/resolved immutable storage; create/list/show/resolve operations; job block references; local versus material resolution disposition; transaction and replay behavior.

Out of scope: designer `askQuestions`, authority mutation, MCP and Cockpit request APIs, corrective job generation, broad invalidation closure, and legacy task-scoped request changes.

## Current Foundation And Ownership
Build a native request owner over the transaction and job-lifecycle boundaries from preceding packets. Legacy `request_models.py` and current request routes remain bootstrap-carrier code until DN-009/DN-012.

## Authority
Resolve behavior from `REQ-015`, `REQ-016`, `KEEP-006`, `IF-003`, `PROOF-003`, and design section 11. Material authority changes return a typed design re-entry disposition rather than editing authority inside the runtime.

Proof guidance: exercise public native request operations over temporary change/work roots, including linked versus unrelated jobs, exact replay, concurrent resolution, local resume, and material re-entry.

[[2026-07-23T11:29:26+02:00]]
## Shape Notes
- Repair classification: connected dependency-closure audit; no operative contract change required.
- Dependency closure: #2005 introduces its own native request contracts/storage and consumes the transaction kernel and job/claim foundation from #2002/#2003. AC-2 and AC-3 already require atomic request identity/resolution with linked job references, no partial links, and scoped invalidation intent. No sibling or descendant producer is required.
- Ownership boundary: request activity remains request/job-link mutation in this task; broad invalidation closure and corrective jobs remain #2006. Material authority resolution still returns design re-entry without mutating authority.
- Board audit: remains `build`, parent #1979, dependencies #2002 and #2003, and is correctly dependency-blocked.
