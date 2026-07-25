---
id: 2048
title: 'P7-02: Expose the frontier planner and independent plan reviewer'
status: build
priority: high
created: 2026-07-25T15:09:33.441773+02:00
updated: 2026-07-25T15:09:33.441773+02:00
tags:
  - phase-7
  - scope:agent
  - planner
  - challenger
  - orchestrator
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-006
  - packet:DN-006-PK-002
  - interface:IF-007
parent: 1983
depends_on:
  - 2047
ac:
  - 'AC-1: `planner.agent.md` requires `w-frontier-planning`, receives only the orchestrator-supplied
    started job, uses read-only repository plus native query/request tools, delegates
    only declared read-only specialists, cannot call `finish_plan` or edit admitted
    authority, and returns the exact structured workflow disposition; agent validation
    and frontmatter/body audit verify the runtime contract.'
  - 'AC-2: `planner-challenger.agent.md` is hard read-only and returns one source-grounded
    disposition/evidence row for packet completeness, admitted references, impact
    closure, dependency order, proof boundary, and material expansion, with no approval
    or lifecycle tools; hook and declaration audit verify the restriction.'
  - 'AC-3: `orchestrator.agent.md` installs planner in the subagent allowlist and
    `w-orchestration` passes the engine-owned start context to planner, maps planner
    Success fields unchanged into public `finish_plan`, maps a planner-created request
    disposition to `release_job` followed by a fresh pick, and never constructs node
    plans itself; assembled declaration inspection verifies the handoff.'
  - 'AC-4: `share/WIRING.md` agrees with executable declarations on planner skill
    loading, planner-to-challenger delegation, orchestrator-to-planner dispatch, native
    tools, and hard read-only enforcement; ecosystem validators verify no drift.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-006-PK-002`. Resolve normative behavior from `DN-006`, `IF-007`, `MOD-003`, `RISK-007`, `RISK-011`, and `PROOF-005`; this record is not specification authority.

## Outcome
Expose the native planner and hard-read-only plan reviewer, and complete the orchestrator handoff from engine-owned start context to structured planner result and public lifecycle completion.

## Envelope
In: planner and reviewer agents, orchestrator allowlist, `w-orchestration` native planner handling, exact existing native tools, and `share/WIRING.md`.

Out: engine or MCP contracts, planner proof scenarios, setup/seed propagation, builder/acceptor/auditor roles, and Specification edits.

Proof guidance: derive role loading, delegation, tools, structured result routing, request release, and write denial from executable declarations; validators must agree with WIRING.