---
id: 2036
title: 'P1-C5: Dispatch the plan frontier through engine authority'
status: build
priority: high
created: 2026-07-25T02:46:52.874110+02:00
updated: 2026-07-25T08:09:07.723984+02:00
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
  - 2037
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
In scope: `DispatchRuntime` kinds, profiles, readiness, topological ordering, writer/readers at start, orchestration agent allowlist, workflow mapping, and selected-disposition-to-lifecycle-operation routing.

Out of scope: `DispatchRuntime._finish` participant-factory and holder-release transaction composition owned by #2039, MCP adapter names, planner implementation, and the complete DN-009 API.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-027; DEC-031; DEC-033; DN-004; MOD-003; IF-004; IF-015; PROOF-014.

Complexity waiver: the fifth AC closes the admitted production-orchestrator consumer edge inside the same assembled orchestration boundary.

Proof guidance: run dispatch topology/readiness/coordination checks and the assembled orchestrator scenario with only the selected runner replaced below that boundary.

[[2026-07-25T07:17:09+02:00]]
## Builder Notes
- Change envelope: align `DispatchRuntime` plan profile, the orchestrator tool allowlist, and `w-orchestration` success dispatch with `planner` and `finish_plan`; exercise the assembled native MCP scenario as the cheapest causal proof.
- Files probed: `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/tests/test_dispatch_runtime.py`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py`, `share/agents/orchestrator.agent.md`, and `share/skills/w-orchestration/SKILL.md`.
- First proof failure: `DispatchRuntime.finish_plan` passed a coordination participant tuple to `NativeRuntime._finish`, whose current interface requires a participant callback.
- Blocking proof failure after a local probe: `server._finish_job` constructed generic `FinishJobRequest` for `finish_accept`, while `DispatchRuntime.finish_accept` requires `FinishAcceptRequest.reconciliation_plan_job_ids`.
- All probe edits were removed. The task returned to shape because its assembled proof required completion work outside the accepted task scope.
- Required shape repair: reconcile #2036 AC3 with the core completion and strict MCP adapter prerequisites before redispatch.

## Shape Notes
- Classification: prescribed connected split and dependency repair after the builder's assembled boundary exposed two independent prerequisite failure domains.
- #2039 exclusively owns `_finish` participant-factory and coordination-holder transaction composition. This task retains picker topology/profile/readiness/start coordination and selected-disposition routing.
- #2037 owns strict MCP request construction and delegation. Replaced the obsolete #2035 dependency with #2037, making #2039 transitive through #2037.
- Active chain: `#2039 -> #2037 -> #2036 -> #1983`.
- Failure key `#2036-AC3/accept-completion-prerequisite` resolves when #2039 supplies working completion composition and #2037 supplies strict `FinishAcceptRequest` construction; the existing assembled PROOF-014 scenario remains this task's causal discriminator.
- Shaper challenge validated the split's AC quality, current-source ownership, dependency closure, scenario closure, and boundary proof after task #2039 was materialized.

[[2026-07-25T08:09:07+02:00]]
## Shape Notes
- Rejection source: builder's assembled PROOF-014 scenario found a core participant-callback defect followed by a strict accept-request MCP defect. Classification: prescribed connected split/dependency repair; product behavior and admitted authority are unchanged.
- Created prerequisite #2039 for `DispatchRuntime._finish` participant-factory and holder-release transaction composition; carved that primitive out of this task's scope.
- Replaced obsolete dependency #2035 with #2037. #2037 depends on #2039, so this task's assembled orchestration proof receives both prerequisites in order.
- Failure key `#2036-AC3/accept-completion-prerequisite` is resolved by the live graph `#2039 -> #2037 -> #2036`; #1983 now depends on #2036 and remains parked behind the completed chain.
- Current-source checks: Python 3.14.6 imports and compiles all named modules; the assembled TestProof014 scenario executes and fails exactly where dispatch passes a tuple as native participant callback. This disconfirmed the challenger's temporary syntax concern.
- Shaper-challenger passed the materialized graph for readiness, authority, invariant ownership, dependency/scenario closure, boundary proof, and fidelity.
- Memory assessment: all recalled entries assessed; active-repository guidance applied.
- Resulting route: advance to build, dependency-gated until #2039 and #2037 archive.
