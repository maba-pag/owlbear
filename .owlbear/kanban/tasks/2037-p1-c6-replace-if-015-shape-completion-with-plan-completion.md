---
id: 2037
title: 'P1-C6: Replace IF-015 shape completion with plan completion'
status: build
priority: high
created: 2026-07-25T02:46:59.817987+02:00
updated: 2026-07-25T08:09:00.923940+02:00
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
  - 2039
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
  - 'AC4: Given strict `finish_accept` parameters including `reconciliation_plan_job_ids`,
    the adapter constructs `FinishAcceptRequest` and returns `DispatchRuntime.finish_accept`
    success or its stable domain diagnostic; it never substitutes generic `FinishJobRequest`
    or alternate mutation.'
  - 'AC5: Given a lifecycle-tool invocation across the assembled MCP server using
    `start_job`, `finish_plan`, `finish_build`, `finish_accept`, `finish_audit`, `release_job`,
    or `recover_expired_claims`, the adapter performs only lifecycle delegation; it
    does not select a job, profile, dependency route, or subsequent invocation outside
    `pick_jobs`.'
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

## Shape Notes
- Connected local repair after #2036's assembled scenario exposed two ordered prerequisites: #2039 owns core completion participant composition, then this task owns strict MCP request construction and delegation.
- Removed the false dependency on #2036 and added #2039. This task remains build-ready but dependency-gated until #2039 archives.
- Added explicit `FinishAcceptRequest` ownership so a builder cannot satisfy the bridge while leaving the generic `FinishJobRequest` defect in place.
- Replaced the old forward-reference AC with an assembled invocation boundary that proves MCP adapters do not select or chain work.
- Active chain: `#2039 -> #2037 -> #2036 -> #1983`.
- Shaper challenge validated AC quality, authority, ownership, dependency closure, scenario closure, and boundary proof after the prerequisite task received a stable ID.

[[2026-07-25T08:09:00+02:00]]
## Shape Notes
- Connected local repair removed the false dependency on #2036 and added prerequisite #2039, which owns the core completion callback composition required by this task's assembled bridge proof.
- Added explicit AC4 ownership for strict `FinishAcceptRequest` construction with `reconciliation_plan_job_ids`; added AC5 for delegation-only lifecycle adapters with no scheduling authority.
- Preserved objective, scope, authority, AC1-AC3, and build status. Task remains dependency-gated until #2039 archives.
- Shaper-challenger passed the materialized `#2039 -> #2037 -> #2036 -> #1983` graph after direct Python 3.14.6 proof established the actual #2039 boundary.
