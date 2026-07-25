---
id: 2037
title: 'P1-C6: Replace IF-015 shape completion with plan completion'
status: build
priority: high
created: 2026-07-25T02:46:59.817987+02:00
updated: 2026-07-25T02:46:59.817987+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-004
  - corrective
  - scope:mcp-kanban
  - mcp
  - interface:IF-015
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2036
ac:
  - 'AC1: The assembled MCP server registers `pick_jobs`, `start_job`, `finish_plan`,
    `finish_build`, `finish_accept`, `finish_audit`, `release_job`, and `recover_expired_claims`;
    its tool inventory contains no `finish_shape` registration or alias.'
  - 'AC2: Given strict `finish_plan` parameters, the adapter constructs `FinishPlanRequest`
    and returns `DispatchRuntime.finish_plan` success or its stable domain diagnostic
    without alternate file or task mutation.'
  - 'AC3: Given accept or audit start and completion through the assembled server,
    checkout setup precedes claim and cleanup follows finish, release, or recovery;
    setup or residual-cleanup failure returns the declared diagnostic without a current
    receipt.'
  - 'AC4: Given the engine-selected profile from #2036, MCP tools expose lifecycle
    operations only; no adapter chooses a job, profile, dependency route, or subsequent
    invocation outside `pick_jobs`.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Expose the corrected purpose-specific native completion bridge through MCP without a shape alias or duplicate scheduling authority.

## Scope
In scope: MCP parameter models, registrations, strict adapters, response/error mapping, proof-checkout composition for accept/audit, exports, and focused bridge tests.

Out of scope: DN-009 change/admission/history/request APIs, Cockpit, planner policy, and scheduling decisions.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-033; MIG-004; DN-004; IF-005; IF-015; PROOF-014.

Proof guidance: run assembled FastMCP inventory and invocation checks over real `DispatchRuntime` with contained stores and proof-checkout dependency below the bridge.