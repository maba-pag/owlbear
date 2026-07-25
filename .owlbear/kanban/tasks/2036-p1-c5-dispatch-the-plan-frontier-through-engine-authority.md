---
id: 2036
title: 'P1-C5: Dispatch the plan frontier through engine authority'
status: build
priority: high
created: 2026-07-25T02:46:52.874110+02:00
updated: 2026-07-25T02:46:52.874110+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-004
  - corrective
  - scope:core
  - scope:copilot
  - dispatch
  - orchestration
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2035
ac:
  - 'AC1: Given initially eligible plan jobs in unsorted storage order, `pick_jobs`
    returns stable delivery-node topological order with profile `planner`; build,
    accept, and audit entries retain their admitted profiles.'
  - 'AC2: Given concurrent starts, plan and build share one writer lease while accept
    and audit overlap no writer; conflicting starts return the stable coordination
    diagnostic without job or attempt mutation.'
  - 'AC3: Given one engine-selected job, the orchestrator invokes its assigned profile
    once, maps `Success | RateLimited | Crash` to the matching lifecycle operation,
    and returns before a repick; causal proof bypassing the returned disposition fails.'
  - 'AC4: Given a dependent build before reconciliation gates pass, `pick_jobs` omits
    it as predecessor-invalid; after the superseding plan receipt becomes current,
    the same query can select it without prose routing.'
  - 'AC5: After plan cutover, `orchestrator.agent.md` lists `ob-kanban/finish_plan`
    and not `finish_shape`; `w-orchestration` maps profile `planner` success to `finish_plan`
    and has no native `shaper` profile. Direct inspection and the assembled scenario
    verify both consumers.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Make the engine picker own plan/build/accept/audit topology, profiles, readiness, coordination, and one-invocation orchestration results.

## Scope
In scope: `DispatchRuntime` kinds, profiles, readiness, topological ordering, writer/readers, orchestration agent allowlist, workflow mapping, and causal lifecycle result handling.

Out of scope: MCP adapter names, planner implementation, and the complete DN-009 API.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-027; DEC-031; DEC-033; DN-004; MOD-003; IF-004; IF-015; PROOF-014.

Complexity waiver: the fifth AC closes the admitted production-orchestrator consumer edge inside the same assembled orchestration boundary.

Proof guidance: run dispatch topology/readiness/coordination checks and the assembled orchestrator scenario with only the selected runner replaced below that boundary.