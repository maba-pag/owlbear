---
id: 2036
title: 'P1-C5: Dispatch the plan frontier through engine authority'
status: shape
priority: high
created: 2026-07-25T02:46:52.874110+02:00
updated: 2026-07-25T07:17:09.063589+02:00
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

[[2026-07-25T07:17:09+02:00]]
## Builder Notes

- Change envelope: align `DispatchRuntime` plan profile, the orchestrator tool allowlist, and `w-orchestration` success dispatch with `planner` and `finish_plan`; exercise the assembled native MCP scenario as the cheapest causal proof.
- Files probed: `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/tests/test_dispatch_runtime.py`, `serve/mcp-kanban/tests/test_mcp_surface_contract.py`, `share/agents/orchestrator.agent.md`, and `share/skills/w-orchestration/SKILL.md`.
- Change Module Map: no explicit Engine Handoff or Change Module Map section was present in the claimed task body. The named current owners supported the planned dispatch-profile correction, but the assembled consumer exposed a prerequisite completion contract outside this task's stated scope.
- Required follow-up: none present in the claimed task context.
- Proof selected: `uv run pytest serve/mcp-kanban/tests/test_mcp_surface_contract.py::TestProof014NativeMcpScenario::test_profiles_release_recovery_and_replanning_use_native_tools -q`.
- First proof failure: `DispatchRuntime.finish_plan` passed a coordination participant tuple to `NativeRuntime._finish`, whose current interface requires a participant callback. A local probe adapter correction advanced the scenario to the acceptance completion boundary.
- Blocking proof failure: `server._finish_job` constructs `FinishJobRequest` for `finish_accept`, while `DispatchRuntime.finish_accept` delegates to `NativeRuntime._accept_participants`, which requires `FinishAcceptRequest` and its `reconciliation_plan_job_ids`. The assembled scenario fails with that assertion before the selected accept disposition can complete.
- Planning contradiction: AC3 requires the assembled orchestrator scenario to map selected `Success`, `RateLimited`, and `Crash` dispositions to matching lifecycle operations. The task explicitly excludes MCP adapter names and directs this builder not to expand into `#2037` IF-015 MCP completion. Constructing the required acceptance request is that reserved completion work; adding a fallback or alias would invent an out-of-scope compatibility path.
- AC-to-evidence: AC1 and AC5 identify the required `planner` and `finish_plan` consumer edits, but cannot be accepted independently because AC3's required causal scenario fails at the current MCP completion boundary. AC2 and AC4 were not separately run after the blocking AC3 failure, because they cannot close the missing accepted completion premise.
- Commands run: the focused assembled scenario twice; `git diff --check` on all five probe paths; scoped diff name check returned no remaining probe paths.
- Result: all probe edits were removed. No task-owned source, test, prompt, or task-record commit is appropriate on this reject.
- Memory: recalled entries were assessed; one entry ID was no longer present when assessment was submitted.
- Builder-challenger: not called because this is a planning-premise reject, not a DONE proposal.
- Required shape repair: reconcile #2036 AC3 and its out-of-scope boundary with #2037. Either make IF-015 acceptance completion available before the assembled scenario is required, or narrow #2036 proof to a current executable boundary that does not claim end-to-end acceptance completion.
