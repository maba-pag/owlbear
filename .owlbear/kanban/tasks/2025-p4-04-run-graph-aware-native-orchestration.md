---
id: 2025
title: 'P4-04: Run graph-aware native orchestration'
status: shape
priority: high
created: 2026-07-24T16:54:49.020973+02:00
updated: 2026-07-24T18:11:14.363588+02:00
tags:
  - phase-4
  - scope:core
  - runtime
  - orchestration
  - integration
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-004
  - packet:DN-004-PK-004
parent: 1980
depends_on:
  - 2022
  - 2023
  - 2024
ac:
  - 'AC-1: The graph-aware orchestrator dispatches each job and assigned profile only
    from one fresh `DispatchRuntime.pick_waves` result, starts it through `DispatchRuntime`,
    finalizes one structured attempt outcome, and replans after consuming the wave
    without interpreting prose.'
  - 'AC-2: Crash, expiry, rate limit, stale lease, checkout setup failure, cleanup
    failure, and orphan recovery use typed dispatch, lifecycle, or health outcomes;
    observed execution contains no overlapping writers and no `accept | audit` overlap
    with a writer.'
  - 'AC-3: The maintained PROOF-014 scenario crosses public dispatch planning/start/finalization/recovery
    and proof-checkout boundaries in a temporary repository, exercising `shape | build
    | accept | audit`, exact commit materialization, cleanup, and current-state replanning.'
  - 'AC-4: The orchestrator agent, workflow skill, prompt, and `share/WIRING.md` pass
    ecosystem validation and expose native job/profile routing only; they do not route
    legacy builder/verifier/collector task stages or copy normative graph contracts.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `DN-004-PK-004`. Resolve normative behavior from `DN-004`, `IF-004`, `IF-005`, `REQ-022`, `PROOF-014`, and design §§8.6-8.7/12; this record is not specification authority.

## Outcome
Replace task-board orchestration wiring with graph-aware native job execution. The orchestrator consumes fresh engine-selected waves, dispatches exact profiles, uses proof checkout for read-only proof jobs, finalizes typed attempts once, recovers, and replans.

## Envelope
In: orchestrator agent, `w-orchestration`, `/orchestrate`, `share/WIRING.md`, and durable PROOF-014 integration tests. Preserve ecosystem loading/structure rules. Out: shaper/builder/acceptor/auditor role implementation, MCP/Cockpit surfaces, and broad legacy deletion owned by later nodes.

Proof guidance: real public dispatch and checkout boundaries in a temporary repository; replace only clock and subagent runner as PROOF-014 permits.

## Orchestration Containment

Builder crashed twice before claiming or reading the task; both returns asked what `2025` meant. The orchestrator released after the first crash and retried the same fresh-plan pair once. No product or task implementation changes were reported by either invocation. Recovery owner: agent-runtime/tool dispatch. Recovery step: restore builder task-ID dispatch recognition, clear the block, then require a fresh `pick_tasks` plan before redispatch.

## Recovery

The current session revalidated the builder contract and task path: `builder.agent.md` accepts one task ID and has `start_work`; no partial implementation or source mutation exists. Treat the prior bare-ID ambiguity as a contained invocation failure. Block cleared for one fresh-plan redispatch.

[[2026-07-24T18:11:14+02:00]]
## Builder Notes

- Change envelope: replace the orchestrator agent, `w-orchestration`, `/orchestrate`, `share/WIRING.md`, and PROOF-014 integration boundary so it dispatches native graph jobs through public engine-selected waves.
- Files changed: none.
- Change Module Map deviation: current source contradicts the packet premise. `serve/kanban/src/owlbear_kanban/dispatch.py` provides `DispatchRuntime.pick_waves`, `start`, kind-specific finish methods, and expired-claim recovery, but `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` exposes only the legacy `pick_tasks` task-board route. The orchestrator agent has only `ob-kanban/pick_tasks`, `end_work`, and `edit_task`; no public native dispatch/planning/start/finalization/recovery/proof-checkout operations or profile-runner interface exists.
- Contract classification: missing load-bearing public interface and mutation owner. Implementing AC-1 through AC-3 would require inventing the native MCP/tool API and how agents return typed outcomes, which belongs to the control-plane surface excluded from this packet and owned by the native control-plane work.
- Proof selected: targeted source boundary inspection. `serve/kanban/tests/test_dispatch_runtime.py` confirms native runtime internals, including wave selection, writer coordination, and expiry recovery, but cannot establish the public orchestrator boundary required by PROOF-014.
- Commands run: targeted repository searches and source reads only; no product edit was valid under the missing interface.
- AC-to-evidence map: AC-1 cannot be implemented because a native plan/start/finalization API is not public to the orchestrator; AC-2 cannot route typed recovery or proof-checkout outcomes through an agent boundary; AC-3 cannot cross a nonexistent public dispatch boundary; AC-4 identifies the current legacy routing that must be replaced once the public native interface is available.
- Current failure keys: none.
- Builder-challenger: not run; a DONE claim was not proposed.
- Follow-up risk: shape must either depend this packet on the native control-plane interface task or explicitly assign the missing public dispatch/profile-runner contract to this packet with a concrete module map and interface authority.
