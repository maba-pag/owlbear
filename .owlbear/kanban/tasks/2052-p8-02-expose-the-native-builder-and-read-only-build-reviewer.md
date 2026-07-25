---
id: 2052
title: 'P8-02: Expose the native builder and read-only build reviewer'
status: build
priority: high
created: 2026-07-25T16:14:20.905544+02:00
updated: 2026-07-25T16:14:20.905544+02:00
tags:
  - phase-8
  - scope:agent
  - builder
  - reviewer
  - orchestrator
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-007
  - packet:DN-007-PK-002
  - interface:IF-008
parent: 1984
depends_on:
  - 2051
ac:
  - 'AC-1: In explicit native mode, `builder.agent.md` requires `w-packet-building`,
    accepts only orchestrator-supplied started build context, exposes existing edit,
    proof, commit, and native read tools, delegates to `build-reviewer`, cannot call
    native finish, release, start, or pick operations, and returns one workflow disposition;
    declaration audit verifies the contract while bootstrap task mode remains available.'
  - 'AC-2: `build-reviewer.agent.md` is hard read-only with `deny-writes.py`, a distinct
    model, no lifecycle or edit tools, and source-grounded rows for authority and
    packet obligations, diff and changed paths, proof, commit context, scope, and
    typed findings; hook and declaration audit verifies omitted context is malformed
    and the reviewer cannot repair its findings.'
  - 'AC-3: `w-orchestration` sends only the successful start result to builder, forwards
    `BuilderSuccess` fields unchanged to public `finish_build`, and maps `SpecificationReentry`,
    `CommitFailed`, or `BuildBlocked` to identity-preserving `release_job` plus halt
    and report; artifact inspection verifies no failed disposition issues a receipt
    or creates corrective work.'
  - 'AC-4: `share/WIRING.md`, `h-agent-structure`, and `validate_agents.py` agree
    with executable builder and reviewer loading, delegation, native tools, result
    routing, ND3 metadata, and write denial; ecosystem validators verify no drift.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-007-PK-002`. Resolve normative behavior from `DN-007`, `IF-008`, `NEG-006`, `NEG-009`, `RISK-008`, and `PROOF-006`; this record is not specification authority.

## Outcome
Expose the native outcome builder and hard-read-only build reviewer, and complete the orchestrator handoff from engine-owned build start context to finish or fail-closed release.

## Envelope
In: builder and reviewer declarations, orchestrator allowlist and workflow routing, existing native tools, ND3 enforcement, and WIRING synchronization.

Out: runtime or MCP semantics, proof scenarios, acceptor or auditor roles, setup or seed propagation, and removal of legacy task mode during bootstrap.

Proof guidance: validate executable declarations, reviewer write denial, structured result routing, public tool schemas, and WIRING agreement.